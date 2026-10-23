"""Run the four macro readings once on stored live observations.

Does not ingest provider files, delete rows, or reset the database.
publication_allowed stays false. A failed method does not cancel the others.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime

import psycopg

from aqil_research.contracts.observation import AnalysisMode, EconomicObservation
from aqil_research.methods.configs import (
    CREDIT_STANDARDS_AND_VOLUMES_PUBLISHED,
    INDUSTRIAL_PRODUCTION_PUBLISHED,
    LABOUR_MARKET_PUBLISHED,
    PRICES_AND_POLICY_PUBLISHED,
)
from aqil_research.methods.credit_standards_and_volumes import (
    CREDIT_STANDARDS_AND_VOLUMES_METHOD_ID,
    H8_DATASET_ID,
    SLOOS_DATASET_ID,
)
from aqil_research.methods.industrial_production_activity import (
    INDUSTRIAL_PRODUCTION_DATASET_ID,
    INDUSTRIAL_PRODUCTION_METHOD_ID,
)
from aqil_research.methods.labour_market import (
    LABOUR_MARKET_METHOD_ID,
    OPENINGS_DATASET_ID,
    PAYROLLS_DATASET_ID,
    UNEMPLOYMENT_DATASET_ID,
)
from aqil_research.methods.macro_reading_synthesis import (
    MacroReadingInput,
    build_synthesis_run,
    synthesize_macro_readings,
)
from aqil_research.methods.prices_and_policy import (
    CPI_DATASET_ID,
    FED_FUNDS_DATASET_ID,
    PRICES_AND_POLICY_METHOD_ID,
    TREASURY_10Y_DATASET_ID,
)
from aqil_research.methods.registry import default_method_registry
from aqil_research.persistence.mapping import row_to_observation
from aqil_research.persistence.observation_store import _OBSERVATION_COLUMNS
from aqil_research.persistence.runs import save_research_run
from aqil_research.pipeline.models import ResearchExecutionRequest, ResearchRun
from aqil_research.pipeline.orchestrate import execute_research_run
from aqil_research.sources.rights import load_source_rights
from aqil_research.sources.rights_gate import resolve_research_rights_by_dataset
from aqil_research.vintages.asof import select_as_of_series
from aqil_research.vintages.store import AppendResult

LIVE_DATASETS = (
    UNEMPLOYMENT_DATASET_ID,
    CPI_DATASET_ID,
    PAYROLLS_DATASET_ID,
    OPENINGS_DATASET_ID,
    INDUSTRIAL_PRODUCTION_DATASET_ID,
    H8_DATASET_ID,
    FED_FUNDS_DATASET_ID,
    TREASURY_10Y_DATASET_ID,
    "ecb.icp.M.U2.Y.000000.3.INX",
    SLOOS_DATASET_ID,
)


@dataclass(frozen=True, slots=True)
class _ReadingSpec:
    method_id: str
    dataset_id: str
    config: dict[str, str]
    evaluation: str


_SPECS = (
    _ReadingSpec(
        LABOUR_MARKET_METHOD_ID,
        UNEMPLOYMENT_DATASET_ID,
        LABOUR_MARKET_PUBLISHED,
        "labour",
    ),
    _ReadingSpec(
        PRICES_AND_POLICY_METHOD_ID,
        CPI_DATASET_ID,
        PRICES_AND_POLICY_PUBLISHED,
        "prices",
    ),
    _ReadingSpec(
        INDUSTRIAL_PRODUCTION_METHOD_ID,
        INDUSTRIAL_PRODUCTION_DATASET_ID,
        INDUSTRIAL_PRODUCTION_PUBLISHED,
        "production",
    ),
    _ReadingSpec(
        CREDIT_STANDARDS_AND_VOLUMES_METHOD_ID,
        H8_DATASET_ID,
        CREDIT_STANDARDS_AND_VOLUMES_PUBLISHED,
        "credit",
    ),
)


class _LiveStore:
    """Read-only view of live retrievals. Fixtures are not included."""

    def __init__(self, rows: tuple[EconomicObservation, ...]) -> None:
        self._rows = rows

    def append(self, observation: EconomicObservation) -> AppendResult:
        raise RuntimeError("live reading store is read-only")

    def append_many(self, observations: tuple[EconomicObservation, ...]) -> AppendResult:
        raise RuntimeError("live reading store is read-only")

    def all_observations(self) -> tuple[EconomicObservation, ...]:
        return self._rows

    def as_of(
        self,
        dataset_id: str,
        decision_at: datetime,
        mode: AnalysisMode,
    ) -> dict[date, EconomicObservation]:
        return select_as_of_series(self._rows, dataset_id, decision_at, mode)


def record_macro_readings(conn: psycopg.Connection) -> dict[str, object]:
    """Append one run per method, then one synthesis run."""
    before = preservation_counts(conn)
    now = datetime.now(tz=UTC)
    rights = load_source_rights()
    store = _LiveStore(_load_live_rows(conn))
    registry = default_method_registry()
    series = {
        dataset_id: store.as_of(dataset_id, now, AnalysisMode.LATEST_REVISED)
        for dataset_id in LIVE_DATASETS
    }
    evaluations = _evaluation_periods(series, now.date())
    outcomes: list[dict[str, object]] = []
    inputs: list[MacroReadingInput] = []
    for spec in _SPECS:
        outcome, reading = _run_one(
            conn,
            spec,
            store=store,
            rights=rights,
            registry=registry,
            evaluation=evaluations[spec.evaluation],
            decision_at=now,
        )
        outcomes.append(outcome)
        if reading is not None:
            inputs.append(reading)

    synthesis_report: dict[str, object]
    try:
        production_run = next(
            (item for item in inputs if item.method_id == INDUSTRIAL_PRODUCTION_METHOD_ID),
            None,
        )
        endpoints = _production_endpoints(
            series[INDUSTRIAL_PRODUCTION_DATASET_ID],
            production_run,
        )
        synthesis = synthesize_macro_readings(
            _with_price_endpoints(inputs, series),
            production_endpoints=endpoints,
        )
        primary = resolve_research_rights_by_dataset(
            rights,
            dataset_id=UNEMPLOYMENT_DATASET_ID,
        )
        datasets = sorted({dataset_id for spec in _SPECS for dataset_id in _datasets(spec)})
        synthesis_run = build_synthesis_run(
            synthesis,
            dataset_id=UNEMPLOYMENT_DATASET_ID,
            source_id=primary.source_id,
            input_dataset_ids=datasets,
            evaluation_period=evaluations["credit"].isoformat(),
            executed_at=now,
        )
        _save(conn, synthesis_run)
        synthesis_report = {
            "run_id": synthesis_run.run_id,
            "publication_allowed": synthesis_run.publication_allowed,
            "sufficiency": synthesis.sufficiency,
            "summary": synthesis.summary,
            "agreements": list(synthesis.agreements),
            "divergences": list(synthesis.divergences),
            "mismatched_latest_months": list(synthesis.mismatched_latest_months),
            "stale_inputs": list(synthesis.stale_inputs),
            "cited_changes": list(synthesis.cited_changes),
            "limitations": list(synthesis.limitations),
            "observation_ids": list(synthesis.observation_ids),
            "source_run_ids": list(synthesis.source_run_ids),
        }
    except Exception as exc:
        synthesis_report = {"status": "error", "detail": str(exc)}
    after = preservation_counts(conn)
    return {
        "before": before,
        "after": after,
        "evaluations": {key: value.isoformat() for key, value in evaluations.items()},
        "methods": outcomes,
        "synthesis": synthesis_report,
    }


def preservation_counts(conn: psycopg.Connection) -> dict[str, object]:
    with conn.cursor() as cur:
        cur.execute(
            """
            select o.dataset_id, r.collection_mode, count(*)
            from research.economic_observations o
            join research.source_retrievals r using (retrieval_id)
            group by o.dataset_id, r.collection_mode
            order by o.dataset_id, r.collection_mode
            """,
        )
        observations = [
            {"dataset_id": row[0], "collection_mode": row[1], "count": row[2]}
            for row in cur.fetchall()
        ]
        cur.execute(
            """
            select source_id, count(*)
            from research.sourced_updates
            group by source_id
            order by source_id
            """,
        )
        publications = {row[0]: row[1] for row in cur.fetchall()}
        cur.execute(
            """
            select count(*)
            from forward.catalyst_events
            where source_id = 'bls_ics_schedule'
              and scheduled_at > now()
            """,
        )
        calendar = cur.fetchone()[0]
        cur.execute("select count(*) from research.research_runs")
        runs = cur.fetchone()[0]
    return {
        "observations": observations,
        "publications": publications,
        "future_bls_calendar_rows": calendar,
        "research_runs": runs,
    }


def _run_one(
    conn: psycopg.Connection,
    spec: _ReadingSpec,
    *,
    store: _LiveStore,
    rights: tuple,
    registry: object,
    evaluation: date,
    decision_at: datetime,
) -> tuple[dict[str, object], MacroReadingInput | None]:
    try:
        source = resolve_research_rights_by_dataset(rights, dataset_id=spec.dataset_id)
        request = ResearchExecutionRequest(
            source_id=source.source_id,
            dataset_id=spec.dataset_id,
            decision_at=decision_at,
            analysis_mode=AnalysisMode.LATEST_REVISED,
            evaluation_period=evaluation.isoformat(),
            method_id=spec.method_id,
            method_config=dict(spec.config),
            collect=False,
        )
        run = execute_research_run(
            request,
            store=store,
            rights_records=rights,
            method_registry=registry,
            executed_at=decision_at,
        )
        if run.publication_allowed:
            raise RuntimeError(f"{spec.method_id} set publication_allowed")
        _save(conn, run)
    except Exception as exc:
        return (
            {
                "method_id": spec.method_id,
                "status": "error",
                "detail": str(exc),
                "publication_allowed": False,
            },
            None,
        )
    return _compact(run), MacroReadingInput(
        method_id=run.method_id,
        sufficiency=run.data_sufficiency,
        missing_reason=run.missing_data_reason,
        calculation=run.calculation,
        run_id=run.run_id,
    )


def _save(conn: psycopg.Connection, run: ResearchRun) -> None:
    with conn.transaction():
        save_research_run(conn, run)


def _compact(run: ResearchRun) -> dict[str, object]:
    calculation = run.calculation if isinstance(run.calculation, dict) else None
    return {
        "method_id": run.method_id,
        "method_version": run.method_version,
        "run_id": run.run_id,
        "execution_status": run.execution_status,
        "data_sufficiency": run.data_sufficiency,
        "missing_data_reason": run.missing_data_reason,
        "publication_allowed": run.publication_allowed,
        "investment_implication": run.investment_implication,
        "causal_hypothesis": run.causal_hypothesis,
        "evaluation_period": run.evaluation_period,
        "narrative": run.narrative,
        "limitations": run.limitations,
        "calculation": _without_history_ids(calculation),
    }


def _without_history_ids(calculation: dict[str, object] | None) -> dict[str, object] | None:
    if calculation is None:
        return None
    trimmed: dict[str, object] = {}
    for key, value in calculation.items():
        if key == "observation_ids" and isinstance(value, list) and len(value) > 12:
            trimmed[key] = {"count": len(value)}
            continue
        if isinstance(value, dict):
            trimmed[key] = _without_history_ids(value)
            continue
        if isinstance(value, list) and value and isinstance(value[0], dict):
            trimmed[key] = [
                _without_history_ids(item) if isinstance(item, dict) else item for item in value
            ]
            continue
        trimmed[key] = value
    return trimmed


def _evaluation_periods(
    series: dict[str, dict[date, EconomicObservation]],
    today: date,
) -> dict[str, date]:
    unemployment = _latest(series, UNEMPLOYMENT_DATASET_ID) or today.replace(day=1)
    cpi = _latest(series, CPI_DATASET_ID)
    funds = _latest(series, FED_FUNDS_DATASET_ID)
    treasury = _latest(series, TREASURY_10Y_DATASET_ID)
    monthly = [item for item in (cpi, funds, treasury) if item is not None]
    prices = min(monthly) if monthly else unemployment
    production = _latest(series, INDUSTRIAL_PRODUCTION_DATASET_ID) or prices
    credit = _latest(series, H8_DATASET_ID) or _latest(series, SLOOS_DATASET_ID) or prices
    return {
        "labour": unemployment,
        "prices": prices,
        "production": production,
        "credit": credit,
    }


def _latest(
    series: dict[str, dict[date, EconomicObservation]],
    dataset_id: str,
) -> date | None:
    rows = series.get(dataset_id) or {}
    if not rows:
        return None
    return max(rows)


def _with_price_endpoints(
    inputs: list[MacroReadingInput],
    series: dict[str, dict[date, EconomicObservation]],
) -> list[MacroReadingInput]:
    """Name the stored endpoint observations on a copy used only for the comparison."""
    stamped: list[MacroReadingInput] = []
    for item in inputs:
        if item.method_id != PRICES_AND_POLICY_METHOD_ID or not isinstance(item.calculation, dict):
            stamped.append(item)
            continue
        calculation = dict(item.calculation)
        calculation["cpi_u"] = _stamp_endpoints(
            calculation.get("cpi_u"),
            series.get(CPI_DATASET_ID, {}),
            prior_key="comparison_period",
            prior_id_key="comparison_observation_id",
        )
        calculation["federal_funds"] = _stamp_endpoints(
            calculation.get("federal_funds"),
            series.get(FED_FUNDS_DATASET_ID, {}),
            prior_key="prior_period",
            prior_id_key="prior_observation_id",
        )
        calculation["treasury_10_year"] = _stamp_endpoints(
            calculation.get("treasury_10_year"),
            series.get(TREASURY_10Y_DATASET_ID, {}),
            prior_key="prior_period",
            prior_id_key="prior_observation_id",
        )
        stamped.append(
            MacroReadingInput(
                method_id=item.method_id,
                sufficiency=item.sufficiency,
                missing_reason=item.missing_reason,
                calculation=calculation,
                run_id=item.run_id,
            ),
        )
    return stamped


def _stamp_endpoints(
    block: object,
    rows: dict[date, EconomicObservation],
    *,
    prior_key: str,
    prior_id_key: str,
) -> object:
    if not isinstance(block, dict):
        return block
    stamped = dict(block)
    current = rows.get(_period(block.get("period")) or date.min)
    prior = rows.get(_period(block.get(prior_key)) or date.min)
    if current is not None:
        stamped["observation_id"] = current.observation_id
    if prior is not None:
        stamped[prior_id_key] = prior.observation_id
    return stamped


def _production_endpoints(
    series: dict[date, EconomicObservation],
    reading: MacroReadingInput | None,
) -> dict[str, str] | None:
    if reading is None or not isinstance(reading.calculation, dict):
        return None
    latest = _period(reading.calculation.get("latest_period"))
    earlier = _period(reading.calculation.get("earlier_period"))
    if latest is None or earlier is None:
        return None
    latest_row = series.get(latest)
    earlier_row = series.get(earlier)
    if latest_row is None or earlier_row is None:
        return None
    return {"latest": latest_row.observation_id, "earlier": earlier_row.observation_id}


def _period(value: object) -> date | None:
    if not isinstance(value, str):
        return None
    return date.fromisoformat(value[:10])


def _datasets(spec: _ReadingSpec) -> tuple[str, ...]:
    if spec.method_id == LABOUR_MARKET_METHOD_ID:
        return (UNEMPLOYMENT_DATASET_ID, PAYROLLS_DATASET_ID, OPENINGS_DATASET_ID)
    if spec.method_id == PRICES_AND_POLICY_METHOD_ID:
        return (CPI_DATASET_ID, FED_FUNDS_DATASET_ID, TREASURY_10Y_DATASET_ID)
    if spec.method_id == CREDIT_STANDARDS_AND_VOLUMES_METHOD_ID:
        return (SLOOS_DATASET_ID, H8_DATASET_ID)
    return (spec.dataset_id,)


def _load_live_rows(conn: psycopg.Connection) -> tuple[EconomicObservation, ...]:
    columns = ", ".join(f"o.{name}" for name in _OBSERVATION_COLUMNS)
    with conn.cursor() as cur:
        cur.execute(
            f"""
            select {columns}
            from research.economic_observations o
            join research.source_retrievals r using (retrieval_id)
            where r.collection_mode = 'live'
              and o.dataset_id = any(%s)
            """,
            (list(LIVE_DATASETS),),
        )
        fetched = cur.fetchall()
    return tuple(row_to_observation(row, _OBSERVATION_COLUMNS) for row in fetched)
