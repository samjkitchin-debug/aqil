"""Deterministic scientific status. A language model does not assign this."""

from __future__ import annotations

from decimal import Decimal

from aqil_research.long_horizon.money import decimal_text

FORBIDDEN_FOR_CATEGORY_C = frozenset(
    {
        "statistically_supported",
        "economically_useful",
        "forward_validated",
    }
)

SCIENTIFIC_STATUSES = frozenset(
    {
        "proposed",
        "exploratory",
        "retrospective_only",
        "insufficient_data",
        "statistically_supported",
        "economically_useful",
        "rejected",
        "inconclusive",
        "superseded",
        "forward_validated",
    }
)


class StatusAssignmentError(ValueError):
    """The status is not allowed for this category."""


def assign_category_c_status(
    *,
    reconciled: bool,
    alternative_terminal: Decimal,
    passive_terminal: Decimal,
) -> str:
    """Map one frozen category C window onto a status.

    A larger alternative terminal wealth is inconclusive. It is not
    statistical support, economic usefulness, or forward validation. A
    smaller or equal terminal wealth rejects the registered inequality on
    this window only.
    """
    if not reconciled:
        status = "insufficient_data"
    elif alternative_terminal > passive_terminal:
        status = "inconclusive"
    else:
        status = "rejected"
    assert_status_allowed("C", status)
    return status


def assert_status_allowed(category: str, status: str) -> None:
    if status not in SCIENTIFIC_STATUSES:
        raise StatusAssignmentError(f"unknown status {status}")
    if category == "C" and status in FORBIDDEN_FOR_CATEGORY_C:
        raise StatusAssignmentError(
            "category C cannot be statistically supported, economically useful, "
            "or forward-validated"
        )


def claim_proposition(
    *,
    status: str,
    alternative_terminal: Decimal,
    passive_terminal: Decimal,
) -> str:
    difference = alternative_terminal - passive_terminal
    return (
        "The frozen category C comparison of LH-E-001 is "
        f"{status}. Alternative terminal wealth is {decimal_text(alternative_terminal)}. "
        f"Passive terminal wealth is {decimal_text(passive_terminal)}. "
        "Difference, alternative minus passive, is "
        f"{decimal_text(difference)}. "
        "This is not an investment claim, not economically useful, "
        "and not forward-validated."
    )
