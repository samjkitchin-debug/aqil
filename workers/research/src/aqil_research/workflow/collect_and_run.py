"""End-to-end collect → research → persist → verify."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import psycopg

from aqil_research.collection.service import collect_bls_unemployment
from aqil_research.contracts.observation import AnalysisMode
from aqil_research.insight.build_sahm import build_sahm_insight
from aqil_research.insight.models import ChartPoint, ResearchInsight
from aqil_research.methods.configs import SAHM_PUBLISHED
from aqil_research.methods.evaluation import sahm_window_complete
from aqil_research.methods.registry import SAHM_METHOD_ID, default_method_registry
from aqil_research.persistence.reproduce import verify_stored_run_replay
from aqil_research.persistence.runs import save_research_run
from aqil_research.pipeline.models import ResearchExecutionRequest
from aqil_research.pipeline.orchestrate import execute_research_run
from aqil_research.sources.rights import load_source_rights
from aqil_research.vintages.store import ObservationStore

BLS_DATASET_ID = "bls.ln.LNS14000000"


@dataclass(frozen=True, slots=True)
class CollectAndRunResult:
    collection_outcome: str
    run_id: str | None
    execution_status: str | None
    analytical_payload_hash: str | None
    recompute_match: bool | None
    insight: ResearchInsight | None
    warnings: tuple[str, ...]


def collect_and_run_sahm(
    conn: psycopg.Connection,
    *,
    live: bool,
    fixture_path: Path | None,
    start_year: int | None,
    end_year: int | None,
    run_id: str,
    evaluation_period: str | None = None,
    allow_evaluation_fallback: bool = False,
) -> CollectAndRunResult:
    now = datetime.now(tz=UTC)
    rights = load_source_rights()
    collection_result, store = collect_bls_unemployment(
        store_backend="postgres",
        collected_at=now,
        live=live,
        fixture_path=str(fixture_path) if fixture_path else None,
        start_year=start_year,
        end_year=end_year,
        conn=conn,
    )
    warnings = list(collection_result.warnings)
    if collection_result.outcome in ("failed_rights", "failed_fetch", "failed_validation"):
        return CollectAndRunResult(
            collection_outcome=collection_result.outcome,
            run_id=None,
            execution_status=None,
            analytical_payload_hash=None,
            recompute_match=None,
            insight=None,
            warnings=tuple(warnings),
        )
    if collection_result.conflicts_detected:
        warnings.append(f"{collection_result.conflicts_detected} observation conflict(s) detected")

    if not isinstance(store, ObservationStore):
        raise TypeError("expected ObservationStore from collection")

    by_period = store.as_of(BLS_DATASET_ID, now, AnalysisMode.LATEST_REVISED)
    if not by_period:
        return CollectAndRunResult(
            collection_outcome=collection_result.outcome,
            run_id=None,
            execution_status="failed_ingest",
            analytical_payload_hash=None,
            recompute_match=None,
            insight=None,
            warnings=tuple(warnings + ["No observations available after collection"]),
        )

    if evaluation_period:
        from datetime import date

        evaluation = date.fromisoformat(evaluation_period)
        if evaluation.day != 1 or not sahm_window_complete(by_period, evaluation):
            return CollectAndRunResult(
                collection_outcome=collection_result.outcome,
                run_id=None,
                execution_status="completed_insufficient",
                analytical_payload_hash=None,
                recompute_match=None,
                insight=None,
                warnings=tuple(warnings + ["Evaluation period insufficient for Sahm"]),
            )
        eval_str = evaluation_period
    else:
        evaluation = max(by_period)
        if not sahm_window_complete(by_period, evaluation):
            if not allow_evaluation_fallback:
                return CollectAndRunResult(
                    collection_outcome=collection_result.outcome,
                    run_id=None,
                    execution_status="completed_insufficient",
                    analytical_payload_hash=None,
                    recompute_match=None,
                    insight=None,
                    warnings=tuple(
                        warnings
                        + [
                            "Latest month lacks full Sahm window; "
                            "pass evaluation period or fallback",
                        ],
                    ),
                )
        eval_str = evaluation.isoformat()

    request = ResearchExecutionRequest(
        source_id="bls_cps_unemployment_rate",
        dataset_id=BLS_DATASET_ID,
        decision_at=now,
        analysis_mode=AnalysisMode.LATEST_REVISED,
        evaluation_period=eval_str,
        method_id=SAHM_METHOD_ID,
        method_config=SAHM_PUBLISHED.model_dump(mode="json"),
        collect=False,
        primary_adapter_id="bls_api_lns14000000",
    )
    run = execute_research_run(
        request,
        store=store,
        rights_records=rights,
        method_registry=default_method_registry(),
        executed_at=now,
        run_id=run_id,
    )
    save_research_run(conn, run)
    replay = verify_stored_run_replay(conn, run_id)
    recompute_match = replay.full_match

    chart_points = _chart_points(by_period)
    insight = build_sahm_insight(run, chart_points=chart_points)

    return CollectAndRunResult(
        collection_outcome=collection_result.outcome,
        run_id=run.run_id,
        execution_status=run.execution_status,
        analytical_payload_hash=run.analytical_payload_hash,
        recompute_match=recompute_match,
        insight=insight,
        warnings=tuple(warnings),
    )


def _chart_points(by_period: dict) -> list[ChartPoint]:
    points: list[ChartPoint] = []
    for period in sorted(by_period):
        obs = by_period[period]
        try:
            value = float(obs.raw_value)
        except (TypeError, ValueError):
            continue
        points.append(ChartPoint(period=period.isoformat(), value=value))
    return points[-24:]
