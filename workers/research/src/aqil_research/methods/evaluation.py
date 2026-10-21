"""Shared evaluation-period helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Literal

from aqil_research.contracts.observation import EconomicObservation

SAHM_MONTHS_REQUIRED = 15

# BLS marked October 2025 unavailable, footnote 9, because of the appropriations lapse.
# That month was not collected. It is not an outstanding release.
PERMANENT_CPS_ABSENCES: tuple[date, ...] = (date(2025, 10, 1),)

SahmWindowStatus = Literal["eligible", "permanently_invalid", "awaiting_observations"]


def _add_months(anchor: date, delta: int) -> date:
    year = anchor.year + (anchor.month - 1 + delta) // 12
    month = (anchor.month - 1 + delta) % 12 + 1
    return date(year, month, 1)


def sahm_window_complete(
    by_period: dict[date, EconomicObservation],
    evaluation: date,
) -> bool:
    return all(month in by_period for month in required_sahm_months(evaluation))


@dataclass(frozen=True, slots=True)
class SahmWindowEligibility:
    evaluation_period: date
    status: SahmWindowStatus
    missing_months: tuple[date, ...]
    permanent_months: tuple[date, ...]
    next_possible_evaluation: date | None


def required_sahm_months(evaluation: date) -> tuple[date, ...]:
    earliest = _add_months(evaluation, -(SAHM_MONTHS_REQUIRED - 1))
    months: list[date] = []
    cursor = earliest
    while cursor <= evaluation:
        months.append(cursor)
        cursor = _add_months(cursor, 1)
    return tuple(months)


def classify_sahm_window(
    present_months: set[date],
    evaluation: date,
    permanent_absences: tuple[date, ...] = PERMANENT_CPS_ABSENCES,
) -> SahmWindowEligibility:
    """Classify one 15-month window without filling a missing month."""
    required = required_sahm_months(evaluation)
    missing = tuple(month for month in required if month not in present_months)
    permanent = tuple(month for month in missing if month in permanent_absences)
    if permanent:
        status: SahmWindowStatus = "permanently_invalid"
        next_possible = _add_months(max(permanent), SAHM_MONTHS_REQUIRED)
    elif missing:
        status = "awaiting_observations"
        next_possible = None
    else:
        status = "eligible"
        next_possible = None
    return SahmWindowEligibility(
        evaluation_period=evaluation,
        status=status,
        missing_months=missing,
        permanent_months=permanent,
        next_possible_evaluation=next_possible,
    )


def sahm_window_refusal(present_months: set[date], evaluation: date) -> str:
    """Why this window cannot be the current Sahm result. The formula is unchanged."""
    finding = classify_sahm_window(present_months, evaluation)
    if finding.status == "permanently_invalid":
        named = ", ".join(month.isoformat() for month in finding.permanent_months)
        nxt = finding.next_possible_evaluation
        nxt_text = nxt.isoformat() if nxt else "unknown"
        return (
            f"{evaluation.isoformat()} is permanently ineligible because the window "
            f"includes {named}, which was not collected. Do not interpolate. "
            f"The next evaluation month that excludes that absence is {nxt_text}, "
            "once those observations exist. An earlier complete window is not the current month."
        )
    if finding.status == "awaiting_observations":
        named = ", ".join(month.isoformat() for month in finding.missing_months)
        return f"{evaluation.isoformat()} is awaiting observations: {named}."
    return f"{evaluation.isoformat()} has a complete Sahm window."


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
