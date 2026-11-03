"""Catalogue EVT-DEF-002 and score VWRA, EIMI, and their matched excess once.

A second run inserts nothing when the stored artifact still matches.
This module does not build a portfolio path.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

import psycopg

from aqil_research.long_horizon.etf_protocol.events import catalogue_new_families
from aqil_research.long_horizon.etf_protocol.package_hash import protocol_code_hash
from aqil_research.long_horizon.etf_protocol.report import write_documents
from aqil_research.long_horizon.etf_protocol.rules import (
    assert_session_allowed,
    predictor_value,
    relative_class,
    stored_direction_sign,
    trailing_volatility_median,
)
from aqil_research.long_horizon.etf_protocol.score import AnchorState, DossierScore, score_dossier
from aqil_research.long_horizon.etf_protocol.specification import (
    DOSSIERS,
    ECONOMIC_TRANSFORMS,
    EVENT_DEFINITION_V2,
    HORIZONS,
    HYPOTHESES,
    PAIR_CONTROLS,
    PRICE_FEATURES,
    PROTOCOL,
    PROTOCOL_ID,
    PROTOCOL_VERSION,
    VWRA_FIRST_SESSION,
    ProtocolError,
    TrialKey,
    assert_v1_hash_unchanged,
    declare_trials,
    event_definition_v2_hash,
    protocol_hash,
)
from aqil_research.long_horizon.etf_protocol.store import (
    store_chain,
    store_definition,
    store_dependency,
    store_events,
    store_specification,
    store_trials,
)
from aqil_research.long_horizon.events.identify import ListingSeries, assert_listing_series
from aqil_research.long_horizon.events.scan import load_prices
from aqil_research.long_horizon.money import sha256_document
from aqil_research.long_horizon.pilot import (
    LOCAL_ETF_URL,
    LOCAL_RESEARCH_URL,
    PilotError,
    assert_loopback,
    git_commit,
    library_versions,
    repo_root,
)
from aqil_research.long_horizon.state_atlas.build import method_inventory_payload
from aqil_research.long_horizon.state_atlas.specification import EVT_DEFINITION_HASH
from aqil_research.methods.registry import default_method_registry

REPRODUCTION = "uv run python -m aqil_research.long_horizon.etf_protocol"
PRICE_FEATURE_SET = tuple(PRICE_FEATURES) + tuple(PAIR_CONTROLS)
DEPENDENCY_TARGETS = (
    "ATLAS-DEF-001",
    "EVT-DEF-001",
    "EVT-DEF-002",
    "ETF-PROT-001",
)


def _fingerprint(connection: psycopg.Connection) -> str:
    hypotheses = connection.execute(
        """
        select hypothesis_id, proposition, initial_status
        from research.hypotheses
        where hypothesis_id in ('LH-H-001', 'LH-H-002', 'LH-H-003', 'LH-H-004')
        order by hypothesis_id
        """
    ).fetchall()
    event_hash = connection.execute(
        """
        select specification_hash
        from research.event_definitions
        where definition_id = 'EVT-DEF-001' and version = 1
        """
    ).fetchone()
    status_count = connection.execute(
        """
        select count(*)::int
        from research.scientific_status_events
        where subject_id in (
          'LH-H-001', 'LH-H-002', 'LH-H-003', 'LH-H-004',
          'LH-E-001', 'LH-E-002', 'LH-E-003', 'LH-E-004',
          'LH-C-001', 'LH-C-002', 'LH-C-003', 'LH-C-004'
        )
        """
    ).fetchone()
    if event_hash is None or status_count is None:
        raise ProtocolError("the earlier registry is missing")
    if event_hash[0] != EVT_DEFINITION_HASH:
        raise ProtocolError("EVT-DEF-001 hash changed")
    return sha256_document(
        {
            "event_hash": event_hash[0],
            "hypotheses": [list(row) for row in hypotheses],
            "status_count": status_count[0],
        }
    )


def _decimal(feature_id: str, text: str | None, availability: str) -> Decimal | None:
    if availability != "observed" or text is None:
        return None
    if feature_id.endswith(":direction"):
        return stored_direction_sign(text)
    return Decimal(text)


def _load_panel(
    connection: psycopg.Connection,
) -> dict[str, dict[date, tuple[dict[str, Decimal | None], dict[str, Decimal | None]]]]:
    states = connection.execute(
        """
        select a.symbol, a.session_date, s.feature_id, s.availability, s.value_text
        from research.decision_anchors a
        join research.state_observations s on s.anchor_id = a.anchor_id
        where a.anchor_kind = 'listing_month_end'
          and a.symbol in ('VWRA', 'EIMI')
          and (
            s.feature_id = any(%s)
            or s.feature_id like '%%:direction'
            or s.feature_id like '%%:year_on_year'
            or s.feature_id like '%%:acceleration'
          )
        """,
        (list(PRICE_FEATURE_SET),),
    ).fetchall()
    outcomes = connection.execute(
        """
        select a.symbol, a.session_date, o.horizon_label, o.status, o.value_text
        from research.decision_anchors a
        join research.outcome_measures o on o.anchor_id = a.anchor_id
        where a.anchor_kind = 'listing_month_end'
          and a.symbol in ('VWRA', 'EIMI')
        """
    ).fetchall()
    panel: dict[str, dict[date, tuple[dict[str, Decimal | None], dict[str, Decimal | None]]]] = {
        "VWRA": {},
        "EIMI": {},
    }
    for symbol, session, feature_id, availability, value_text in states:
        values, stored_outcomes = panel[symbol].setdefault(session, ({}, {}))
        values[feature_id] = _decimal(feature_id, value_text, availability)
    for symbol, session, horizon, status, value_text in outcomes:
        values, stored_outcomes = panel[symbol].setdefault(session, ({}, {}))
        stored_outcomes[horizon] = (
            None if status != "observed" or value_text is None else Decimal(value_text)
        )
    return panel


def _anchors_for(
    symbol: str,
    listing: ListingSeries,
    panel: dict[date, tuple[dict[str, Decimal | None], dict[str, Decimal | None]]],
) -> list[AnchorState]:
    index_of = {session: index for index, session in enumerate(listing.dates)}
    anchors: list[AnchorState] = []
    for session in sorted(panel):
        assert_session_allowed(symbol, session)
        index = index_of.get(session)
        if index is None:
            raise ProtocolError(f"{symbol} anchor {session.isoformat()} is not a stored session")
        values, outcomes = panel[session]
        for feature in PRICE_FEATURES:
            if feature not in values:
                raise ProtocolError(f"{symbol} {session.isoformat()} has no {feature}")
            computed = predictor_value(listing.closes, index, feature)
            if values[feature] != computed:
                raise ProtocolError(
                    f"{symbol} {session.isoformat()} {feature} does not match the frozen predictor"
                )
        median = trailing_volatility_median(listing.closes, index)
        anchors.append(AnchorState(session, values, outcomes, {}, median))
    return anchors


def _match(eimi: list[AnchorState], vwra: list[AnchorState]) -> list[AnchorState]:
    matched: list[AnchorState] = []
    for row in eimi:
        choices: list[tuple[int, date, AnchorState]] = []
        for other in vwra:
            delta = abs((row.session - other.session).days)
            if delta <= 5:
                choices.append((delta, other.session, other))
        if not choices:
            continue
        _delta, _session, other = sorted(choices)[0]
        outcomes: dict[str, Decimal | None] = {}
        classes: dict[str, str | None] = {}
        for horizon in HORIZONS:
            left = row.outcomes.get(horizon)
            right = other.outcomes.get(horizon)
            if left is None or right is None:
                outcomes[horizon] = None
                classes[horizon] = None
                continue
            outcomes[horizon] = left - right
            classes[horizon] = relative_class(left, right)
        matched.append(
            AnchorState(row.session, row.values, outcomes, classes, row.volatility_median)
        )
    return matched


def _datasets(anchors: list[AnchorState]) -> tuple[str, ...]:
    found: set[str] = set()
    for anchor in anchors:
        for feature in anchor.values:
            if ":" not in feature:
                continue
            dataset, transform = feature.rsplit(":", 1)
            if transform in ECONOMIC_TRANSFORMS:
                found.add(dataset)
    return tuple(sorted(found))


def _catalogue(
    listings: list[ListingSeries],
    hashes: dict[str, str],
    recorded_at: datetime,
) -> tuple[list[tuple[Any, ...]], list[tuple[Any, ...]], dict[str, int]]:
    events: list[tuple[Any, ...]] = []
    families: list[tuple[Any, ...]] = []
    seen: set[str] = set()
    totals: dict[str, int] = defaultdict(int)
    for listing in listings:
        if listing.symbol == "INRG":
            raise ProtocolError("INRG has prices and was not expected")
        assert_listing_series(
            listing.symbol,
            listing.dates,
            listing.closes,
            listing.currency,
            listing.currency,
        )
        print(f"cataloguing {listing.symbol}", flush=True)
        series_hash = hashes[listing.symbol]
        for count in catalogue_new_families(listing.dates, listing.closes):
            families.append(
                (
                    "EVT-DEF-002",
                    1,
                    listing.symbol,
                    count.family,
                    count.horizon_label,
                    count.status,
                    count.reason,
                    len(count.events),
                    count.windows_examined,
                    count.qualifier_window_count,
                    count.censored_count,
                    series_hash,
                    False,
                    recorded_at,
                )
            )
            totals[count.family] += len(count.events)
            for event in count.events:
                start = listing.dates[event.start_index]
                end = listing.dates[event.end_index]
                confirmed = (
                    None
                    if event.label_confirmed_index is None
                    else listing.dates[event.label_confirmed_index]
                )
                event_id = (
                    f"PE-v2-{listing.symbol}-{event.family}-{event.horizon_label}-"
                    f"{start.isoformat()}-{end.isoformat()}"
                )
                if event_id in seen:
                    raise ProtocolError(f"duplicate event {event_id}")
                seen.add(event_id)
                events.append(
                    (
                        event_id,
                        "EVT-DEF-002",
                        1,
                        listing.symbol,
                        listing.currency,
                        event.family,
                        event.horizon_label,
                        start,
                        end,
                        confirmed,
                        event.price_return,
                        event.end_index - event.start_index,
                        event.max_intervening_drawdown,
                        event.up_session_fraction,
                        event.label_uses_later_prices,
                        False,
                        event.historically_observable_at_event_date,
                        series_hash,
                        event.detail,
                        False,
                        recorded_at,
                    )
                )
    return events, families, dict(totals)


def _citations(connection: psycopg.Connection) -> dict[str, dict[str, str]]:
    periods = connection.execute(
        """
        select symbol,
               count(*)::int,
               count(*) filter (where condition_met)::int,
               count(*) filter (where outcome_advance)::int
        from research.comparison_periods
        where experiment_id = 'LH-E-002' and experiment_version = 1
          and symbol in ('VWRA', 'EIMI')
        group by symbol
        """
    ).fetchall()
    by_symbol = {symbol: (rows, met, advances) for symbol, rows, met, advances in periods}
    body = connection.execute(
        "select body from research.evidence_records where evidence_id = 'LH-V-004'"
    ).fetchone()
    if body is None:
        raise ProtocolError("LH-V-004 evidence is missing")
    payload = body[0]
    dates = payload.get("sequence_decision_dates", [])
    status = str(payload.get("status"))
    cited: dict[str, dict[str, str]] = {}
    for symbol in ("VWRA", "EIMI"):
        rows, met, advances = by_symbol.get(symbol, (0, 0, 0))
        sequence_dates = sum(1 for item in dates if item[0] == symbol)
        cited[symbol] = {
            "LH-E-002": (
                f"Stored comparison rows {rows}, condition true {met}, "
                f"labelled advances {advances}. Not re-estimated."
            ),
            "LH-E-004": (
                f"Stored status {status}. Sequence dates for this symbol {sequence_dates}. "
                "Not re-estimated."
            ),
        }
    return cited


def _methods(connection: psycopg.Connection) -> dict[str, str]:
    rows = connection.execute(
        """
        select distinct o.dataset_id
        from research.economic_observations o
        join research.source_retrievals r on r.retrieval_id = o.retrieval_id
        where r.collection_mode = 'live'
          and o.series_provenance = 'latest_revised'
          and o.quality_status = 'observed'
        """
    ).fetchall()
    stored = {row[0] for row in rows}
    replay: dict[str, str] = {}
    for method in default_method_registry().registered():
        payload = method_inventory_payload(method, stored)
        status = str(payload["replay_status"])
        if payload["point_in_time"] is not False:
            raise ProtocolError("a method was marked point-in-time")
        replay[str(payload["method_id"])] = status
    if len(replay) != 26:
        raise ProtocolError(f"expected 26 methods and found {len(replay)}")
    return replay


def _trial_line(record: Any) -> str:
    key = record.key
    return "|".join(
        (
            key.identity(),
            record.effect or "",
            record.result or "",
            record.refusal or "",
            record.p_value or "",
            record.result_status or "",
            record.detail,
        )
    )


def _prose(symbol: str, status: str) -> str:
    if symbol == "EIMI-VWRA":
        return (
            "Matched US-dollar month-ends within five days. The outcome is the "
            "session-step return of EIMI minus the session-step return of VWRA. "
            "A missing session is censored and is not filled. EIMI is an "
            "emerging-market overweight relative to VWRA, not a separate diversifier. "
            f"The dossier status is {status}. No allocation policy is registered."
        )
    history = (
        f"Sessions before {VWRA_FIRST_SESSION} are refused."
        if symbol == "VWRA"
        else "EIMI uses its own longer stored history."
    )
    return (
        f"{history} The same threshold table is used for every symbol. "
        f"The conjunction status is {status}. Latest-revised features are not decision inputs."
    )


def _summary(
    *,
    scores: dict[str, DossierScore],
    keys: tuple[TrialKey, ...],
    event_totals: dict[str, int],
    event_count: int,
    catalogue_symbols: int,
    commit: str,
) -> dict[str, Any]:
    dossiers: dict[str, Any] = {}
    for dossier in DOSSIERS:
        symbol = str(dossier["symbol"])
        score = scores[symbol]
        records = score.records
        dossiers[symbol] = {
            "hypothesis_id": dossier["hypothesis_id"],
            "execution_id": dossier["execution_id"],
            "status": score.status,
            "policy": score.policy,
            "trial_count": len(records),
            "refused_count": sum(record.refusal is not None for record in records),
            "effect_count": sum(record.effect is not None for record in records),
            "bh_tested": score.bh_tested,
            "bh_flagged": score.bh_flagged,
            "class_counts": score.class_counts,
            "eligible": score.conjunction_counts.get("eligible"),
            "prose": _prose(symbol, score.status),
        }
    lines = sorted(_trial_line(record) for score in scores.values() for record in score.records)
    return {
        "schema_version": "1.0",
        "git_commit": commit,
        "protocol_hash": protocol_hash(),
        "evt_def_001_hash": EVT_DEFINITION_HASH,
        "evt_def_002_hash": event_definition_v2_hash(),
        "catalogue_symbols": catalogue_symbols,
        "event_count": event_count,
        "event_totals": event_totals,
        "trial_count": len(lines),
        "declared_count": len(keys),
        "trial_checksum": sha256_document(lines),
        "policy": "no_policy_registered",
        "publication_allowed": False,
        "portfolio_path": "not_called",
        "catalogue_scenarios_executed": 0,
        "dossiers": dossiers,
    }


def _trial_rows(score: DossierScore, recorded_at: datetime) -> list[tuple[Any, ...]]:
    specification_hash = protocol_hash()
    rows: list[tuple[Any, ...]] = []
    for record in score.records:
        key = record.key
        rows.append(
            (
                key.identity(),
                PROTOCOL_ID,
                PROTOCOL_VERSION,
                specification_hash,
                key.dossier_id,
                key.symbol,
                key.feature,
                key.transform,
                key.horizon_label,
                key.outcome,
                key.statistic,
                key.eligibility,
                record.result,
                record.refusal,
                record.effect,
                record.p_value,
                record.result_status,
                record.detail,
                False,
                recorded_at,
            )
        )
    return rows


def run() -> dict[str, Any]:
    assert_loopback(LOCAL_RESEARCH_URL, "postgres")
    assert_loopback(LOCAL_ETF_URL, "aqil_etf")
    assert_v1_hash_unchanged()
    recorded_at = datetime.now(UTC)
    commit = git_commit(repo_root())
    with psycopg.connect(LOCAL_RESEARCH_URL) as research:
        research.read_only = True
        if research.execute("select current_database()").fetchone()[0] != "postgres":
            raise PilotError("the protocol stays on database postgres")
        before = _fingerprint(research)
        panel = _load_panel(research)
        citations = _citations(research)
        methods = _methods(research)
        anchor_rows = research.execute(
            """
            select count(*)::int from research.decision_anchors
            """
        ).fetchone()
    with psycopg.connect(LOCAL_ETF_URL) as etf:
        listings, hashes, fx_count, _distributions = load_prices(etf)
    if fx_count != 0:
        raise ProtocolError("foreign-exchange rows are present")
    if anchor_rows is None or anchor_rows[0] < 2358:
        raise ProtocolError("the atlas anchor count is below the recounted prior")
    by_symbol = {listing.symbol: listing for listing in listings}
    for required in ("VWRA", "EIMI"):
        if required not in by_symbol:
            raise ProtocolError(f"{required} has no stored closes")
    print("scoring VWRA", flush=True)
    vwra = _anchors_for("VWRA", by_symbol["VWRA"], panel["VWRA"])
    print("scoring EIMI", flush=True)
    eimi = _anchors_for("EIMI", by_symbol["EIMI"], panel["EIMI"])
    paired = _match(eimi, vwra)
    datasets = _datasets(vwra + eimi)
    keys = declare_trials(datasets, tuple(methods))
    grouped: dict[str, list[TrialKey]] = defaultdict(list)
    for key in keys:
        grouped[key.symbol].append(key)
    anchors = {"VWRA": vwra, "EIMI": eimi, "EIMI-VWRA": paired}
    scores: dict[str, DossierScore] = {}
    for dossier in DOSSIERS:
        symbol = str(dossier["symbol"])
        scores[symbol] = score_dossier(
            grouped[symbol],
            anchors[symbol],
            method_replay=methods,
            citations=citations.get(symbol, {}),
            kind=str(dossier["kind"]),
        )
        if scores[symbol].policy != "no_policy_registered":
            raise ProtocolError("a policy was registered")
        if len(scores[symbol].records) != len(grouped[symbol]):
            raise ProtocolError("the scored trial count left the declared grid")
    if sum(len(score.records) for score in scores.values()) != len(keys):
        raise ProtocolError("the stored trial count left the declared grid")
    events, families, event_totals = _catalogue(listings, hashes, recorded_at)
    summary = _summary(
        scores=scores,
        keys=keys,
        event_totals=event_totals,
        event_count=len(events),
        catalogue_symbols=len(listings),
        commit=commit,
    )
    artifact_hash = sha256_document(summary)
    with psycopg.connect(LOCAL_RESEARCH_URL) as research:
        existing = research.execute(
            """
            select execution_id, artifact_sha256
            from research.experiment_executions
            where execution_id in ('LH-X-005', 'LH-X-006', 'LH-X-007')
            order by execution_id
            """
        ).fetchall()
        if len(existing) == 3:
            if any(row[1] != artifact_hash for row in existing):
                raise ProtocolError("a second run does not match the stored artifact")
            stored_events = research.execute(
                """
                select count(*)::int from research.market_events
                where definition_id = 'EVT-DEF-002' and definition_version = 1
                """
            ).fetchone()
            stored_trials = research.execute(
                "select count(*)::int from research.etf_protocol_trials"
            ).fetchone()
            if stored_events is None or stored_trials is None:
                raise ProtocolError("stored protocol counts are missing")
            if stored_events[0] != len(events) or stored_trials[0] != summary["trial_count"]:
                raise ProtocolError("a second run would change the stored counts")
            if _fingerprint(research) != before:
                raise ProtocolError("earlier hypotheses changed")
            print("unchanged")
            print("inserted_events=0")
            print("inserted_trials=0")
            print(f"events={stored_events[0]}")
            print(f"trials={stored_trials[0]}")
            print("policy=no_policy_registered")
            summary["action"] = "unchanged"
            return summary
        if existing:
            raise ProtocolError("a partial protocol execution is already stored")
        if _fingerprint(research) != before:
            raise ProtocolError("earlier hypotheses changed before the write")
        store_definition(
            research,
            definition=EVENT_DEFINITION_V2,
            definition_hash=event_definition_v2_hash(),
            frozen_at=recorded_at,
        )
        store_events(research, events, families)
        store_specification(
            research,
            specification=PROTOCOL,
            specification_hash=protocol_hash(),
            frozen_at=recorded_at,
        )
        versions = [{"symbol": symbol, "sha256": hashes[symbol]} for symbol in sorted(hashes)]
        libraries = library_versions()
        code_hash = protocol_code_hash()
        for dossier in DOSSIERS:
            symbol = str(dossier["symbol"])
            score = scores[symbol]
            span = anchors[symbol]
            store_chain(
                research,
                dossier=dossier,
                hypothesis=HYPOTHESES[str(dossier["hypothesis_id"])],
                specification=PROTOCOL,
                specification_hash=protocol_hash(),
                status=score.status,
                rationale=(
                    "The frozen rule assigned this status on the inspected history. "
                    "It is not a promoted claim."
                ),
                artifact=summary,
                artifact_sha256=artifact_hash,
                recorded_at=recorded_at,
                git_commit=commit,
                code_hash=code_hash,
                input_manifest={
                    "anchors": len(span),
                    "datasets": list(datasets),
                    "fx_observations": fx_count,
                    "event_definition_v1_hash": EVT_DEFINITION_HASH,
                },
                price_series_versions=versions,
                library_versions=libraries,
                configuration={
                    "policy": "no_policy_registered",
                    "trial_count": summary["trial_count"],
                    "event_count": len(events),
                    "portfolio_path": "not_called",
                },
                simulation_start=span[0].session if span else None,
                simulation_end=span[-1].session if span else None,
                reproduction_command=REPRODUCTION,
                availability_cutoff=recorded_at,
            )
            dependency_ids = dossier["dependency_ids"]
            if not isinstance(dependency_ids, tuple):
                raise ProtocolError("dependency ids are missing")
            for dependency_id, target in zip(dependency_ids, DEPENDENCY_TARGETS, strict=True):
                store_dependency(
                    research,
                    dependency_id=str(dependency_id),
                    experiment_id=str(dossier["experiment_id"]),
                    right_id=target,
                    detail=(
                        f"{dossier['experiment_id']} depends on {target}. "
                        "Confirmation is not independent."
                    ),
                    recorded_at=recorded_at,
                )
        trial_rows: list[tuple[Any, ...]] = []
        for dossier in DOSSIERS:
            trial_rows.extend(_trial_rows(scores[str(dossier["symbol"])], recorded_at))
        store_trials(research, trial_rows)
        if _fingerprint(research) != before:
            raise ProtocolError("earlier hypotheses changed during the write")
    write_documents(repo_root(), summary)
    print("stored")
    print(f"inserted_events={len(events)}")
    print(f"inserted_trials={summary['trial_count']}")
    print(f"events={len(events)}")
    print(f"trials={summary['trial_count']}")
    print(f"declared={summary['declared_count']}")
    print("policy=no_policy_registered")
    for symbol, row in summary["dossiers"].items():
        print(f"status_{symbol}={row['status']}")
    summary["action"] = "stored"
    return summary
