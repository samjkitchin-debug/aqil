"""Intercept-only Bai–Perron mean shifts in monthly log-growth.

Named relationship: monthly log-growth of ``fed.g17.IP.B50001.S``,
``latest_revised``. The model is the pure structural-change model in Bai and
Perron (1998), restricted to a shifting intercept and no other regressor:

    y_t = μ_j + u_t,  T_{j-1} < t ≤ T_j,  j = 1, ..., m + 1,

with T_0 = 0 and T_{m+1} = T. Least squares minimises the sum of squared
residuals over partitions whose segments each contain at least h observations.
The minimiser is computed by the dynamic programme

    SSR(0, n) = SSR of observations 1..n,
    SSR(r, n) = min_{r h ≤ j ≤ n - h} [ SSR(r - 1, j) + SSR of observations j+1..n ].

This module uses NumPy for that recursion. It does not call a change-point
library, and it does not estimate the general Bai–Perron model with regressors.

Trimming is frozen before looking at a result:

    h = max(24, floor(0.15 * T)),

where T is the number of monthly log-growth observations. The break count is
capped at 5.

The break count minimises the Schwarz criterion in Bai and Perron (2003),
specialised to this least-squares mean-shift model (q = 1 changing intercept,
p = 0 non-breaking regressors):

    BIC(m) = ln(SSR(m) / T) + (2 m + 1) * ln(T) / T.

The parameter count 2 m + 1 equals (m + 1) q + m + p. SSR(m) is the minimised
residual sum of squares. The variance divisor is T. An additive constant that
does not depend on m is omitted. If two break counts tie, the smaller count is
kept. The penalty is not adjusted to a sample.

T_i in Bai and Perron is the last observation of regime i. The reported break
date is the following month, the first month of the new mean. Both are point
estimates. Confidence intervals are not computed.

The fit is retrospective on the latest revised file. It is not a forecast.
``publication_allowed`` stays false.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import numpy as np
from pydantic import BaseModel, ConfigDict, Field

from aqil_research.contracts.observation import AnalysisMode
from aqil_research.methods.bry_boschan_monthly import (
    G17_DATASET_ID,
    G17_LEVEL_UNIT,
    G17InputPoint,
    assess_g17_level_input,
)
from aqil_research.methods.parameters import MethodParameterDocument
from aqil_research.methods.protocol import MethodContext, MethodExecutionResult

BAI_PERRON_MEAN_SHIFTS = "BAI_PERRON_MEAN_SHIFTS"
METHOD_VERSION = "1.0.0"
PUBLICATION_ALLOWED = False
MAX_BREAKS = 5
SEGMENT_FLOOR = 24
TRIM_NUMERATOR = 15
TRIM_DENOMINATOR = 100
BIC_FORMULA = "ln(SSR(m) / T) + (2 * m + 1) * ln(T) / T"
DATE_STATUS = "point_estimates_only"
CAUSAL_HYPOTHESIS = "No causal mechanism is established."
NAMED_RELATIONSHIP = "intercept-only mean shifts in monthly log-growth of fed.g17.IP.B50001.S"

PUBLISHED_CONFIG: dict[str, str] = {
    "config_id": "bai_perron_mean_shifts_v1",
    "label": "Intercept-only mean shifts in monthly log-growth of industrial production",
}


class BaiPerronMeanShiftsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    config_id: str = Field(min_length=1)
    label: str = Field(min_length=1)


@dataclass(frozen=True, slots=True)
class MeanShiftPartition:
    break_count: int
    regime_start_indices: tuple[int, ...]
    sum_of_squared_residuals: float
    schwarz_bic: float
    segment_means: tuple[float, ...]
    parameter_count: int


@dataclass(frozen=True, slots=True)
class MeanShiftSelection:
    sample_size: int
    minimum_segment_length: int
    max_breaks: int
    feasible_break_count_before_cap: int
    selected: MeanShiftPartition
    candidates: tuple[MeanShiftPartition, ...]


def minimum_segment_length(sample_size: int) -> int:
    """Return h = max(24, floor(0.15 * T)) for a log-growth sample of length T."""

    if sample_size < 1:
        raise ValueError("sample size must be positive")
    trimmed = (sample_size * TRIM_NUMERATOR) // TRIM_DENOMINATOR
    return max(SEGMENT_FLOOR, trimmed)


def schwarz_bic(sum_of_squared_residuals: float, break_count: int, sample_size: int) -> float:
    """Return BIC(m) = ln(SSR(m) / T) + (2 m + 1) * ln(T) / T.

    A zero residual sum of squares returns negative infinity. The caller breaks
    ties by preferring the smaller break count.
    """

    if sample_size < 1:
        raise ValueError("sample size must be positive")
    if break_count < 0:
        raise ValueError("break count cannot be negative")
    residual = float(sum_of_squared_residuals)
    if residual < 0.0 and residual > -1e-8:
        residual = 0.0
    if residual < 0.0:
        raise ValueError("sum of squared residuals cannot be negative")
    penalty = (2 * break_count + 1) * math.log(sample_size) / sample_size
    if residual == 0.0:
        return -math.inf
    return math.log(residual / sample_size) + penalty


def select_mean_shifts(
    values: np.ndarray,
    *,
    minimum_segment_length: int,
    max_breaks: int = MAX_BREAKS,
) -> MeanShiftSelection:
    """Least-squares mean-shift partitions for m = 0, ..., min(5, feasible).

    ``regime_start_indices`` are 0-based positions in ``values``. Index 0 is
    always the first regime. Each later index is the first observation of a
    new mean, which is observation T_i + 1 in Bai and Perron.
    """

    series = _as_series(values)
    if minimum_segment_length < 1:
        raise ValueError("minimum segment length must be at least 1")
    if max_breaks < 0:
        raise ValueError("max breaks cannot be negative")
    sample_size = int(series.shape[0])
    feasible = max(0, sample_size // minimum_segment_length - 1)
    capped = min(max_breaks, feasible)
    prefix, squares = _prefix_sums(series)
    candidates = [
        _partition(
            prefix,
            squares,
            break_count=0,
            regime_starts=(0,),
            sample_size=sample_size,
        ),
    ]
    if capped > 0:
        cost, predecessor = _dynamic_programme(
            prefix,
            squares,
            sample_size=sample_size,
            minimum_segment_length=minimum_segment_length,
            max_breaks=capped,
        )
        for break_count in range(1, capped + 1):
            regime_starts = _regime_starts(predecessor, break_count, sample_size)
            candidates.append(
                _partition(
                    prefix,
                    squares,
                    break_count=break_count,
                    regime_starts=regime_starts,
                    sample_size=sample_size,
                    cached_ssr=float(cost[break_count, sample_size]),
                ),
            )
    selected = min(
        candidates,
        key=lambda item: (item.schwarz_bic, item.break_count),
    )
    return MeanShiftSelection(
        sample_size=sample_size,
        minimum_segment_length=minimum_segment_length,
        max_breaks=max_breaks,
        feasible_break_count_before_cap=feasible,
        selected=selected,
        candidates=tuple(candidates),
    )


def implementation_hash() -> str:
    """SHA-256 of this module. Transitive imports are not included."""

    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


class BaiPerronMeanShiftsMethod:
    method_id = BAI_PERRON_MEAN_SHIFTS
    method_version = METHOD_VERSION

    def implementation_hash(self) -> str:
        return implementation_hash()

    def required_dataset_ids(self) -> tuple[str, ...]:
        return (G17_DATASET_ID,)

    def parse_config(self, payload: dict[str, object]) -> BaiPerronMeanShiftsConfig:
        return BaiPerronMeanShiftsConfig.model_validate(payload)

    def config_hash(self, config: BaseModel) -> str:
        if not isinstance(config, BaiPerronMeanShiftsConfig):
            raise TypeError("expected BaiPerronMeanShiftsConfig")
        return MethodParameterDocument(
            config_id=config.config_id,
            label=config.label,
            scalars={
                "transformation": "monthly_log_growth",
                "trim_fraction": f"{TRIM_NUMERATOR}/{TRIM_DENOMINATOR}",
                "segment_floor": str(SEGMENT_FLOOR),
                "max_breaks": str(MAX_BREAKS),
                "bic_formula": BIC_FORMULA,
                "date_status": DATE_STATUS,
            },
        ).config_hash()

    def run(self, context: MethodContext, config: BaseModel) -> MethodExecutionResult:
        if not isinstance(config, BaiPerronMeanShiftsConfig):
            raise TypeError("expected BaiPerronMeanShiftsConfig")
        if context.analysis_mode != AnalysisMode.LATEST_REVISED:
            return _insufficient(
                "The stored G.17 file is a latest revised file, not a vintage panel.",
            )
        series = {
            period: observation
            for period, observation in context.inputs_by_dataset.get(G17_DATASET_ID, {}).items()
            if period <= context.evaluation_period
        }
        if context.evaluation_period not in series:
            return _insufficient(
                f"No stored month at {context.evaluation_period.isoformat()}.",
            )
        points = tuple(
            G17InputPoint(observation=observation, collection_mode="live")
            for observation in series.values()
        )
        assessment = assess_g17_level_input(points)
        if (
            not assessment.eligible
            or assessment.sample_start is None
            or assessment.sample_end is None
        ):
            return _insufficient("; ".join(assessment.reasons) or "G.17 input is ineligible.")
        chosen = [
            series[period]
            for period in sorted(series)
            if assessment.sample_start <= period <= assessment.sample_end
        ]
        levels = [observation.decimal_value() for observation in chosen]
        if any(level <= 0 for level in levels):
            return _insufficient(
                "Monthly log-growth needs a positive industrial production index.",
            )
        growth_dates = tuple(observation.period_start for observation in chosen[1:])
        growth = np.diff(np.log(np.array([float(level) for level in levels], dtype=np.float64)))
        if growth.size < 2 or not np.isfinite(growth).all():
            return _insufficient("Monthly log-growth is not a finite sample.")
        segment_length = minimum_segment_length(int(growth.size))
        selection = select_mean_shifts(
            growth,
            minimum_segment_length=segment_length,
            max_breaks=MAX_BREAKS,
        )
        sensitivity = _trimming_sensitivity(growth, growth_dates, selection)
        calculation = _calculation(
            selection,
            sensitivity,
            level_start=chosen[0].period_start,
            level_end=chosen[-1].period_start,
            level_count=len(chosen),
            growth_dates=growth_dates,
        )
        return MethodExecutionResult(
            sufficiency="sufficient",
            calculation=calculation,
            observation_ids=tuple(observation.observation_id for observation in chosen),
            assumptions=_assumptions(),
            limitations=_limitations(sensitivity["dates_sensitive_to_trimming"] is True),
            missing_reason=None,
            statistical_interpretation=(
                "Least-squares point estimates of intercept shifts in monthly "
                "log-growth. The Schwarz criterion selected the break count. "
                "These dates are retrospective. They are not a forecast."
            ),
            causal_hypothesis=CAUSAL_HYPOTHESIS,
            investment_implication="no_action",
            narrative=_narrative(selection, sensitivity["dates_sensitive_to_trimming"] is True),
        )


def _as_series(values: np.ndarray) -> np.ndarray:
    series = np.asarray(values, dtype=np.float64)
    if series.ndim != 1:
        raise ValueError("the mean-shift sample must be one-dimensional")
    if series.size < 1:
        raise ValueError("sample is empty")
    if not np.isfinite(series).all():
        raise ValueError("the mean-shift sample must be finite")
    return series


def _prefix_sums(values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    prefix = np.empty(values.shape[0] + 1, dtype=np.float64)
    squares = np.empty(values.shape[0] + 1, dtype=np.float64)
    prefix[0] = 0.0
    squares[0] = 0.0
    np.cumsum(values, out=prefix[1:])
    np.cumsum(values * values, out=squares[1:])
    return prefix, squares


def _segment_ssr(prefix: np.ndarray, squares: np.ndarray, start: int, end: int) -> float:
    """SSR of ``values[start:end]`` from prefix sums. ``end`` is exclusive."""

    count = end - start
    if count <= 0:
        raise ValueError("segment is empty")
    total = float(prefix[end] - prefix[start])
    quad = float(squares[end] - squares[start])
    residual = quad - (total * total) / count
    if residual < 0.0:
        return 0.0
    return residual


def _dynamic_programme(
    prefix: np.ndarray,
    squares: np.ndarray,
    *,
    sample_size: int,
    minimum_segment_length: int,
    max_breaks: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Global least-squares costs. Ties keep the earliest admissible break."""

    length = minimum_segment_length
    cost = np.full((max_breaks + 1, sample_size + 1), np.inf, dtype=np.float64)
    predecessor = np.full((max_breaks + 1, sample_size + 1), -1, dtype=np.int64)
    ends = np.arange(length, sample_size + 1, dtype=np.int64)
    totals = prefix[ends] - prefix[0]
    quads = squares[ends] - squares[0]
    base = quads - (totals * totals) / ends
    np.maximum(base, 0.0, out=base)
    cost[0, length:] = base
    predecessor[0, length:] = 0

    for breaks in range(1, max_breaks + 1):
        earliest_end = (breaks + 1) * length
        for end in range(earliest_end, sample_size + 1):
            first = breaks * length
            last = end - length
            starts = np.arange(first, last + 1, dtype=np.int64)
            counts = end - starts
            segment_total = prefix[end] - prefix[starts]
            segment_quad = squares[end] - squares[starts]
            segment = segment_quad - (segment_total * segment_total) / counts
            np.maximum(segment, 0.0, out=segment)
            total_cost = cost[breaks - 1, starts] + segment
            choice = int(np.argmin(np.where(np.isfinite(total_cost), total_cost, np.inf)))
            chosen = float(total_cost[choice])
            if math.isfinite(chosen):
                cost[breaks, end] = chosen
                predecessor[breaks, end] = int(starts[choice])
    return cost, predecessor


