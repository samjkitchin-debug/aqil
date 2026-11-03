"""Load stored closes, freeze the specifications, then store the result.

The specification rows are committed before any price row is read.
"""

from __future__ import annotations

import hashlib
import subprocess
from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import psycopg

from aqil_research.long_horizon.events.compute import (
    MACRO_CLAIM_TEXT,
    Analysis,
    MacroFacts,
    analyse,
    claim_proposition,
)
from aqil_research.long_horizon.events.definition import (
    DEFINITION_ID,
    DEFINITION_VERSION,
    EVENT_DEFINITION,
    FROZEN_MACRO_INTERSECTION,
    FROZEN_PILOT_INTERSECTION,
    MACRO_CLAIM_ID,
    MACRO_EVIDENCE_ID,
    MACRO_EXECUTION_ID,
    MACRO_EXPERIMENT_ID,
    MACRO_HYPOTHESIS,
    MACRO_HYPOTHESIS_ID,
    PILOT_CLAIM_ID,
    PILOT_EVIDENCE_ID,
    PILOT_EXECUTION_ID,
    PILOT_EXPERIMENT_ID,
    PILOT_HYPOTHESIS,
    PILOT_HYPOTHESIS_ID,
    event_definition_hash,
    macro_intersection_hash,
    pilot_intersection_hash,
)
from aqil_research.long_horizon.events.identify import ListingSeries
from aqil_research.long_horizon.events.package_hash import events_code_hash
from aqil_research.long_horizon.events.registry import (
    store_availability,
    store_comparisons,
    store_definition,
    store_dependency,
    store_events,
    store_execution,
    store_family_counts,
    store_hypothesis_and_specification,
)
from aqil_research.long_horizon.events.report import write_result_files
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

REPRODUCTION = "uv run python -m aqil_research.long_horizon.events.reproduce"
ALLOWED_DIRTY = {
    "apps/web/public/icons/icon.svg",
    "docs/research/events/INVENTORY.md",
    "docs/research/events/PILOT_RESULT.md",
    "docs/research/events/FEATURE_AVAILABILITY.csv",
    "docs/research/events/inventory-summary.json",
    "docs/research/events/inventory-events.jsonl",
}


def assert_worktree(root: Path) -> None:
    completed = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    unexpected: list[str] = []
    for line in completed.stdout.splitlines():
        path = line[3:].strip().replace("\\", "/")
        if path not in ALLOWED_DIRTY:
            unexpected.append(path)
    if unexpected:
        raise PilotError("refusing to scan while the worktree has " + ", ".join(unexpected))
    staged = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    if staged.stdout.strip():
        raise PilotError("refusing to scan while a file is staged")


def _database(connection: psycopg.Connection, expected: str) -> None:
    found = connection.execute("select current_database()").fetchone()
    if found is None or found[0] != expected:
        raise PilotError(f"expected database {expected}")


def freeze_specifications(connection: psycopg.Connection, frozen_at: datetime) -> None:
    """Write the frozen rows and commit them before prices are read."""
    _database(connection, "postgres")
    store_definition(
        connection,
        definition_id=DEFINITION_ID,
        version=DEFINITION_VERSION,
        specification=EVENT_DEFINITION,
        specification_hash=event_definition_hash(),
        frozen_at=frozen_at,
    )
    store_hypothesis_and_specification(
        connection,
        hypothesis=PILOT_HYPOTHESIS,
        specification=FROZEN_PILOT_INTERSECTION,
        specification_hash=pilot_intersection_hash(),
        category="C",
        category_label="price_only_simulator_research",
        frozen_at=frozen_at,
        hypothesis_status_id="LH-S-H-002-proposed",
        experiment_status_id="LH-S-E-002-proposed",
        status="proposed",
        rationale="Specification frozen before the intersection was scored.",
    )
    store_hypothesis_and_specification(
        connection,
        hypothesis=MACRO_HYPOTHESIS,
        specification=FROZEN_MACRO_INTERSECTION,
        specification_hash=macro_intersection_hash(),
        category="B",
        category_label="retrospective_economic_research",
        frozen_at=frozen_at,
        hypothesis_status_id="LH-S-H-003-retrospective",
        experiment_status_id="LH-S-E-003-retrospective",
        status="retrospective_only",
        rationale="Registered before any macro value was read. The intersection is not estimated.",
    )
    connection.commit()


