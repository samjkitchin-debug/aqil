"""Eligibility and approval stay separate. Nothing here inserts a founder approval."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ApprovalDraft(BaseModel):
    """A caller-supplied approval. An empty actor or rationale is refused."""

    model_config = ConfigDict(extra="forbid")

    decision: str = Field(pattern="^(approved|restricted|suspended|rejected|retired)$")
    actor: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    recorded_at: datetime


class GovernanceError(Exception):
    """Raised when an approval would be invented or eligiblity would be copied."""


def draft_approval(
    *,
    decision: str,
    actor: str,
    rationale: str,
    recorded_at: datetime,
    autonomous: bool,
) -> ApprovalDraft:
    """Build an approval only for an explicit non-autonomous caller."""

    if autonomous:
        raise GovernanceError("an autonomous run must not insert a founder approval")
    if not actor.strip() or not rationale.strip():
        raise GovernanceError("an approval requires an actor and a rationale")
    return ApprovalDraft(
        decision=decision,
        actor=actor.strip(),
        rationale=rationale.strip(),
        recorded_at=recorded_at,
    )


def eligibility_is_not_approval(eligibility: str) -> bool:
    """CORE, CONDITIONAL, EXCLUDED, and UNKNOWN are not founder approvals."""

    return eligibility in {"CORE", "CONDITIONAL", "EXCLUDED", "UNKNOWN", "eligible", "insufficient"}
