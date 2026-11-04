"""Score EIMI and the matched excess. The specification is already frozen.

persist=False rolls back. A second persist inserts nothing when the artifact matches.
VWRA discovery rows are not rewritten. publication_allowed stays false.
"""

from __future__ import annotations

import hashlib
from collections import defaultdict
from datetime import UTC, date, datetime
from decimal import Decimal
from importlib.metadata import PackageNotFoundError, version
from typing import Any

import psycopg

from aqil_research.long_horizon.money import decimal_text, sha256_document
from aqil_research.long_horizon.pilot import (
    LOCAL_ETF_URL,
    LOCAL_RESEARCH_URL,
    assert_loopback,
    assert_only_icon_is_dirty,
    git_commit,
    library_versions,
    repo_root,
)
from aqil_research.long_horizon.policies import ImmediateSingleAssetPolicy
from aqil_research.long_horizon.simulator import (
    CashFlow,
    PriceBar,
    SimulatorError,
    simulate,
)
from aqil_research.long_horizon.spec import PILOT_CONTRIBUTION, PILOT_COST_RATE, PILOT_INTEREST_RATE
from aqil_research.long_horizon.state_atlas.specification import SESSION_STEPS
from aqil_research.long_horizon.vwra_discovery.align import (
    market_values,
    refuse_fx_count,
)
from aqil_research.long_horizon.vwra_discovery.audit import (
    MethodCensus,
    load_census,
    render_coverage,
)
from aqil_research.long_horizon.vwra_discovery.battery import (
    ScoredTrial,
    _apply_bh,
    _raw,
    assign_ids,
    casebook_rows,
    experiment_id,
    findings_for,
    grid_holds,
    score_excess_pairs,
    score_features,
    score_horizons,
    score_named_associations,
    score_pairs,
    score_sequence,
)
from aqil_research.long_horizon.vwra_discovery.compare_store import (
    artifact_bodies,
    store_comparison,
)
from aqil_research.long_horizon.vwra_discovery.comparison import (
    MATCHED_NOT_BEFORE,
    PRICE_CONTROL,
    RELATIVE_CONTROL,
    SPECIFICATION_ID,
    STORED_METHOD_SPECIFICATION,
    excess_return,
    is_advance,
    is_decline,
    match_month_ends,
    portfolio_claim_status,
    portfolio_statement,
    shared_date,
    specification_hash,
)
from aqil_research.long_horizon.vwra_discovery.dossier import (
    Anchor,
    AnchorFeature,
    Finding,
    _added_market,
    _joined_methods,
)
from aqil_research.long_horizon.vwra_discovery.guards import assert_state_feature
from aqil_research.long_horizon.vwra_discovery.materialise import code_hash
from aqil_research.long_horizon.vwra_discovery.portfolio_rule import (
    EqualCashMixPolicy,
    RelativeMomentumPolicy,
)
from aqil_research.long_horizon.vwra_discovery.replay import MethodRun, StoredPoint
from aqil_research.long_horizon.vwra_discovery.report_compare import write_documents
from aqil_research.long_horizon.vwra_discovery.specification import sequence_finding
from aqil_research.long_horizon.vwra_discovery.statistics import (
    atlas_unit,
    model_allowed,
    parse_decimal,
    thin_indexes,
)

PROTECTED_EXECUTIONS = tuple(f"LH-X-{index:03d}" for index in range(1, 12))
PRIMARY_STEPS = SESSION_STEPS["6m"]


def run(*, persist: bool) -> dict[str, object]:
    """Read stored inputs, score, and append the new chain once."""
    assert_loopback(LOCAL_RESEARCH_URL, "postgres")
    assert_loopback(LOCAL_ETF_URL, "aqil_etf")
    with psycopg.connect(LOCAL_ETF_URL) as etf:
        prices, price_hashes = _load_prices(etf)
        fx_count = _fx_count(etf)
    refuse_fx_count(fx_count)
    with psycopg.connect(LOCAL_RESEARCH_URL) as research:
        existing = _existing_executions(research)
        if persist and not existing:
            assert_only_icon_is_dirty(repo_root())
        commit = git_commit(repo_root())
        digest = code_hash()
        before = _snapshot(research)
        census = load_census(research)
        _assert_registry(census)
        prepared = _prepare(research, prices, census)
        inserted = 0
        if persist:
            versions = library_versions()
            try:
                versions["statsmodels"] = version("statsmodels")
            except PackageNotFoundError:
                versions["statsmodels"] = "not_installed"
            inserted = store_comparison(
                research,
                trials=prepared["trials"],
                cases=prepared["cases"],
                findings=prepared["findings"],
                features=prepared["features"],
                bodies=prepared["bodies"],
                hashes=prepared["hashes"],
                recorded_at=datetime.now(UTC),
                git_commit=commit,
                code_hash=digest,
                input_manifest={
                    "specification_id": SPECIFICATION_ID,
                    "specification_hash": specification_hash(),
                    "eimi_anchors": prepared["coverage"]["eimi_anchors"],
                    "matched_anchors": prepared["coverage"]["matched_anchors"],
                    "fx_observations": 0,
                    "publication_allowed": False,
                    "point_in_time": False,
                    "catalogue_scenarios_executed": 0,
                    "bea_vintage_used_as_decision_input": False,
                },
                price_series_versions=[
                    {
                        "symbol": symbol,
                        "sha256": price_hashes[symbol],
                        "price_type": "adjusted_close",
                        "currency": "USD",
                    }
                    for symbol in ("EIMI", "VWRA")
                ],
                library_versions=versions,
            )
            _assert_unchanged(before, _snapshot(research))
            _assert_unpublished(research)
        else:
            research.rollback()
    if persist and inserted:
        write_documents(
            prepared,
            census_markdown=render_coverage(census),
            git_commit=commit,
            folder=repo_root() / "docs" / "research" / "eimi-discovery",
        )
    print(
        f"persist={persist} inserted_executions={inserted} "
        f"trials={len(prepared['trials'])} matched={prepared['coverage']['matched_anchors']}",
        flush=True,
    )
    return {
        "inserted_executions": inserted,
        "persist": persist,
        "coverage": prepared["coverage"],
        "portfolio": prepared["portfolio"],
        "artifact_sha256": prepared["hashes"],
        "git_commit": commit,
        "trials": len(prepared["trials"]),
        "findings": [
            {
                "finding_id": item.finding_id,
                "finding_class": item.finding_class,
                "statement": item.statement,
            }
            for item in prepared["findings"]
        ],
    }


