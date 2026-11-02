"""Append one autoregressive benchmark run on stored industrial production.

There is no second ingest path. Observations come from the research observation
store. Fixture-linked rows are omitted before as-of selection. A matching
stored run is left in place. publication_allowed stays false.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from urllib.parse import urlparse

import psycopg

from aqil_research.contracts.observation import AnalysisMode, EconomicObservation
from aqil_research.methods.autoregressive_benchmark import (
    AUTOREGRESSIVE_BENCHMARK,
    INDUSTRIAL_PRODUCTION_DATASET_ID,
    PUBLISHED_CONFIG,
    AutoregressiveBenchmarkMethod,
)
from aqil_research.methods.registry import MethodRegistry
from aqil_research.persistence.config import DEFAULT_LOCAL_URL
from aqil_research.persistence.observation_store import load_observations_for_dataset
from aqil_research.persistence.runs import save_research_run
from aqil_research.pipeline.models import ResearchExecutionRequest
from aqil_research.pipeline.orchestrate import execute_research_run
from aqil_research.sources.rights import load_source_rights
from aqil_research.vintages.asof import select_as_of_series
from aqil_research.vintages.store import AppendResult

PRIMARY_SOURCE_ID = "federal_reserve_g17_total_ip"


@dataclass(frozen=True, slots=True)
class AutoregressiveBenchmarkReadingResult:
    status: str
    run_id: str | None
    detail: str


class _LiveObservationStore:
    """Read-only store. Fixture rows are dropped before as-of selection."""

    def __init__(self, conn: psycopg.Connection, fixture_observation_ids: frozenset[str]) -> None:
        self._conn = conn
        self._fixture_observation_ids = fixture_observation_ids

    def append(self, observation: EconomicObservation) -> AppendResult:
        raise RuntimeError("the autoregressive benchmark store is read-only")

    def append_many(self, observations: tuple[EconomicObservation, ...]) -> AppendResult:
        raise RuntimeError("the autoregressive benchmark store is read-only")

    def all_observations(self) -> tuple[EconomicObservation, ...]:
        return tuple(
            row
            for row in load_observations_for_dataset(self._conn, INDUSTRIAL_PRODUCTION_DATASET_ID)
            if row.observation_id not in self._fixture_observation_ids
        )

    def as_of(
        self,
        dataset_id: str,
        decision_at: datetime,
        mode: AnalysisMode,
    ) -> dict[date, EconomicObservation]:
        rows = tuple(
            row
            for row in load_observations_for_dataset(self._conn, dataset_id)
            if row.observation_id not in self._fixture_observation_ids
        )
        return select_as_of_series(rows, dataset_id, decision_at, mode)


def record_autoregressive_benchmark(
    conn: psycopg.Connection,
    *,
    decision_at: datetime | None = None,
) -> AutoregressiveBenchmarkReadingResult:
    """Append one run. Does not overwrite a stored run."""
    now = decision_at or datetime.now(tz=UTC)
    store = _LiveObservationStore(conn, _fixture_observation_ids(conn))
    primary = store.as_of(INDUSTRIAL_PRODUCTION_DATASET_ID, now, AnalysisMode.LATEST_REVISED)
    if not primary:
        return AutoregressiveBenchmarkReadingResult(
            "completed_insufficient",
            None,
            "No stored live industrial production month was available.",
        )
    evaluation = max(primary)
    registry = MethodRegistry()
    registry.register(AutoregressiveBenchmarkMethod())
    run = execute_research_run(
        ResearchExecutionRequest(
            source_id=PRIMARY_SOURCE_ID,
            dataset_id=INDUSTRIAL_PRODUCTION_DATASET_ID,
            decision_at=now,
            analysis_mode=AnalysisMode.LATEST_REVISED,
            evaluation_period=evaluation.isoformat(),
            method_id=AUTOREGRESSIVE_BENCHMARK,
            method_config=dict(PUBLISHED_CONFIG),
            collect=False,
        ),
        store=store,
        rights_records=load_source_rights(),
        method_registry=registry,
        executed_at=now,
    )
    if run.publication_allowed:
        raise RuntimeError("publication_allowed must stay false")
    if run.calculation is not None and run.calculation.get("publication_allowed") is not False:
        raise RuntimeError("publication_allowed must stay false")
    if run.execution_status not in {"completed", "completed_insufficient"}:
        return AutoregressiveBenchmarkReadingResult(
            run.execution_status,
            None,
            run.narrative,
        )
    if _same_reading(
        conn,
        run.input_snapshot_hash,
        run.method_version,
        run.implementation_hash,
        run.evaluation_period,
        run.data_sufficiency,
    ):
        return AutoregressiveBenchmarkReadingResult(
            "unchanged",
            _latest_run_id(conn),
            "Stored reading already matches.",
        )
    save_research_run(conn, run)
    return AutoregressiveBenchmarkReadingResult(run.execution_status, run.run_id, run.narrative)


def try_record_autoregressive_benchmark() -> AutoregressiveBenchmarkReadingResult:
    """Append when the preserved local database accepts a connection."""
    url = _preserved_local_url()
    try:
        with psycopg.connect(url, connect_timeout=3) as conn:
            result = record_autoregressive_benchmark(conn)
            conn.commit()
            return result
    except psycopg.Error as exc:
        return AutoregressiveBenchmarkReadingResult(
            "database_unreachable",
            None,
            _safe_error(exc),
        )


def _preserved_local_url() -> str:
    parsed = urlparse(DEFAULT_LOCAL_URL)
    if parsed.hostname != "127.0.0.1" or parsed.port != 55432:
        raise RuntimeError(
            "refusing to connect to a database that is not the preserved local postgres",
        )
    return DEFAULT_LOCAL_URL


def _fixture_observation_ids(conn: psycopg.Connection) -> frozenset[str]:
    with conn.cursor() as cur:
        cur.execute(
            """
            select observation.observation_id
            from research.economic_observations as observation
            join research.source_retrievals as retrieval
              on retrieval.retrieval_id = observation.retrieval_id
            where observation.dataset_id = %s
              and retrieval.collection_mode = 'fixture'
            """,
            (INDUSTRIAL_PRODUCTION_DATASET_ID,),
        )
        return frozenset(str(row[0]) for row in cur.fetchall())


def _same_reading(
    conn: psycopg.Connection,
    input_snapshot_hash: str,
    method_version: str,
    implementation_hash: str,
    evaluation_period: str,
    data_sufficiency: str,
) -> bool:
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
            (AUTOREGRESSIVE_BENCHMARK,),
        )
        row = cur.fetchone()
    if row is None:
        return False
    return (
        row[0] == input_snapshot_hash
        and row[1] == method_version
        and row[2] == implementation_hash
        and row[3] == evaluation_period
        and row[4] == data_sufficiency
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
            (AUTOREGRESSIVE_BENCHMARK,),
        )
        row = cur.fetchone()
    if row is None:
        return None
    return str(row[0])


def _safe_error(exc: Exception) -> str:
    text = str(exc)
    if "://" in text or "@" in text or "password" in text.lower():
        return exc.__class__.__name__
    return f"{exc.__class__.__name__}: {text[:300]}"
