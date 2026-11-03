"""Materialise the local atlas and score LH-H-004 once.

A second run inserts nothing when the content checksum matches.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import psycopg

from aqil_research.long_horizon.events.definition import event_definition_hash
from aqil_research.long_horizon.events.identify import ListingSeries
from aqil_research.long_horizon.events.reproduce import reproduce_outcome
from aqil_research.long_horizon.events.scan import load_prices
from aqil_research.long_horizon.money import decimal_text, sha256_document
from aqil_research.long_horizon.pilot import (
    LOCAL_ETF_URL,
    LOCAL_RESEARCH_URL,
    PilotError,
    assert_loopback,
    git_commit,
    library_versions,
    repo_root,
)
from aqil_research.long_horizon.state_atlas.build import (
    AtlasBatch,
    AtlasBuildError,
    StoredEvent,
    StoredSeries,
    VintageRow,
    anchor_identity,
    checksum_lines,
    compile_listing,
    compile_releases,
    content_checksum,
    group_episodes,
    link_events,
    method_inventory_payload,
)
from aqil_research.long_horizon.state_atlas.features import EconomicPoint, period_bound
from aqil_research.long_horizon.state_atlas.package_hash import atlas_code_hash
from aqil_research.long_horizon.state_atlas.rule import (
    SymbolSequence,
    assign_sequence_status,
    median,
    reconcile_checksum,
    summarise,
)
from aqil_research.long_horizon.state_atlas.specification import (
    ATLAS_SPECIFICATION,
    EVT_DEFINITION_HASH,
    POINT_IN_TIME_DATASET,
    SEQUENCE_EXPERIMENT,
    SEQUENCE_HYPOTHESIS,
    SPECIFICATION_ID,
    SPECIFICATION_VERSION,
    assert_sequence_status_allowed,
    atlas_specification_hash,
    sequence_experiment_hash,
)
from aqil_research.long_horizon.state_atlas.store import (
    copy_atlas,
    store_chain,
    store_claim_anchors,
    store_coverage,
    store_dependency,
    store_specification,
)
from aqil_research.methods.registry import default_method_registry

REPRODUCTION = "uv run python -m aqil_research.long_horizon.state_atlas"
REQUIRED_COUNTS = {
    "events": 1749,
    "eligible": 1700,
    "condition_false": 1553,
    "condition_true": 147,
    "advances": 631,
    "both": 62,
    "false_positives": 85,
    "status": "inconclusive",
}


class AtlasRunError(RuntimeError):
    """The atlas cannot be stored on this database."""


def _require_lh_x_002() -> dict[str, object]:
    reproduced = reproduce_outcome()
    if reproduced["status"] != REQUIRED_COUNTS["status"]:
        raise AtlasRunError("LH-X-002 did not reproduce as inconclusive")
    if int(reproduced["event_count"]) != REQUIRED_COUNTS["events"]:
        raise AtlasRunError("LH-X-002 event count did not reproduce")
    with psycopg.connect(LOCAL_RESEARCH_URL) as connection:
        connection.read_only = True
        row = connection.execute(
            """
            select
              count(*)::int,
              count(*) filter (where not condition_met)::int,
              count(*) filter (where condition_met)::int,
              count(*) filter (where outcome_advance)::int,
              count(*) filter (where condition_met and outcome_advance)::int,
              count(*) filter (where condition_met and not outcome_advance)::int
            from research.comparison_periods
            where experiment_id = 'LH-E-002' and experiment_version = 1
            """
        ).fetchone()
    if row is None:
        raise AtlasRunError("LH-E-002 comparison periods are missing")
    eligible, false_rows, true_rows, advances, both, false_positives = row
    actual = {
        "eligible": eligible,
        "condition_false": false_rows,
        "condition_true": true_rows,
        "advances": advances,
        "both": both,
        "false_positives": false_positives,
    }
    for key, expected in REQUIRED_COUNTS.items():
        if key in {"events", "status"}:
            continue
        if actual[key] != expected:
            raise AtlasRunError(f"LH-X-002 {key} is {actual[key]}, not {expected}")
    return {
        "execution_id": "LH-X-002",
        "status": "inconclusive",
        "not_reestimated": True,
        **REQUIRED_COUNTS,
    }


def _fingerprint(connection: psycopg.Connection) -> str:
    hypotheses = connection.execute(
        """
        select hypothesis_id, proposition, initial_status
        from research.hypotheses
        where hypothesis_id in ('LH-H-001', 'LH-H-002', 'LH-H-003')
        order by hypothesis_id
        """
    ).fetchall()
    executions = connection.execute(
        """
        select execution_id, state, validation_status, artifact_sha256
        from research.experiment_executions
        where execution_id in ('LH-X-001', 'LH-X-002', 'LH-X-003')
        order by execution_id
        """
    ).fetchall()
    event_hash = connection.execute(
        """
        select specification_hash
        from research.event_definitions
        where definition_id = 'EVT-DEF-001' and version = 1
        """
    ).fetchone()
    return sha256_document(
        {
            "hypotheses": [list(row) for row in hypotheses],
            "executions": [list(row) for row in executions],
            "event_hash": None if event_hash is None else event_hash[0],
        }
    )


def _load_series(connection: psycopg.Connection) -> tuple[list[StoredSeries], int, int, int]:
    rows = connection.execute(
        """
        select distinct on (o.dataset_id, o.period_start)
          o.dataset_id, o.period_start, o.period_end, o.frequency, o.unit,
          o.seasonal_adjustment, o.raw_value
        from research.economic_observations o
        join research.source_retrievals r on r.retrieval_id = o.retrieval_id
        where r.collection_mode = 'live'
          and o.series_provenance = 'latest_revised'
          and o.quality_status = 'observed'
        order by o.dataset_id, o.period_start, o.provider_vintage_date desc, o.retrieved_at desc
        """
    ).fetchall()
    counts = connection.execute(
        """
        select
          count(*) filter (
            where r.collection_mode = 'live' and o.series_provenance = 'latest_revised'
          )::int,
          count(*) filter (
            where o.dataset_id = 'bea.vintage.real_gdp.pct_preceding'
              and o.series_provenance = 'provider_vintage'
          )::int,
          count(*) filter (where o.dataset_id = 'fred.alfred.UNRATE')::int,
          count(*) filter (where o.dataset_id = 'census.m3.adv.MDM.NO')::int
        from research.economic_observations o
        join research.source_retrievals r on r.retrieval_id = o.retrieval_id
        """
    ).fetchone()
    if counts is None:
        raise AtlasRunError("economic counts are missing")
    grouped: dict[str, list[EconomicPoint]] = defaultdict(list)
    meta: dict[str, tuple[str, str, str]] = {}
    for dataset_id, period_start, period_end, frequency, unit, seasonal, raw_value in rows:
        grouped[dataset_id].append(
            EconomicPoint(period_start, period_end, frequency, Decimal(raw_value))
        )
        meta[dataset_id] = (frequency, unit, seasonal)
    series: list[StoredSeries] = []
    for dataset_id in sorted(grouped):
        points = tuple(sorted(grouped[dataset_id], key=lambda item: item.period_start))
        frequency, unit, seasonal = meta[dataset_id]
        bounds = tuple(
            period_bound(point.period_start, point.period_end, point.frequency) for point in points
        )
        if list(bounds) != sorted(bounds):
            raise AtlasBuildError(f"{dataset_id} period bounds are not in period order")
        series.append(StoredSeries(dataset_id, frequency, unit, seasonal, points, bounds))
    live, bea, alfred, census = counts
    if alfred != 0 or census != 0:
        raise AtlasRunError("ALFRED or Census advance orders became stored; the inventory stops")
    return series, live, bea, alfred


def _load_vintages(connection: psycopg.Connection) -> list[VintageRow]:
    rows = connection.execute(
        """
        select period_start, period_end, provider_vintage_date, raw_value
        from research.economic_observations
        where dataset_id = %s
          and series_provenance = 'provider_vintage'
          and quality_status = 'observed'
          and provider_vintage_date is not null
          and source_release_at is not null
          and period_end is not null
        order by period_start, provider_vintage_date
        """,
        (POINT_IN_TIME_DATASET,),
    ).fetchall()
    return [
        VintageRow(period_start, period_end, release, Decimal(raw_value))
        for period_start, period_end, release, raw_value in rows
    ]


def _load_events(connection: psycopg.Connection) -> list[StoredEvent]:
    rows = connection.execute(
        """
        select event_id, symbol, family, start_date, end_date
        from research.market_events
        where definition_id = 'EVT-DEF-001' and definition_version = 1
        order by event_id
        """
    ).fetchall()
    return [StoredEvent(*row) for row in rows]


def _inventory(
    batch: AtlasBatch,
    *,
    series: list[StoredSeries],
    listings: list[ListingSeries],
    hashes: dict[str, str],
    fx_count: int,
    distribution_tables: tuple[str, ...],
    inrg_count: int,
    recorded_at: datetime,
) -> None:
    stored = {curve.dataset_id for curve in series}
    for curve in series:
        batch.inventory.append(
            (
                SPECIFICATION_ID,
                SPECIFICATION_VERSION,
                "economic_series",
                curve.dataset_id,
                {
                    "dataset_id": curve.dataset_id,
                    "frequency": curve.frequency,
                    "unit": curve.unit,
                    "seasonal_adjustment": curve.seasonal_adjustment,
                    "rows": len(curve.points),
                    "provenance": "latest_revised",
                    "clock": "retrospective_latest_revised_release_lag_unknown",
                    "usable_as_decision_input": False,
                    "release_lag": "unknown",
                },
                False,
                recorded_at,
            )
        )
    for method in default_method_registry().registered():
        payload = method_inventory_payload(method, stored)
        if payload["vintage_class"] != "latest_revised" or payload["point_in_time"] is not False:
            raise AtlasRunError("a registered method was labelled point-in-time")
        batch.inventory.append(
            (
                SPECIFICATION_ID,
                SPECIFICATION_VERSION,
                "method",
                str(payload["method_id"]),
                payload,
                False,
                recorded_at,
            )
        )
    for listing in listings:
        batch.inventory.append(
            (
                SPECIFICATION_ID,
                SPECIFICATION_VERSION,
                "listing",
                listing.symbol,
                {
                    "symbol": listing.symbol,
                    "currency": listing.currency,
                    "price_type": "adjusted_close",
                    "adjustment_status": "adjusted",
                    "rows": len(listing.closes),
                    "first_session": listing.dates[0].isoformat(),
                    "last_session": listing.dates[-1].isoformat(),
                    "series_sha256": hashes[listing.symbol],
                    "total_return": "blocked",
                },
                False,
                recorded_at,
            )
        )
    unavailable = {
        "surprise": "blocked_no_consensus",
        "euna_relative_performance": "blocked_no_foreign_exchange",
        "total_return": "blocked",
        "distributions": "blocked",
        "fx_observations": f"row_count:{fx_count}",
        "inrg_prices": f"row_count:{inrg_count}",
        "CENSUS_ADV_DURABLE_ORDERS": "unavailable_input",
        "fred.alfred.UNRATE": "unstored",
        "full_sample_z_score": "refused",
        "volatility_transition": "absent_from_evt_def_001_version_1",
        "failed_recovery": "absent_from_evt_def_001_version_1",
        "trend_reversal": "absent_from_evt_def_001_version_1",
    }
    for key, reason in unavailable.items():
        batch.inventory.append(
            (
                SPECIFICATION_ID,
                SPECIFICATION_VERSION,
                "unavailable_dimension",
                key,
                {
                    "dimension": key,
                    "status": reason,
                    "distribution_tables": list(distribution_tables),
                },
                False,
                recorded_at,
            )
        )


def _score(batch: AtlasBatch, listings: list[ListingSeries]) -> dict[str, Any]:
    grouped: dict[str, list[Any]] = defaultdict(list)
    for decision in batch.decisions:
        grouped[decision.symbol].append(decision)
    summaries: list[SymbolSequence] = []
    for listing in listings:
        rows = grouped.get(listing.symbol, [])
        summaries.append(
            summarise(rows) if rows else SymbolSequence(listing.symbol, 0, 0, 0, 0, 0, 0, 0)
        )
    status, reasons = assign_sequence_status(summaries)
    assert_sequence_status_allowed(status)
    qualifying = [item for item in summaries if item.qualifies()]
    if len(qualifying) < 5:
        medians: dict[str, str] = {
            "incremental": "not_defined",
            "sequence_lift": "not_defined",
            "event_share": "not_defined",
        }
    else:
        medians = {
            "incremental": decimal_text(median([item.incremental() for item in qualifying])),
            "sequence_lift": decimal_text(median([item.sequence_lift() for item in qualifying])),
            "event_share": decimal_text(median([item.event_share() for item in qualifying])),
        }
    false_positives = sorted(
        (row.symbol, row.decision_date.isoformat())
        for row in batch.decisions
        if row.sequence and not row.outcome_advance
    )
    missed = sorted(
        (row.symbol, row.decision_date.isoformat())
        for row in batch.decisions
        if row.outcome_advance and not row.sequence
    )
    sequence_dates = sorted(
        (row.symbol, row.decision_date.isoformat()) for row in batch.decisions if row.sequence
    )
    pooled = {
        "eligible": sum(item.eligible for item in summaries),
        "sequence": sum(item.sequence for item in summaries),
        "sequence_and_advance": sum(item.sequence_and_advance for item in summaries),
        "control": sum(item.control for item in summaries),
        "control_and_advance": sum(item.control_and_advance for item in summaries),
        "component_b_alone": sum(item.component for item in summaries),
        "advances": sum(item.advances for item in summaries),
        "false_positives": len(false_positives),
        "missed_advances": len(missed),
    }
    proposition = (
        f"The preregistered category C sequence is {status}. "
        f"{' '.join(reasons)} "
        "False positives and missed advances are retained. Overlapping months and "
        "shared equity paths are dependence limits, not a causal claim. This is not "
        "an investment claim. publication_allowed is false."
    )
    return {
        "schema_version": "1.0",
        "experiment_id": "LH-E-004",
        "execution_id": "LH-X-004",
        "status": status,
        "reasons": list(reasons),
        "medians": medians,
        "qualifying_symbols": len(qualifying),
        "pooled": pooled,
        "false_positive_dates": [list(item) for item in false_positives],
        "missed_advance_dates": [list(item) for item in missed],
        "sequence_decision_dates": [list(item) for item in sequence_dates],
        "dependence_limits": [
            "Overlapping month-ends are not independent trials.",
            "Listings share equity paths.",
            "The inspected history is not an untouched holdout.",
        ],
        "counterexamples_preserved": True,
        "lh_x_002_citation": {
            "execution_id": "LH-X-002",
            "status": "inconclusive",
            "not_reestimated": True,
        },
        "portfolio_simulator": "not_called",
        "catalogue_scenarios_executed": 0,
        "publication_allowed": False,
        "proposition": proposition,
    }


def _claim_anchors(batch: AtlasBatch, recorded_at: datetime) -> list[tuple[object, ...]]:
    rows: list[tuple[object, ...]] = []
    for decision in batch.decisions:
        if decision.sequence:
            role = "sequence_decision"
        elif decision.condition_b_alone and not decision.prior_a:
            role = "primary_control"
        else:
            role = "eligible_month_end"
        rows.append(
            (
                anchor_identity(decision.symbol, "listing_month_end", decision.decision_date),
                "LH-C-004",
                1,
                role,
                False,
                recorded_at,
            )
        )
    return rows


def _coverage(batch: AtlasBatch, digest: str, recorded_at: datetime) -> list[tuple[object, ...]]:
    censored = sum(1 for row in batch.outcomes if row[4] == "censored")
    metrics = {
        "decision_anchors": len(batch.anchors),
        "state_observations": len(batch.states),
        "outcome_measures": len(batch.outcomes),
        "outcome_censored": censored,
        "scientific_inventory_rows": len(batch.inventory),
        "anchor_event_links": len(batch.links),
        "market_episodes": len(batch.episodes),
        "content_sha256": 1,
    }
    rows = []
    for metric, count in metrics.items():
        detail = digest if metric == "content_sha256" else metric
        rows.append(
            (SPECIFICATION_ID, SPECIFICATION_VERSION, metric, count, detail, False, recorded_at)
        )
    return rows


def _guard_states(batch: AtlasBatch) -> None:
    for row in batch.states:
        feature_id = str(row[2])
        if "surprise" in feature_id or feature_id.startswith("outcome_"):
            raise AtlasRunError("a state row includes a blocked feature")
        if ":EUNA:" in str(row[1]) or str(row[1]).split(":")[2] == "EUNA":
            if feature_id.startswith("relative_performance") and row[7] is not None:
                raise AtlasRunError("EUNA relative performance was calculated")
        if row[5] == "retrospective_latest_revised_release_lag_unknown" and row[6] is not False:
            raise AtlasRunError("a latest-revised state was marked usable")
        if row[5] == "point_in_time_observation" and not feature_id.startswith(
            f"{POINT_IN_TIME_DATASET}:"
        ):
            raise AtlasRunError("point-in-time was applied outside the BEA vintage")


def _assemble(recorded_at: datetime) -> tuple[AtlasBatch, dict[str, Any], dict[str, Any], str]:
    print("reproducing LH-X-002", flush=True)
    citation = _require_lh_x_002()
    if event_definition_hash() != EVT_DEFINITION_HASH:
        raise AtlasRunError("EVT-DEF-001 hash changed")
    with psycopg.connect(LOCAL_ETF_URL) as etf:
        etf.read_only = True
        listings, hashes, fx_count, distribution_tables = load_prices(etf)
        inrg = etf.execute(
            """
            select count(*)::int
            from instruments.listings listing
            join instruments.market_price_observations price
              on price.listing_id = listing.listing_id
            where listing.ticker = 'INRG' and price.price_type = 'adjusted_close'
            """
        ).fetchone()
    if fx_count != 0:
        raise AtlasRunError(
            "fx_observations is no longer empty; EUNA stays blocked and the run stops"
        )
    inrg_count = 0 if inrg is None else int(inrg[0])
    with psycopg.connect(LOCAL_RESEARCH_URL) as research:
        research.read_only = True
        series, live_count, bea_count, _alfred = _load_series(research)
        vintages = _load_vintages(research)
        events = _load_events(research)
    if len(vintages) != bea_count:
        raise AtlasRunError("BEA vintage rows without a release date were not given an anchor")
    vwra = next((item for item in listings if item.symbol == "VWRA"), None)
    if vwra is None:
        raise AtlasRunError("VWRA is not stored")
    specification_hash = atlas_specification_hash()
    release_anchors, release_states, pit_by_release = compile_releases(
        vintages,
        specification_hash=specification_hash,
        recorded_at=recorded_at,
    )
    batch = AtlasBatch()
    ordered = sorted(listings, key=lambda item: item.symbol)
    for listing in ordered:
        print(f"assembling {listing.symbol}", flush=True)
        anchors, states, outcomes, decisions = compile_listing(
            listing,
            specification_hash=specification_hash,
            series=series,
            pit_by_release=pit_by_release,
            vwra=vwra,
            recorded_at=recorded_at,
        )
        batch.anchors.extend(anchors)
        batch.states.extend(states)
        batch.outcomes.extend(outcomes)
        batch.decisions.extend(decisions)
        batch.anchor_dates[listing.symbol] = [
            (row[6], str(row[0])) for row in anchors if row[5] == "listing_month_end"
        ]
    batch.anchors.extend(release_anchors)
    batch.states.extend(release_states)
    _inventory(
        batch,
        series=series,
        listings=listings,
        hashes=hashes,
        fx_count=fx_count,
        distribution_tables=distribution_tables,
        inrg_count=inrg_count,
        recorded_at=recorded_at,
    )
    batch.links = link_events(events, batch.anchor_dates, recorded_at)
    batch.episodes, batch.episode_events = group_episodes(events, recorded_at=recorded_at)
    _guard_states(batch)
    digest = content_checksum(checksum_lines(batch, specification_hash))
    artifact = _score(batch, listings)
    artifact["lh_x_002_citation"] = citation
    context = {
        "live_latest_revised": live_count,
        "bea_vintage_rows": bea_count,
        "fx_observations": fx_count,
        "inrg_prices": inrg_count,
        "adjusted_closes": sum(len(item.closes) for item in listings),
        "listings": len(listings),
        "price_series": [{"symbol": symbol, "sha256": hashes[symbol]} for symbol in sorted(hashes)],
        "simulation_start": min(item.dates[0] for item in listings),
        "simulation_end": max(item.dates[-1] for item in listings),
    }
    return batch, artifact, context, digest


def _stored_checksum(connection: psycopg.Connection) -> str | None:
    row = connection.execute(
        """
        select detail
        from research.atlas_coverage_counts
        where specification_id = %s and specification_version = %s and metric = 'content_sha256'
        """,
        (SPECIFICATION_ID, SPECIFICATION_VERSION),
    ).fetchone()
    return None if row is None else str(row[0])


def _stored_artifact(connection: psycopg.Connection) -> str | None:
    row = connection.execute(
        """
        select artifact_sha256
        from research.experiment_executions
        where execution_id = 'LH-X-004'
        """
    ).fetchone()
    return None if row is None else str(row[0])


def run() -> dict[str, object]:
    assert_loopback(LOCAL_RESEARCH_URL, "postgres")
    assert_loopback(LOCAL_ETF_URL, "aqil_etf")
    recorded_at = datetime.now(UTC)
    before = ""
    with psycopg.connect(LOCAL_RESEARCH_URL) as research:
        research.read_only = True
        if research.execute("select current_database()").fetchone()[0] != "postgres":
            raise PilotError("the atlas stays on database postgres")
        before = _fingerprint(research)
    batch, artifact, context, digest = _assemble(recorded_at)
    artifact_hash = sha256_document(artifact)
    with psycopg.connect(LOCAL_RESEARCH_URL) as research:
        existing = _stored_checksum(research)
        action = reconcile_checksum(existing, digest)
        if action == "unchanged":
            stored_artifact = _stored_artifact(research)
            if stored_artifact != artifact_hash:
                raise AtlasRunError(
                    "recomputed LH-H-004 artifact does not match the stored checksum"
                )
            if _fingerprint(research) != before:
                raise AtlasRunError("protected rows changed")
            return {
                "action": "unchanged",
                "inserted_anchors": 0,
                "checksum": digest,
                "artifact_sha256": artifact_hash,
                "status": artifact["status"],
                "live_latest_revised": context["live_latest_revised"],
                "bea_vintage_rows": context["bea_vintage_rows"],
                "adjusted_closes": context["adjusted_closes"],
                "fx_observations": context["fx_observations"],
                "inrg_prices": context["inrg_prices"],
            }
        store_specification(
            research,
            specification_id=SPECIFICATION_ID,
            version=SPECIFICATION_VERSION,
            specification=ATLAS_SPECIFICATION,
            specification_hash=atlas_specification_hash(),
            frozen_at=recorded_at,
        )
        copy_atlas(research, batch)
        store_coverage(research, _coverage(batch, digest, recorded_at))
        store_chain(
            research,
            hypothesis=SEQUENCE_HYPOTHESIS,
            specification=SEQUENCE_EXPERIMENT,
            specification_hash=sequence_experiment_hash(),
            status=str(artifact["status"]),
            rationale=" ".join(artifact["reasons"]),
            artifact=artifact,
            artifact_sha256=artifact_hash,
            recorded_at=recorded_at,
            git_commit=git_commit(repo_root()),
            code_hash=atlas_code_hash(),
            input_manifest={
                "atlas_specification_hash": atlas_specification_hash(),
                "sequence_experiment_hash": sequence_experiment_hash(),
                "event_definition_hash": EVT_DEFINITION_HASH,
                "live_latest_revised": context["live_latest_revised"],
                "bea_vintage_rows": context["bea_vintage_rows"],
                "fx_observations": context["fx_observations"],
                "inrg_prices": context["inrg_prices"],
                "adjusted_closes": context["adjusted_closes"],
            },
            price_series_versions=context["price_series"],
            library_versions=library_versions(),
            configuration={
                "status": artifact["status"],
                "medians": artifact["medians"],
                "pooled": artifact["pooled"],
                "portfolio_simulator": "not_called",
            },
            simulation_start=context["simulation_start"],
            simulation_end=context["simulation_end"],
            reproduction_command=REPRODUCTION,
            availability_cutoff=recorded_at,
        )
        for dependency in (
            (
                "LH-D-011",
                "experiment",
                "LH-E-004",
                "methodology",
                SPECIFICATION_ID,
                "shares_methodology",
                SPECIFICATION_ID,
                None,
                "The sequence uses the frozen atlas specification.",
            ),
            (
                "LH-D-012",
                "experiment",
                "LH-E-004",
                "methodology",
                "EVT-DEF-001",
                "shares_methodology",
                "EVT-DEF-001",
                None,
                "The labelled advance is the existing 126-session outcome, not a new event family.",
            ),
            (
                "LH-D-013",
                "experiment",
                "LH-E-004",
                "experiment",
                "LH-E-002",
                "overlaps_period",
                None,
                None,
                "The same inspected price history. LH-X-002 is cited and is not re-estimated.",
            ),
            (
                "LH-D-014",
                "experiment",
                "LH-E-004",
                "control",
                "standalone_bounce_without_prior_near_trough",
                "matched_control",
                None,
                None,
                "Primary control. Overlapping months are not independent confirmation.",
            ),
        ):
            store_dependency(
                research,
                dependency_id=dependency[0],
                left_kind=dependency[1],
                left_id=dependency[2],
                right_kind=dependency[3],
                right_id=dependency[4],
                relation=dependency[5],
                methodology_id=dependency[6],
                instrument_id=dependency[7],
                detail=dependency[8],
                recorded_at=recorded_at,
            )
        store_claim_anchors(research, _claim_anchors(batch, recorded_at))
        if _fingerprint(research) != before:
            raise AtlasRunError("protected rows changed during the write")
        if _stored_checksum(research) != digest:
            raise AtlasRunError("the stored checksum does not match the assembled atlas")
    return {
        "action": "insert",
        "inserted_anchors": len(batch.anchors),
        "inserted_states": len(batch.states),
        "inserted_outcomes": len(batch.outcomes),
        "checksum": digest,
        "artifact_sha256": artifact_hash,
        "status": artifact["status"],
        "reasons": artifact["reasons"],
        "pooled": artifact["pooled"],
        "medians": artifact["medians"],
        "live_latest_revised": context["live_latest_revised"],
        "bea_vintage_rows": context["bea_vintage_rows"],
        "adjusted_closes": context["adjusted_closes"],
        "fx_observations": context["fx_observations"],
        "inrg_prices": context["inrg_prices"],
        "episodes": len(batch.episodes),
        "links": len(batch.links),
    }


def main() -> None:
    result = run()
    print(
        f"{result['action']} status {result['status']} checksum {result['checksum']} "
        f"anchors {result.get('inserted_anchors', 0)}"
    )


if __name__ == "__main__":
    main()