def main() -> None:
    run(persist=True)


def _prepare(
    connection: psycopg.Connection,
    prices: dict[str, dict[date, PriceBar]],
    census: tuple[MethodCensus, ...],
) -> dict[str, Any]:
    anchors = _anchors(connection)
    atlas, units, skipped = _atlas(connection)
    outcomes = _outcomes(connection)
    runs = _runs(connection)
    eimi_added = _added_market(
        anchors["EIMI"],
        _dates(prices["EIMI"]),
        _closes(prices["EIMI"]),
        _index(prices["EIMI"]),
    )
    vwra_added = _added_market(
        anchors["VWRA"],
        _dates(prices["VWRA"]),
        _closes(prices["VWRA"]),
        _index(prices["VWRA"]),
    )
    eimi_methods = _joined_methods(anchors["EIMI"], runs)
    _merge(atlas["EIMI"], units, eimi_added)
    _merge(atlas["VWRA"], units, vwra_added)
    battery_panel = {
        anchor.anchor_id: dict(atlas["EIMI"].get(anchor.anchor_id, {}))
        for anchor in anchors["EIMI"]
    }
    _merge(battery_panel, units, eimi_methods)
    units[PRICE_CONTROL] = "ratio"
    units[RELATIVE_CONTROL] = "ratio"
    eimi_ids = [anchor.anchor_id for anchor in anchors["EIMI"]]
    eimi_returns = _return_map(outcomes, "EIMI", PRIMARY_STEPS)
    _assert_labels(outcomes)
    eimi_thinned = _thinned(
        [anchor_id for anchor_id in eimi_ids if eimi_returns.get(anchor_id) is not None],
        {anchor.anchor_id: anchor.session for anchor in anchors["EIMI"]},
        _index(prices["EIMI"]),
    )
    eimi_positive = {
        anchor_id: None if value is None else is_advance(value)
        for anchor_id, value in ((item, eimi_returns.get(item)) for item in eimi_ids)
    }
    eimi_negative = {
        anchor_id: None if value is None else is_decline(value)
        for anchor_id, value in ((item, eimi_returns.get(item)) for item in eimi_ids)
    }
    reasons = {run.method_id: run.reason or run.status for run in runs if run.status != "succeeded"}
    trials: list[ScoredTrial] = []
    trials.extend(_census_trials(census))
    trials.extend(_skipped(skipped["EIMI"], experiment_id("LH-H-013"), "EIMI"))
    trials.extend(
        score_features(
            hypothesis_id="LH-H-013",
            symbol="EIMI",
            panel=battery_panel,
            units=units,
            row_ids=eimi_ids,
            outcomes=eimi_returns,
            positive_labels=eimi_positive,
            negative_labels=eimi_negative,
            thinned_ids=eimi_thinned,
            non_overlapping=len(eimi_thinned),
            numeric_outcome="return_126",
            positive_statistic="conditional_advance",
            positive_outcome="advance_126",
            negative_statistic="conditional_decline",
            negative_outcome="decline_126",
            logistic_outcome="advance_126",
        )
    )
    trials.extend(
        score_pairs(
            hypothesis_id="LH-H-014",
            symbol="EIMI",
            panel=battery_panel,
            row_ids=eimi_ids,
            positive_labels=eimi_positive,
            negative_labels=eimi_negative,
            non_overlapping=len(eimi_thinned),
            reasons=reasons,
            positive_statistic="conditional_advance",
            positive_outcome="advance_126",
            negative_statistic="conditional_decline",
            negative_outcome="decline_126",
        )
    )
    sequence_labels = [eimi_positive[anchor_id] for anchor_id in eimi_ids]
    sequence_counts, sequence_trials = score_sequence(
        hypothesis_id="LH-H-015",
        symbol="EIMI",
        panel=battery_panel,
        row_ids=eimi_ids,
        labels=sequence_labels,
        non_overlapping=len(eimi_thinned),
        outcome_name="advance_126",
        label_note="The label is an EIMI advance of at least 0.10.",
    )
    trials.extend(sequence_trials)
    matched, matched_panel = _matched(anchors, atlas, runs, outcomes, units)
    matched_ids = [str(row["row_id"]) for row in matched]
    matched_outcomes = {
        str(row["row_id"]): {
            "eimi_return_126": row["eimi_126"],
            "vwra_return_126": row["vwra_126"],
            "excess_126": excess_return(row["eimi_126"], row["vwra_126"]),
        }
        for row in matched
    }
    excess_values = {row_id: values["excess_126"] for row_id, values in matched_outcomes.items()}
    eimi_leg = {row_id: values["eimi_return_126"] for row_id, values in matched_outcomes.items()}
    vwra_leg = {row_id: values["vwra_return_126"] for row_id, values in matched_outcomes.items()}
    matched_session = {str(row["row_id"]): row["vwra_day"] for row in matched}
    matched_thinned = _thinned(
        [row_id for row_id, value in excess_values.items() if value is not None],
        matched_session,
        _index(prices["VWRA"]),
    )
    panels = {
        "EIMI": _score_panel(matched_panel, "EIMI"),
        "VWRA": _score_panel(matched_panel, "VWRA"),
        "EIMI-VWRA": _score_panel(matched_panel, "EIMI"),
    }
    feature_trials: list[ScoredTrial] = []
    for (
        symbol,
        outcome_map,
        positive,
        negative,
        numeric,
        positive_name,
        negative_name,
        logistic,
    ) in (
        (
            "EIMI",
            eimi_leg,
            {key: None if value is None else is_advance(value) for key, value in eimi_leg.items()},
            {key: None if value is None else is_decline(value) for key, value in eimi_leg.items()},
            "eimi_return_126",
            "conditional_advance",
            "conditional_decline",
            "eimi_advance_126",
        ),
        (
            "VWRA",
            vwra_leg,
            {key: None if value is None else is_advance(value) for key, value in vwra_leg.items()},
            {key: None if value is None else is_decline(value) for key, value in vwra_leg.items()},
            "vwra_return_126",
            "conditional_advance",
            "conditional_decline",
            "vwra_advance_126",
        ),
        (
            "EIMI-VWRA",
            excess_values,
            {key: None if value is None else value > 0 for key, value in excess_values.items()},
            {key: None if value is None else value < 0 for key, value in excess_values.items()},
            "excess_126",
            "conditional_eimi_ahead",
            "conditional_vwra_ahead",
            "excess_positive_126",
        ),
    ):
        feature_trials.extend(
            score_features(
                hypothesis_id="LH-H-016",
                symbol=symbol,
                panel=panels[symbol],
                units=units,
                row_ids=matched_ids,
                outcomes=outcome_map,
                positive_labels=positive,
                negative_labels=negative,
                thinned_ids=matched_thinned,
                non_overlapping=len(matched_thinned),
                numeric_outcome=numeric,
                positive_statistic=positive_name,
                positive_outcome=numeric,
                negative_statistic=negative_name,
                negative_outcome=numeric,
                logistic_outcome=logistic,
                apply_bh=False,
            )
        )
    _apply_bh(feature_trials, experiment_id("LH-H-016"), "EIMI-VWRA")
    trials.extend(feature_trials)
    trials.extend(score_horizons(_horizon_rows(matched, outcomes)))
    trials.extend(
        score_named_associations(
            panels["EIMI-VWRA"], matched_ids, matched_outcomes, len(matched_thinned)
        )
    )
    trials.extend(
        score_excess_pairs(
            panels["EIMI-VWRA"], matched_ids, matched_outcomes, len(matched_thinned), reasons
        )
    )
    for symbol, panel_name, labels, outcome_name, note in (
        (
            "EIMI",
            "EIMI",
            [None if row["eimi_126"] is None else is_advance(row["eimi_126"]) for row in matched],
            "eimi_advance_126",
            "Matched EIMI. The label is an absolute advance of at least 0.10.",
        ),
        (
            "VWRA",
            "VWRA",
            [None if row["vwra_126"] is None else is_advance(row["vwra_126"]) for row in matched],
            "vwra_advance_126",
            "Matched VWRA. The label is an absolute advance of at least 0.10.",
        ),
        (
            "EIMI-VWRA",
            "EIMI-VWRA",
            [
                None
                if excess_return(row["eimi_126"], row["vwra_126"]) is None
                else excess_return(row["eimi_126"], row["vwra_126"]) > 0
                for row in matched
            ],
            "excess_positive_126",
            "The label is excess greater than zero. That is not an absolute advance.",
        ),
    ):
        _counts, rows = score_sequence(
            hypothesis_id="LH-H-016",
            symbol=symbol,
            panel=panels[panel_name],
            row_ids=matched_ids,
            labels=labels,
            non_overlapping=len(matched_thinned),
            outcome_name=outcome_name,
            label_note=note,
        )
        trials.extend(rows)
    cases = casebook_rows(matched, panels["EIMI-VWRA"])
    portfolio = _portfolio(prices)
    findings = findings_for(trials, str(sequence_counts["comparison_status"]))
    findings.append(_portfolio_finding(portfolio))
    assign_ids(trials, cases)
    if not grid_holds(trials):
        raise RuntimeError("the trial grid does not account for every row")
    stored_features = _feature_rows(eimi_added + eimi_methods)
    coverage = _coverage(
        anchors,
        prices,
        outcomes,
        matched,
        census,
        len(eimi_thinned),
        len(matched_thinned),
        model_allowed(
            sum(1 for value in eimi_returns.values() if value is not None),
            len(eimi_thinned),
        ),
        model_allowed(
            sum(1 for value in excess_values.values() if value is not None), len(matched_thinned)
        ),
        sequence_counts,
        trials,
    )
    bodies = artifact_bodies(trials, cases, findings, coverage, portfolio)
    _windows(bodies, coverage, portfolio)
    hashes = {key: sha256_document(value) for key, value in bodies.items()}
    return {
        "trials": trials,
        "cases": cases,
        "findings": findings,
        "features": stored_features,
        "coverage": coverage,
        "portfolio": portfolio,
        "bodies": bodies,
        "hashes": hashes,
    }


