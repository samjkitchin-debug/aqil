"""Lead-lag cross-correlations of four coincident monthly log-growth rates.

The series are industrial production, real personal income excluding transfers,
real manufacturing and trade sales, and total nonfarm payroll employment.
The transformation is monthly natural log-growth on the balanced overlap of
latest_revised levels. Three-month changes are not used.

Positive lag means the second series lags the first. Significance uses
Bartlett standard errors that include the autocorrelations of both series.
Independent-and-identical standard errors are not used.

Historical correlation is not a structural lead. No series is given a fixed
leading-indicator status. publication_allowed stays false.
"""

from __future__ import annotations

import hashlib
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date

import numpy as np
from pydantic import BaseModel, ConfigDict, Field

from aqil_research.contracts.observation import (
    AnalysisMode,
    EconomicObservation,
    Frequency,
    QualityStatus,
    SeasonalAdjustment,
    SeriesProvenance,
)
from aqil_research.methods.parameters import MethodParameterDocument
from aqil_research.methods.protocol import MethodContext, MethodExecutionResult

LEAD_LAG_CROSS_CORRELATION = "LEAD_LAG_CROSS_CORRELATION"
METHOD_VERSION = "0.1.0"
PUBLICATION_ALLOWED = False

TRANSFORMATION = "monthly_log_growth"
MIN_LAG = -12
MAX_LAG = 12
BARTLETT_TRUNCATION = 24
CRITICAL_VALUE = 1.96
MIN_SUBSAMPLE_GROWTH_MONTHS = 60
MIN_PAIRS = 3

SIGN_CONVENTION = "Positive lag means the second series lags the first."
NOT_A_STRUCTURAL_LEAD = "Historical correlation is not a structural lead."
NO_FIXED_STATUS = "No series is assigned a fixed leading-indicator status."

SERIES = (
    ("fed.g17.IP.B50001.S", "index_2017_100", "Industrial production"),
    (
        "bea.nipa.T20600.W875RX",
        "millions_chained_2017_dollars",
        "Real personal income excluding transfers",
    ),
    (
        "bea.nipa.U002BU.KPMT",
        "millions_chained_2017_dollars",
        "Real manufacturing and trade sales",
    ),
    ("bls.ce.CES0000000001", "thousands", "Total nonfarm payroll employment"),
)
DATASET_IDS = tuple(dataset_id for dataset_id, _unit, _label in SERIES)
LABELS = {dataset_id: label for dataset_id, _unit, label in SERIES}
UNITS = {dataset_id: unit for dataset_id, unit, _label in SERIES}

PUBLISHED_CONFIG = {
    "config_id": "lead-lag-cross-correlation-v1",
    "label": "Cross-correlations of coincident monthly log-growth",
}


@dataclass(frozen=True, slots=True)
class SubsampleWindow:
    name: str
    start: date
    end: date


EARLY_SUBSAMPLE = SubsampleWindow(
    "1997-01 through 2007-12",
    date(1997, 1, 1),
    date(2007, 12, 1),
)
LATE_SUBSAMPLE = SubsampleWindow(
    "2010-01 through 2019-12",
    date(2010, 1, 1),
    date(2019, 12, 1),
)
ILLUSTRATED_BREAK = SubsampleWindow(
    "2008-01 through 2009-12",
    date(2008, 1, 1),
    date(2009, 12, 1),
)
SUBSAMPLES = (EARLY_SUBSAMPLE, LATE_SUBSAMPLE)


class LeadLagConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    config_id: str = Field(min_length=1)
    label: str = Field(min_length=1)


@dataclass(frozen=True, slots=True)
class LagCorrelation:
    lag: int
    correlation: float | None
    bartlett_standard_error: float | None
    distinguishable_from_zero: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "lag": self.lag,
            "correlation": _round(self.correlation),
            "bartlett_standard_error": _round(self.bartlett_standard_error),
            "distinguishable_from_zero": self.distinguishable_from_zero,
        }


