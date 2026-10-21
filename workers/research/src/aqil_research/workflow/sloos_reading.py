"""Run the existing SLOOS method on stored live observations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import psycopg

from aqil_research.adapters.fed_sloos.parse import DATASET_ID, SOURCE_ID
from aqil_research.adapters.fed_sloos.stability import StoredSloosPoint
from aqil_research.contracts.observation import AnalysisMode
from aqil_research.methods.configs import SLOOS_CIL_PUBLISHED
from aqil_research.methods.registry import default_method_registry
from aqil_research.methods.sloos_cil import SLOOS_CIL_METHOD_ID
from aqil_research.persistence.observation_store import PostgresDatasetObservationStore
from aqil_research.persistence.runs import save_research_run
from aqil_research.pipeline.models import ResearchExecutionRequest
from aqil_research.pipeline.orchestrate import execute_research_run
from aqil_research.sources.rights import load_source_rights


@dataclass(frozen=True, slots=True)
class SloosReadingResult:
    status: str
    run_id: str | None
    detail: str


def load_sloos_priors(conn: psycopg.Connection) -> tuple[StoredSloosPoint, ...]:
    """Every stored SLOOS point, so a later fetch can reuse an unchanged identity."""
    with conn.cursor() as cur:
        cur.execute(
            """
            select period_start, observation_id, raw_value, provider_vintage_date,
                   source_release_at, retrieved_at
            from research.economic_observations
            where dataset_id = %s
            """,
            (DATASET_ID,),
        )
        rows = cur.fetchall()
    return tuple(
        StoredSloosPoint(
            period_start=row[0],
            observation_id=str(row[1]),
            raw_value=str(row[2]),
            provider_vintage_date=row[3],
            source_release_at=row[4],
            retrieved_at=row[5],
        )
        for row in rows
    )


def record_sloos_reading(
    conn: psycopg.Connection,
    *,
    decision_at: datetime | None = None,
) -> SloosReadingResult:
    """Calculate the latest stored quarter and append a run when the result changes."""
    now = decision_at or datetime.now(tz=UTC)
    store = PostgresDatasetObservationStore(conn, DATASET_ID)
    series = store.as_of(DATASET_ID, now, AnalysisMode.LATEST_REVISED)
    evaluation = max(series) if series else now.date().replace(day=1)
    request = ResearchExecutionRequest(
        source_id=SOURCE_ID,
        dataset_id=DATASET_ID,
        decision_at=now,
        analysis_mode=AnalysisMode.LATEST_REVISED,
        evaluation_period=evaluation.isoformat(),
        method_id=SLOOS_CIL_METHOD_ID,
        method_config=dict(SLOOS_CIL_PUBLISHED),
        collect=False,
    )
    run = execute_research_run(
        request,
        store=store,
        rights_records=load_source_rights(),
        method_registry=default_method_registry(),
        executed_at=now,
    )
    if _same_reading(conn, run):
        saved_id = _latest_run_id(conn)
        return SloosReadingResult("unchanged", saved_id, "stored reading already matches")
    save_research_run(conn, run)
    return SloosReadingResult(run.execution_status, run.run_id, run.narrative)


def _same_reading(conn: psycopg.Connection, run: object) -> bool:
    from aqil_research.pipeline.models import ResearchRun

    if not isinstance(run, ResearchRun):
        return False
    with conn.cursor() as cur:
        cur.execute(
            """
            select input_snapshot_hash, method_version, evaluation_period::text,
                   data_sufficiency, missing_data_reason
            from research.research_runs
            where method_id = %s
            order by executed_at desc
            limit 1
            """,
            (SLOOS_CIL_METHOD_ID,),
        )
        row = cur.fetchone()
    if row is None:
        return False
    return (
        row[0] == run.input_snapshot_hash
        and row[1] == run.method_version
        and row[2] == run.evaluation_period
        and row[3] == run.data_sufficiency
        and row[4] == run.missing_data_reason
    )


def _latest_run_id(conn: psycopg.Connection) -> str | None:
    with conn.cursor() as cur:
        cur.execute(
            """
            select run_id
            from research.research_runs
            where method_id = %s
            order by executed_at desc
            limit 1
            """,
            (SLOOS_CIL_METHOD_ID,),
        )
        row = cur.fetchone()
    if row is None:
        return None
    return str(row[0])
