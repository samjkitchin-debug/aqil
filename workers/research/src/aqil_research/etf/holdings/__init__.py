"""ETF holdings coverage.

A source that fails the rights gate is not fetched. This package does not
download issuer files and does not treat a missing file as an empty portfolio.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from aqil_research.etf.contracts import holdings_cleared_for_read
from aqil_research.sources.rights import OperationalStatus, RightsDecision, SourceRightsRecord

RightsGate = Literal["permitted", "prohibited", "unknown", "disabled"]

_NOT_FETCHED = "The source was not fetched."
_NO_FILE = "No holdings file has been supplied by the caller."
_OVERLAP_MISSING = (
    "Top-ten overlap is partial. "
    "Missing or restricted holdings are not treated as an empty portfolio."
)
_OVERLAP_UNNAMED = "Top-ten overlap is partial. No shared names were supplied by the caller."


class HoldingsStatus(StrEnum):
    INSUFFICIENT = "insufficient_coverage"
    PARTIAL = "partial"
    FULL = "full"


class HoldingsCoverage(BaseModel):
    """Coverage of one holdings source. Holding lines are not included."""

    model_config = ConfigDict(extra="forbid")

    status: HoldingsStatus
    rights_gate: RightsGate
    line_count: int = Field(ge=0)
    reason: str


def coverage_for_record(record: SourceRightsRecord) -> HoldingsCoverage:
    """Describe coverage without contacting the provider.

    A cleared source still has no lines until the caller supplies a file.
    """
    if not holdings_cleared_for_read(record):
        gate = _closed_rights_gate(record)
        return HoldingsCoverage(
            status=HoldingsStatus.INSUFFICIENT,
            rights_gate=gate,
            line_count=0,
            reason=f"{_NOT_FETCHED} The rights gate is {gate}.",
        )
    return HoldingsCoverage(
        status=HoldingsStatus.PARTIAL,
        rights_gate="permitted",
        line_count=0,
        reason=_NO_FILE,
    )


def top_ten_overlap(
    *,
    left_line_count: int,
    right_line_count: int,
    rights_cleared: bool,
    shared_names: tuple[str, ...] = (),
) -> dict[str, str | bool | int]:
    """Count only names the caller supplied. The label stays partial.

    Restricted or missing holdings are not an empty portfolio, so they do not
    produce an overlap count.
    """
    if not rights_cleared or left_line_count <= 0 or right_line_count <= 0:
        return {
            "label": "partial",
            "computed": False,
            "reason": _OVERLAP_MISSING,
        }
    if not shared_names:
        return {
            "label": "partial",
            "computed": False,
            "reason": _OVERLAP_UNNAMED,
        }
    return {
        "label": "partial",
        "computed": True,
        "overlap_count": len(shared_names),
        "reason": (
            "Top-ten overlap is partial. "
            "The overlap count is the number of names supplied by the caller."
        ),
    }


def _closed_rights_gate(
    record: SourceRightsRecord,
) -> Literal["prohibited", "unknown", "disabled"]:
    """Report the first fact that keeps the holdings gate closed."""
    if record.operational_status != OperationalStatus.ENABLED:
        return "disabled"
    if record.automated_access == RightsDecision.PROHIBITED:
        return "prohibited"
    if record.automated_access == RightsDecision.UNKNOWN:
        return "unknown"
    if record.redistribution == RightsDecision.PROHIBITED:
        return "prohibited"
    return "unknown"