def implementation_hash() -> str:
    payload = "|".join(
        (
            LEAD_LAG_CROSS_CORRELATION,
            METHOD_VERSION,
            TRANSFORMATION,
            f"lags-{MIN_LAG}-to-{MAX_LAG}",
            f"bartlett-truncation-{BARTLETT_TRUNCATION}",
            f"critical-{CRITICAL_VALUE}",
            f"min-subsample-{MIN_SUBSAMPLE_GROWTH_MONTHS}",
            EARLY_SUBSAMPLE.name,
            LATE_SUBSAMPLE.name,
            ILLUSTRATED_BREAK.name,
            "no-iid-standard-errors",
        ),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def next_month(month_start: date) -> date:
    if month_start.month == 12:
        return date(month_start.year + 1, 1, 1)
    return date(month_start.year, month_start.month + 1, 1)


def previous_month(month_start: date) -> date:
    if month_start.month == 1:
        return date(month_start.year - 1, 12, 1)
    return date(month_start.year, month_start.month - 1, 1)


def windows_avoid_illustrated_break() -> bool:
    """The two subsamples do not overlap each other or the illustrated break."""
    return not _overlaps(EARLY_SUBSAMPLE, LATE_SUBSAMPLE) and all(
        not _overlaps(window, ILLUSTRATED_BREAK) for window in SUBSAMPLES
    )


def balanced_monthly_log_growth(
    levels: Mapping[str, Mapping[date, float]],
) -> tuple[tuple[date, ...], dict[str, tuple[float, ...]], int]:
    """Monthly log-growth on the earliest longest month where every series exists.

    Gaps are not interpolated. The integer is the count of overlap months left out.
    """
    growth = {
        dataset_id: _series_log_growth(levels.get(dataset_id, {})) for dataset_id in DATASET_IDS
    }
    if any(not series for series in growth.values()):
        return (), {}, 0
    overlap = set.intersection(*(set(series) for series in growth.values()))
    chosen = _longest_run(sorted(overlap))
    if not chosen:
        return (), {}, 0
    aligned = {
        dataset_id: tuple(series[month] for month in chosen)
        for dataset_id, series in growth.items()
    }
    return tuple(chosen), aligned, len(overlap) - len(chosen)


def cross_correlations(
    first: Sequence[float],
    second: Sequence[float],
) -> tuple[LagCorrelation, ...]:
    """Correlate first at t with second at t+lag. Positive lag: second lags first."""
    left = np.asarray(list(first), dtype=float)
    right = np.asarray(list(second), dtype=float)
    if left.size != right.size or left.size < MIN_PAIRS:
        return tuple(LagCorrelation(lag, None, None, False) for lag in range(MIN_LAG, MAX_LAG + 1))
    rows: list[LagCorrelation] = []
    for lag in range(MIN_LAG, MAX_LAG + 1):
        aligned = _aligned(left, right, lag)
        if aligned is None:
            rows.append(LagCorrelation(lag, None, None, False))
            continue
        first_values, second_values = aligned
        correlation = _pearson(first_values, second_values)
        standard_error = bartlett_standard_error(left, right, int(first_values.size))
        rows.append(
            LagCorrelation(
                lag,
                correlation,
                standard_error,
                distinguishable_from_zero(correlation, standard_error),
            ),
        )
    return tuple(rows)


def bartlett_long_run_variance(
    autocorrelations_first: Sequence[float],
    autocorrelations_second: Sequence[float],
) -> float | None:
    """Sum of rho_x(j) rho_y(j), with negative lags folded in as twice the product.

    This is Bartlett's large-sample factor for the cross-correlation when the
    series may be serially dependent. A non-positive estimate is not replaced
    with an independent-and-identical variance.
    """
    if len(autocorrelations_first) != len(autocorrelations_second) or not autocorrelations_first:
        return None
    total = 0.0
    for lag, (first, second) in enumerate(
        zip(autocorrelations_first, autocorrelations_second, strict=True),
    ):
        weight = 1.0 if lag == 0 else 2.0
        total += weight * float(first) * float(second)
    if not math.isfinite(total) or total <= 0:
        return None
    return total


def bartlett_standard_error(
    first: np.ndarray,
    second: np.ndarray,
    overlap_count: int,
) -> float | None:
    """Standard error using both autocorrelation functions. Not an iid error."""
    if overlap_count < MIN_PAIRS or int(first.size) <= BARTLETT_TRUNCATION + 2:
        return None
    long_run = bartlett_long_run_variance(
        sample_autocorrelations(first, BARTLETT_TRUNCATION),
        sample_autocorrelations(second, BARTLETT_TRUNCATION),
    )
    if long_run is None:
        return None
    return math.sqrt(long_run / overlap_count)


def sample_autocorrelations(values: np.ndarray, max_lag: int) -> list[float]:
    """Biased sample autocorrelations from lag 0 through max_lag."""
    centred = np.asarray(values, dtype=float)
    centred = centred - centred.mean()
    sample_size = int(centred.size)
    scale = float(centred @ centred) / sample_size
    if sample_size == 0 or scale <= 0:
        return [1.0, *([0.0] * max_lag)]
    correlations = [1.0]
    for lag in range(1, max_lag + 1):
        if lag >= sample_size:
            correlations.append(0.0)
            continue
        correlations.append(float(centred[lag:] @ centred[:-lag]) / sample_size / scale)
    return correlations


def distinguishable_from_zero(
    correlation: float | None,
    standard_error: float | None,
) -> bool:
    """Strict comparison with the predeclared normal critical value."""
    if correlation is None or standard_error is None:
        return False
    if not math.isfinite(correlation) or not math.isfinite(standard_error) or standard_error <= 0:
        return False
    return abs(correlation) > CRITICAL_VALUE * standard_error


def strongest_absolute_correlation(
    rows: Sequence[LagCorrelation],
) -> LagCorrelation | None:
    """Largest absolute correlation. Ties prefer the smaller absolute lag."""
    available = [row for row in rows if row.correlation is not None]
    if not available:
        return None
    return min(
        available,
        key=lambda row: (-abs(row.correlation or 0.0), abs(row.lag), row.lag),
    )


def subsample_is_stable(early: Mapping[str, object], late: Mapping[str, object]) -> bool:
    """Same distinguishable peak lag and sign in both subsamples. Not a lead."""
    if early.get("status") != "computed" or late.get("status") != "computed":
        return False
    early_peak = early.get("strongest_absolute_correlation")
    late_peak = late.get("strongest_absolute_correlation")
    if not isinstance(early_peak, dict) or not isinstance(late_peak, dict):
        return False
    if (
        early_peak.get("distinguishable_from_zero") is not True
        or late_peak.get("distinguishable_from_zero") is not True
    ):
        return False
    if early_peak.get("lag") != late_peak.get("lag"):
        return False
    early_correlation = early_peak.get("correlation")
    late_correlation = late_peak.get("correlation")
    if not isinstance(early_correlation, (int, float)) or not isinstance(
        late_correlation,
        (int, float),
    ):
        return False
    if early_correlation == 0 or late_correlation == 0:
        return False
    return (early_correlation > 0) == (late_correlation > 0)


def lead_lag_from_growth(
    months: Sequence[date],
    growth: Mapping[str, Sequence[float]],
    *,
    excluded_overlap_months: int = 0,
) -> dict[str, object]:
    """Cross-correlations and the two predeclared subsamples."""
    if not windows_avoid_illustrated_break():
        return _insufficient_payload(
            "The predeclared subsamples overlap the illustrated break or each other.",
        )
    arrays = {
        dataset_id: np.asarray(list(growth[dataset_id]), dtype=float) for dataset_id in DATASET_IDS
    }
    if not _months_are_contiguous(months):
        return _insufficient_payload(
            "The balanced overlap is not one contiguous monthly run.",
        )
    too_short = any(
        array.size != len(months) or array.size < MIN_SUBSAMPLE_GROWTH_MONTHS
        for array in arrays.values()
    )
    if too_short:
        return _insufficient_payload(
            "The balanced monthly log-growth overlap is shorter than "
            f"{MIN_SUBSAMPLE_GROWTH_MONTHS} months.",
        )
    if any(not np.all(np.isfinite(array)) for array in arrays.values()):
        return _insufficient_payload("A balanced log-growth value was not finite.")
    pairs = [_pair_payload(months, arrays, first, second) for first, second in _ordered_pairs()]
    distinguishable = [
        peak for pair in pairs for peak in pair["distinguishable_peaks"] if isinstance(peak, dict)
    ]
    return {
        "sufficient": True,
        "method_id": LEAD_LAG_CROSS_CORRELATION,
        "publication_allowed": PUBLICATION_ALLOWED,
        "transformation": TRANSFORMATION,
        "three_month_growth_used": False,
        "input_vintage": "latest_revised",
        "sign_convention": SIGN_CONVENTION,
        "standard_error": "bartlett_autocorrelations_of_both_series",
        "iid_standard_errors_used": False,
        "historical_correlation_is_not_a_structural_lead": True,
        "fixed_leading_indicator_assigned": False,
        "growth_start": months[0].isoformat(),
        "growth_end": months[-1].isoformat(),
        "growth_month_count": len(months),
        "excluded_overlap_months": excluded_overlap_months,
        "subsamples_overlap_illustrated_break": False,
        "subsamples_overlap_each_other": False,
        "illustrated_break_excluded": ILLUSTRATED_BREAK.name,
        "predeclared": {
            "transformation": TRANSFORMATION,
            "minimum_lag": MIN_LAG,
            "maximum_lag": MAX_LAG,
            "bartlett_truncation_lag": BARTLETT_TRUNCATION,
            "critical_value": CRITICAL_VALUE,
            "minimum_subsample_growth_months": MIN_SUBSAMPLE_GROWTH_MONTHS,
            "subsamples": [window.name for window in SUBSAMPLES],
        },
        "pairs": pairs,
        "distinguishable_peaks": distinguishable,
        "sources": list(DATASET_IDS),
    }


class LeadLagCrossCorrelationMethod:
    """Cross-correlations on the balanced coincident log-growth overlap.

    Registration, for the integrator, inside ``default_method_registry``::

        registry.register(LeadLagCrossCorrelationMethod())
    """

    method_id = LEAD_LAG_CROSS_CORRELATION
    method_version = METHOD_VERSION

    def implementation_hash(self) -> str:
        return implementation_hash()

    def required_dataset_ids(self) -> tuple[str, ...]:
        return DATASET_IDS

    def parse_config(self, payload: dict[str, object]) -> LeadLagConfig:
        return LeadLagConfig.model_validate(payload)

    def config_hash(self, config: BaseModel) -> str:
        if not isinstance(config, LeadLagConfig):
            raise TypeError("expected LeadLagConfig")
        return MethodParameterDocument(
            config_id=config.config_id,
            label=config.label,
            scalars={"transformation": TRANSFORMATION},
        ).config_hash()

    def run(self, context: MethodContext, config: BaseModel) -> MethodExecutionResult:
        if not isinstance(config, LeadLagConfig):
            raise TypeError("expected LeadLagConfig")
        if context.analysis_mode != AnalysisMode.LATEST_REVISED:
            return _insufficient(
                "These levels are dated on latest_revised observations. "
                "A point-in-time request was not dated.",
            )
        levels: dict[str, dict[date, float]] = {}
        series_by_dataset: dict[str, Mapping[date, EconomicObservation]] = {}
        for dataset_id, _unit, label in SERIES:
            series = context.inputs_by_dataset.get(dataset_id)
            if not series:
                return _insufficient(f"No observations were available for {label}.")
            series_by_dataset[dataset_id] = series
            extracted = _eligible_levels(dataset_id, series)
            if not extracted:
                return _insufficient(f"No eligible latest-revised level was available for {label}.")
            levels[dataset_id] = extracted
        months, growth, excluded = balanced_monthly_log_growth(levels)
        calculation = lead_lag_from_growth(months, growth, excluded_overlap_months=excluded)
        if calculation.get("sufficient") is not True:
            reason = calculation.get("reason")
            return _insufficient(
                reason
                if isinstance(reason, str)
                else "Lead-lag cross-correlations were not computed.",
            )
        observation_ids = _observation_ids(series_by_dataset, months)
        return MethodExecutionResult(
            sufficiency="sufficient",
            calculation=calculation,
            observation_ids=observation_ids,
            assumptions=_assumptions(excluded),
            limitations=_limitations(calculation),
            missing_reason=None,
            statistical_interpretation=_interpretation(calculation),
            causal_hypothesis="none",
            investment_implication="no_action",
            narrative=_narrative(calculation),
        )


def _pair_payload(
    months: Sequence[date],
    arrays: Mapping[str, np.ndarray],
    first: str,
    second: str,
) -> dict[str, object]:
    rows = cross_correlations(arrays[first], arrays[second])
    peak = strongest_absolute_correlation(rows)
    subsamples = [
        _subsample_payload(months, arrays[first], arrays[second], window) for window in SUBSAMPLES
    ]
    early, late = subsamples
    peak_dict = None if peak is None else peak.to_dict()
    distinguishable = [
        {
            "first_dataset_id": first,
            "second_dataset_id": second,
            "first_label": LABELS[first],
            "second_label": LABELS[second],
            **row.to_dict(),
        }
        for row in rows
        if row.distinguishable_from_zero
    ]
    return {
        "first_dataset_id": first,
        "second_dataset_id": second,
        "first_label": LABELS[first],
        "second_label": LABELS[second],
        "sign_convention": SIGN_CONVENTION,
        "lags": [row.to_dict() for row in rows],
        "strongest_absolute_correlation": peak_dict,
        "distinguishable_peaks": distinguishable,
        "subsamples": subsamples,
        "same_peak_lag_in_both_subsamples": subsample_is_stable(early, late),
        "stability_note": NOT_A_STRUCTURAL_LEAD,
    }


def _subsample_payload(
    months: Sequence[date],
    first: np.ndarray,
    second: np.ndarray,
    window: SubsampleWindow,
) -> dict[str, object]:
    indexes = [index for index, month in enumerate(months) if window.start <= month <= window.end]
    base = {
        "window": window.name,
        "start": window.start.isoformat(),
        "end": window.end.isoformat(),
        "overlaps_illustrated_break": False,
    }
    selected_months = [months[index] for index in indexes]
    if len(selected_months) < MIN_SUBSAMPLE_GROWTH_MONTHS:
        return {
            **base,
            "status": "skipped",
            "growth_month_count": len(selected_months),
            "reason": (
                f"The subsample has {len(selected_months)} growth months, below the "
                f"predeclared minimum of {MIN_SUBSAMPLE_GROWTH_MONTHS}."
            ),
        }
    if not _months_are_contiguous(selected_months):
        return {
            **base,
            "status": "skipped",
            "growth_month_count": len(selected_months),
            "reason": "The subsample is not one contiguous monthly run, so it was skipped.",
        }
    first_values = first[indexes]
    second_values = second[indexes]
    rows = cross_correlations(first_values, second_values)
    peak = strongest_absolute_correlation(rows)
    return {
        **base,
        "status": "computed",
        "growth_month_count": len(indexes),
        "growth_start": months[indexes[0]].isoformat(),
        "growth_end": months[indexes[-1]].isoformat(),
        "strongest_absolute_correlation": None if peak is None else peak.to_dict(),
        "distinguishable_lag_count": sum(1 for row in rows if row.distinguishable_from_zero),
    }


def _series_log_growth(levels: Mapping[date, float]) -> dict[date, float]:
    growth: dict[date, float] = {}
    for month, value in levels.items():
        if month.day != 1 or not math.isfinite(value) or value <= 0:
            continue
        prior = previous_month(month)
        prior_value = levels.get(prior)
        if prior_value is None or not math.isfinite(prior_value) or prior_value <= 0:
            continue
        difference = math.log(value) - math.log(prior_value)
        if math.isfinite(difference):
            growth[month] = difference
    return growth


def _eligible_levels(
    dataset_id: str,
    series: Mapping[date, EconomicObservation],
) -> dict[date, float]:
    levels: dict[date, float] = {}
    for period, observation in series.items():
        if not _level_is_eligible(dataset_id, observation):
            continue
        value = float(observation.decimal_value())
        if math.isfinite(value) and value > 0:
            levels[period] = value
    return levels


def _level_is_eligible(dataset_id: str, observation: EconomicObservation) -> bool:
    return (
        observation.dataset_id == dataset_id
        and observation.series_provenance == SeriesProvenance.LATEST_REVISED
        and observation.quality_status == QualityStatus.OBSERVED
        and observation.frequency == Frequency.MONTHLY
        and observation.seasonal_adjustment == SeasonalAdjustment.SEASONALLY_ADJUSTED
        and observation.unit == UNITS[dataset_id]
        and observation.period_start.day == 1
    )


def _observation_ids(
    series_by_dataset: Mapping[str, Mapping[date, EconomicObservation]],
    growth_months: Sequence[date],
) -> tuple[str, ...]:
    if not growth_months:
        return ()
    level_months = (previous_month(growth_months[0]), *growth_months)
    identifiers: list[str] = []
    for dataset_id in DATASET_IDS:
        series = series_by_dataset[dataset_id]
        for month in level_months:
            observation = series.get(month)
            if observation is not None:
                identifiers.append(observation.observation_id)
    return tuple(identifiers)


def _ordered_pairs() -> tuple[tuple[str, str], ...]:
    pairs: list[tuple[str, str]] = []
    for index, first in enumerate(DATASET_IDS):
        for second in DATASET_IDS[index + 1 :]:
            pairs.append((first, second))
    return tuple(pairs)


def _aligned(
    first: np.ndarray,
    second: np.ndarray,
    lag: int,
) -> tuple[np.ndarray, np.ndarray] | None:
    """Pair first_t with second_{t+lag}."""
    if lag >= 0:
        if lag >= first.size:
            return None
        return first[: first.size - lag], second[lag:]
    shift = -lag
    if shift >= first.size:
        return None
    return first[shift:], second[: second.size - shift]


def _pearson(first: np.ndarray, second: np.ndarray) -> float | None:
    if first.size != second.size or first.size < MIN_PAIRS:
        return None
    left = first - first.mean()
    right = second - second.mean()
    denominator = math.sqrt(float(left @ left) * float(right @ right))
    if denominator == 0 or not math.isfinite(denominator):
        return None
    correlation = float(left @ right) / denominator
    if not math.isfinite(correlation):
        return None
    return correlation


def _longest_run(months: list[date]) -> list[date]:
    best: list[date] = []
    current: list[date] = []
    for month in months:
        if current and month != next_month(current[-1]):
            if len(current) > len(best):
                best = current
            current = [month]
        else:
            current.append(month)
    if len(current) > len(best):
        best = current
    return best


def _months_are_contiguous(months: Sequence[date]) -> bool:
    return all(right == next_month(left) for left, right in zip(months, months[1:], strict=False))


def _overlaps(left: SubsampleWindow, right: SubsampleWindow) -> bool:
    return left.start <= right.end and right.start <= left.end


def _round(value: float | None) -> float | None:
    if value is None or not math.isfinite(value):
        return None
    return round(float(value), 6)


def _assumptions(excluded_overlap_months: int) -> tuple[str, ...]:
    assumptions = [
        "Each series enters as a monthly natural log-growth of adjacent levels.",
        "The sample is the balanced overlap of the four series.",
        SIGN_CONVENTION,
        (
            "Bartlett standard errors use the autocorrelations of both series "
            f"through lag {BARTLETT_TRUNCATION}. "
            "Independent-and-identical standard errors are not used."
        ),
        (
            "A correlation is distinguishable from zero only when its absolute "
            f"value exceeds {CRITICAL_VALUE} Bartlett standard errors."
        ),
        (
            f"The subsamples are {EARLY_SUBSAMPLE.name} and {LATE_SUBSAMPLE.name}. "
            f"They leave out {ILLUSTRATED_BREAK.name}."
        ),
        NOT_A_STRUCTURAL_LEAD,
        NO_FIXED_STATUS,
    ]
    if excluded_overlap_months:
        assumptions.append(
            "Overlap months outside the longest contiguous run were left out. "
            "Gaps were not interpolated.",
        )
    return tuple(assumptions)


def _limitations(calculation: Mapping[str, object]) -> tuple[str, ...]:
    stable = 0
    pairs = calculation.get("pairs")
    if isinstance(pairs, list):
        stable = sum(
            1
            for pair in pairs
            if isinstance(pair, dict) and pair.get("same_peak_lag_in_both_subsamples") is True
        )
    return (
        "Publication allowed is false.",
        NOT_A_STRUCTURAL_LEAD,
        NO_FIXED_STATUS,
        "The path is latest_revised. It is not a real-time vintage.",
        (
            "A Bartlett variance estimate that is not positive does not fall back "
            "to an independent-and-identical standard error. That lag is not "
            "called distinguishable from zero."
        ),
        (
            f"Subsample agreement of the strongest absolute correlation holds for "
            f"{stable} of the pairs. Agreement is not a structural lead."
        ),
    )


def _interpretation(calculation: Mapping[str, object]) -> str:
    peaks = calculation.get("distinguishable_peaks")
    count = len(peaks) if isinstance(peaks, list) else 0
    return (
        "Cross-correlations of monthly log-growth at lags from -12 to 12 months. "
        f"{SIGN_CONVENTION} Significance uses Bartlett standard errors that include "
        "the autocorrelations of both series. "
        f"{count} lag correlations are distinguishable from zero on the balanced sample. "
        f"{NOT_A_STRUCTURAL_LEAD} {NO_FIXED_STATUS} Publication allowed is false."
    )


def _narrative(calculation: Mapping[str, object]) -> str:
    return (
        "Lead-lag cross-correlations on the balanced monthly log-growth of the "
        f"four coincident series. {_interpretation(calculation)}"
    )


def _insufficient_payload(reason: str) -> dict[str, object]:
    return {
        "sufficient": False,
        "reason": reason,
        "method_id": LEAD_LAG_CROSS_CORRELATION,
        "publication_allowed": PUBLICATION_ALLOWED,
        "iid_standard_errors_used": False,
        "fixed_leading_indicator_assigned": False,
        "transformation": TRANSFORMATION,
    }


def _insufficient(reason: str) -> MethodExecutionResult:
    return MethodExecutionResult(
        sufficiency="insufficient",
        calculation={
            "method_id": LEAD_LAG_CROSS_CORRELATION,
            "publication_allowed": PUBLICATION_ALLOWED,
            "iid_standard_errors_used": False,
            "fixed_leading_indicator_assigned": False,
            "transformation": TRANSFORMATION,
        },
        observation_ids=(),
        assumptions=(SIGN_CONVENTION, NOT_A_STRUCTURAL_LEAD),
        limitations=("Publication allowed is false.", NO_FIXED_STATUS),
        missing_reason=reason,
        statistical_interpretation="Lead-lag cross-correlations were not computed.",
        causal_hypothesis="none",
        investment_implication="insufficient_evidence",
        narrative=f"Lead-lag cross-correlations incomplete. Reason: {reason}",
    )