def _load_prices(
    connection: psycopg.Connection,
) -> tuple[dict[str, dict[date, PriceBar]], dict[str, str]]:
    connection.read_only = True
    with connection.cursor() as cursor:
        cursor.execute("select current_database()")
        if cursor.fetchone()[0] != "aqil_etf":
            raise RuntimeError("price reads must use aqil_etf")
        cursor.execute(
            """
            select l.ticker, p.session_date, p.value::text, p.currency, p.quote_unit,
                   p.adjustment_status, p.price_type
            from instruments.listings l
            join instruments.market_price_observations p
              on p.listing_id = l.listing_id
            where l.ticker in ('EIMI', 'VWRA')
              and p.price_type = 'adjusted_close'
            order by l.ticker, p.session_date
            """
        )
        fetched = cursor.fetchall()
    prices: dict[str, dict[date, PriceBar]] = defaultdict(dict)
    per_symbol: dict[str, list[str]] = defaultdict(list)
    seen: set[tuple[str, date]] = set()
    for ticker, session, raw_value, currency, quote_unit, adjustment_status, price_type in fetched:
        if price_type != "adjusted_close" or adjustment_status != "adjusted":
            raise RuntimeError("the comparison uses stored split-adjusted closes only")
        if currency != "USD" or quote_unit != "USD":
            raise RuntimeError("currency conversion is unsupported")
        key = (ticker, session)
        if key in seen:
            raise RuntimeError(f"duplicate stored close for {ticker} {session}")
        seen.add(key)
        prices[ticker][session] = PriceBar(session, Decimal(raw_value), currency)
        per_symbol[ticker].append(
            f"{ticker}|{session.isoformat()}|{raw_value}|{currency}|{quote_unit}"
        )
    if set(prices) != {"EIMI", "VWRA"}:
        raise RuntimeError("EIMI and VWRA stored closes are required")
    hashes = {
        ticker: hashlib.sha256("\n".join(rows).encode("utf-8")).hexdigest()
        for ticker, rows in per_symbol.items()
    }
    return prices, hashes


