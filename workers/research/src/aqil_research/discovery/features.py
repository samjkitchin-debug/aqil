"""Causal transforms. A missing month stays missing."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from aqil_research.discovery.calendar import add_months


def level(series: dict[date, Decimal]) -> dict[date, Decimal]:
    return dict(series)


def difference_over(series: dict[date, Decimal], months: int) -> dict[date, Decimal]:
    """Difference against the same calendar month. A gap is not bridged."""
    transformed: dict[date, Decimal] = {}
    for period, value in series.items():
        prior = series.get(add_months(period, -months))
        if prior is None:
            continue
        transformed[period] = value - prior
    return transformed


def ratio_change_over(series: dict[date, Decimal], months: int) -> dict[date, Decimal]:
    """Ratio change against the same calendar month. A zero base is left missing."""
    transformed: dict[date, Decimal] = {}
    for period, value in series.items():
        prior = series.get(add_months(period, -months))
        if prior is None or prior == 0:
            continue
        transformed[period] = (value / prior) - Decimal(1)
    return transformed


def change_from_previous_stored(
    series: dict[date, Decimal],
) -> dict[date, tuple[Decimal, int]]:
    """Change from the previous stored month, with the gap in calendar months.

    The gap is reported. The missing month is not filled.
    """
    ordered = sorted(series)
    transformed: dict[date, tuple[Decimal, int]] = {}
    for previous, current in zip(ordered, ordered[1:], strict=False):
        gap = (current.year - previous.year) * 12 + (current.month - previous.month)
        transformed[current] = (series[current] - series[previous], gap)
    return transformed


def past_rolling_percentile(series: dict[date, Decimal], window: int) -> dict[date, Decimal]:
    """Percentile of the current value inside the previous window only.

    The current observation and every later observation stay out of the window.
    """
    if window < 1:
        raise ValueError("window must be at least 1")
    ordered = sorted(series)
    history: list[Decimal] = []
    transformed: dict[date, Decimal] = {}
    for period in ordered:
        if len(history) >= window:
            sample = history[-window:]
            rank = sum(1 for item in sample if item <= series[period])
            transformed[period] = Decimal(rank) / Decimal(window)
        history.append(series[period])
    return transformed
