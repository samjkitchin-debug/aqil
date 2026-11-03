"""State and outcome arithmetic. Windows never include a later observation."""

from __future__ import annotations

import calendar
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from aqil_research.long_horizon.money import decimal_text
from aqil_research.long_horizon.state_atlas.specification import (
    ATLAS_SPECIFICATION,
    SESSION_STEPS,
)


class AtlasFeatureError(ValueError):
    """A feature asked for a full-sample statistic or a filled session."""


def _spec() -> dict[str, object]:
    return ATLAS_SPECIFICATION


def _counts() -> dict[str, int]:
    raw = _spec()["trailing_observation_counts"]
    assert isinstance(raw, dict)
    return {str(key): int(value) for key, value in raw.items()}


def _yoy_steps() -> dict[str, int]:
    raw = _spec()["year_on_year_steps"]
    assert isinstance(raw, dict)
    return {str(key): int(value) for key, value in raw.items()}


def period_bound(period_start: date, period_end: date | None, frequency: str) -> date:
    """Inclusive end of the stored period. A null period_end is not a release date."""
    if period_end is not None:
        return period_end
    if frequency == "monthly":
        last = calendar.monthrange(period_start.year, period_start.month)[1]
        return date(period_start.year, period_start.month, last)
    if frequency == "quarterly":
        end_month = ((period_start.month - 1) // 3 + 1) * 3
        last = calendar.monthrange(period_start.year, end_month)[1]
        return date(period_start.year, end_month, last)
    if frequency in {"weekly", "daily"}:
        return period_start
    if frequency == "annual":
        return date(period_start.year, 12, 31)
    raise AtlasFeatureError(f"unknown frequency {frequency}")


def _shift_months(day: date, months: int) -> date:
    index = day.year * 12 + (day.month - 1) + months
    year, month_index = divmod(index, 12)
    month = month_index + 1
    last = calendar.monthrange(year, month)[1]
    return date(year, month, min(day.day, last))


def sample_standard_deviation(values: Sequence[Decimal]) -> Decimal | None:
    count = len(values)
    if count < 2:
        return None
    mean = sum(values, Decimal(0)) / Decimal(count)
    variance = sum((item - mean) ** 2 for item in values) / Decimal(count - 1)
    if variance == 0:
        return Decimal(0)
    return variance.sqrt()


@dataclass(frozen=True)
class FeatureValue:
    availability: str
    value: str | None


def _observed(value: Decimal | str) -> FeatureValue:
    text = value if isinstance(value, str) else decimal_text(value)
    return FeatureValue("observed", text)


def _missing(availability: str) -> FeatureValue:
    return FeatureValue(availability, None)


@dataclass(frozen=True)
class EconomicPoint:
    period_start: date
    period_end: date | None
    frequency: str
    value: Decimal


def trailing_sample(points: Sequence[EconomicPoint], anchor: date) -> list[EconomicPoint]:
    """Observations whose period bound is on or before the anchor. Later rows are dropped."""
    selected = [
        point
        for point in points
        if period_bound(point.period_start, point.period_end, point.frequency) <= anchor
    ]
    selected.sort(key=lambda point: (point.period_start, point.value))
    return selected


def _percent_change(current: Decimal, previous: Decimal) -> FeatureValue:
    if previous == 0:
        return _missing("insufficient_zero_base")
    return _observed(current / previous - 1)


def _year_on_year(sample: Sequence[EconomicPoint]) -> FeatureValue:
    if not sample:
        return _missing("insufficient_lookback")
    frequency = sample[-1].frequency
    steps = _yoy_steps().get(frequency)
    if steps is None:
        return _missing("insufficient_frequency")
    if len(sample) <= steps:
        return _missing("insufficient_lookback")
    current = sample[-1]
    earlier = sample[-1 - steps]
    if frequency == "weekly":
        expected = current.period_start - timedelta(weeks=steps)
    elif frequency == "quarterly":
        expected = _shift_months(current.period_start, -steps * 3)
    else:
        expected = _shift_months(current.period_start, -steps)
    if earlier.period_start != expected:
        return _missing("insufficient_gap_not_filled")
    return _percent_change(current.value, earlier.value)


def _persistence(values: Sequence[Decimal]) -> FeatureValue:
    if len(values) < 2:
        return _missing("insufficient_lookback")
    differences = [right - left for left, right in zip(values, values[1:], strict=False)]
    latest = differences[-1]
    if latest > 0:
        sign = 1
    elif latest < 0:
        sign = -1
    else:
        sign = 0
    run = 0
    for item in reversed(differences):
        item_sign = 1 if item > 0 else -1 if item < 0 else 0
        if item_sign != sign:
            break
        run += 1
    return _observed(str(run))


def economic_features(points: Sequence[EconomicPoint], anchor: date) -> dict[str, FeatureValue]:
    """Nine retrospective features. The trailing window is not the full stored sample."""
    sample = trailing_sample(points, anchor)
    window_count = _counts()[sample[-1].frequency] if sample else 0
    window = sample[-window_count:] if sample else []
    features: dict[str, FeatureValue] = {}
    if not sample:
        for name in (
            "level",
            "direction",
            "difference",
            "percent_change",
            "year_on_year",
            "acceleration",
            "persistence",
            "trailing_percentile",
            "trailing_standardisation",
        ):
            features[name] = _missing("insufficient_lookback")
        return features
    current = sample[-1].value
    features["level"] = _observed(current)
    if len(sample) < 2:
        features["direction"] = _missing("insufficient_lookback")
        features["difference"] = _missing("insufficient_lookback")
        features["percent_change"] = _missing("insufficient_lookback")
        features["acceleration"] = _missing("insufficient_lookback")
    else:
        previous = sample[-2].value
        difference = current - previous
        if difference > 0:
            direction = "up"
        elif difference < 0:
            direction = "down"
        else:
            direction = "flat"
        features["direction"] = _observed(direction)
        features["difference"] = _observed(difference)
        features["percent_change"] = _percent_change(current, previous)
        if len(sample) < 3 or sample[-3].value == 0 or previous == 0:
            features["acceleration"] = (
                _missing("insufficient_lookback")
                if len(sample) < 3
                else _missing("insufficient_zero_base")
            )
        else:
            latest_change = current / previous - 1
            prior_change = previous / sample[-3].value - 1
            features["acceleration"] = _observed(latest_change - prior_change)
    features["year_on_year"] = _year_on_year(sample)
    if len(window) < window_count or window_count < 2:
        features["persistence"] = _missing("insufficient_lookback")
        features["trailing_percentile"] = _missing("insufficient_lookback")
        features["trailing_standardisation"] = _missing("insufficient_lookback")
        return features
    values = [point.value for point in window]
    features["persistence"] = _persistence(values)
    not_above = sum(1 for item in values if item <= current)
    features["trailing_percentile"] = _observed(Decimal(not_above) / Decimal(len(values)))
    deviation = sample_standard_deviation(values)
    if deviation is None or deviation == 0:
        features["trailing_standardisation"] = _missing("insufficient_zero_variance")
    else:
        mean = sum(values, Decimal(0)) / Decimal(len(values))
        features["trailing_standardisation"] = _observed((current - mean) / deviation)
    return features


def _history(closes: Sequence[Decimal], index: int) -> Sequence[Decimal]:
    if index < 0 or index >= len(closes):
        raise AtlasFeatureError("the anchor index is outside the series")
    return closes[: index + 1]


def trailing_return(closes: Sequence[Decimal], index: int, steps: int) -> FeatureValue:
    history = _history(closes, index)
    if index < steps:
        return _missing("insufficient_lookback")
    return _observed(history[index] / history[index - steps] - 1)


def trailing_acceleration(closes: Sequence[Decimal], index: int, steps: int) -> FeatureValue:
    if index < steps * 2:
        return _missing("insufficient_lookback")
    latest = trailing_return(closes, index, steps)
    earlier = trailing_return(closes, index - steps, steps)
    if latest.value is None or earlier.value is None:
        return _missing("insufficient_lookback")
    return _observed(Decimal(latest.value) - Decimal(earlier.value))


def drawdown(closes: Sequence[Decimal], index: int, steps: int) -> FeatureValue:
    history = _history(closes, index)
    if index < steps:
        return _missing("insufficient_lookback")
    window = history[index - steps : index + 1]
    peak = max(window)
    return _observed(history[index] / peak - 1)


def recovery_from_prior_trough(closes: Sequence[Decimal], index: int, steps: int) -> FeatureValue:
    if index < 0 or index >= len(closes):
        raise AtlasFeatureError("the anchor index is outside the series")
    if index < steps:
        return _missing("insufficient_lookback")
    found = trough_after_peak(closes, index, steps)
    if found is None:
        return _missing("insufficient_no_trough_after_peak")
    _peak, trough = found
    return _observed(closes[index] / trough - 1)


def trough_after_peak(
    closes: Sequence[Decimal],
    index: int,
    steps: int,
) -> tuple[Decimal, Decimal] | None:
    """Earliest peak in the trailing window, then the lowest close after it."""
    history = _history(closes, index)
    if index < steps:
        return None
    window = history[index - steps : index + 1]
    peak = max(window)
    peak_at = window.index(peak)
    if peak_at == len(window) - 1:
        return None
    trough = min(window[peak_at + 1 :])
    return peak, trough


def volatility(closes: Sequence[Decimal], index: int, steps: int) -> FeatureValue:
    history = _history(closes, index)
    if index < steps:
        return _missing("insufficient_lookback")
    window = history[index - steps : index + 1]
    returns = [right / left - 1 for left, right in zip(window, window[1:], strict=False)]
    deviation = sample_standard_deviation(returns)
    if deviation is None:
        return _missing("insufficient_lookback")
    return _observed(deviation)


def outcome_at(closes: Sequence[Decimal], index: int, steps: int) -> tuple[str, str | None]:
    """Forward return. A missing later session is censored and is not filled."""
    if steps not in SESSION_STEPS.values():
        raise AtlasFeatureError("the outcome horizon is not a frozen session step")
    if index < 0 or index >= len(closes):
        raise AtlasFeatureError("the anchor index is outside the series")
    if index + steps >= len(closes):
        return "censored", None
    forward = closes[index + steps] / closes[index] - 1
    return "observed", decimal_text(forward)


def labelled_advance(closes: Sequence[Decimal], index: int) -> tuple[str, bool | None, str | None]:
    """The existing 126-session advance. It reads a later close and is not a state."""
    from aqil_research.long_horizon.state_atlas.specification import SEQUENCE_EXPERIMENT

    label = SEQUENCE_EXPERIMENT["outcome_label"]
    assert isinstance(label, dict)
    steps = int(label["steps"])
    status, text = outcome_at(closes, index, steps)
    if status == "censored" or text is None:
        return "censored", None, None
    advance = Decimal(text) >= Decimal(str(label["minimum_return"]))
    return "observed", advance, text
