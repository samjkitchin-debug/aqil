"""Rights checks for manual ETF holdings file import."""

from __future__ import annotations

from aqil_research.sources.rights import (
    OperationalStatus,
    RightsDecision,
    RightsOperation,
    SourceRightsRecord,
)
from aqil_research.sources.rights_gate import RightsGateError


def assert_manual_holdings_ingest(
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
    if rights.decision_for(RightsOperation.AUTOMATED_ACCESS) == RightsDecision.PERMITTED:
        raise RightsGateError(
            f"manual holdings import must not use automated_access sources ({rights.source_id})",
        )
    for operation in (
        RightsOperation.RAW_DATA_RETENTION,
        RightsOperation.INTERNAL_COMPUTATION,
    ):
        if rights.decision_for(operation) != RightsDecision.PERMITTED:
            raise RightsGateError(
                f"operation {operation.value} is not permitted for {rights.source_id}",
            )
