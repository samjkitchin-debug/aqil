from datetime import date
from decimal import Decimal

from aqil_research.forward.materiality import (
    MaterialityInput,
    assess_event_materiality,
    assess_materiality,
)


def test_high_materiality_for_meaningful_weight() -> None:
    result = assess_materiality(
        MaterialityInput(
            weight_percentage=Decimal("4.2"),
            holdings_completeness="top_holdings_partial",
            snapshot_as_of=date(2025, 6, 30),
            reference_date=date(2025, 9, 1),
            event_category="company_earnings",
        ),
    )
    assert result.category == "high"


def test_insufficient_when_holdings_stale() -> None:
    result = assess_materiality(
        MaterialityInput(
            weight_percentage=Decimal("4.2"),
            holdings_completeness="top_holdings_partial",
            snapshot_as_of=date(2024, 1, 1),
            reference_date=date(2026, 10, 17),
            event_category="company_earnings",
        ),
    )
    assert result.category == "insufficient_evidence"


def test_missing_weight_is_insufficient_not_a_score() -> None:
    result = assess_event_materiality(
        weight_percentage=None,
        holdings_completeness=None,
        snapshot_as_of=None,
        reference_date=date(2026, 10, 17),
        event_category="central_bank_meeting",
    )
    assert result.category == "insufficient_evidence"
    assert "not assessed" in result.rationale
