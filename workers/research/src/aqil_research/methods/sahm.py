"""Sahm rule — three-month average unemployment gap (Claudia Sahm, 2019)."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from aqil_research.contracts.observation import (
    EconomicObservation,
    Frequency,
    SeasonalAdjustment,
)
from aqil_research.vintages.asof import monthly_decimal_series

SAHM_METHOD_ID = "SAHM_UNEMPLOYMENT_GAP"
SAHM_METHOD_VERSION = "1.0.1"

REQUIRED_GEOGRAPHY = "US"
REQUIRED_UNIT = "percent"
REQUIRED_FREQUENCY = Frequency.MONTHLY
REQUIRED_SEASONAL = SeasonalAdjustment.SEASONALLY_ADJUSTED

# Published rule: 0.50 percentage-point rise in the 3-month average relative to the
# prior 12-month low of that average; the 12-month look-back excludes the current month.
LOOKBACK_MONTHS = 12
AVERAGE_WINDOW_MONTHS = 3


class SahmMethodError(Exception):
    """Raised when inputs are insufficient or inconsistent for the Sahm rule."""


class SahmConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    config_id: str = Field(min_length=1)
    threshold_percentage_points: Decimal = Field(gt=Decimal("0"))
    label: str = Field(min_length=1)

    def config_hash(self) -> str:
        payload = {
            "config_id": self.config_id,
            "threshold_percentage_points": str(self.threshold_percentage_points),
            "label": self.label,
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True, slots=True)
class SahmOutput:
    evaluation_period: date
    three_month_average: Decimal
    prior_twelve_month_low_of_average: Decimal
    gap_percentage_points: Decimal
    threshold_percentage_points: Decimal
    triggered: bool
    months_used_for_average: tuple[date, ...]
    months_used_for_lookback: tuple[date, ...]
    observation_ids: tuple[str, ...]
    assumptions: tuple[str, ...]
    limitations: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "evaluation_period": self.evaluation_period.isoformat(),
            "three_month_average": str(self.three_month_average),
            "prior_twelve_month_low_of_average": str(self.prior_twelve_month_low_of_average),
            "gap_percentage_points": str(self.gap_percentage_points),
            "threshold_percentage_points": str(self.threshold_percentage_points),
            "triggered": self.triggered,
            "months_used_for_average": [
                month.isoformat() for month in self.months_used_for_average
            ],
            "months_used_for_lookback": [
                month.isoformat() for month in self.months_used_for_lookback
            ],
            "observation_ids": list(self.observation_ids),
            "assumptions": list(self.assumptions),
            "limitations": list(self.limitations),
        }


def sahm_implementation_hash() -> str:
    """SHA-256 of this module's source bytes (identity anchor for the Sahm formula code path).

    Does not hash transitive dependencies, interpreter version or shared helpers in other modules.
    """
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def run_sahm(
    by_period: dict[date, EconomicObservation],
    evaluation_period: date,
    config: SahmConfig,
) -> SahmOutput:
    if evaluation_period.day != 1:
        raise SahmMethodError("evaluation_period must be the first day of a calendar month")
    _validate_input_contract(by_period)
    values = monthly_decimal_series(by_period)
    months = _month_range_required(evaluation_period)
    missing = [month for month in months if month not in values]
    if missing:
        raise SahmMethodError(f"missing months for Sahm calculation: {missing[0].isoformat()}")

    average_months = _last_n_months(evaluation_period, AVERAGE_WINDOW_MONTHS)
    avg = _mean(values[month] for month in average_months)

    lookback_end = _add_months(evaluation_period, -1)
    lookback_starts = tuple(_last_n_months(lookback_end, LOOKBACK_MONTHS))
    lookback_averages = [
        _round_average(_three_month_average(values, month)) for month in lookback_starts
    ]
    prior_low = min(lookback_averages)
    avg_rounded = _round_average(avg)

    gap = (avg_rounded - prior_low).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    threshold = config.threshold_percentage_points
    triggered = gap >= threshold

    obs_ids = tuple(
        sorted({by_period[month].observation_id for month in months if month in by_period}),
    )

    assumptions = (
        "US seasonally adjusted U-3 unemployment rate in percent.",
        "Three-month average uses the evaluation month and the two prior months.",
        (
            "Prior low uses the minimum three-month average over the 12 months "
            "before the evaluation month."
        ),
        "The 12-month look-back excludes the evaluation month (Claudia Sahm, 2019).",
        f"Threshold is {threshold} percentage points ({config.label}).",
    )
    limitations = (
        (
            "This is a published association with recessions already under way, "
            "not an NBER determination."
        ),
        "Not a forward recession forecast or an investment signal.",
        "Market pricing is not assessed here.",
    )

    return SahmOutput(
        evaluation_period=evaluation_period,
        three_month_average=avg_rounded,
        prior_twelve_month_low_of_average=prior_low,
        gap_percentage_points=gap,
        threshold_percentage_points=threshold,
        triggered=triggered,
        months_used_for_average=average_months,
        months_used_for_lookback=lookback_starts,
        observation_ids=obs_ids,
        assumptions=assumptions,
        limitations=limitations,
    )


def sahm_threshold_crossed(
    by_period: dict[date, EconomicObservation],
    evaluation_period: date,
    config: SahmConfig,
) -> bool:
    """True only when the threshold is met and the prior month was below threshold."""
    current = run_sahm(by_period, evaluation_period, config)
    if not current.triggered:
        return False
    prior_month = _add_months(evaluation_period, -1)
    try:
        prior = run_sahm(by_period, prior_month, config)
    except SahmMethodError:
        return False
    return not prior.triggered


def _validate_input_contract(by_period: dict[date, EconomicObservation]) -> None:
    for row in by_period.values():
        if row.geography != REQUIRED_GEOGRAPHY:
            raise SahmMethodError(f"geography must be {REQUIRED_GEOGRAPHY}, got {row.geography}")
        if row.unit != REQUIRED_UNIT:
            raise SahmMethodError(f"unit must be {REQUIRED_UNIT}, got {row.unit}")
        if row.frequency != REQUIRED_FREQUENCY:
            raise SahmMethodError(f"frequency must be {REQUIRED_FREQUENCY.value}")
        if row.seasonal_adjustment != REQUIRED_SEASONAL:
            raise SahmMethodError("seasonal adjustment must be seasonally_adjusted")
        _validate_one_decimal_percent(row.raw_value)


def _validate_one_decimal_percent(raw_value: str) -> None:
    parsed = Decimal(raw_value)
    if parsed != parsed.quantize(Decimal("0.1")):
        raise SahmMethodError(
            "Sahm inputs must use one decimal place (BLS U-3 convention)",
        )


def _round_average(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _month_range_required(evaluation_period: date) -> tuple[date, ...]:
    earliest = _add_months(evaluation_period, -(LOOKBACK_MONTHS + AVERAGE_WINDOW_MONTHS - 1))
    months: list[date] = []
    cursor = earliest
    while cursor <= evaluation_period:
        months.append(cursor)
        cursor = _add_months(cursor, 1)
    return tuple(months)


def _three_month_average(values: dict[date, Decimal], end_month: date) -> Decimal:
    months = _last_n_months(end_month, AVERAGE_WINDOW_MONTHS)
    return _mean(values[month] for month in months)


def _last_n_months(end_month: date, count: int) -> tuple[date, ...]:
    months: list[date] = []
    cursor = end_month
    for _ in range(count):
        months.append(cursor)
        cursor = _add_months(cursor, -1)
    return tuple(reversed(months))


def _add_months(anchor: date, delta: int) -> date:
    year = anchor.year + (anchor.month - 1 + delta) // 12
    month = (anchor.month - 1 + delta) % 12 + 1
    return date(year, month, 1)


def _mean(values: tuple[Decimal, ...] | list[Decimal]) -> Decimal:
    items = list(values)
    total = sum(items, start=Decimal("0"))
    return (total / Decimal(len(items))).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


# Presentation fields in SahmOutput use four decimals for gap display; averages are two-decimal.
