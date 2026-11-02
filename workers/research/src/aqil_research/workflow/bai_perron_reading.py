"""Append one mean-shift reading for stored industrial production.

There is no jobs table and no cron. The same inputs do not append another run.
``publication_allowed`` stays false. The default method registry is left
unchanged; this function registers the method on a local registry.

Dates are retrospective point estimates on latest revised log-growth. They
are not a forecast.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import psycopg

from aqil_research.adapters.fed_g17.parse import DATASET_ID, SOURCE_ID
from aqil_research.contracts.observation import AnalysisMode
from aqil_research.methods.bai_perron_mean_shifts import (
    BAI_PERRON_MEAN_SHIFTS,
    PUBLISHED_CONFIG,
    BaiPerronMeanShiftsMethod,
)
from aqil_research.methods.registry import MethodRegistry
from aqil_research.persistence.observation_store import PostgresDatasetObservationStore
from aqil_research.persistence.runs import save_research_run
from aqil_research.pipeline.models import ResearchExecutionRequest, ResearchRun
from aqil_research.pipeline.orchestrate import execute_research_run
from aqil_research.sources.rights import load_source_rights


@dataclass(frozen=True, slots=True)
class BaiPerronReadingResult:
    status: str
    run_id: str | None
    detail: str


def record_g17_bai_perron_mean_shifts(
    conn: psycopg.Connection,
    *,
    decision_at: datetime | None = None,
) -> BaiPerronReadingResult:
    """Append one run when the latest revised G.17 snapshot changes."""

    now = decision_at or datetime.now(tz=UTC)
    if _fixture_retrieval_present(conn):
        return BaiPerronReadingResult(
            "refused_fixture",
            None,
            "Fixture G.17 rows are not an input to this variant.",
        )
    store = PostgresDatasetObservationStore(conn, DATASET_ID)
    series = store.as_of(DATASET_ID, now, AnalysisMode.LATEST_REVISED)
    if not series:
        return BaiPerronReadingResult(
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
        method_id=BAI_PERRON_MEAN_SHIFTS,
        method_config=dict(PUBLISHED_CONFIG),
        collect=False,
    )
    run = execute_research_run(
        request,
        store=store,
        rights_records=load_source_rights(),
        method_registry=_method_registry(),
        executed_at=now,
    )
    if run.publication_allowed:
        raise RuntimeError("publication_allowed must stay false")
    if run.calculation is not None and run.calculation.get("publication_allowed") is True:
        raise RuntimeError("publication_allowed must stay false")
    if _same_reading(conn, run):
        return BaiPerronReadingResult(
            "unchanged",
            _latest_run_id(conn),
            "Stored reading already matches.",
        )
    save_research_run(conn, run)
    return BaiPerronReadingResult(run.execution_status, run.run_id, run.narrative)


def _method_registry() -> MethodRegistry:
    registry = MethodRegistry()
    registry.register(BaiPerronMeanShiftsMethod())
    return registry


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
            (BAI_PERRON_MEAN_SHIFTS,),
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
            (BAI_PERRON_MEAN_SHIFTS,),
        )
        row = cur.fetchone()
    if row is None:
        return None
    return str(row[0])
