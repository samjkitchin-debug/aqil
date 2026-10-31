"""Registered source connectors for refresh and the daily cycle.

A connector identifies a source, fetches, parses, and validates. It returns
the existing observation contract. It does not contain a method or a page.
Disabling a source is a registry flag. The implementation stays registered.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from aqil_research.contracts.observation import EconomicObservation


class InvalidObservationUnit(Exception):
    """The payload names a unit this connector does not accept."""


class RightsBlocked(Exception):
    """Permanent rights or access refusal. The cycle does not retry it."""

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class TransientSourceError(Exception):
    """A retryable fetch failure."""


@dataclass(frozen=True, slots=True)
class SourceIdentity:
    source_id: str
    cadence: str
    enabled: bool
    rights_record_id: str
    dataset_ids: tuple[str, ...]
    data_frequency: str


@dataclass(frozen=True, slots=True)
class ParsedSource:
    """Observations already on the economic-observation contract."""

    observations: tuple[EconomicObservation, ...]
    detail: str = ""


class SourceConnector(Protocol):
    def identity(self) -> SourceIdentity: ...

    def fetch(self, now: datetime) -> object: ...

    def parse(self, fetched: object) -> ParsedSource: ...

    def validate(self, parsed: ParsedSource) -> ParsedSource: ...

    def refresh(self, now: datetime) -> object: ...


class FunctionSourceConnector:
    """Wrap one existing refresh callable. The callable still persists."""

    def __init__(
        self,
        *,
        source_id: str,
        action: Callable[[datetime], object],
        cadence: str,
        data_frequency: str,
        rights_record_id: str,
        dataset_ids: tuple[str, ...] = (),
        enabled: bool = True,
        allowed_units: tuple[str, ...] = (),
    ) -> None:
        self._source_id = source_id
        self._action = action
        self._cadence = cadence
        self._data_frequency = data_frequency
        self._rights_record_id = rights_record_id
        self._dataset_ids = dataset_ids
        self._enabled = enabled
        self._allowed_units = allowed_units

    def identity(self) -> SourceIdentity:
        return SourceIdentity(
            source_id=self._source_id,
            cadence=self._cadence,
            enabled=self._enabled,
            rights_record_id=self._rights_record_id,
            dataset_ids=self._dataset_ids,
            data_frequency=self._data_frequency,
        )

    def fetch(self, now: datetime) -> object:
        del now
        return None

    def parse(self, fetched: object) -> ParsedSource:
        if isinstance(fetched, ParsedSource):
            return fetched
        return ParsedSource(())

    def validate(self, parsed: ParsedSource) -> ParsedSource:
        if not self._allowed_units:
            return parsed
        allowed = set(self._allowed_units)
        for observation in parsed.observations:
            if observation.unit not in allowed:
                raise InvalidObservationUnit(observation.dataset_id)
        return parsed

    def refresh(self, now: datetime) -> object:
        return self._action(now)


class SourceRegistry:
    """Ordered connectors. A disabled id is omitted from refresh steps."""

    def __init__(self) -> None:
        self._order: list[SourceConnector] = []
        self._disabled: set[str] = set()

    def register(self, connector: SourceConnector) -> None:
        source_id = connector.identity().source_id
        self._order = [item for item in self._order if item.identity().source_id != source_id]
        self._disabled.discard(source_id)
        self._order.append(connector)

    def disable(self, source_id: str) -> None:
        self._disabled.add(source_id)

    def source_ids(self, *, enabled_only: bool = False) -> tuple[str, ...]:
        ids: list[str] = []
        for connector in self._order:
            source_id = connector.identity().source_id
            if enabled_only and (source_id in self._disabled or not connector.identity().enabled):
                continue
            ids.append(source_id)
        return tuple(ids)

    def get(self, source_id: str) -> SourceConnector:
        for connector in self._order:
            if connector.identity().source_id == source_id:
                return connector
        raise KeyError(source_id)

    def refresh_steps(self) -> tuple[tuple[str, Callable[[datetime], object]], ...]:
        steps: list[tuple[str, Callable[[datetime], object]]] = []
        for connector in self._order:
            identity = connector.identity()
            if identity.source_id in self._disabled or not identity.enabled:
                continue
            steps.append((identity.source_id, connector.refresh))
        return tuple(steps)

    def enabled_connectors(self) -> tuple[SourceConnector, ...]:
        return tuple(self.get(source_id) for source_id in self.source_ids(enabled_only=True))
