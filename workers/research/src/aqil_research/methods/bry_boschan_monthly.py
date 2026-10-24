"""Monthly Bry–Boschan specification and the G.17 level-index contract.

Bry and Boschan, chapter 2 (NBER c2148, read 25 October 2026), states the
censoring windows and the 3.5-standard-deviation ratio rule. It does not
print the fifteen-point Spencer coefficients, the twelve-month moving-average
alignment, or the program listing. Dating stays refused until those constants
are read from that chapter. This module does not smooth a series and does not
import NumPy.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from aqil_research.contracts.observation import (
    EconomicObservation,
    Frequency,
    QualityStatus,
    SeasonalAdjustment,
    SeriesProvenance,
)

BRY_BOSCHAN_MONTHLY_1971 = "BRY_BOSCHAN_MONTHLY_1971"
G17_DATASET_ID = "fed.g17.IP.B50001.S"
G17_LEVEL_UNIT = "index_2017_100"
LEVEL_REPRESENTATION = "level"
PUBLICATION_ALLOWED = False

# Readable from chapter 2 prose and Table 1. Not a dating implementation.
OUTLIER_CONTROL_LIMIT = Decimal("3.5")
TWELVE_MONTH_NEIGHBOURHOOD_MONTHS = 5
SPENCER_SEARCH_MONTHS = 5
MCD_SEARCH_MONTHS = 5
MINIMUM_CYCLE_MONTHS = 15
MINIMUM_PHASE_MONTHS = 5
ENDPOINT_BAN_MONTHS = 6
MCD_SMOOTHER_FLOOR = 3
MCD_SMOOTHER_CAP = 6
FINAL_WINDOW_FLOOR_MONTHS = 4
CROSSOVER_CONTRACTION_MONTHS = 10
SPENCER_TERM_MONTHS = 15

DATING_BLOCKER = (
    "Bry-Boschan dating is blocked. NBER chapter 2 "
    "(https://www.nber.org/system/files/chapters/c2148/c2148.pdf, 58 pages) "
    "does not print the fifteen-point Spencer coefficients, does not state "
    "which month receives the twelve-month moving average, and does not "
    "include the program listing. The appendix is the bituminous-coal sample "
    "run. Weights were not invented."
)


class BryBoschanSpecificationBlocked(RuntimeError):
    """A chapter-2 constant required for dating was not in the chapter PDF."""


@dataclass(frozen=True, slots=True)
class BryBoschanMonthlySpec:
    """Constants read from chapter 2, plus the explicit gaps."""

    version: str = BRY_BOSCHAN_MONTHLY_1971
    outlier_control_limit: Decimal = OUTLIER_CONTROL_LIMIT
    twelve_month_neighbourhood_months: int = TWELVE_MONTH_NEIGHBOURHOOD_MONTHS
    spencer_search_months: int = SPENCER_SEARCH_MONTHS
    mcd_search_months: int = MCD_SEARCH_MONTHS
    minimum_cycle_months: int = MINIMUM_CYCLE_MONTHS
    minimum_phase_months: int = MINIMUM_PHASE_MONTHS
    endpoint_ban_months: int = ENDPOINT_BAN_MONTHS
    mcd_smoother_floor: int = MCD_SMOOTHER_FLOOR
    mcd_smoother_cap: int = MCD_SMOOTHER_CAP
    final_window_floor_months: int = FINAL_WINDOW_FLOOR_MONTHS
    crossover_contraction_months: int = CROSSOVER_CONTRACTION_MONTHS
    spencer_term_months: int = SPENCER_TERM_MONTHS
    spencer_weights: None = None
    twelve_month_alignment: None = None
    publication_allowed: bool = PUBLICATION_ALLOWED
    quarterly_bbq_is_a_parameter: bool = False


def frozen_spec() -> BryBoschanMonthlySpec:
    return BryBoschanMonthlySpec()


def date_specific_cycles(
    levels: tuple[tuple[date, Decimal], ...],
    spec: BryBoschanMonthlySpec | None = None,
) -> None:
    """Refuse to date. The signature accepts a level series and does not use it."""

    del levels, spec
    raise BryBoschanSpecificationBlocked(DATING_BLOCKER)


@dataclass(frozen=True, slots=True)
class G17InputPoint:
    observation: EconomicObservation
    collection_mode: str


@dataclass(frozen=True, slots=True)
class G17InputAssessment:
    eligible: bool
    reasons: tuple[str, ...]
    sample_start: date | None
    sample_end: date | None
    month_count: int


def assess_g17_level_input(
    points: tuple[G17InputPoint, ...] | list[G17InputPoint],
    *,
    representation: str = LEVEL_REPRESENTATION,
) -> G17InputAssessment:
    """Accept one contiguous live month of the G.17 level index, or say why not.

    A gap is not filled. A fixture retrieval is not a live month. A growth rate
    is not the chapter's input. Seasonal adjustment is not applied here.
    """

    reasons: list[str] = []
    if representation != LEVEL_REPRESENTATION:
        reasons.append(
            "non-level input is ineligible; the procedure dates the index level, not a growth rate"
        )
    if not points:
        reasons.append("no observations")
        return G17InputAssessment(False, tuple(reasons), None, None, 0)

    periods: dict[date, G17InputPoint] = {}
    for point in points:
        observation = point.observation
        if point.collection_mode != "live":
            reasons.append(
                f"{observation.period_start.isoformat()} retrieval is "
                f"{point.collection_mode}, not live"
            )
        if observation.dataset_id != G17_DATASET_ID:
            reasons.append(f"dataset {observation.dataset_id} is not {G17_DATASET_ID}")
        if observation.unit != G17_LEVEL_UNIT:
            reasons.append(
                f"{observation.period_start.isoformat()} unit {observation.unit} "
                "is not the level index"
            )
        if observation.seasonal_adjustment is not SeasonalAdjustment.SEASONALLY_ADJUSTED:
            reasons.append(
                f"{observation.period_start.isoformat()} is not seasonally adjusted; "
                "this procedure does not seasonally adjust"
            )
        if observation.frequency is not Frequency.MONTHLY:
            reasons.append(f"{observation.period_start.isoformat()} is not monthly")
        if observation.series_provenance is not SeriesProvenance.LATEST_REVISED:
            reasons.append(f"{observation.period_start.isoformat()} is not latest_revised")
        if observation.quality_status is not QualityStatus.OBSERVED:
            reasons.append(f"{observation.period_start.isoformat()} is not observed")
        if observation.period_start.day != 1:
            reasons.append(f"{observation.period_start.isoformat()} is not a month start")
        if not observation.decimal_value().is_finite():
            reasons.append(f"{observation.period_start.isoformat()} is not finite")
        if observation.period_start in periods:
            reasons.append(f"duplicate month {observation.period_start.isoformat()}")
        periods[observation.period_start] = point

    if not periods:
        return G17InputAssessment(False, tuple(reasons), None, None, 0)

    ordered = tuple(sorted(periods))
    start = ordered[0]
    end = ordered[-1]
    cursor = start
    missing: list[str] = []
    while cursor <= end:
        if cursor not in periods:
            missing.append(cursor.isoformat())
        cursor = _next_month(cursor)
    if missing:
        shown = ", ".join(missing[:6])
        extra = len(missing) - 6
        if extra > 0:
            shown = f"{shown}, and {extra} more"
        reasons.append(f"gap in monthly index: {shown}")

    unique_reasons = tuple(dict.fromkeys(reasons))
    return G17InputAssessment(
        eligible=not unique_reasons,
        reasons=unique_reasons,
        sample_start=start,
        sample_end=end,
        month_count=len(periods),
    )


def _next_month(month_start: date) -> date:
    if month_start.month == 12:
        return date(month_start.year + 1, 1, 1)
    return date(month_start.year, month_start.month + 1, 1)
