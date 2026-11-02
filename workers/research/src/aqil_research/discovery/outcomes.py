"""Listing outcomes. Price ratios go through the existing return functions."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from aqil_research.discovery.guards import LeakageError, assert_entry_on_or_after_decision
from aqil_research.etf.performance.returns import total_return


class OutcomeError(Exception):
    """Raised when the existing return function refuses the window."""


def listing_total_return(
    *,
    distribution_policy: str,
    start_value: Decimal,
    end_value: Decimal,
    quote_unit: str,
    dividend: Decimal | None,
    uses_adjusted_close: bool,
    inception_bound: date | None,
    entry: date,
    decision: date,
) -> Decimal:
    """Accept only a return the existing total-return function accepts."""
    assert_entry_on_or_after_decision(entry, decision)
    if distribution_policy not in {"accumulating", "distributing", "unknown"}:
        raise OutcomeError("distribution policy is not a known contract value")
    result = total_return(
        distribution_policy=distribution_policy,  # type: ignore[arg-type]
        start_value=start_value,
        end_value=end_value,
        start_unit=quote_unit,
        end_unit=quote_unit,
        dividend=dividend,
        uses_adjusted_close=uses_adjusted_close,
        inception=inception_bound,
        period_start=entry,
    )
    if not result.accepted or result.value is None:
        raise OutcomeError(result.reason)
    if entry < decision:
        raise LeakageError("a return window cannot start before the decision time")
    return result.value