def _regime_starts(predecessor: np.ndarray, break_count: int, sample_size: int) -> tuple[int, ...]:
    starts: list[int] = []
    end = sample_size
    for breaks in range(break_count, 0, -1):
        start = int(predecessor[breaks, end])
        if start < 0:
            raise RuntimeError("the dynamic programme has no break for this partition")
        starts.append(start)
        end = start
    starts.append(0)
    starts.reverse()
    if starts[0] != 0 or len(starts) != break_count + 1:
        raise RuntimeError("reconstructed regimes do not match the break count")
    return tuple(starts)


def _partition(
    prefix: np.ndarray,
    squares: np.ndarray,
    *,
    break_count: int,
    regime_starts: tuple[int, ...],
    sample_size: int,
    cached_ssr: float | None = None,
) -> MeanShiftPartition:
    bounds = (*regime_starts, sample_size)
    residual = 0.0
    means: list[float] = []
    for index in range(len(bounds) - 1):
        left = bounds[index]
        right = bounds[index + 1]
        if right <= left:
            raise RuntimeError("regime bounds are not increasing")
        count = right - left
        total = float(prefix[right] - prefix[left])
        means.append(total / count)
        residual += _segment_ssr(prefix, squares, left, right)
    if cached_ssr is not None and not math.isclose(
        cached_ssr,
        residual,
        rel_tol=1e-9,
        abs_tol=1e-8,
    ):
        raise RuntimeError("dynamic programme cost does not match the segment residuals")
    return MeanShiftPartition(
        break_count=break_count,
        regime_start_indices=regime_starts,
        sum_of_squared_residuals=residual,
        schwarz_bic=schwarz_bic(residual, break_count, sample_size),
        segment_means=tuple(means),
        parameter_count=2 * break_count + 1,
    )


