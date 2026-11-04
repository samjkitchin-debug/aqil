"""Score CNDX and the matched excess. The specification is already frozen.

persist=False rolls back. A second persist inserts nothing when the artifact matches.
Earlier executions are not rewritten. publication_allowed stays false.
"""

from __future__ import annotations

import hashlib
from collections import defaultdict
from datetime import UTC, date, datetime
from decimal import Decimal
from importlib.metadata import PackageNotFoundError, version
from typing import Any

import psycopg

from aqil_research.certification.baselines import (
    BaselineError,
    CalendarRebalancePolicy,
    CashFlowOnlyPolicy,
    ThresholdRebalancePolicy,
    common_sessions,
    equal_weights,
)
from aqil_research.certification.vintage_gate import load_registered_assessment
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
    is_market_feature,
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
    experiment_id,
    grid_holds,
    score_excess_pairs,
    score_features,
    score_horizons,
    score_named_associations,
    score_pairs,
    score_sequence,
)
from aqil_research.long_horizon.vwra_discovery.cndx_comparison import (
    BLOCKED_PORTFOLIO_PATHS,
    EXCLUSIVE_CLASSES,
    EXCLUSIVE_RENAME,
    HYPOTHESES,
    MATCHED_NOT_BEFORE,
    PAIR,
    PEER,
    PRICE_CONTROL,
    REAL_GDP_FEATURE,
    RELATIVE_CONTROL,
    SPECIFICATION_ID,
    STATIC_MIX,
    THRESHOLD_BAND,
    TOLERANCE_DAYS,
    UNEMPLOYMENT_FEATURE,
    excess_survives_price_control,
    matched_floor,
    refuse_before_listing,
    relative_classification,
    specification_hash,
)
from aqil_research.long_horizon.vwra_discovery.cndx_report import write_documents
from aqil_research.long_horizon.vwra_discovery.cndx_score import (
    assign_cndx_ids,
    casebook_rows,
    findings_for_cndx,
)
from aqil_research.long_horizon.vwra_discovery.cndx_store import artifact_bodies, store_comparison
from aqil_research.long_horizon.vwra_discovery.compare import (
    _assert_registry,
    _dates,
    _feature_rows,
    _index,
    _merge,
    _one_return,
    _return_map,
    _runs,
    _skipped,
    _thinned,
)
from aqil_research.long_horizon.vwra_discovery.comparison import (
    excess_return,
    is_advance,
    is_decline,
    match_month_ends,
    portfolio_claim_status,
    portfolio_statement,
    shared_date,
)
from aqil_research.long_horizon.vwra_discovery.dossier import (
    Anchor,
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
from aqil_research.long_horizon.vwra_discovery.replay import MethodRun
from aqil_research.long_horizon.vwra_discovery.specification import sequence_finding
from aqil_research.long_horizon.vwra_discovery.statistics import (
    atlas_unit,
    model_allowed,
    parse_decimal,
)

PRIMARY_STEPS = SESSION_STEPS["6m"]
PROTECTED_EXECUTIONS = tuple(f"LH-X-{index:03d}" for index in range(1, 19))
EARLIER_SPECIFICATIONS = ("VWRA-DISCOVERY-001", "EIMI-VWRA-COMPARISON-001")


def run(*, persist: bool) -> dict[str, object]:
    """Read stored inputs, score, and append the new chain once."""
    assert_loopback(LOCAL_RESEARCH_URL, "postgres")
    assert_loopback(LOCAL_ETF_URL, "aqil_etf")
    with psycopg.connect(LOCAL_ETF_URL) as etf:
        prices, price_hashes = _load_prices(etf)
        fx_count = _fx_count(etf)
        next_etf = _next_etf(etf)
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
        prepared["records"] = {
            "earlier": _earlier_trials(research),
            "vintage": _vintage_facts(research),
            "next_etf": next_etf,
            "census_markdown": render_coverage(census),
            "assessment_blocker": load_registered_assessment().blocker,
        }
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
                    "cndx_anchors": prepared["coverage"]["cndx_anchors"],
                    "matched_anchors": prepared["coverage"]["matched_anchors"],
                    "fx_observations": 0,
                    "publication_allowed": False,
                    "point_in_time": False,
                    "catalogue_scenarios_executed": 0,
                    "bea_vintage_used_as_decision_input": False,
                    "total_return": "not_represented",
                },
                price_series_versions=[
                    {
                        "symbol": symbol,
                        "sha256": price_hashes[symbol],
                        "price_type": "adjusted_close",
                        "currency": "USD",
                    }
                    for symbol in (PEER, "VWRA")
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
            git_commit=commit,
            folder=repo_root() / "docs" / "research" / "cndx-discovery",
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
    _refuse_early_anchors(anchors, prices)
    floor = matched_floor(min(prices[PEER]), min(prices["VWRA"]))
    if floor != MATCHED_NOT_BEFORE:
        raise RuntimeError("the later stored session is not 2019-07-25 and was not retuned")
    atlas, units, skipped = _atlas(connection)
    outcomes = _outcomes(connection)
    _assert_labels(outcomes)
    runs = _runs(connection)
    added = _added_market(
        anchors[PEER], _dates(prices[PEER]), _closes(prices[PEER]), _index(prices[PEER])
    )
    methods = _joined_methods(anchors[PEER], runs)
    _merge(atlas[PEER], units, added)
    battery_panel = {
        anchor.anchor_id: dict(atlas[PEER].get(anchor.anchor_id, {})) for anchor in anchors[PEER]
    }
    _merge(battery_panel, units, methods)
    units[PRICE_CONTROL] = "ratio"
    units[RELATIVE_CONTROL] = "ratio"
    peer_ids = [anchor.anchor_id for anchor in anchors[PEER]]
    peer_returns = _return_map(outcomes, PEER, PRIMARY_STEPS)
    peer_thinned = _thinned(
        [anchor_id for anchor_id in peer_ids if peer_returns.get(anchor_id) is not None],
        {anchor.anchor_id: anchor.session for anchor in anchors[PEER]},
        _index(prices[PEER]),
    )
    peer_positive = {
        anchor_id: None if value is None else is_advance(value)
        for anchor_id, value in ((item, peer_returns.get(item)) for item in peer_ids)
    }
    peer_negative = {
        anchor_id: None if value is None else is_decline(value)
        for anchor_id, value in ((item, peer_returns.get(item)) for item in peer_ids)
    }
    reasons = {run.method_id: run.reason or run.status for run in runs if run.status != "succeeded"}
    hypotheses = HYPOTHESES
    trials: list[ScoredTrial] = []
    trials.extend(_census_trials(census))
    trials.extend(_skipped(skipped[PEER], experiment_id("LH-H-020", hypotheses), PEER))
    trials.extend(
        score_features(
            hypothesis_id="LH-H-020",
            hypotheses=hypotheses,
            symbol=PEER,
            panel=battery_panel,
            units=units,
            row_ids=peer_ids,
            outcomes=peer_returns,
            positive_labels=peer_positive,
            negative_labels=peer_negative,
            thinned_ids=peer_thinned,
            non_overlapping=len(peer_thinned),
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
            hypothesis_id="LH-H-021",
            hypotheses=hypotheses,
            symbol=PEER,
            panel=battery_panel,
            row_ids=peer_ids,
            positive_labels=peer_positive,
            negative_labels=peer_negative,
            non_overlapping=len(peer_thinned),
            reasons=reasons,
            positive_statistic="conditional_advance",
            positive_outcome="advance_126",
            negative_statistic="conditional_decline",
            negative_outcome="decline_126",
        )
    )
    sequence_counts, sequence_trials = score_sequence(
        hypothesis_id="LH-H-022",
        hypotheses=hypotheses,
        symbol=PEER,
        panel=battery_panel,
        row_ids=peer_ids,
        labels=[peer_positive[anchor_id] for anchor_id in peer_ids],
        non_overlapping=len(peer_thinned),
        outcome_name="advance_126",
        label_note=(
            "The label is a CNDX advance of at least 0.10. "
            "The 0.05 binary is not substituted."
        ),
    )
    trials.extend(sequence_trials)
    matched, matched_panel = _matched(anchors, atlas, runs, outcomes, units, floor)
    matched_ids = [str(row["row_id"]) for row in matched]
    matched_outcomes = {
        str(row["row_id"]): {
            "cndx_return_126": row["cndx_126"],
            "vwra_return_126": row["vwra_126"],
            "excess_126": excess_return(row["cndx_126"], row["vwra_126"]),
        }
        for row in matched
    }
    excess_values = {row_id: values["excess_126"] for row_id, values in matched_outcomes.items()}
    cndx_leg = {row_id: values["cndx_return_126"] for row_id, values in matched_outcomes.items()}
    vwra_leg = {row_id: values["vwra_return_126"] for row_id, values in matched_outcomes.items()}
    matched_session = {str(row["row_id"]): row["vwra_day"] for row in matched}
    matched_thinned = _thinned(
        [row_id for row_id, value in excess_values.items() if value is not None],
        matched_session,
        _index(prices["VWRA"]),
    )
    panels = {
        PEER: _score_panel(matched_panel, PEER),
        "VWRA": _score_panel(matched_panel, "VWRA"),
        PAIR: _score_panel(matched_panel, PEER),
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
            PEER,
            cndx_leg,
            {key: None if value is None else is_advance(value) for key, value in cndx_leg.items()},
            {key: None if value is None else is_decline(value) for key, value in cndx_leg.items()},
            "cndx_return_126",
            "conditional_advance",
            "conditional_decline",
            "cndx_advance_126",
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
            PAIR,
            excess_values,
            {key: None if value is None else value > 0 for key, value in excess_values.items()},
            {key: None if value is None else value < 0 for key, value in excess_values.items()},
            "excess_126",
            "conditional_cndx_ahead",
            "conditional_vwra_ahead",
            "excess_positive_126",
        ),
    ):
        feature_trials.extend(
            score_features(
                hypothesis_id="LH-H-023",
                hypotheses=hypotheses,
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
    _apply_bh(feature_trials, experiment_id("LH-H-023", hypotheses), PAIR)
    trials.extend(feature_trials)
    trials.extend(
        score_horizons(
            _horizon_rows(matched, outcomes),
            peer=PEER,
            pair_symbol=PAIR,
            hypothesis_id="LH-H-023",
            hypotheses=hypotheses,
            class_names=EXCLUSIVE_CLASSES,
            rename=EXCLUSIVE_RENAME,
        )
    )
    trials.extend(
        score_named_associations(
            panels[PAIR],
            matched_ids,
            matched_outcomes,
            len(matched_thinned),
            peer=PEER,
            peer_outcome="cndx_return_126",
            control_outcome="vwra_return_126",
            excess_outcome="excess_126",
            pair_symbol=PAIR,
            relation_outcome="cndx_minus_vwra",
            peer_label="cndx",
            hypothesis_id="LH-H-023",
            hypotheses=hypotheses,
            price_control=PRICE_CONTROL,
            relative_control=RELATIVE_CONTROL,
        )
    )
    trials.extend(
        score_excess_pairs(
            panels[PAIR],
            matched_ids,
            matched_outcomes,
            len(matched_thinned),
            reasons,
            pair_symbol=PAIR,
            hypothesis_id="LH-H-023",
            hypotheses=hypotheses,
            positive_statistic="conditional_cndx_ahead",
            positive_outcome="cndx_ahead_126",
            negative_statistic="conditional_vwra_ahead",
            negative_outcome="vwra_ahead_126",
            conjunction_outcome="cndx_ahead_126",
            relative_control=RELATIVE_CONTROL,
        )
    )
    for symbol, panel_name, labels, outcome_name, note in (
        (
            PEER,
            PEER,
            [None if row["cndx_126"] is None else is_advance(row["cndx_126"]) for row in matched],
            "cndx_advance_126",
            "Matched CNDX. The label is an absolute advance of at least 0.10.",
        ),
        (
            "VWRA",
            "VWRA",
            [None if row["vwra_126"] is None else is_advance(row["vwra_126"]) for row in matched],
            "vwra_advance_126",
            "Matched VWRA. The label is an absolute advance of at least 0.10.",
        ),
        (
            PAIR,
            PAIR,
            [
                None
                if excess_return(row["cndx_126"], row["vwra_126"]) is None
                else excess_return(row["cndx_126"], row["vwra_126"]) > 0
                for row in matched
            ],
            "excess_positive_126",
            "The label is excess greater than zero. That is not an absolute advance.",
        ),
    ):
        _counts, rows = score_sequence(
            hypothesis_id="LH-H-023",
            hypotheses=hypotheses,
            symbol=symbol,
            panel=panels[panel_name],
            row_ids=matched_ids,
            labels=labels,
            non_overlapping=len(matched_thinned),
            outcome_name=outcome_name,
            label_note=note,
        )
        trials.extend(rows)
    unemployment_partial = _coefficient(
        trials,
        symbol=PAIR,
        feature=UNEMPLOYMENT_FEATURE,
        statistic="partial_spearman",
        outcome="excess_126",
        paired=PRICE_CONTROL,
    )
    gdp_partial = _coefficient(
        trials,
        symbol=PAIR,
        feature=REAL_GDP_FEATURE,
        statistic="partial_spearman",
        outcome="excess_126",
        paired=PRICE_CONTROL,
    )
    control_spearman = _coefficient(
        trials,
        symbol=PAIR,
        feature=RELATIVE_CONTROL,
        statistic="spearman",
        outcome="excess_126",
        paired=None,
    )
    unemployment_survives = excess_survives_price_control(unemployment_partial, control_spearman)
    gdp_survives = excess_survives_price_control(gdp_partial, control_spearman)
    classification = relative_classification(unemployment_survives, gdp_survives)
    trials.append(
        _raw(
            PAIR,
            experiment_id("LH-H-023", hypotheses),
            "relative_classification",
            PRICE_CONTROL,
            "predeclared_rule",
            "excess_126",
            len(matched_ids),
            len(matched_thinned),
            classification,
            None,
            "descriptive",
            (
                f"unemployment_partial_spearman={_text(unemployment_partial)}. "
                f"real_gdp_partial_spearman={_text(gdp_partial)}. "
                f"relative_control_spearman={_text(control_spearman)}. "
                "Survival requires the absolute excess partial to exceed the absolute "
                "price-only relative-performance Spearman. A miss is structural exposure "
                "or price momentum, not macroeconomic information. "
                "The rule was frozen before the score. Benjamini-Hochberg cannot promote it."
            ),
        )
    )
    cases = casebook_rows(matched, panels[PAIR])
    portfolio = _portfolio(prices, floor)
    findings = findings_for_cndx(
        trials,
        str(sequence_counts["comparison_status"]),
        classification,
        cases,
    )
    findings.append(_portfolio_finding(portfolio))
    assign_cndx_ids(trials, cases)
    if not grid_holds(trials):
        raise RuntimeError("the trial grid does not account for every row")
    coverage = _coverage(
        anchors,
        prices,
        outcomes,
        matched,
        census,
        len(peer_thinned),
        len(matched_thinned),
        model_allowed(
            sum(1 for value in peer_returns.values() if value is not None),
            len(peer_thinned),
        ),
        model_allowed(
            sum(1 for value in excess_values.values() if value is not None),
            len(matched_thinned),
        ),
        sequence_counts,
        classification,
        unemployment_survives,
        gdp_survives,
        trials,
    )
    bodies = artifact_bodies(trials, cases, findings, coverage, portfolio)
    _windows(bodies, coverage, portfolio)
    hashes = {key: sha256_document(value) for key, value in bodies.items()}
    return {
        "trials": trials,
        "cases": cases,
        "findings": findings,
        "features": _feature_rows(added + methods),
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
            where l.ticker in ('CNDX', 'VWRA')
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
    if set(prices) != {PEER, "VWRA"}:
        raise RuntimeError("CNDX and VWRA stored closes are required")
    first = min(prices[PEER])
    for session in prices[PEER]:
        refuse_before_listing(session, first, PEER)
    hashes = {
        ticker: hashlib.sha256("\n".join(rows).encode("utf-8")).hexdigest()
        for ticker, rows in per_symbol.items()
    }
    return prices, hashes


def _fx_count(connection: psycopg.Connection) -> int:
    with connection.cursor() as cursor:
        cursor.execute("select count(*)::int from instruments.fx_observations")
        return int(cursor.fetchone()[0])


def _next_etf(connection: psycopg.Connection) -> list[dict[str, object]]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            select l.ticker, l.trading_currency, count(*)::int,
                   min(p.session_date), max(p.session_date)
            from instruments.listings l
            join instruments.market_price_observations p on p.listing_id = l.listing_id
            where p.price_type = 'adjusted_close'
              and p.adjustment_status = 'adjusted'
              and l.ticker in ('CSPX', 'IWDA', 'IUIT')
            group by l.ticker, l.trading_currency
            order by l.ticker
            """
        )
        rows = cursor.fetchall()
    return [
        {
            "ticker": ticker,
            "currency": currency,
            "sessions": count,
            "first": first.isoformat(),
            "last": last.isoformat(),
        }
        for ticker, currency, count, first, last in rows
    ]


def _anchors(connection: psycopg.Connection) -> dict[str, list[Anchor]]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            select symbol, anchor_id, session_date
            from research.decision_anchors
            where symbol in ('CNDX', 'VWRA')
              and anchor_kind = 'listing_month_end'
            order by symbol, session_date
            """
        )
        grouped: dict[str, list[Anchor]] = {PEER: [], "VWRA": []}
        for symbol, anchor_id, session in cursor.fetchall():
            grouped[str(symbol)].append(Anchor(str(anchor_id), session))
    if not grouped[PEER] or not grouped["VWRA"]:
        raise RuntimeError("CNDX and VWRA month-end anchors are required")
    return grouped


def _refuse_early_anchors(
    anchors: dict[str, list[Anchor]], prices: dict[str, dict[date, PriceBar]]
) -> None:
    for symbol in (PEER, "VWRA"):
        first = min(prices[symbol])
        for anchor in anchors[symbol]:
            refuse_before_listing(anchor.session, first, symbol)


def _atlas(
    connection: psycopg.Connection,
) -> tuple[dict[str, dict[str, dict[str, str]]], dict[str, str], dict[str, dict[str, int]]]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            select a.symbol, s.anchor_id, s.feature_id, s.availability, s.value_text, s.clock
            from research.state_observations s
            join research.decision_anchors a on a.anchor_id = s.anchor_id
            where a.symbol in ('CNDX', 'VWRA')
              and a.anchor_kind = 'listing_month_end'
            """
        )
        fetched = cursor.fetchall()
    panels: dict[str, dict[str, dict[str, str]]] = {
        PEER: defaultdict(dict),
        "VWRA": defaultdict(dict),
    }
    units: dict[str, str] = {}
    skipped: dict[str, dict[str, int]] = {PEER: defaultdict(int), "VWRA": defaultdict(int)}
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
            select a.symbol, o.anchor_id, o.session_steps, o.status,
                   o.value_text, o.labelled_advance
            from research.outcome_measures o
            join research.decision_anchors a on a.anchor_id = o.anchor_id
            where a.symbol in ('CNDX', 'VWRA')
              and a.anchor_kind = 'listing_month_end'
            """
        )
        fetched = cursor.fetchall()
    grouped: dict[str, dict[str, dict[int, tuple[str, Decimal | None, bool | None]]]] = {
        PEER: defaultdict(dict),
        "VWRA": defaultdict(dict),
    }
    for symbol, anchor_id, steps, status, value_text, labelled in fetched:
        value = None if value_text is None else Decimal(value_text)
        grouped[str(symbol)][str(anchor_id)][int(steps)] = (str(status), value, labelled)
    return grouped


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


def _matched(
    anchors: dict[str, list[Anchor]],
    atlas: dict[str, dict[str, dict[str, str]]],
    runs: list[MethodRun],
    outcomes: dict[str, dict[str, dict[int, tuple[str, Decimal | None, bool | None]]]],
    units: dict[str, str],
    floor: date,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, str]]]:
    pairs = match_month_ends(
        tuple((anchor.anchor_id, anchor.session) for anchor in anchors["VWRA"]),
        tuple((anchor.anchor_id, anchor.session) for anchor in anchors[PEER]),
    )
    ordered = sorted(pairs, key=lambda item: (shared_date(item[1], item[3]), item[1], item[3]))
    synthetic = [
        Anchor(f"{vwra_id}__{peer_id}", shared_date(vwra_day, peer_day))
        for vwra_id, vwra_day, peer_id, peer_day, _gap in ordered
    ]
    method_panel: dict[str, dict[str, str]] = {anchor.anchor_id: {} for anchor in synthetic}
    _merge(method_panel, units, _joined_methods(synthetic, runs))
    rows: list[dict[str, Any]] = []
    panel: dict[str, dict[str, str]] = {}
    for vwra_id, vwra_day, peer_id, peer_day, gap in ordered:
        if vwra_day < floor or peer_day < floor or gap > TOLERANCE_DAYS:
            raise RuntimeError("a matched anchor breaks the frozen date rule")
        shared = shared_date(vwra_day, peer_day)
        if shared > vwra_day or shared > peer_day:
            raise RuntimeError("the shared date is after an anchor")
        row_id = f"{vwra_id}__{peer_id}"
        state: dict[str, str] = {}
        _copy_macro(state, atlas[PEER].get(peer_id, {}), peer_day, shared)
        _copy_macro(state, atlas["VWRA"].get(vwra_id, {}), vwra_day, shared)
        state.update(method_panel.get(row_id, {}))
        for feature, value in market_values(peer_day, shared, atlas[PEER].get(peer_id, {})).items():
            state[f"{PEER}:{feature}"] = value
        for feature, value in market_values(
            vwra_day, shared, atlas["VWRA"].get(vwra_id, {})
        ).items():
            state[f"VWRA:{feature}"] = value
        panel[row_id] = state
        rows.append(
            {
                "row_id": row_id,
                "vwra_day": vwra_day,
                "cndx_day": peer_day,
                "shared": shared,
                "gap": gap,
                "cndx_126": _one_return(outcomes, PEER, peer_id, PRIMARY_STEPS),
                "vwra_126": _one_return(outcomes, "VWRA", vwra_id, PRIMARY_STEPS),
                "cndx_id": peer_id,
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
        if feature.startswith(("method:", "EIMI:", "VWRA:", "CNDX:")) or is_market_feature(feature):
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
            key: value
            for key, value in features.items()
            if not key.startswith(("EIMI:", "VWRA:", "CNDX:"))
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
            row[f"{PEER}:{steps}"] = _one_return(outcomes, PEER, str(item["cndx_id"]), steps)
            row[f"VWRA:{steps}"] = _one_return(outcomes, "VWRA", str(item["vwra_id"]), steps)
        rows.append(row)
    return rows


def _portfolio(prices: dict[str, dict[date, PriceBar]], floor: date) -> dict[str, Any]:
    """Price-only paths. No macroeconomic state is passed to the simulator."""
    configuration = _blocked_configuration()
    blocked_note = (
        "Bounded VWRA-to-CNDX rotation is blocked and was not implemented. "
        "No stored policy sells one listing to buy the other under a bound."
    )
    try:
        sessions = common_sessions({PEER: prices[PEER], "VWRA": prices["VWRA"]})
    except BaselineError as exc:
        return _blocked_portfolio(str(exc), configuration, blocked_note)
    if not sessions or sessions[0] != floor or sessions[0] != MATCHED_NOT_BEFORE:
        return _blocked_portfolio(
            "the common window does not start on the later stored session 2019-07-25",
            configuration,
            blocked_note,
        )
    for session in sessions:
        for symbol in (PEER, "VWRA"):
            bar = prices[symbol].get(session)
            if bar is None or bar.currency != "USD" or bar.price <= 0:
                return _blocked_portfolio(
                    f"{symbol} has no stored US-dollar close on {session.isoformat()}",
                    configuration,
                    blocked_note,
                )
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
    weights = equal_weights(PEER, "VWRA")
    try:
        passive = simulate(
            policy=ImmediateSingleAssetPolicy("VWRA"), rebalance_sessions=set(), **shared
        )
        cndx = simulate(
            policy=ImmediateSingleAssetPolicy(PEER, name="immediate_cndx"),
            rebalance_sessions=set(),
            **shared,
        )
        mix = simulate(
            policy=EqualCashMixPolicy(name=STATIC_MIX, symbols=(PEER, "VWRA")),
            rebalance_sessions=january,
            **shared,
        )
        momentum_policy = RelativeMomentumPolicy(prices, peer=PEER, control="VWRA", baseline="VWRA")
        momentum = simulate(policy=momentum_policy, rebalance_sessions=set(), **shared)
        calendar = simulate(
            policy=CalendarRebalancePolicy(weights),
            rebalance_sessions=january,
            **shared,
        )
        threshold = simulate(
            policy=ThresholdRebalancePolicy(weights, Decimal(THRESHOLD_BAND)),
            rebalance_sessions=set(),
            **shared,
        )
        cash_flow = simulate(
            policy=CashFlowOnlyPolicy(weights),
            rebalance_sessions=set(),
            **shared,
        )
    except SimulatorError as exc:
        return _blocked_portfolio(str(exc), configuration, blocked_note)
    paths = {
        "immediate_vwra": passive,
        "immediate_cndx": cndx,
        "static_mix": mix,
        "relative_momentum": momentum,
        "calendar_rebalance": calendar,
        "threshold_rebalance": threshold,
        "cash_flow_only": cash_flow,
    }
    wealth = {name: decimal_text(result.terminal_wealth) for name, result in paths.items()}
    alternatives = {
        name: result.terminal_wealth for name, result in paths.items() if name != "immediate_vwra"
    }
    status = portfolio_claim_status(
        reconciled=True,
        passive_terminal=passive.terminal_wealth,
        alternatives=alternatives,
    )
    statement = portfolio_statement(status, wealth) + " " + blocked_note
    return {
        "blocked": False,
        "claim_status": status,
        "execution_state": "succeeded",
        "reason": None,
        "statement": statement,
        "wealth": wealth,
        "ending_cash": {name: decimal_text(result.ending_cash) for name, result in paths.items()},
        "total_costs": {name: decimal_text(result.total_costs) for name, result in paths.items()},
        "ending_units": {name: result.ending_units for name, result in paths.items()},
        "session_count": len(sessions),
        "contribution_count": len(contributions),
        "start": sessions[0].isoformat(),
        "end": sessions[-1].isoformat(),
        "fallbacks": momentum_policy.fallbacks,
        "ties": momentum_policy.ties,
        "cndx_choices": sum(1 for choice in momentum_policy.choices if choice == PEER),
        "vwra_choices": sum(1 for choice in momentum_policy.choices if choice == "VWRA"),
        "blocked_paths": list(BLOCKED_PORTFOLIO_PATHS),
        "configuration": {
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
        },
        "catalogue_scenarios_executed": 0,
        "price_type": "adjusted_close",
    }


def _blocked_configuration() -> dict[str, Any]:
    return {
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


def _blocked_portfolio(
    reason: str, configuration: dict[str, Any], blocked_note: str
) -> dict[str, Any]:
    statement = (
        f"The price-only comparison is blocked. {reason} "
        "No wealth path was stored. It is not a total return, not an SGD investor return, "
        "not economically useful, and not forward-validated. " + blocked_note
    )
    return {
        "blocked": True,
        "claim_status": "insufficient_data",
        "execution_state": "blocked",
        "reason": reason,
        "statement": statement,
        "wealth": {},
        "blocked_paths": list(BLOCKED_PORTFOLIO_PATHS),
        "configuration": configuration,
        "catalogue_scenarios_executed": 0,
    }


def _portfolio_finding(portfolio: dict[str, Any]) -> Finding:
    claim = str(portfolio["claim_status"])
    finding_class = "insufficient_sample" if claim == "insufficient_data" else claim
    if finding_class not in {"insufficient_sample", "inconclusive", "rejected"}:
        raise RuntimeError("the portfolio finding is not an allowed class")
    return Finding("CNDX-F-025", "LH-H-025", "LH-E-025", finding_class, str(portfolio["statement"]))


def _census_trials(rows: tuple[MethodCensus, ...]) -> list[ScoredTrial]:
    experiment = experiment_id("LH-H-019", HYPOTHESES)
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
            "Components are not distinct dates. This census is not a CNDX score."
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


def _coverage(
    anchors: dict[str, list[Anchor]],
    prices: dict[str, dict[date, PriceBar]],
    outcomes: dict[str, dict[str, dict[int, tuple[str, Decimal | None, bool | None]]]],
    matched: list[dict[str, Any]],
    census: tuple[MethodCensus, ...],
    peer_keeps: int,
    matched_keeps: int,
    peer_logistic: bool,
    matched_logistic: bool,
    sequence_counts: dict[str, int | str],
    classification: str,
    unemployment_survives: bool,
    gdp_survives: bool,
    trials: list[ScoredTrial],
) -> dict[str, Any]:
    ends = [row.earliest for row in census if row.earliest is not None]
    lasts = [row.latest for row in census if row.latest is not None]
    executed = sum(1 for row in trials if row.trial.result_text is not None)
    refused = sum(1 for row in trials if row.trial.refusal_reason is not None)
    return {
        "cndx_anchors": len(anchors[PEER]),
        "cndx_first_anchor": anchors[PEER][0].session.isoformat(),
        "cndx_last_anchor": anchors[PEER][-1].session.isoformat(),
        "cndx_first_session": min(prices[PEER]).isoformat(),
        "cndx_sessions": len(prices[PEER]),
        "vwra_anchors": len(anchors["VWRA"]),
        "vwra_first_anchor": anchors["VWRA"][0].session.isoformat(),
        "vwra_last_anchor": anchors["VWRA"][-1].session.isoformat(),
        "vwra_first_session": min(prices["VWRA"]).isoformat(),
        "vwra_sessions": len(prices["VWRA"]),
        "matched_anchors": len(matched),
        "matched_first": None if not matched else matched[0]["shared"].isoformat(),
        "matched_last": None if not matched else matched[-1]["shared"].isoformat(),
        "matched_max_gap_days": 0 if not matched else max(int(row["gap"]) for row in matched),
        "outcomes": {symbol: _outcome_counts(outcomes, symbol) for symbol in (PEER, "VWRA")},
        "cndx_non_overlapping_126": peer_keeps,
        "matched_non_overlapping_126": matched_keeps,
        "cndx_logistic_allowed": peer_logistic,
        "matched_logistic_allowed": matched_logistic,
        "sequence_status": sequence_counts["comparison_status"],
        "sequence_finding": sequence_finding(str(sequence_counts["comparison_status"])),
        "sequence_counts": {key: value for key, value in sequence_counts.items()},
        "relative_classification": classification,
        "unemployment_excess_partial_survives": unemployment_survives,
        "real_gdp_excess_partial_survives": gdp_survives,
        "method_earliest": None if not ends else min(ends).isoformat(),
        "method_latest": None if not lasts else max(lasts).isoformat(),
        "executed_trials": executed,
        "refused_trials": refused,
        "price_type": "adjusted_close",
        "total_return": "not_represented",
        "publication_allowed": False,
    }


def _outcome_counts(
    outcomes: dict[str, dict[str, dict[int, tuple[str, Decimal | None, bool | None]]]],
    symbol: str,
) -> dict[str, dict[str, int]]:
    counted: dict[str, dict[str, int]] = {}
    for steps in SESSION_STEPS.values():
        observed = 0
        censored = 0
        for horizons in outcomes[symbol].values():
            found = horizons.get(steps)
            if found is None:
                continue
            if found[0] == "observed":
                observed += 1
            else:
                censored += 1
        counted[str(steps)] = {"observed": observed, "censored": censored}
    return counted


def _windows(
    bodies: dict[str, dict[str, Any]],
    coverage: dict[str, Any],
    portfolio: dict[str, Any],
) -> None:
    peer = (coverage["cndx_first_anchor"], coverage["cndx_last_anchor"])
    matched = (coverage["matched_first"], coverage["matched_last"])
    methods = (coverage["method_earliest"], coverage["method_latest"])
    path: tuple[str | None, str | None]
    if portfolio["blocked"]:
        path = (None, None)
    else:
        path = (str(portfolio["start"]), str(portfolio["end"]))
    windows = {
        "LH-X-019": methods,
        "LH-X-020": peer,
        "LH-X-021": peer,
        "LH-X-022": peer,
        "LH-X-023": matched,
        "LH-X-024": matched,
        "LH-X-025": path,
    }
    for execution_id, (start, end) in windows.items():
        bodies[execution_id]["simulation_start"] = start
        bodies[execution_id]["simulation_end"] = end


def _closes(bars: dict[date, PriceBar]) -> tuple[Decimal, ...]:
    return tuple(bars[day].price for day in sorted(bars))


def _coefficient(
    trials: list[ScoredTrial],
    *,
    symbol: str,
    feature: str,
    statistic: str,
    outcome: str,
    paired: str | None,
) -> Decimal | None:
    matches = [
        row.trial.result_text
        for row in trials
        if row.symbol == symbol
        and row.trial.feature == feature
        and row.trial.statistic == statistic
        and row.trial.outcome == outcome
        and row.trial.paired_feature == paired
        and row.trial.experiment_id == "LH-E-023"
    ]
    if len(matches) > 1:
        raise RuntimeError(f"more than one coefficient for {feature} {statistic}")
    if not matches:
        return None
    return parse_decimal(matches[0])


def _text(value: Decimal | None) -> str:
    if value is None:
        return "absent"
    return decimal_text(value)


def _earlier_trials(connection: psycopg.Connection) -> list[dict[str, object]]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            select specification_id,
                   count(*) filter (where result_text is not null)::int,
                   count(*) filter (where refusal_reason is not null)::int
            from research.discovery_v2_trials
            where specification_id = any(%s)
            group by specification_id
            order by specification_id
            """,
            (list(EARLIER_SPECIFICATIONS),),
        )
        return [
            {"specification_id": spec, "executed": executed, "refused": refused}
            for spec, executed, refused in cursor.fetchall()
        ]


def _vintage_facts(connection: psycopg.Connection) -> dict[str, object]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            select count(*)::int, min(provider_vintage_date), max(provider_vintage_date)
            from research.economic_observations
            where dataset_id = 'bls.ln.LNS14000000'
              and series_provenance = 'provider_vintage'
            """
        )
        count, first, last = cursor.fetchone()
        cursor.execute(
            """
            select count(*)::int
            from research.decision_anchors
            where symbol = 'CSPX' and anchor_kind = 'listing_month_end'
            """
        )
        cspx_anchors = int(cursor.fetchone()[0])
    return {
        "unemployment_provider_vintage_rows": int(count),
        "unemployment_provider_vintage_first": None if first is None else first.isoformat(),
        "unemployment_provider_vintage_last": None if last is None else last.isoformat(),
        "cspx_month_end_anchors": cspx_anchors,
    }


def _existing_executions(connection: psycopg.Connection) -> bool:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            select count(*)::int
            from research.experiment_executions
            where execution_id = any(%s)
            """,
            ([str(row["execution_id"]) for row in HYPOTHESES],),
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
            select specification_id, count(*)::int
            from research.discovery_v2_trials
            where specification_id = any(%s)
            group by specification_id
            order by specification_id
            """,
            (list(EARLIER_SPECIFICATIONS),),
        )
        earlier = tuple((str(row[0]), int(row[1])) for row in cursor.fetchall())
        cursor.execute(
            """
            select a.symbol, count(*)::int
            from research.discovery_v2_anchor_features f
            join research.decision_anchors a on a.anchor_id = f.anchor_id
            where a.symbol in ('VWRA', 'EIMI')
            group by a.symbol
            order by a.symbol
            """
        )
        features = tuple((str(row[0]), int(row[1])) for row in cursor.fetchall())
        cursor.execute(
            """
            select statement from research.discovery_v2_findings where finding_id = 'CMP-F-017'
            """
        )
        finding = cursor.fetchone()
        cursor.execute(
            """
            select version, proposition
            from research.scientific_claims
            where claim_id = 'LH-C-017'
            order by version
            """
        )
        claims = tuple((int(row[0]), str(row[1])) for row in cursor.fetchall())
        cursor.execute(
            """
            select content_sha256 from research.evidence_records where evidence_id = 'LH-V-017'
            """
        )
        evidence = cursor.fetchone()
        cursor.execute(
            """
            select episode_group, sample_count
            from research.discovery_v2_casebook
            where specification_id = 'EIMI-VWRA-COMPARISON-001'
              and family = 'anchor_count'
            order by episode_group
            """
        )
        casebook = tuple((str(row[0]), int(row[1])) for row in cursor.fetchall())
        cursor.execute(
            """
            select count(*)::int from research.experiment_executions where publication_allowed
            """
        )
        published = int(cursor.fetchone()[0])
    return {
        "executions": executions,
        "points": points,
        "runs": runs,
        "earlier_trials": earlier,
        "features": features,
        "finding": None if finding is None else str(finding[0]),
        "claims": claims,
        "evidence": None if evidence is None else str(evidence[0]),
        "casebook": casebook,
        "published": published,
    }


def _assert_unchanged(before: dict[str, object], after: dict[str, object]) -> None:
    if before != after:
        raise RuntimeError("stored VWRA or EIMI rows changed and the comparison was rolled back")


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
