"""Pre-event coverage. Observation values are not an input."""

from __future__ import annotations

import calendar
from bisect import bisect_right
from dataclasses import dataclass
from datetime import date

from aqil_research.long_horizon.events.definition import EVENT_DEFINITION


@dataclass(frozen=True)
class AvailabilityRow:
    symbol: str
    feature_id: str
    lookback_label: str
    clock: str
    availability: str
    covered_event_count: int
    catalogued_event_count: int
    seasonal_adjustment: str | None
    detail: str


def subtract_months(day: date, months: int) -> date:
    month_index = day.month - months
    year = day.year
    while month_index <= 0:
        month_index += 12
        year -= 1
    last_day = calendar.monthrange(year, month_index)[1]
    return date(year, month_index, min(day.day, last_day))


def covered_by_period_start(
    event_starts: list[date],
    period_starts: list[date],
    months: int,
) -> int:
    """Count events with a period_start in (start minus months, start]."""
    ordered = sorted(period_starts)
    covered = 0
    for start in event_starts:
        boundary = subtract_months(start, months)
        left = bisect_right(ordered, boundary)
        right = bisect_right(ordered, start)
        if right > left:
            covered += 1
    return covered


def _session_steps() -> dict[str, int]:
    raw = EVENT_DEFINITION["session_steps"]
    assert isinstance(raw, dict)
    return {str(label): int(steps) for label, steps in raw.items()}


def build_feature_rows(
    symbol: str,
    event_starts: list[tuple[date, int]],
    macro_periods: dict[str, list[date]],
    macro_seasonal: dict[str, str | None],
    blocked_notes: list[tuple[str, str]],
) -> list[AvailabilityRow]:
    """Coverage only. Macro rows do not carry observation values."""
    catalogued = len(event_starts)
    rows: list[AvailabilityRow] = []
    for label, steps in _session_steps().items():
        covered = sum(1 for _start, index in event_starts if index >= steps)
        detail = (
            f"{covered} of {catalogued} catalogued events have at least {steps} "
            "prior stored sessions. That is price history, not a total return."
        )
        availability = (
            "observable_from_stored_closes" if catalogued or steps >= 0 else "not_applicable"
        )
        if catalogued == 0:
            availability = "observable_from_stored_closes"
            detail = (
                "No catalogued price event. The stored closes can still be read. "
                "This row is not a signal."
            )
        for feature_id in (
            "trailing_split_adjusted_close_return",
            "completed_drawdown_state",
        ):
            rows.append(
                AvailabilityRow(
                    symbol=symbol,
                    feature_id=feature_id,
                    lookback_label=label,
                    clock="stored_sessions",
                    availability=availability,
                    covered_event_count=covered,
                    catalogued_event_count=catalogued,
                    seasonal_adjustment=None,
                    detail=detail,
                )
            )
    for feature_id, note in blocked_notes:
        rows.append(
            AvailabilityRow(
                symbol=symbol,
                feature_id=feature_id,
                lookback_label="not_applicable",
                clock="not_applicable",
                availability="blocked",
                covered_event_count=0,
                catalogued_event_count=0,
                seasonal_adjustment=None,
                detail=note,
            )
        )
    starts = [start for start, _index in event_starts]
    for dataset_id in sorted(macro_periods):
        periods = macro_periods[dataset_id]
        seasonal = macro_seasonal.get(dataset_id)
        for months in (1, 3, 6, 12, 24):
            if catalogued == 0:
                rows.append(
                    AvailabilityRow(
                        symbol=symbol,
                        feature_id=dataset_id,
                        lookback_label=f"{months}m",
                        clock="calendar_months",
                        availability="not_applicable",
                        covered_event_count=0,
                        catalogued_event_count=0,
                        seasonal_adjustment=seasonal,
                        detail=(
                            "No catalogued price event, so a pre-event lookback is not "
                            "defined. Latest-revised coverage was not treated as a signal."
                        ),
                    )
                )
                continue
            covered = covered_by_period_start(starts, periods, months)
            rows.append(
                AvailabilityRow(
                    symbol=symbol,
                    feature_id=dataset_id,
                    lookback_label=f"{months}m",
                    clock="calendar_months",
                    availability="exploratory_latest_revised",
                    covered_event_count=covered,
                    catalogued_event_count=catalogued,
                    seasonal_adjustment=seasonal,
                    detail=(
                        f"{covered} of {catalogued} event starts have a latest-revised "
                        f"period_start inside {months} calendar months before the start. "
                        "period_start is not a release timestamp. This coverage is "
                        "exploratory and is not a point-in-time signal. Seasonal "
                        "adjustment is the stored label only."
                    ),
                )
            )
    return rows