def load_prices(
    connection: psycopg.Connection,
) -> tuple[list[ListingSeries], dict[str, str], int, tuple[str, ...]]:
    connection.read_only = True
    _database(connection, "aqil_etf")
    with connection.cursor() as cursor:
        cursor.execute(
            """
            select l.ticker, l.trading_currency
            from instruments.listings l
            order by l.ticker
            """
        )
        listed = cursor.fetchall()
        cursor.execute(
            """
            select l.ticker, p.session_date, p.value::text, p.currency, p.quote_unit,
                   p.adjustment_status, p.price_type
            from instruments.listings l
            join instruments.market_price_observations p
              on p.listing_id = l.listing_id
            order by l.ticker, p.session_date
            """
        )
        fetched = cursor.fetchall()
        cursor.execute("select count(*) from instruments.fx_observations")
        fx_count = int(cursor.fetchone()[0])
        cursor.execute(
            """
            select table_schema || '.' || table_name
            from information_schema.tables
            where table_name ilike '%distrib%'
              and table_schema in ('instruments', 'research', 'public')
            order by 1
            """
        )
        distribution_tables = tuple(row[0] for row in cursor.fetchall())
    grouped: dict[str, list[tuple[date, str, str, str]]] = {
        ticker: [] for ticker, _currency in listed
    }
    seen: set[tuple[str, date]] = set()
    for ticker, session, value_text, currency, quote_unit, adjustment_status, price_type in fetched:
        if price_type != "adjusted_close" or adjustment_status != "adjusted":
            raise PilotError(f"{ticker} is not a stored split-adjusted close")
        if quote_unit != currency:
            raise PilotError(f"{ticker} quote unit is not its currency")
        key = (ticker, session)
        if key in seen:
            raise PilotError(f"duplicate stored close for {ticker} {session}")
        seen.add(key)
        grouped.setdefault(ticker, []).append((session, value_text, currency, quote_unit))
    listings: list[ListingSeries] = []
    hashes: dict[str, str] = {}
    for ticker, trading_currency in listed:
        rows = grouped.get(ticker, [])
        if not rows:
            raise PilotError(f"{ticker} has a listing and no stored close; none was manufactured")
        if any(item[2] != trading_currency for item in rows):
            raise PilotError(f"{ticker} currency does not match the listing")
        dates = tuple(item[0] for item in rows)
        closes = tuple(Decimal(item[1]) for item in rows)
        lines = [f"{ticker}|{item[0].isoformat()}|{item[1]}|{item[2]}|{item[3]}" for item in rows]
        listings.append(ListingSeries(ticker, trading_currency, dates, closes))
        hashes[ticker] = hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()
    return listings, hashes, fx_count, distribution_tables


def load_macro(connection: psycopg.Connection) -> MacroFacts:
    connection.read_only = True
    _database(connection, "postgres")
    with connection.cursor() as cursor:
        cursor.execute(
            """
            select dataset_id, series_provenance, seasonal_adjustment, quality_status, period_start
            from research.economic_observations
            """
        )
        observations = cursor.fetchall()
        cursor.execute(
            """
            select count(*)
            from research.economic_observations
            where dataset_id ilike '%alfred%'
            """
        )
        alfred_count = int(cursor.fetchone()[0])
    periods: dict[str, list[date]] = {}
    seasonal: dict[str, set[str]] = {}
    gdp_dates: list[date] = []
    gdp_seasonal: set[str] = set()
    unemployment_dates: list[date] = []
    for dataset_id, provenance, adjustment, quality, period_start in observations:
        if dataset_id == "bea.vintage.real_gdp.pct_preceding" and provenance == "provider_vintage":
            gdp_dates.append(period_start)
            gdp_seasonal.add(adjustment)
        if dataset_id == "bls.ln.LNS14000000" and provenance == "provider_vintage":
            unemployment_dates.append(period_start)
        if provenance == "latest_revised" and quality == "observed":
            periods.setdefault(dataset_id, []).append(period_start)
            seasonal.setdefault(dataset_id, set()).add(adjustment)
    chosen = {
        dataset_id: next(iter(labels)) if len(labels) == 1 else None
        for dataset_id, labels in seasonal.items()
    }
    return MacroFacts(
        periods={key: tuple(sorted(value)) for key, value in periods.items()},
        seasonal=chosen,
        gdp_vintage_count=len(gdp_dates),
        gdp_first=min(gdp_dates).isoformat() if gdp_dates else "none",
        gdp_last=max(gdp_dates).isoformat() if gdp_dates else "none",
        gdp_seasonal=next(iter(gdp_seasonal)) if len(gdp_seasonal) == 1 else None,
        unemployment_vintage_count=len(unemployment_dates),
        unemployment_first=min(unemployment_dates).isoformat() if unemployment_dates else "none",
        unemployment_last=max(unemployment_dates).isoformat() if unemployment_dates else "none",
        alfred_count=alfred_count,
        fx_count=0,
        distribution_tables=(),
    )


def _cutoff(day: date) -> datetime:
    return datetime(day.year, day.month, day.day, tzinfo=UTC)


