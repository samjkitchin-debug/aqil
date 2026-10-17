"""Research-run publication checks — fail-closed extension of claim verification."""

from __future__ import annotations

from typing import Any

from aqil_research.editorial.claim_verifier import ClaimVerificationError
from aqil_research.pipeline.models import ResearchRun


def verify_research_run_for_publication(run: ResearchRun) -> None:
    """Block publication until deterministic verification exists."""
    if run.execution_status not in ("completed",):
        raise ClaimVerificationError("research run did not complete successfully")
    if run.data_sufficiency != "sufficient":
        raise ClaimVerificationError("research run has insufficient data")
    if not run.publication_allowed:
        raise ClaimVerificationError(
            "research run is not approved for publication",
        )
    raise ClaimVerificationError(
        "research publication verification not implemented; blocked by default",
    )


def verify_calculated_claim_for_publication(claim: dict[str, Any]) -> None:
    """Calculated claims require explicit verification metadata."""
    claim_type = claim.get("claim_type")
    if claim_type == "calculated":
        status = claim.get("verification_status")
        if status != "verified":
            raise ClaimVerificationError(
                "calculated claims cannot be published without verified status",
            )
    raise ClaimVerificationError(
        "claim verification not implemented; publication blocked by default",
    )
