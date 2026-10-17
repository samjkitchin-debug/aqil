"""Append-only in-memory observation store."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol, runtime_checkable

from aqil_research.contracts.canonical import observation_canonical_dict
from aqil_research.contracts.observation import AnalysisMode, EconomicObservation
from aqil_research.vintages.asof import select_as_of_series


class VintageConflictError(Exception):
    """Raised when a duplicate vintage identity carries a different value."""


@dataclass(frozen=True, slots=True)
class AppendResult:
    inserted: int
    unchanged: int
    conflicts: int


@runtime_checkable
class ObservationStore(Protocol):
    def append(self, observation: EconomicObservation) -> AppendResult: ...

    def append_many(self, observations: tuple[EconomicObservation, ...]) -> AppendResult: ...

    def all_observations(self) -> tuple[EconomicObservation, ...]: ...

    def as_of(
        self,
        dataset_id: str,
        decision_at: datetime,
        mode: AnalysisMode,
    ) -> dict[date, EconomicObservation]: ...


def content_snapshot_hash(observations: tuple[EconomicObservation, ...]) -> str:
    """Deterministic hash from canonical observation content, not insertion order."""
    payload = [
        observation_canonical_dict(row)
        for row in sorted(
            observations,
            key=lambda item: (
                item.dataset_id,
                item.period_start,
                item.provider_vintage_date,
                item.observation_id,
            ),
        )
    ]
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class InMemoryObservationStore:
    """Append-only store. Partial or empty batches never delete rows."""

    def __init__(self) -> None:
        self._rows: list[EconomicObservation] = []
        self._by_vintage: dict[tuple[str, date, date], EconomicObservation] = {}

    def append(self, observation: EconomicObservation) -> AppendResult:
        return self.append_many((observation,))

    def append_many(self, observations: tuple[EconomicObservation, ...]) -> AppendResult:
        inserted = 0
        unchanged = 0
        for observation in observations:
            key = observation.vintage_identity()
            existing = self._by_vintage.get(key)
            if existing is None:
                self._by_vintage[key] = observation
                self._rows.append(observation)
                inserted += 1
                continue
            if _observations_equal(existing, observation):
                unchanged += 1
                continue
            raise VintageConflictError(
                f"conflicting value for vintage {key}: "
                f"{existing.raw_value} vs {observation.raw_value}",
            )
        return AppendResult(inserted=inserted, unchanged=unchanged, conflicts=0)

    def all_observations(self) -> tuple[EconomicObservation, ...]:
        return tuple(self._rows)

    def as_of(
        self,
        dataset_id: str,
        decision_at: datetime,
        mode: AnalysisMode,
    ) -> dict[date, EconomicObservation]:
        return select_as_of_series(self.all_observations(), dataset_id, decision_at, mode)


def _observations_equal(left: EconomicObservation, right: EconomicObservation) -> bool:
    return left.model_dump() == right.model_dump()