def _persist(
    connection: psycopg.Connection,
    analysis: Analysis,
    facts: MacroFacts,
    *,
    recorded_at: datetime,
    code_hash: str,
    commit: str,
) -> None:
    _database(connection, "postgres")
    artifact = analysis.artifact
    if not analysis.decisions:
        raise PilotError("the intersection produced no eligible month-end")
    store_events(
        connection,
        [
            (
                event.event_id,
                DEFINITION_ID,
                DEFINITION_VERSION,
                event.symbol,
                event.currency,
                event.family,
                event.horizon_label,
                event.start_date,
                event.end_date,
                event.label_confirmed_on,
                event.price_return,
                event.session_steps,
                event.max_intervening_drawdown,
                event.up_session_fraction,
                event.label_uses_later_prices,
                event.historically_observable_at_event_date,
                event.price_series_sha256,
                event.detail,
                recorded_at,
            )
            for event in analysis.events
        ],
    )
    store_family_counts(
        connection,
        [
            (
                DEFINITION_ID,
                DEFINITION_VERSION,
                row.symbol,
                row.family,
                row.horizon_label,
                row.status,
                row.reason,
                row.event_count,
                row.windows_examined,
                row.qualifier_window_count,
                row.censored_count,
                row.price_series_sha256,
                recorded_at,
            )
            for row in analysis.families
        ],
    )
    store_availability(
        connection,
        [
            (
                DEFINITION_ID,
                DEFINITION_VERSION,
                row.symbol,
                row.feature_id,
                row.lookback_label,
                row.clock,
                row.availability,
                row.covered_event_count,
                row.catalogued_event_count,
                row.seasonal_adjustment,
                row.detail,
                recorded_at,
            )
            for row in analysis.availability
        ],
    )
    store_comparisons(
        connection,
        [
            (
                f"CP-v1-{row.symbol}-{row.decision_date.isoformat()}",
                PILOT_EXPERIMENT_ID,
                row.symbol,
                row.decision_date,
                row.condition_met,
                row.outcome_advance,
                row.forward_price_return,
                recorded_at,
            )
            for row in analysis.decisions
        ],
    )
    versions = [
        {
            "symbol": symbol,
            "sha256": digest,
        }
        for symbol, digest in sorted(artifact["price_series_sha256"].items())
    ]
    assert isinstance(artifact["price_series_sha256"], dict)
    first = min(row.decision_date for row in analysis.decisions)
    last = max(row.decision_date for row in analysis.decisions)
    status = str(artifact["status"])
    relation = "contradicts" if status == "rejected" else "qualifies"
    store_execution(
        connection,
        execution_id=PILOT_EXECUTION_ID,
        experiment_id=PILOT_EXPERIMENT_ID,
        hypothesis_id=PILOT_HYPOTHESIS_ID,
        state="succeeded",
        validation_status=status,
        artifact=artifact,
        artifact_sha256=sha256_document(artifact),
        evidence_id=PILOT_EVIDENCE_ID,
        evidence_kind="statistical_note",
        claim_id=PILOT_CLAIM_ID,
        claim_proposition=claim_proposition(artifact),
        claim_status=status,
        eligibility_class="category_c_price_only",
        statistical_validity="not assessed; overlapping month-ends are not independent trials",
        economic_usefulness="not established",
        independent_validation="not recorded",
        remaining_uncertainty=(
            "Category C uses one inspected window, split-adjusted closes, and no holdout."
        ),
        evidence_relation=relation,
        recorded_at=recorded_at,
        availability_cutoff=_cutoff(last),
        git_commit=commit,
        code_hash=code_hash,
        input_manifest={
            "definition_hash": artifact["definition_hash"],
            "pilot_specification_hash": artifact["pilot_specification_hash"],
            "event_identity_sha256": artifact["event_identity_sha256"],
            "comparison_identity_sha256": artifact["comparison_identity_sha256"],
            "macro_values_read": False,
        },
        price_series_versions=versions,
        library_versions=library_versions(),
        configuration={
            "portfolio_comparison": "blocked",
            "holdout": "none",
            "code_hash_scope": "aqil_research.long_horizon.events",
        },
        simulation_start=first,
        simulation_end=last,
        reproduction_command=REPRODUCTION,
        claim_status_id="LH-S-C-002-result",
        hypothesis_status_id="LH-S-H-002-result",
        experiment_status_id="LH-S-E-002-result",
    )
    macro_body = {
        "experiment_id": MACRO_EXPERIMENT_ID,
        "estimated": False,
        "values_read": False,
        "portfolio_comparison": "blocked",
        "gdp_vintage_rows": facts.gdp_vintage_count,
        "alfred_rows": facts.alfred_count,
        "fx_rows": facts.fx_count,
        "specification_hash": macro_intersection_hash(),
        "publication_allowed": False,
        "not_an_investment_claim": True,
    }
    store_execution(
        connection,
        execution_id=MACRO_EXECUTION_ID,
        experiment_id=MACRO_EXPERIMENT_ID,
        hypothesis_id=MACRO_HYPOTHESIS_ID,
        state="blocked",
        validation_status="retrospective_only",
        artifact=macro_body,
        artifact_sha256=sha256_document(macro_body),
        evidence_id=MACRO_EVIDENCE_ID,
        evidence_kind="negative_finding",
        claim_id=MACRO_CLAIM_ID,
        claim_proposition=MACRO_CLAIM_TEXT,
        claim_status="retrospective_only",
        eligibility_class="category_b_retrospective",
        statistical_validity="not estimated",
        economic_usefulness="not established",
        independent_validation="not recorded",
        remaining_uncertainty="No original vintage covers this intersection.",
        evidence_relation="qualifies",
        recorded_at=recorded_at,
        availability_cutoff=_cutoff(last),
        git_commit=commit,
        code_hash=code_hash,
        input_manifest={
            "prices_read": False,
            "macro_values_read": False,
            "specification_hash": macro_intersection_hash(),
        },
        price_series_versions=[],
        library_versions=library_versions(),
        configuration={"portfolio_comparison": "blocked", "values_read": False},
        simulation_start=None,
        simulation_end=None,
        reproduction_command=REPRODUCTION,
        claim_status_id="LH-S-C-003-retrospective",
        hypothesis_status_id="LH-S-H-003-result",
        experiment_status_id="LH-S-E-003-result",
    )
    store_dependency(
        connection,
        dependency_id="LH-D-007",
        left_kind="hypothesis",
        left_id=PILOT_HYPOTHESIS_ID,
        right_kind="dataset",
        right_id="aqil_etf.adjusted_close",
        relation="shares_dataset",
        dataset_id="aqil_etf.adjusted_close",
        instrument_id=None,
        period_start=first,
        period_end=last,
        detail=(
            "The intersection reads stored split-adjusted closes. It is not a second confirmation."
        ),
        recorded_at=recorded_at,
    )
    store_dependency(
        connection,
        dependency_id="LH-D-008",
        left_kind="experiment",
        left_id=PILOT_EXPERIMENT_ID,
        right_kind="experiment",
        right_id="LH-E-001",
        relation="overlaps_period",
        dataset_id=None,
        instrument_id=None,
        period_start=first,
        period_end=last,
        detail="LH-E-002 uses the same price store as LH-E-001. It does not rescore LH-X-001.",
        recorded_at=recorded_at,
    )
    store_dependency(
        connection,
        dependency_id="LH-D-009",
        left_kind="experiment",
        left_id=PILOT_EXPERIMENT_ID,
        right_kind="control",
        right_id="condition_false_month_ends",
        relation="matched_control",
        dataset_id=None,
        instrument_id=None,
        period_start=first,
        period_end=last,
        detail=(
            "Condition-false eligible month-ends are the controls. "
            "They are not chosen by the later return."
        ),
        recorded_at=recorded_at,
    )
    store_dependency(
        connection,
        dependency_id="LH-D-010",
        left_kind="experiment",
        left_id=MACRO_EXPERIMENT_ID,
        right_kind="experiment",
        right_id=PILOT_EXPERIMENT_ID,
        relation="overlaps_period",
        dataset_id=None,
        instrument_id=None,
        period_start=None,
        period_end=None,
        detail=(
            "Registered in the same programme. No macro value was read. "
            "Not an independent confirmation."
        ),
        recorded_at=recorded_at,
    )
    connection.commit()