def _fx_count(connection: psycopg.Connection) -> int:
    with connection.cursor() as cursor:
        cursor.execute("select count(*)::int from instruments.fx_observations")
        return int(cursor.fetchone()[0])


def _anchors(connection: psycopg.Connection) -> dict[str, list[Anchor]]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            select symbol, anchor_id, session_date
            from research.decision_anchors
            where symbol in ('EIMI', 'VWRA')
              and anchor_kind = 'listing_month_end'
            order by symbol, session_date
            """
        )
        grouped: dict[str, list[Anchor]] = {"EIMI": [], "VWRA": []}
        for symbol, anchor_id, session in cursor.fetchall():
            grouped[str(symbol)].append(Anchor(str(anchor_id), session))
    if not grouped["EIMI"] or not grouped["VWRA"]:
        raise RuntimeError("EIMI and VWRA month-end anchors are required")
    return grouped


def _atlas(
    connection: psycopg.Connection,
) -> tuple[dict[str, dict[str, dict[str, str]]], dict[str, str], dict[str, dict[str, int]]]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            select a.symbol, s.anchor_id, s.feature_id, s.availability, s.value_text, s.clock
            from research.state_observations s
            join research.decision_anchors a on a.anchor_id = s.anchor_id
            where a.symbol in ('EIMI', 'VWRA')
              and a.anchor_kind = 'listing_month_end'
            """
        )
        fetched = cursor.fetchall()
    panels: dict[str, dict[str, dict[str, str]]] = {
        "EIMI": defaultdict(dict),
        "VWRA": defaultdict(dict),
    }
    units: dict[str, str] = {}
    skipped: dict[str, dict[str, int]] = {"EIMI": defaultdict(int), "VWRA": defaultdict(int)}
    for symbol, anchor_id, feature_id, availability, value, clock in fetched:
        feature = str(feature_id)
        if clock == "point_in_time_observation" and not feature.startswith("bea.vintage."):
            raise RuntimeError(f"{feature} is not the stored point-in-time subject")
        if availability != "observed" or value is None:
            continue
        assert_state_feature(feature)
        if parse_decimal(value) is None:
            if feature.endswith(":direction") or value in {"up", "down", "flat"}:
                skipped[str(symbol)][feature] += 1
            continue
        panels[str(symbol)][str(anchor_id)][feature] = str(value)
        units[feature] = atlas_unit(feature)
    return panels, units, skipped


def _outcomes(
    connection: psycopg.Connection,
) -> dict[str, dict[str, dict[int, tuple[str, Decimal | None, bool | None]]]]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            select a.symbol, o.anchor_id, o.session_steps, o.status, o.value_text,
                   o.labelled_advance
            from research.outcome_measures o
            join research.decision_anchors a on a.anchor_id = o.anchor_id
            where a.symbol in ('EIMI', 'VWRA')
              and a.anchor_kind = 'listing_month_end'
            """
        )
        fetched = cursor.fetchall()
    grouped: dict[str, dict[str, dict[int, tuple[str, Decimal | None, bool | None]]]] = {
        "EIMI": defaultdict(dict),
        "VWRA": defaultdict(dict),
    }
    for symbol, anchor_id, steps, status, value_text, labelled in fetched:
        value = None if value_text is None else Decimal(value_text)
        grouped[str(symbol)][str(anchor_id)][int(steps)] = (str(status), value, labelled)
    return grouped


def _runs(connection: psycopg.Connection) -> list[MethodRun]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            select method_id, method_version, implementation_hash, config_hash,
                   parameter_policy, method_class, reconstruction, status, reason
            from research.discovery_v2_method_runs
            where specification_id = %s
            order by method_id
            """,
            (STORED_METHOD_SPECIFICATION,),
        )
        headers = cursor.fetchall()
        cursor.execute(
            """
            select method_id, series_key, period_start, period_end, value_text,
                   direction, change_text, state_label, unit
            from research.discovery_v2_method_points
            where specification_id = %s
            """,
            (STORED_METHOD_SPECIFICATION,),
        )
        points: dict[str, list[StoredPoint]] = defaultdict(list)
        for row in cursor.fetchall():
            points[str(row[0])].append(
                StoredPoint(
                    str(row[1]), row[2], row[3], row[4], row[5], row[6], row[7], str(row[8])
                )
            )
    if len(headers) != 26:
        raise RuntimeError(f"expected 26 stored methods, found {len(headers)}")
    return [
        MethodRun(
            str(method_id),
            str(method_version),
            str(implementation_hash),
            str(config_hash),
            str(parameter_policy),
            str(method_class),
            None if reconstruction is None else str(reconstruction),
            str(status),
            None if reason is None else str(reason),
            points[str(method_id)],
            (),
        )
        for (
            method_id,
            method_version,
            implementation_hash,
            config_hash,
            parameter_policy,
            method_class,
            reconstruction,
            status,
            reason,
        ) in headers
    ]


