"""Shared evaluation-period helpers."""

from __future__ import annotations

from datetime import date

from aqil_research.contracts.observation import EconomicObservation

SAHM_MONTHS_REQUIRED = 15


def _add_months(anchor: date, delta: int) -> date:
    year = anchor.year + (anchor.month - 1 + delta) // 12
    month = (anchor.month - 1 + delta) % 12 + 1
    return date(year, month, 1)


def sahm_window_complete(
    by_period: dict[date, EconomicObservation],
    evaluation: date,
) -> bool:
    earliest = _add_months(evaluation, -(SAHM_MONTHS_REQUIRED - 1))
    cursor = earliest
    while cursor <= evaluation:
        if cursor not in by_period:
            return False
        cursor = _add_months(cursor, 1)
    return True


def latest_sahm_evaluation_period(
    by_period: dict[date, EconomicObservation],
) -> date | None:
    """Latest month with a complete Sahm input window in the as-of view."""
    for candidate in sorted(by_period, reverse=True):
        earliest = _add_months(candidate, -(SAHM_MONTHS_REQUIRED - 1))
        months = []
        cursor = earliest
        while cursor <= candidate:
            months.append(cursor)
            cursor = _add_months(cursor, 1)
        if all(month in by_period for month in months):
            return candidate
    return None