def execute_scan() -> Analysis:
    root = repo_root()
    assert_worktree(root)
    assert_loopback(LOCAL_RESEARCH_URL, "postgres")
    assert_loopback(LOCAL_ETF_URL, "aqil_etf")
    code_hash = events_code_hash()
    commit = git_commit(root)
    frozen_at = datetime.now(UTC)
    with psycopg.connect(LOCAL_RESEARCH_URL) as research:
        freeze_specifications(research, frozen_at)
    with psycopg.connect(LOCAL_ETF_URL) as etf:
        listings, hashes, fx_count, distribution_tables = load_prices(etf)
    with psycopg.connect(LOCAL_RESEARCH_URL) as research:
        facts = replace(
            load_macro(research),
            fx_count=fx_count,
            distribution_tables=distribution_tables,
        )
    analysis = analyse(listings, hashes, facts)
    recorded_at = datetime.now(UTC)
    with psycopg.connect(LOCAL_RESEARCH_URL) as research:
        _persist(
            research,
            analysis,
            facts,
            recorded_at=recorded_at,
            code_hash=code_hash,
            commit=commit,
        )
    write_result_files(root, analysis)
    return analysis


def main() -> None:
    analysis = execute_scan()
    artifact = analysis.artifact
    print(
        f"status {artifact['status']} events {artifact['event_count']} "
        f"comparisons {artifact['comparison_count']}"
    )


if __name__ == "__main__":
    main()
