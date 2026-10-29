"""Record the Spencer-15 variant when stored G.17 changes.

There is no jobs table and no cron. A caller, including the G.17 refresh
hook, invokes this function. The same inputs do not append another run.
publication_allowed stays false.

Stored chronologies are retrospective_full_sample. The Spencer smoother is
centred, so the dates are not a contemporaneous recession call.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import psycopg

from aqil_research.adapters.fed_g17.parse import DATASET_ID, SOURCE_ID
from aqil_research.contracts.observation import AnalysisMode
from aqil_research.methods.bry_boschan_spencer15 import BRY_BOSCHAN_SPENCER15_VARIANT
from aqil_research.methods.configs import BRY_BOSCHAN_SPENCER15_PUBLISHED
from aqil_research.methods.registry import default_method_registry
from aqil_research.persistence.observation_store import PostgresDatasetObservationStore
from aqil_research.persistence.reproduce import verify_stored_run_replay
from aqil_research.persistence.runs import save_research_run
from aqil_research.pipeline.models import ResearchExecutionRequest, ResearchRun
from aqil_research.pipeline.orchestrate import execute_research_run
from aqil_research.sources.rights import load_source_rights


@dataclass(frozen=True, slots=True)
class BryBoschanReadingResult:
    status: str
    run_id: str | None
    detail: str


def record_g17_spencer15_reading(
    conn: psycopg.Connection,
    *,
    decision_at: datetime | None = None,
) -> BryBoschanReadingResult:
    """Append one run when the latest-revised G.17 snapshot changes."""
    now = decision_at or datetime.now(tz=UTC)
    if _fixture_retrieval_present(conn):
        return BryBoschanReadingResult(
            "refused_fixture",
            None,
            "fixture G.17 rows are not an input to this variant",
        )
    store = PostgresDatasetObservationStore(conn, DATASET_ID)
    series = store.as_of(DATASET_ID, now, AnalysisMode.LATEST_REVISED)
    if not series:
        return BryBoschanReadingResult("completed_insufficient", None, "no stored G.17 months")
    evaluation = max(series)
    request = ResearchExecutionRequest(
        source_id=SOURCE_ID,
        dataset_id=DATASET_ID,
        decision_at=now,
        analysis_mode=AnalysisMode.LATEST_REVISED,
        evaluation_period=evaluation.isoformat(),
        method_id=BRY_BOSCHAN_SPENCER15_VARIANT,
        method_config=dict(BRY_BOSCHAN_SPENCER15_PUBLISHED),
        collect=False,
    )
    run = execute_research_run(
        request,
        store=store,
        rights_records=load_source_rights(),
        method_registry=default_method_registry(),
        executed_at=now,
    )
    if run.publication_allowed:
        raise RuntimeError("publication_allowed must stay false")
    if _same_reading(conn, run):
        return BryBoschanReadingResult(
            "unchanged",
            _latest_run_id(conn),
            "stored reading already matches",
        )
    save_research_run(conn, run)
    return BryBoschanReadingResult(run.execution_status, run.run_id, run.narrative)


def replay_stored_reading(conn: psycopg.Connection, run_id: str) -> bool:
    """True when recomputing the stored observation links matches the stored run."""
    return verify_stored_run_replay(conn, run_id).full_match


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
            (BRY_BOSCHAN_SPENCER15_VARIANT,),
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
            (BRY_BOSCHAN_SPENCER15_VARIANT,),
        )
        row = cur.fetchone()
    if row is None:
        return None
    return str(row[0])
