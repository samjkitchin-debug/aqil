"""Status is a function of the frozen rule, not a language-model label."""

from __future__ import annotations

from decimal import Decimal

import pytest

from aqil_research.long_horizon.status import (
    StatusAssignmentError,
    assert_status_allowed,
    assign_category_c_status,
    claim_proposition,
)


def test_category_c_cannot_be_promoted() -> None:
    for status in (
        "statistically_supported",
        "economically_useful",
        "forward_validated",
    ):
        with pytest.raises(StatusAssignmentError):
            assert_status_allowed("C", status)


def test_unreconciled_window_is_insufficient_data() -> None:
    assert (
        assign_category_c_status(
            reconciled=False,
            alternative_terminal=Decimal("9"),
            passive_terminal=Decimal("1"),
        )
        == "insufficient_data"
    )


def test_claim_text_uses_the_supplied_status() -> None:
    text = claim_proposition(
        status="rejected",
        alternative_terminal=Decimal("500"),
        passive_terminal=Decimal("700"),
    )
    assert "rejected" in text
    assert "500" in text
    assert "700" in text
    assert "not an investment claim" in text
    assert "economically useful" in text
