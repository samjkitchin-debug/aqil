"""Fail-closed claim verification until registry and span checks exist (G0 / AQ-013)."""

from typing import Any


class ClaimVerificationError(Exception):
    """Raised when a claim cannot be published."""


def verify_claim_for_publication(_claim: dict[str, Any]) -> None:
    """Block publication until deterministic verification is implemented."""
    raise ClaimVerificationError(
        "claim verification not implemented; publication blocked by default",
    )
