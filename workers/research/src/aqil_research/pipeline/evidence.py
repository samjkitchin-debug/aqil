"""Analytical evidence assessment — separate from publication approval."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class EvidenceAssessment:
    analytical_complete: bool
    publication_eligible: bool
    verification_status: Literal["unverified"]
    reasons: tuple[str, ...]


def assess_analytical_evidence(
    *,
    execution_status: str,
    data_sufficiency: str,
    publication_allowed: bool,
) -> EvidenceAssessment:
    """Analytical completeness only — not claim or span verification."""
    analytical_complete = execution_status == "completed" and data_sufficiency == "sufficient"
    reasons: list[str] = []
    if not analytical_complete:
        reasons.append("analytical run did not complete with sufficient data")
    if not publication_allowed:
        reasons.append("publication gate remains fail-closed")
    reasons.append("this assessment is not claim or span verification")
    return EvidenceAssessment(
        analytical_complete=analytical_complete,
        publication_eligible=False,
        verification_status="unverified",
        reasons=tuple(reasons),
    )
