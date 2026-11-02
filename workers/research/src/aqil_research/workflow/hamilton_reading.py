"""Record the monthly Hamilton regime-switching variant when stored G.17 changes.

There is no jobs table and no cron. A caller invokes this function. The same
inputs do not append another run. publication_allowed stays false.

The estimate is retrospective on the latest-revised sample. Smoothed
probabilities use future observations, so the stored path is not a
real-time assessment.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import psycopg

from aqil_research.adapters.fed_g17.parse import DATASET_ID, SOURCE_ID
from aqil_research.contracts.observation import AnalysisMode
from aqil_research.methods.bry_boschan_monthly import G17_DATASET_ID
from aqil_research.methods.hamilton_monthly import (
    HAMILTON_MONTHLY_PUBLISHED,
    METHOD_ID,
    HamiltonMonthlyMethod,
)
from aqil_research.methods.registry import MethodRegistry
from aqil_research.persistence.observation_store import PostgresDatasetObservationStore
from aqil_research.persistence.runs import save_research_run
from aqil_research.pipeline.models import ResearchExecutionRequest, ResearchRun
from aqil_research.pipeline.orchestrate import execute_research_run
from aqil_research.sources.rights import load_source_rights


@dataclass(frozen=True, slots=True)
class HamiltonReadingResult:
    status: str
    run_id: str | None
    detail: str


def record_hamilton_monthly_reading(
    conn: psycopg.Connection,
    *,
    decision_at: datetime | None = None,
) -> HamiltonReadingResult:
    """Append one run when the latest-revised G.17 snapshot is not already stored."""

    if DATASET_ID != G17_DATASET_ID:
        raise RuntimeError("G.17 dataset id does not match the Bry-Boschan loader")
    now = decision_at or datetime.now(tz=UTC)
    if _fixture_retrieval_present(conn):
        return HamiltonReadingResult(
            "refused_fixture",
            None,
            "Fixture G.17 rows are not an input to this variant.",
        )
    store = PostgresDatasetObservationStore(conn, DATASET_ID)
    series = store.as_of(DATASET_ID, now, AnalysisMode.LATEST_REVISED)
    if not series:
        return HamiltonReadingResult(
            "completed_insufficient",
            None,
            "No stored G.17 months.",
        )
    evaluation = max(series)
    request = ResearchExecutionRequest(
        source_id=SOURCE_ID,
        dataset_id=DATASET_ID,
        decision_at=now,
        analysis_mode=AnalysisMode.LATEST_REVISED,
        evaluation_period=evaluation.isoformat(),
        method_id=METHOD_ID,
        method_config=dict(HAMILTON_MONTHLY_PUBLISHED),
        collect=False,
    )
    run = execute_research_run(
        request,
        store=store,
        rights_records=load_source_rights(),
        method_registry=_registry(),
        executed_at=now,
    )
    _refuse_publication(run)
    if run.execution_status not in {"completed", "completed_insufficient"}:
        return HamiltonReadingResult(run.execution_status, None, run.narrative)
    if _same_reading(conn, run):
        return HamiltonReadingResult(
            "unchanged",
            _latest_run_id(conn),
            "Stored reading already matches.",
        )
    save_research_run(conn, run)
    return HamiltonReadingResult(run.execution_status, run.run_id, run.narrative)


def _registry() -> MethodRegistry:
    registry = MethodRegistry()
    registry.register(HamiltonMonthlyMethod())
    return registry


def _refuse_publication(run: ResearchRun) -> None:
    if run.publication_allowed:
        raise RuntimeError("publication_allowed must stay false")
    calculation = run.calculation or {}
    if calculation.get("publication_allowed") is not False:
        raise RuntimeError("publication_allowed must stay false")
    if calculation.get("operational") is not False:
        raise RuntimeError("the method must not be stored as operational")
    if calculation.get("empirically_qualified") is not False:
        raise RuntimeError("the method must not be stored as empirically qualified")


def _fixture_retrieval_present(conn: psycopg.Connection) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            """
            select 1
            from research.economic_observations as observation
            join research.source_retrievals as retrieval
              on retrieval.retrieval_id = observation.retrieval_id
            where observation.dataset_id = %s
              and retrieval.collection_mode = 'fixture'
            limit 1
            """,
            (DATASET_ID,),
        )
        return cur.fetchone() is not None


def _same_reading(conn: psycopg.Connection, run: ResearchRun) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            """
            select input_snapshot_hash, method_version, implementation_hash,
                   evaluation_period::text, data_sufficiency
            from research.research_runs
            where method_id = %s
            order by executed_at desc
            limit 1
            """,
            (METHOD_ID,),
        )
        row = cur.fetchone()
    if row is None:
        return False
    return (
        row[0] == run.input_snapshot_hash
        and row[1] == run.method_version
        and row[2] == run.implementation_hash
        and row[3] == run.evaluation_period
        and row[4] == run.data_sufficiency
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
            (METHOD_ID,),
        )
        row = cur.fetchone()
    if row is None:
        return None
    return str(row[0])