def _matched(
    anchors: dict[str, list[Anchor]],
    atlas: dict[str, dict[str, dict[str, str]]],
    runs: list[MethodRun],
    outcomes: dict[str, dict[str, dict[int, tuple[str, Decimal | None, bool | None]]]],
    units: dict[str, str],
) -> tuple[list[dict[str, Any]], dict[str, dict[str, str]]]:
    pairs = match_month_ends(
        tuple((anchor.anchor_id, anchor.session) for anchor in anchors["VWRA"]),
        tuple((anchor.anchor_id, anchor.session) for anchor in anchors["EIMI"]),
    )
    ordered = sorted(pairs, key=lambda item: (shared_date(item[1], item[3]), item[1], item[3]))
    synthetic = [
        Anchor(f"{vwra_id}__{eimi_id}", shared_date(vwra_day, eimi_day))
        for vwra_id, vwra_day, eimi_id, eimi_day, _gap in ordered
    ]
    method_panel: dict[str, dict[str, str]] = {anchor.anchor_id: {} for anchor in synthetic}
    _merge(method_panel, units, _joined_methods(synthetic, runs))
    rows: list[dict[str, Any]] = []
    panel: dict[str, dict[str, str]] = {}
    for vwra_id, vwra_day, eimi_id, eimi_day, gap in ordered:
        shared = shared_date(vwra_day, eimi_day)
        row_id = f"{vwra_id}__{eimi_id}"
        state: dict[str, str] = {}
        _copy_macro(state, atlas["EIMI"].get(eimi_id, {}), eimi_day, shared)
        _copy_macro(state, atlas["VWRA"].get(vwra_id, {}), vwra_day, shared)
        state.update(method_panel.get(row_id, {}))
        for feature, value in market_values(
            eimi_day, shared, atlas["EIMI"].get(eimi_id, {})
        ).items():
            state[f"EIMI:{feature}"] = value
        for feature, value in market_values(
            vwra_day, shared, atlas["VWRA"].get(vwra_id, {})
        ).items():
            state[f"VWRA:{feature}"] = value
        panel[row_id] = state
        rows.append(
            {
                "row_id": row_id,
                "vwra_day": vwra_day,
                "eimi_day": eimi_day,
                "shared": shared,
                "gap": gap,
                "eimi_126": _one_return(outcomes, "EIMI", eimi_id, PRIMARY_STEPS),
                "vwra_126": _one_return(outcomes, "VWRA", vwra_id, PRIMARY_STEPS),
                "eimi_id": eimi_id,
                "vwra_id": vwra_id,
            }
        )
    return rows, panel


def _copy_macro(
    target: dict[str, str], source: dict[str, str], anchor_day: date, shared: date
) -> None:
    if anchor_day > shared:
        return
    for feature, value in source.items():
        if feature.startswith("method:") or feature.startswith(("EIMI:", "VWRA:")):
            continue
        if feature.startswith(
            (
                "trailing_return_",
                "drawdown_",
                "volatility_",
                "recovery_",
                "relative_performance_",
                "downside_volatility_",
                "trend_persistence_",
            )
        ):
            continue
        previous = target.get(feature)
        if previous is not None and previous != value:
            raise RuntimeError(f"{feature} disagrees on the shared date")
        target[feature] = value


def _score_panel(panel: dict[str, dict[str, str]], symbol: str) -> dict[str, dict[str, str]]:
    prefix = symbol + ":"
    built: dict[str, dict[str, str]] = {}
    for row_id, features in panel.items():
        row = {
            key: value for key, value in features.items() if not key.startswith(("EIMI:", "VWRA:"))
        }
        for key, value in features.items():
            if key.startswith(prefix):
                row[key.removeprefix(prefix)] = value
        if PRICE_CONTROL in features:
            row[PRICE_CONTROL] = features[PRICE_CONTROL]
        if RELATIVE_CONTROL in features:
            row[RELATIVE_CONTROL] = features[RELATIVE_CONTROL]
        built[row_id] = row
    return built


def _horizon_rows(
    matched: list[dict[str, Any]],
    outcomes: dict[str, dict[str, dict[int, tuple[str, Decimal | None, bool | None]]]],
) -> list[dict[str, Decimal | None]]:
    rows: list[dict[str, Decimal | None]] = []
    for item in matched:
        row: dict[str, Decimal | None] = {}
        for steps in SESSION_STEPS.values():
            row[f"EIMI:{steps}"] = _one_return(outcomes, "EIMI", str(item["eimi_id"]), steps)
            row[f"VWRA:{steps}"] = _one_return(outcomes, "VWRA", str(item["vwra_id"]), steps)
        rows.append(row)
    return rows


