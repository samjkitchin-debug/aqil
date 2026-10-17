"""Deterministic materiality rules (configurable, testable)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

MATERIALITY_RULES_VERSION = "forward_materiality_v1"

HIGH_WEIGHT_THRESHOLD = Decimal("3.0")
MEDIUM_WEIGHT_THRESHOLD = Decimal("1.0")
STALE_HOLDINGS_DAYS = 120


@dataclass(frozen=True, slots=True)
class MaterialityInput:
    weight_percentage: Decimal
    holdings_completeness: str
    snapshot_as_of: date
    reference_date: date
    event_category: str
    overlap_etf_count: int = 1


@dataclass(frozen=True, slots=True)
class MaterialityResult:
    category: str
    rules_version: str
    rationale: str


def assess_event_materiality(
    *,
    weight_percentage: Decimal | None,
    holdings_completeness: str | None,
    snapshot_as_of: date | None,
    reference_date: date,
    event_category: str,
) -> MaterialityResult:
    """Same rules for every event. Missing weight evidence is not a materiality score."""
    if weight_percentage is None or holdings_completeness is None or snapshot_as_of is None:
        return MaterialityResult(
            category="insufficient_evidence",
            rules_version=MATERIALITY_RULES_VERSION,
            rationale="No holdings weight is linked, so materiality is not assessed.",
        )
    return assess_materiality(
        MaterialityInput(
            weight_percentage=weight_percentage,
            holdings_completeness=holdings_completeness,
            snapshot_as_of=snapshot_as_of,
            reference_date=reference_date,
            event_category=event_category,
        ),
    )


def assess_materiality(inputs: MaterialityInput) -> MaterialityResult:
    if inputs.holdings_completeness in ("unknown", "not_available"):
        return MaterialityResult(
            category="insufficient_evidence",
            rules_version=MATERIALITY_RULES_VERSION,
            rationale="Holdings evidence is not available for this ETF.",
        )

    age_days = (inputs.reference_date - inputs.snapshot_as_of).days
    if age_days > STALE_HOLDINGS_DAYS:
        return MaterialityResult(
            category="insufficient_evidence",
            rules_version=MATERIALITY_RULES_VERSION,
            rationale=(
                f"Holdings snapshot is {age_days} days old relative to the event horizon; "
                f"limit is {STALE_HOLDINGS_DAYS} days."
            ),
        )

    weight = inputs.weight_percentage
    if weight >= HIGH_WEIGHT_THRESHOLD:
        category = "high"
    elif weight >= MEDIUM_WEIGHT_THRESHOLD:
        category = "medium"
    else:
        category = "low"

    overlap_note = ""
    if inputs.overlap_etf_count > 1:
        overlap_note = f" Shared across {inputs.overlap_etf_count} vetted ETFs."

    completeness_note = f" Holdings completeness: {inputs.holdings_completeness}."
    rationale = (
        f"Constituent weight {weight}% with snapshot dated {inputs.snapshot_as_of.isoformat()}."
        f"{completeness_note}{overlap_note}"
    )
    return MaterialityResult(
        category=category,
        rules_version=MATERIALITY_RULES_VERSION,
        rationale=rationale.strip(),
    )
