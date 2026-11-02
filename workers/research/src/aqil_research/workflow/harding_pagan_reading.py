"""Record Harding–Pagan characteristics for the coincident level series.

There is no jobs table and no cron. The same inputs do not append another run.
publication_allowed stays false. Dates are retrospective_full_sample on
latest_revised levels. A fixture retrieval is left out of the input, so that
series is not given a turning point.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime

import psycopg

from aqil_research.contracts.observation import AnalysisMode, EconomicObservation
from aqil_research.methods.bry_boschan_monthly import G17_DATASET_ID
from aqil_research.methods.harding_pagan_characteristics import (
    HARDING_PAGAN_CHARACTERISTICS,
    HARDING_PAGAN_CHARACTERISTICS_PUBLISHED,
    HardingPaganCharacteristicsMethod,
)
from aqil_research.methods.registry import MethodRegistry
from aqil_research.persistence.observation_store import PostgresResearchObservationStore
from aqil_research.persistence.runs import save_research_run
from aqil_research.pipeline.models import ResearchExecutionRequest, ResearchRun
from aqil_research.pipeline.orchestrate import execute_research_run
from aqil_research.sources.rights import load_source_rights
from aqil_research.vintages.store import AppendResult

PRIMARY_SOURCE_ID = "federal_reserve_g17_total_ip"


@dataclass(frozen=True, slots=True)
class HardingPaganReadingResult:
    status: str
    run_id: str | None
    detail: str


class _LiveObservationStore:
    """Read-only store that omits fixture-linked observations."""

    def __init__(
        self,
        inner: PostgresResearchObservationStore,
        fixture_observation_ids: frozenset[str],
    ) -> None:
        self._inner = inner
        self._fixture_observation_ids = fixture_observation_ids

    def append(self, observation: EconomicObservation) -> AppendResult:
        raise RuntimeError("the characteristics store is read-only")

    def append_many(self, observations: tuple[EconomicObservation, ...]) -> AppendResult:
        del observations
        raise RuntimeError("the characteristics store is read-only")

    def all_observations(self) -> tuple[EconomicObservation, ...]:
        return tuple(
            row
            for row in self._inner.all_observations()
            if row.observation_id not in self._fixture_observation_ids
        )

    def as_of(
        self,
        dataset_id: str,
        decision_at: datetime,
        mode: AnalysisMode,
    ) -> dict[date, EconomicObservation]:
        series = self._inner.as_of(dataset_id, decision_at, mode)
        return {
            period: observation
            for period, observation in series.items()
            if observation.observation_id not in self._fixture_observation_ids
        }


def record_harding_pagan_characteristics(
    conn: psycopg.Connection,
    *,
    decision_at: datetime | None = None,
) -> HardingPaganReadingResult:
    """Append one characteristics run for the stored coincident levels."""
    now = decision_at or datetime.now(tz=UTC)
    inner = PostgresResearchObservationStore(conn)
    store = _LiveObservationStore(inner, _fixture_observation_ids(conn))
    primary = store.as_of(G17_DATASET_ID, now, AnalysisMode.LATEST_REVISED)
    if not primary:
        return HardingPaganReadingResult(
            "completed_insufficient",
            None,
            "no stored live industrial production months",
        )
    evaluation = max(primary)
    request = ResearchExecutionRequest(
        source_id=PRIMARY_SOURCE_ID,
        dataset_id=G17_DATASET_ID,
        decision_at=now,
        analysis_mode=AnalysisMode.LATEST_REVISED,
        evaluation_period=evaluation.isoformat(),
        method_id=HARDING_PAGAN_CHARACTERISTICS,
        method_config=dict(HARDING_PAGAN_CHARACTERISTICS_PUBLISHED),
        collect=False,
    )
    run = execute_research_run(
        request,
        store=store,
        rights_records=load_source_rights(),
        method_registry=_registry(),
        executed_at=now,
    )
    if run.publication_allowed:
        raise RuntimeError("publication_allowed must stay false")
    if _same_reading(conn, run):
        return HardingPaganReadingResult(
            "unchanged",
            _latest_run_id(conn),
            "stored reading already matches",
        )
    save_research_run(conn, run)
    return HardingPaganReadingResult(run.execution_status, run.run_id, run.narrative)


def _registry() -> MethodRegistry:
    registry = MethodRegistry()
    registry.register(HardingPaganCharacteristicsMethod())
    return registry


def _fixture_observation_ids(conn: psycopg.Connection) -> frozenset[str]:
    with conn.cursor() as cur:
        cur.execute(
            """
            select observation.observation_id
            from research.economic_observations as observation
            join research.source_retrievals as retrieval
              on retrieval.retrieval_id = observation.retrieval_id
            where observation.dataset_id = any(%s)
              and retrieval.collection_mode = 'fixture'
            """,
            ([spec_id for spec_id in HardingPaganCharacteristicsMethod().required_dataset_ids()],),
        )
        return frozenset(str(row[0]) for row in cur.fetchall())


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
            (HARDING_PAGAN_CHARACTERISTICS,),
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
            (HARDING_PAGAN_CHARACTERISTICS,),
        )
        row = cur.fetchone()
    if row is None:
        return None
    return str(row[0])
