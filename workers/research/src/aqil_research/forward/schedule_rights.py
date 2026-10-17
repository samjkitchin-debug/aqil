"""Rights checks for forward calendar ingestion."""

from __future__ import annotations

from aqil_research.sources.rights import (
    OperationalStatus,
    RightsDecision,
    RightsOperation,
    SourceRightsRecord,
)
from aqil_research.sources.rights_gate import RightsGateError


def assert_schedule_ingest(
    rights: SourceRightsRecord,
    *,
    source_id: str,
    dataset_id: str,
) -> None:
    if rights.source_id != source_id:
        raise RightsGateError(
            f"rights source_id {rights.source_id} does not match expected {source_id}",
        )
    if rights.dataset_id != dataset_id:
        raise RightsGateError(
            f"rights dataset_id {rights.dataset_id} does not match expected {dataset_id}",
        )
    if rights.operational_status != OperationalStatus.ENABLED:
        raise RightsGateError(f"source {rights.source_id} is disabled")
    for operation in (
        RightsOperation.AUTOMATED_ACCESS,
        RightsOperation.RAW_DATA_RETENTION,
    ):
        if rights.decision_for(operation) != RightsDecision.PERMITTED:
            raise RightsGateError(
                f"operation {operation.value} is not permitted for {rights.source_id}",
            )
