"""Fail-closed rights enforcement at research execution boundaries."""

from __future__ import annotations

from aqil_research.adapters.protocol import ProviderAdapter
from aqil_research.sources.rights import RightsDecision, RightsOperation, SourceRightsRecord


class RightsGateError(Exception):
    """Raised when a rights decision blocks an operation."""


def resolve_research_rights(
    records: tuple[SourceRightsRecord, ...],
    *,
    source_id: str,
    dataset_id: str,
) -> SourceRightsRecord:
    """Match source and dataset to exactly one enabled register row."""
    matches = [
        row for row in records if row.source_id == source_id and row.dataset_id == dataset_id
    ]
    if not matches:
        raise RightsGateError(
            f"no rights record for source_id={source_id} dataset_id={dataset_id}",
        )
    if len(matches) > 1:
        raise RightsGateError(f"ambiguous rights records for {source_id}/{dataset_id}")
    return matches[0]


def assert_rights_for_ingest(
    rights: SourceRightsRecord,
    adapter: ProviderAdapter,
) -> None:
    if rights.source_id != adapter.identity.source_id:
        raise RightsGateError(
            f"adapter source_id {adapter.identity.source_id} "
            f"does not match rights {rights.source_id}",
        )
    if rights.dataset_id != adapter.identity.dataset_id:
        raise RightsGateError(
            f"adapter dataset_id {adapter.identity.dataset_id} "
            f"does not match rights {rights.dataset_id}",
        )
    _require_enabled(rights)
    _require_permitted(rights, RightsOperation.AUTOMATED_ACCESS)
    _require_permitted(rights, RightsOperation.RAW_DATA_RETENTION)


def assert_rights_for_analysis(rights: SourceRightsRecord) -> None:
    _require_enabled(rights)
    _require_permitted(rights, RightsOperation.INTERNAL_COMPUTATION)


def assert_rights_for_replay(rights: SourceRightsRecord) -> None:
    """Using stored observations for calculation still requires internal computation."""
    assert_rights_for_analysis(rights)


def _require_enabled(rights: SourceRightsRecord) -> None:
    from aqil_research.sources.rights import OperationalStatus

    if rights.operational_status != OperationalStatus.ENABLED:
        raise RightsGateError(f"source {rights.source_id} is disabled")


def _require_permitted(rights: SourceRightsRecord, operation: RightsOperation) -> None:
    decision = rights.decision_for(operation)
    if decision != RightsDecision.PERMITTED:
        raise RightsGateError(
            f"operation {operation.value} is {decision.value} for {rights.source_id}",
        )