def _trimming_sensitivity(
    growth: np.ndarray,
    growth_dates: tuple[date, ...],
    primary: MeanShiftSelection,
) -> dict[str, object]:
    sample_size = int(growth.shape[0])
    alternatives: list[dict[str, object]] = []
    sensitive = False
    primary_dates = _break_dates(growth_dates, primary.selected.regime_start_indices)
    for label, length in _alternative_lengths(sample_size):
        if length < 1 or sample_size // length < 1:
            alternatives.append(
                {
                    "label": label,
                    "minimum_segment_length": length,
                    "estimated": False,
                    "reason": "The alternative trim is longer than the sample.",
                },
            )
            sensitive = True
            continue
        fitted = select_mean_shifts(
            growth,
            minimum_segment_length=length,
            max_breaks=MAX_BREAKS,
        )
        dates = _break_dates(growth_dates, fitted.selected.regime_start_indices)
        differs = (
            dates != primary_dates or fitted.selected.break_count != primary.selected.break_count
        )
        if length == primary.minimum_segment_length and differs:
            raise RuntimeError("the same trim produced different dates")
        if length != primary.minimum_segment_length and differs:
            sensitive = True
        alternatives.append(
            {
                "label": label,
                "minimum_segment_length": length,
                "estimated": True,
                "break_count": fitted.selected.break_count,
                "break_dates": dates,
                "same_dates_as_primary": not differs,
            },
        )
    if sensitive:
        note = (
            "The selected break dates change under at least one documented "
            "alternative minimum segment length. The reported dates use the "
            "primary rule only."
        )
    else:
        note = (
            "The selected break dates are unchanged under the documented "
            "alternative minimum segment lengths."
        )
    return {
        "primary_minimum_segment_length": primary.minimum_segment_length,
        "dates_sensitive_to_trimming": sensitive,
        "note": note,
        "alternatives": alternatives,
    }