def _portfolio(prices: dict[str, dict[date, PriceBar]]) -> dict[str, Any]:
    sessions = sorted(set(prices["VWRA"]) & set(prices["EIMI"]))
    sessions = [day for day in sessions if day >= MATCHED_NOT_BEFORE]
    blocked = _portfolio_block_reason(prices, sessions)
    configuration = {
        "portfolio_simulation": "not_called",
        "portfolio_path": "not_called",
        "portfolio_simulator": "not_called",
        "portfolio_comparison": "blocked",
        "point_in_time": False,
        "executable_strategy": False,
        "specification_id": SPECIFICATION_ID,
        "total_return": "not_represented",
        "sgd_investor_return": "not_represented",
        "macro_states_in_simulator": False,
        "catalogue_scenarios_executed": 0,
    }
    if blocked:
        statement = (
            f"The price-only comparison is blocked. {blocked} "
            "No wealth path was stored. It is not a total return, not an SGD investor return, "
            "not economically useful, and not forward-validated."
        )
        return {
            "blocked": True,
            "claim_status": "insufficient_data",
            "execution_state": "blocked",
            "reason": blocked,
            "statement": statement,
            "wealth": {},
            "configuration": configuration,
            "catalogue_scenarios_executed": 0,
        }
    first_of_month: dict[tuple[int, int], date] = {}
    for session in sessions:
        first_of_month.setdefault((session.year, session.month), session)
    contribution_dates = [first_of_month[key] for key in sorted(first_of_month)]
    contributions = [
        CashFlow(session, Decimal(PILOT_CONTRIBUTION), "contribution")
        for session in contribution_dates
    ]
    january = {session for session in contribution_dates if session.month == 1}
    shared = {
        "sessions": sessions,
        "prices": prices,
        "contributions": contributions,
        "portfolio_currency": "USD",
        "cost_rate": Decimal(PILOT_COST_RATE),
        "cash_interest_rate": Decimal(PILOT_INTEREST_RATE),
        "requires_distributions": False,
    }
    try:
        passive = simulate(
            policy=ImmediateSingleAssetPolicy("VWRA"), rebalance_sessions=set(), **shared
        )
        eimi = simulate(
            policy=ImmediateSingleAssetPolicy("EIMI", name="immediate_eimi"),
            rebalance_sessions=set(),
            **shared,
        )
        mix = simulate(policy=EqualCashMixPolicy(), rebalance_sessions=january, **shared)
        momentum_policy = RelativeMomentumPolicy(prices)
        momentum = simulate(policy=momentum_policy, rebalance_sessions=set(), **shared)
    except SimulatorError as exc:
        statement = (
            f"The price-only comparison is blocked. {exc} "
            "No wealth path was stored. It is not a total return, not an SGD investor return, "
            "not economically useful, and not forward-validated."
        )
        return {
            "blocked": True,
            "claim_status": "insufficient_data",
            "execution_state": "blocked",
            "reason": str(exc),
            "statement": statement,
            "wealth": {},
            "configuration": configuration,
            "catalogue_scenarios_executed": 0,
        }
    wealth = {
        "immediate_vwra": decimal_text(passive.terminal_wealth),
        "immediate_eimi": decimal_text(eimi.terminal_wealth),
        "static_mix": decimal_text(mix.terminal_wealth),
        "relative_momentum": decimal_text(momentum.terminal_wealth),
    }
    status = portfolio_claim_status(
        reconciled=True,
        passive_terminal=passive.terminal_wealth,
        alternatives={
            "immediate_eimi": eimi.terminal_wealth,
            "static_mix": mix.terminal_wealth,
            "relative_momentum": momentum.terminal_wealth,
        },
    )
    configuration = {
        "portfolio_simulation": "price_return_provisional",
        "portfolio_path": "called",
        "portfolio_simulator": "called",
        "portfolio_comparison": "provisional_not_total_return",
        "point_in_time": False,
        "executable_strategy": False,
        "specification_id": SPECIFICATION_ID,
        "total_return": "not_represented",
        "sgd_investor_return": "not_represented",
        "macro_states_in_simulator": False,
        "catalogue_scenarios_executed": 0,
    }
    return {
        "blocked": False,
        "claim_status": status,
        "execution_state": "succeeded",
        "reason": None,
        "statement": portfolio_statement(status, wealth),
        "wealth": wealth,
        "ending_cash": {
            "immediate_vwra": decimal_text(passive.ending_cash),
            "immediate_eimi": decimal_text(eimi.ending_cash),
            "static_mix": decimal_text(mix.ending_cash),
            "relative_momentum": decimal_text(momentum.ending_cash),
        },
        "total_costs": {
            "immediate_vwra": decimal_text(passive.total_costs),
            "immediate_eimi": decimal_text(eimi.total_costs),
            "static_mix": decimal_text(mix.total_costs),
            "relative_momentum": decimal_text(momentum.total_costs),
        },
        "ending_units": {
            "immediate_vwra": passive.ending_units,
            "immediate_eimi": eimi.ending_units,
            "static_mix": mix.ending_units,
            "relative_momentum": momentum.ending_units,
        },
        "session_count": len(sessions),
        "contribution_count": len(contributions),
        "start": sessions[0].isoformat(),
        "end": sessions[-1].isoformat(),
        "fallbacks": momentum_policy.fallbacks,
        "ties": momentum_policy.ties,
        "eimi_choices": sum(1 for choice in momentum_policy.choices if choice == "EIMI"),
        "vwra_choices": sum(1 for choice in momentum_policy.choices if choice == "VWRA"),
        "missing_eimi_on_vwra_sessions": sum(
            1 for day in prices["VWRA"] if day >= MATCHED_NOT_BEFORE and day not in prices["EIMI"]
        ),
        "configuration": configuration,
        "catalogue_scenarios_executed": 0,
        "price_type": "adjusted_close",
    }


def _portfolio_block_reason(
    prices: dict[str, dict[date, PriceBar]], sessions: list[date]
) -> str | None:
    if not sessions or sessions[0] != MATCHED_NOT_BEFORE:
        return "the common window does not start on 2019-07-25"
    if sessions != sorted(set(sessions)):
        return "a session would have to be manufactured"
    for session in sessions:
        for symbol in ("EIMI", "VWRA"):
            bar = prices[symbol].get(session)
            if bar is None or bar.currency != "USD" or bar.price <= 0:
                return f"{symbol} has no stored US-dollar close on {session.isoformat()}"
    return None


def _portfolio_finding(portfolio: dict[str, Any]) -> Finding:
    claim = str(portfolio["claim_status"])
    finding_class = "insufficient_sample" if claim == "insufficient_data" else claim
    if finding_class not in {"insufficient_sample", "inconclusive", "rejected"}:
        raise RuntimeError("the portfolio finding is not an allowed class")
    return Finding(
        "CMP-F-018",
        "LH-H-018",
        "LH-E-018",
        finding_class,
        str(portfolio["statement"]),
    )


