"""Calendar helpers for decision dates and return horizons."""

from __future__ import annotations

import calendar
from datetime import date


def add_months(value: date, months: int) -> date:
    """Move a date by calendar months and clamp the day to the destination month."""
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def month_start(value: date) -> date:
    return date(value.year, value.month, 1)