def _alternative_lengths(sample_size: int) -> tuple[tuple[str, int], ...]:
    return (
        ("segment_floor_24", SEGMENT_FLOOR),
        ("trim_fraction_0_10", max(SEGMENT_FLOOR, (sample_size * 10) // 100)),
        ("trim_fraction_0_20", max(SEGMENT_FLOOR, (sample_size * 20) // 100)),
    )


def _calculation(
    selection: MeanShiftSelection,
    sensitivity: dict[str, object],
    *,
    level_start: date,
    level_end: date,
    level_count: int,
    growth_dates: tuple[date, ...],
) -> dict[str, object]:
    selected = selection.selected
    window = _admissible_window(growth_dates, selection.minimum_segment_length)
    return {
        "method_id": BAI_PERRON_MEAN_SHIFTS,
        "named_relationship": NAMED_RELATIONSHIP,
        "model": "pure_structural_change_intercept_only",
        "general_bai_perron_regressor_model_implemented": False,
        "transformation": "monthly_log_growth",
        "log_growth_definition": (
            "Natural log of the later month's index minus the natural log of "
            "the previous month's index. The growth month is the later month."
        ),
        "input_series": G17_DATASET_ID,
        "input_unit": G17_LEVEL_UNIT,
        "input_revision": AnalysisMode.LATEST_REVISED.value,
        "chronology_class": "retrospective_full_sample",
        "forecast": False,
        "advance_prediction": False,
        "date_status": DATE_STATUS,
        "publication_allowed": PUBLICATION_ALLOWED,
        "level_sample_start": level_start.isoformat(),
        "level_sample_end": level_end.isoformat(),
        "level_month_count": level_count,
        "log_growth_sample_start": growth_dates[0].isoformat(),
        "log_growth_sample_end": growth_dates[-1].isoformat(),
        "log_growth_month_count": selection.sample_size,
        "minimum_segment_length": selection.minimum_segment_length,
        "segment_floor": SEGMENT_FLOOR,
        "trim_fraction": f"{TRIM_NUMERATOR}/{TRIM_DENOMINATOR}",
        "max_breaks": MAX_BREAKS,
        "feasible_break_count_before_cap": selection.feasible_break_count_before_cap,
        "break_count": selected.break_count,
        "bic": _json_number(selected.schwarz_bic),
        "sum_of_squared_residuals": selected.sum_of_squared_residuals,
        "penalty_parameter_count": selected.parameter_count,
        "bic_formula": BIC_FORMULA,
        "break_dates": _break_dates(growth_dates, selected.regime_start_indices),
        "preceding_regime_end_dates": _preceding_ends(
            growth_dates,
            selected.regime_start_indices,
        ),
        "segments": _segments(growth_dates, selected),
        "bic_by_break_count": [
            {
                "break_count": item.break_count,
                "bic": _json_number(item.schwarz_bic),
                "sum_of_squared_residuals": item.sum_of_squared_residuals,
                "penalty_parameter_count": item.parameter_count,
            }
            for item in selection.candidates
        ],
        "admissible_break_window": window,
        "trimming_sensitivity": sensitivity,
        "penalty_tuned_on_sample": False,
        "confidence_intervals_reported": False,
    }


def _break_dates(growth_dates: tuple[date, ...], regime_starts: tuple[int, ...]) -> list[str]:
    return [growth_dates[index].isoformat() for index in regime_starts[1:]]


def _preceding_ends(growth_dates: tuple[date, ...], regime_starts: tuple[int, ...]) -> list[str]:
    return [growth_dates[index - 1].isoformat() for index in regime_starts[1:]]


def _segments(
    growth_dates: tuple[date, ...],
    selected: MeanShiftPartition,
) -> list[dict[str, object]]:
    bounds = (*selected.regime_start_indices, len(growth_dates))
    rows: list[dict[str, object]] = []
    for index, mean in enumerate(selected.segment_means):
        left = bounds[index]
        right = bounds[index + 1]
        rows.append(
            {
                "start": growth_dates[left].isoformat(),
                "end": growth_dates[right - 1].isoformat(),
                "month_count": right - left,
                "mean_log_growth": mean,
            },
        )
    return rows


def _admissible_window(
    growth_dates: tuple[date, ...],
    minimum_segment_length: int,
) -> dict[str, object] | None:
    sample_size = len(growth_dates)
    if sample_size < 2 * minimum_segment_length:
        return None
    earliest = minimum_segment_length
    latest = sample_size - minimum_segment_length
    return {
        "earliest_break_date": growth_dates[earliest].isoformat(),
        "latest_break_date": growth_dates[latest].isoformat(),
        "rule": ("A new mean cannot start in the first or last h log-growth months."),
    }


def _assumptions() -> tuple[str, ...]:
    return (
        f"The named relationship is {NAMED_RELATIONSHIP}.",
        (
            "Monthly log-growth is the change in the natural logarithm of the "
            "seasonally adjusted index."
        ),
        (
            "The estimator is least squares for the pure structural-change model, "
            "computed by dynamic programming."
        ),
        (
            "The minimum segment length is the maximum of 24 months and "
            "floor(0.15 times the number of log-growth months)."
        ),
        "The number of breaks is at most 5.",
        f"The number of breaks minimises BIC(m) = {BIC_FORMULA}.",
        "The dates are retrospective full-sample point estimates on the latest revised file.",
    )


def _limitations(dates_sensitive: bool) -> tuple[str, ...]:
    trimming = (
        "The selected dates change when the documented alternative trims are used. "
        "They are not an advance prediction."
        if dates_sensitive
        else (
            "The documented alternative trims did not change the selected dates. "
            "The dates are still not an advance prediction."
        )
    )
    return (
        "The general Bai–Perron model with regressors is not implemented.",
        "Confidence intervals are not reported. The dates are point estimates only.",
        "This is not a forecast.",
        "Publication allowed is false.",
        (
            "Inputs are latest revised. Revision sensitivity needs a vintage panel, "
            "and none was invented."
        ),
        trimming,
        "The penalty was not tuned on this sample.",
        (
            "The Schwarz penalty is the least-squares criterion. It is not a "
            "heteroskedasticity-and-autocorrelation-robust test."
        ),
    )


def _narrative(selection: MeanShiftSelection, dates_sensitive: bool) -> str:
    count = selection.selected.break_count
    if count == 0:
        chosen = "The primary rule selected no break"
    elif count == 1:
        chosen = "The primary rule selected one break"
    else:
        chosen = f"The primary rule selected {count} breaks"
    sensitivity = (
        "The dates are sensitive to the trimming choice."
        if dates_sensitive
        else "The documented alternative trims leave the selected dates unchanged."
    )
    return (
        f"{chosen} in monthly log-growth of industrial production. {sensitivity} "
        "The dates are retrospective point estimates on the latest revised file. "
        "They are not a forecast. Publication allowed is false."
    )


def _json_number(value: float) -> float | None:
    if math.isfinite(value):
        return float(value)
    return None


def _insufficient(reason: str) -> MethodExecutionResult:
    return MethodExecutionResult(
        sufficiency="insufficient",
        calculation={
            "method_id": BAI_PERRON_MEAN_SHIFTS,
            "publication_allowed": PUBLICATION_ALLOWED,
            "date_status": DATE_STATUS,
            "forecast": False,
            "general_bai_perron_regressor_model_implemented": False,
        },
        observation_ids=(),
        assumptions=_assumptions()[:1],
        limitations=(
            "Publication allowed is false.",
            "The dates were not estimated.",
        ),
        missing_reason=reason,
        statistical_interpretation="Mean shifts were not estimated.",
        causal_hypothesis=CAUSAL_HYPOTHESIS,
        investment_implication="insufficient_evidence",
        narrative=f"Mean shifts were not estimated. Reason: {reason}",
    )