def _census_trials(rows: tuple[MethodCensus, ...]) -> list[ScoredTrial]:
    experiment = experiment_id("LH-H-012")
    trials: list[ScoredTrial] = []
    for row in rows:
        earliest = row.earliest.isoformat() if row.earliest else "none"
        latest = row.latest.isoformat() if row.latest else "none"
        detail = (
            f"class={row.method_class}. version={row.method_version}. "
            f"components={row.component_count}. distinct_dates={row.distinct_dates}. "
            f"window={row.sample_window}. monthly_state_transition={row.monthly_state_transition}. "
            f"timeline={row.timeline}. clock={row.clock}. "
            f"reconstruction={row.reconstruction or 'none'}. "
            f"earliest={earliest}. latest={latest}. "
            "Components are not distinct dates. This census is not an EIMI score."
        )
        if row.status == "succeeded" and row.component_count > 0:
            trials.append(
                _raw(
                    "REGISTRY",
                    experiment,
                    row.method_id,
                    None,
                    "timeline_census",
                    "not_an_outcome",
                    row.component_count,
                    0,
                    f"dates={row.distinct_dates}; components={row.component_count}",
                    None,
                    "descriptive",
                    detail,
                )
            )
        else:
            trials.append(
                _raw(
                    "REGISTRY",
                    experiment,
                    row.method_id,
                    None,
                    "timeline_census",
                    "not_an_outcome",
                    row.component_count,
                    0,
                    None,
                    row.reason or row.status,
                    "insufficient_sample",
                    detail,
                )
            )
    return trials


def _skipped(skipped: dict[str, int], experiment: str, symbol: str) -> list[ScoredTrial]:
    trials: list[ScoredTrial] = []
    for feature, count in sorted(skipped.items()):
        trials.append(
            _raw(
                symbol,
                experiment,
                feature,
                None,
                "not_continuous",
                "not_an_outcome",
                count,
                0,
                None,
                "not_continuous",
                "insufficient_sample",
                f"skipped={count}. A direction label is not a monthly numeric state.",
            )
        )
    return trials


def _coverage(
    anchors: dict[str, list[Anchor]],
    prices: dict[str, dict[date, PriceBar]],
    outcomes: dict[str, dict[str, dict[int, tuple[str, Decimal | None, bool | None]]]],
    matched: list[dict[str, Any]],
    census: tuple[MethodCensus, ...],
    eimi_keeps: int,
    matched_keeps: int,
    eimi_logistic: bool,
    matched_logistic: bool,
    sequence_counts: dict[str, object],
    trials: list[ScoredTrial],
) -> dict[str, Any]:
    ends = [row.earliest for row in census if row.earliest is not None]
    lasts = [row.latest for row in census if row.latest is not None]
    executed = sum(1 for row in trials if row.trial.result_text is not None)
    refused = sum(1 for row in trials if row.trial.refusal_reason is not None)
    return {
        "eimi_anchors": len(anchors["EIMI"]),
        "eimi_first_anchor": anchors["EIMI"][0].session.isoformat(),
        "eimi_last_anchor": anchors["EIMI"][-1].session.isoformat(),
        "eimi_first_session": min(prices["EIMI"]).isoformat(),
        "eimi_sessions": len(prices["EIMI"]),
        "vwra_anchors": len(anchors["VWRA"]),
        "vwra_first_anchor": anchors["VWRA"][0].session.isoformat(),
        "vwra_last_anchor": anchors["VWRA"][-1].session.isoformat(),
        "matched_anchors": len(matched),
        "matched_first": None if not matched else matched[0]["shared"].isoformat(),
        "matched_last": None if not matched else matched[-1]["shared"].isoformat(),
        "matched_max_gap_days": 0 if not matched else max(int(row["gap"]) for row in matched),
        "outcomes": {
            symbol: {
                str(steps): {
                    "observed": sum(
                        1
                        for anchor in grouped.values()
                        if steps in anchor and anchor[steps][0] == "observed"
                    ),
                    "censored": sum(
                        1
                        for anchor in grouped.values()
                        if steps in anchor and anchor[steps][0] == "censored"
                    ),
                }
                for steps in SESSION_STEPS.values()
            }
            for symbol, grouped in outcomes.items()
        },
        "eimi_non_overlapping_126": eimi_keeps,
        "matched_non_overlapping_126": matched_keeps,
        "eimi_logistic_allowed": eimi_logistic,
        "matched_logistic_allowed": matched_logistic,
        "point_in_time_methodology_outputs": 0,
        "method_components": sum(row.component_count for row in census),
        "method_distinct_dates_sum": sum(row.distinct_dates for row in census),
        "method_earliest": None if not ends else min(ends).isoformat(),
        "method_latest": None if not lasts else max(lasts).isoformat(),
        "sequence_status": str(sequence_counts["comparison_status"]),
        "sequence_finding": sequence_finding(str(sequence_counts["comparison_status"])),
        "executed_trials": executed,
        "refused_trials": refused,
        "publication_allowed": False,
        "catalogue_scenarios_executed": 0,
        "fx_observations": 0,
        "price_type": "adjusted_close",
    }


def _windows(
    bodies: dict[str, dict[str, Any]],
    coverage: dict[str, Any],
    portfolio: dict[str, Any],
) -> None:
    eimi = (coverage["eimi_first_anchor"], coverage["eimi_last_anchor"])
    matched = (coverage["matched_first"], coverage["matched_last"])
    methods = (coverage["method_earliest"], coverage["method_latest"])
    if portfolio["blocked"]:
        path: tuple[str | None, str | None] = (None, None)
    else:
        path = (str(portfolio["start"]), str(portfolio["end"]))
    windows = {
        "LH-X-012": methods,
        "LH-X-013": eimi,
        "LH-X-014": eimi,
        "LH-X-015": eimi,
        "LH-X-016": matched,
        "LH-X-017": matched,
        "LH-X-018": path,
    }
    for execution_id, (start, end) in windows.items():
        bodies[execution_id]["simulation_start"] = start
        bodies[execution_id]["simulation_end"] = end


