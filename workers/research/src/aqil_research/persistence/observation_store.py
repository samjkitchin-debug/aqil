"""PostgreSQL-backed observation store."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID

import psycopg

from aqil_research.contracts.observation import AnalysisMode, EconomicObservation
from aqil_research.persistence.mapping import observation_to_insert_params, row_to_observation
from aqil_research.vintages.asof import select_as_of_series
from aqil_research.vintages.store import AppendResult, VintageConflictError

_OBSERVATION_COLUMNS = [
    "observation_id",
    "dataset_id",
    "provider_id",
    "source_id",
    "rights_record_id",
    "period_start",
    "period_end",
    "frequency",
    "geography",
    "unit",
    "seasonal_adjustment",
    "raw_value",
    "quality_status",
    "series_provenance",
    "provider_vintage_date",
    "source_release_at",
    "earliest_model_available_at",
    "availability_precision",
    "retrieved_at",
    "first_seen_at",
    "source_locator",
    "adapter_version",
    "supersedes_observation_id",
]

_TRY_INSERT_SQL = """
select status::text, observation_id, conflict_id
from research.try_insert_observation(
  %(p_observation_id)s,
  %(p_retrieval_id)s,
  %(p_dataset_id)s,
  %(p_provider_id)s,
  %(p_source_id)s,
  %(p_rights_record_id)s,
  %(p_period_start)s,
  %(p_period_end)s,
  %(p_frequency)s,
  %(p_geography)s,
  %(p_unit)s,
  %(p_seasonal_adjustment)s,
  %(p_raw_value)s,
  %(p_quality_status)s,
  %(p_series_provenance)s,
  %(p_provider_vintage_date)s,
  %(p_source_release_at)s,
  %(p_earliest_model_available_at)s,
  %(p_availability_precision)s,
  %(p_retrieved_at)s,
  %(p_first_seen_at)s,
  %(p_source_locator)s,
  %(p_adapter_version)s,
  %(p_supersedes_observation_id)s
)
"""


@dataclass(slots=True)
class PostgresDatasetObservationStore:
    """Read-only view of all observations for a dataset (post-collection research)."""

    _conn: psycopg.Connection
    _dataset_id: str

    def append(self, observation: EconomicObservation) -> AppendResult:
        raise RuntimeError("PostgresDatasetObservationStore is read-only")

    def append_many(self, observations: tuple[EconomicObservation, ...]) -> AppendResult:
        raise RuntimeError("PostgresDatasetObservationStore is read-only")

    def all_observations(self) -> tuple[EconomicObservation, ...]:
        return load_observations_for_dataset(self._conn, self._dataset_id)

    def as_of(
        self,
        dataset_id: str,
        decision_at: datetime,
        mode: AnalysisMode,
    ) -> dict[date, EconomicObservation]:
        rows = load_observations_for_dataset(self._conn, self._dataset_id)
        return select_as_of_series(rows, dataset_id, decision_at, mode)


@dataclass(slots=True)
class PostgresResearchObservationStore:
    """Read-only store spanning all datasets on a connection (post-ingest research)."""

    _conn: psycopg.Connection

    def append(self, observation: EconomicObservation) -> AppendResult:
        raise RuntimeError("PostgresResearchObservationStore is read-only")

    def append_many(self, observations: tuple[EconomicObservation, ...]) -> AppendResult:
        raise RuntimeError("PostgresResearchObservationStore is read-only")

    def all_observations(self) -> tuple[EconomicObservation, ...]:
        return load_all_observations(self._conn)

    def as_of(
        self,
        dataset_id: str,
        decision_at: datetime,
        mode: AnalysisMode,
    ) -> dict[date, EconomicObservation]:
        rows = load_observations_for_dataset(self._conn, dataset_id)
        return select_as_of_series(rows, dataset_id, decision_at, mode)


class PostgresObservationStore:
    """Append-only observation store using research.try_insert_observation."""

    def __init__(self, conn: psycopg.Connection, *, retrieval_id: UUID) -> None:
        self._conn = conn
        self._retrieval_id = retrieval_id

    @property
    def retrieval_id(self) -> UUID:
        return self._retrieval_id

    def append(self, observation: EconomicObservation) -> AppendResult:
        return self.append_many((observation,))

    def append_many(self, observations: tuple[EconomicObservation, ...]) -> AppendResult:
        inserted = 0
        unchanged = 0
        conflicts = 0
        for observation in observations:
            params = observation_to_insert_params(observation, self._retrieval_id)
            with self._conn.cursor() as cur:
                cur.execute(_TRY_INSERT_SQL, params)
                row = cur.fetchone()
            if row is None:
                raise RuntimeError("try_insert_observation returned no row")
            status, _obs_id, _conflict_id = row
            if status == "inserted":
                inserted += 1
            elif status == "unchanged":
                unchanged += 1
            elif status == "conflict":
                conflicts += 1
                raise VintageConflictError(
                    f"conflicting value for vintage {observation.vintage_identity()}",
                )
            else:
                raise RuntimeError(f"unexpected append status {status}")
        return AppendResult(inserted=inserted, unchanged=unchanged, conflicts=conflicts)

    def all_observations(self) -> tuple[EconomicObservation, ...]:
        return load_all_observations(self._conn)

    def as_of(
        self,
        dataset_id: str,
        decision_at: datetime,
        mode: AnalysisMode,
    ) -> dict[date, EconomicObservation]:
        rows = load_observations_for_dataset(self._conn, dataset_id)
        return select_as_of_series(rows, dataset_id, decision_at, mode)


def load_all_observations(conn: psycopg.Connection) -> tuple[EconomicObservation, ...]:
    cols = ", ".join(_OBSERVATION_COLUMNS)
    with conn.cursor() as cur:
        cur.execute(
            f"select {cols} from research.economic_observations order by period_start",
        )
        return tuple(row_to_observation(row, _OBSERVATION_COLUMNS) for row in cur.fetchall())


def load_observations_for_dataset(
    conn: psycopg.Connection,
    dataset_id: str,
) -> tuple[EconomicObservation, ...]:
    cols = ", ".join(_OBSERVATION_COLUMNS)
    with conn.cursor() as cur:
        cur.execute(
            f"select {cols} from research.economic_observations where dataset_id = %s",
            (dataset_id,),
        )
        return tuple(row_to_observation(row, _OBSERVATION_COLUMNS) for row in cur.fetchall())


def load_observations_by_ids(
    conn: psycopg.Connection,
    observation_ids: tuple[str, ...],
) -> tuple[EconomicObservation, ...]:
    if not observation_ids:
        return ()
    cols = ", ".join(_OBSERVATION_COLUMNS)
    with conn.cursor() as cur:
        cur.execute(
            f"select {cols} from research.economic_observations where observation_id = any(%s)",
            (list(observation_ids),),
        )
        return tuple(row_to_observation(row, _OBSERVATION_COLUMNS) for row in cur.fetchall())