def _feature_rows(features: list[AnchorFeature]) -> list[tuple[Any, ...]]:
    rows: list[tuple[Any, ...]] = []
    seen: set[tuple[str, str]] = set()
    for feature in features:
        if feature.value_text is None and feature.state_label is None:
            continue
        key = (feature.anchor_id, feature.feature_id)
        if key in seen:
            raise RuntimeError(f"duplicate feature {feature.feature_id}")
        seen.add(key)
        if feature.period_end > feature.anchor_session:
            raise RuntimeError("a later period cannot be stored on this anchor")
        rows.append(
            (
                feature.anchor_id,
                feature.feature_id,
                feature.anchor_session,
                feature.period_end,
                feature.value_text,
                feature.state_label,
                feature.unit,
                feature.source,
                feature.method_id,
                feature.reconstruction,
            )
        )
    return rows


def _merge(
    panel: dict[str, dict[str, str]],
    units: dict[str, str],
    features: list[AnchorFeature],
) -> None:
    for feature in features:
        if feature.value_text is None:
            continue
        panel.setdefault(feature.anchor_id, {})
        panel[feature.anchor_id][feature.feature_id] = feature.value_text
        units[feature.feature_id] = feature.unit


def _return_map(
    outcomes: dict[str, dict[str, dict[int, tuple[str, Decimal | None, bool | None]]]],
    symbol: str,
    steps: int,
) -> dict[str, Decimal | None]:
    return {
        anchor_id: _one_return(outcomes, symbol, anchor_id, steps) for anchor_id in outcomes[symbol]
    }


def _one_return(
    outcomes: dict[str, dict[str, dict[int, tuple[str, Decimal | None, bool | None]]]],
    symbol: str,
    anchor_id: str,
    steps: int,
) -> Decimal | None:
    found = outcomes[symbol].get(anchor_id, {}).get(steps)
    if found is None or found[0] != "observed" or found[1] is None:
        return None
    return found[1]


def _assert_labels(
    outcomes: dict[str, dict[str, dict[int, tuple[str, Decimal | None, bool | None]]]],
) -> None:
    for grouped in outcomes.values():
        for horizons in grouped.values():
            found = horizons.get(PRIMARY_STEPS)
            if found is None or found[1] is None or found[2] is None:
                continue
            if found[2] != is_advance(found[1]):
                raise RuntimeError("a stored advance label disagrees with the frozen 0.10 rule")


def _thinned(
    row_ids: list[str],
    session_of: dict[str, date],
    index_by_session: dict[date, int],
) -> list[str]:
    ordered = [row_id for row_id in row_ids if session_of.get(row_id) in index_by_session]
    indexes = [index_by_session[session_of[row_id]] for row_id in ordered]
    kept = set(thin_indexes(indexes))
    return [row_id for row_id in ordered if index_by_session[session_of[row_id]] in kept]


def _dates(bars: dict[date, PriceBar]) -> tuple[date, ...]:
    return tuple(sorted(bars))


def _closes(bars: dict[date, PriceBar]) -> tuple[Decimal, ...]:
    return tuple(bars[day].price for day in sorted(bars))


def _index(bars: dict[date, PriceBar]) -> dict[date, int]:
    return {day: index for index, day in enumerate(sorted(bars))}


def _assert_registry(rows: tuple[MethodCensus, ...]) -> None:
    by_id = {row.method_id: row for row in rows}
    if by_id["INFLATION_AUTOREGRESSION"].status != "failed":
        raise RuntimeError("inflation autoregression is not the stored failure")
    if by_id["CENSUS_ADV_DURABLE_ORDERS"].status != "unavailable":
        raise RuntimeError("census advance orders are not the stored unavailable method")
    if by_id["MACRO_CONDITIONS_PANEL"].status != "unavailable":
        raise RuntimeError("the macro-conditions panel is not the stored unavailable method")
    if any(row.clock != "retrospective" for row in rows):
        raise RuntimeError("a method census row is not retrospective")


def _existing_executions(connection: psycopg.Connection) -> bool:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            select count(*)::int
            from research.experiment_executions
            where execution_id = any(%s)
            """,
            ([f"LH-X-{index:03d}" for index in range(12, 19)],),
        )
        return int(cursor.fetchone()[0]) > 0


def _snapshot(connection: psycopg.Connection) -> dict[str, object]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            select execution_id, artifact_sha256
            from research.experiment_executions
            where execution_id = any(%s)
            order by execution_id
            """,
            (list(PROTECTED_EXECUTIONS),),
        )
        executions = tuple((str(row[0]), str(row[1])) for row in cursor.fetchall())
        cursor.execute("select count(*)::int from research.discovery_v2_method_points")
        points = int(cursor.fetchone()[0])
        cursor.execute("select count(*)::int from research.discovery_v2_method_runs")
        runs = int(cursor.fetchone()[0])
        cursor.execute(
            """
            select count(*)::int
            from research.discovery_v2_trials
            where specification_id = %s
            """,
            (STORED_METHOD_SPECIFICATION,),
        )
        trials = int(cursor.fetchone()[0])
        cursor.execute(
            """
            select count(*)::int
            from research.discovery_v2_anchor_features f
            join research.decision_anchors a on a.anchor_id = f.anchor_id
            where a.symbol = 'VWRA'
            """
        )
        features = int(cursor.fetchone()[0])
    return {
        "executions": executions,
        "points": points,
        "runs": runs,
        "trials": trials,
        "vwra_features": features,
    }


def _assert_unchanged(before: dict[str, object], after: dict[str, object]) -> None:
    if before != after:
        raise RuntimeError("stored VWRA discovery rows changed and the comparison was rolled back")


def _assert_unpublished(connection: psycopg.Connection) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            select count(*)::int
            from research.discovery_v2_trials
            where specification_id = %s and publication_allowed
            """,
            (SPECIFICATION_ID,),
        )
        if int(cursor.fetchone()[0]) != 0:
            raise RuntimeError("publication_allowed was set and the comparison was rolled back")


if __name__ == "__main__":
    main()
