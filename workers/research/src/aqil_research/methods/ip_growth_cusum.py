"""CUSUM of recursive residuals for industrial-production log growth.

The series is the monthly natural log-growth of ``fed.g17.IP.B50001.S``
only, from ``contiguous_monthly_log_growth``. The input vintage is
``latest_revised``.

The regression is ordinary least squares of that log-growth on a constant
and one predeclared lag::

    g_t = c + φ g_{t-1} + e_t

The lag is not chosen by an information criterion. Parameter policy is
none.

Recursive residuals and the CUSUM boundary come from
``statsmodels.stats.diagnostic.recursive_olsresiduals`` (statsmodels 0.15),
called on the ordinary-least-squares result with these arguments:

- ``skip=None``. The default sets the initial block to one row per
  regressor, including the constant.
- ``lamda=0.0``. The default. The initial cross-product inverse has no
  ridge term. The parameter name is statsmodels' spelling.
- ``alpha=0.95``. The default. The five percent boundary uses the
  coefficient 0.948.
- ``order_by=None``. The default. The sample order is unchanged.

In that version the returned cumulative sum has one more point than the
returned boundary. The extra point is the residual of the saturated initial
block. This method compares the remaining cumulative sum with the returned
boundary, whose step index starts at 0. A crossing is a point strictly
outside that interval. Staying inside is also a result. No break date is
selected.

The diagnostic is parameter drift in this autoregression. A Chow test is
not estimated. A Bai-Perron mean shift is not estimated. A local projection
is not estimated. ``publication_allowed`` stays false.
"""

from __future__ import annotations

import hashlib
import math
from collections.abc import Mapping, Sequence
from datetime import date

import numpy as np
from pydantic import BaseModel, ConfigDict, Field
from statsmodels.regression.linear_model import OLS
from statsmodels.stats.diagnostic import recursive_olsresiduals

from aqil_research.contracts.observation import (
    AnalysisMode,
    EconomicObservation,
    Frequency,
    QualityStatus,
    SeasonalAdjustment,
    SeriesProvenance,
)
from aqil_research.methods.autoregressive_benchmark import (
    INDUSTRIAL_PRODUCTION_DATASET_ID,
    LEVEL_UNIT,
    contiguous_monthly_log_growth,
)
from aqil_research.methods.parameters import MethodParameterDocument
from aqil_research.methods.protocol import (
    MethodContext,
    MethodDependency,
    MethodExecutionResult,
    bind_dependency,
)

IP_GROWTH_CUSUM = "IP_GROWTH_CUSUM"
METHOD_VERSION = "0.1.0"
PUBLICATION_ALLOWED = False

PREDECLARED_LAG = 1
BOUNDARY_ALPHA = 0.95
BOUNDARY_COEFFICIENT = 0.948
REGRESSOR_COUNT = PREDECLARED_LAG + 1
MINIMUM_GROWTH_MONTHS = 120
NO_CAUSAL_CLAIM = "No causal claim is made."
NO_BREAK_DATE = "No break date is selected."

PUBLISHED_CONFIG = {
    "config_id": "ip-growth-cusum-v1",
    "label": "CUSUM of the industrial production log-growth autoregression",
}


class IpGrowthCusumConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    config_id: str = Field(min_length=1)
    label: str = Field(min_length=1)


def implementation_hash() -> str:
    payload = "|".join(
        (
            IP_GROWTH_CUSUM,
            METHOD_VERSION,
            "monthly-log-growth",
            f"predeclared-lag-{PREDECLARED_LAG}",
            "ols-with-constant",
            "recursive-olsresiduals",
            "skip-none",
            "lamda-0",
            f"alpha-{BOUNDARY_ALPHA}",
            "order-by-none",
            "drop-leading-cusum-point",
            "strictly-outside-returned-boundary",
            "no-break-date",
            f"minimum-growth-{MINIMUM_GROWTH_MONTHS}",
        ),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def autoregressive_design(growth: Sequence[float], lag: int) -> tuple[np.ndarray, np.ndarray]:
    """Design for an autoregression with a constant in column 0."""

    values = np.asarray(list(growth), dtype=np.float64)
    if values.ndim != 1 or lag < 1 or values.size <= lag:
        raise ValueError("the growth sample is shorter than the lag")
    if not np.isfinite(values).all():
        raise ValueError("the growth sample must be finite")
    rows = int(values.size) - lag
    design = np.empty((rows, lag + 1), dtype=np.float64)
    design[:, 0] = 1.0
    for index in range(1, lag + 1):
        design[:, index] = values[lag - index : int(values.size) - index]
    return design, values[lag:]


def cusum_from_growth(growth: Sequence[float]) -> dict[str, object]:
    """CUSUM for the predeclared lag. Crossing and staying inside are both results."""

    values = np.asarray(list(growth), dtype=np.float64)
    if values.size < MINIMUM_GROWTH_MONTHS:
        raise ValueError(
            f"the log-growth sample has {values.size} months, below {MINIMUM_GROWTH_MONTHS}",
        )
    design, target = autoregressive_design(values, PREDECLARED_LAG)
    fitted = OLS(target, design).fit()
    coefficients = np.asarray(fitted.params, dtype=np.float64)
    if coefficients.shape != (REGRESSOR_COUNT,) or not np.isfinite(coefficients).all():
        raise ValueError("the full-sample coefficients are not finite")
    library = recursive_olsresiduals(
        fitted,
        skip=None,
        lamda=0.0,
        alpha=BOUNDARY_ALPHA,
        order_by=None,
    )
    cusum = np.asarray(library[5], dtype=np.float64)
    boundary = np.asarray(library[6], dtype=np.float64)
    if boundary.ndim != 2 or boundary.shape[0] != 2 or cusum.ndim != 1:
        raise ValueError("the CUSUM return from statsmodels has an unexpected layout")
    if cusum.size != boundary.shape[1] + 1:
        raise ValueError(
            "the returned CUSUM and boundary do not differ by the initial residual",
        )
    if not np.isfinite(cusum).all() or not np.isfinite(boundary).all():
        raise ValueError("the CUSUM path is not finite")
    path = cusum[1:]
    lower = boundary[0]
    upper = boundary[1]
    if not np.all(upper > 0.0) or not np.all(lower < 0.0):
        raise ValueError("the CUSUM boundary is not a two-sided interval")
    outside = (path > upper) | (path < lower)
    crosses = bool(np.any(outside))
    extreme = int(np.argmax(np.abs(path)))
    return {
        "crosses_five_percent_boundary": crosses,
        "extreme_index": extreme,
        "extreme_cusum": float(path[extreme]),
        "boundary_at_extreme": float(upper[extreme]),
        "lower_boundary_at_extreme": float(lower[extreme]),
        "recursive_residual_count": int(path.size),
        "coefficients": coefficients,
        "regression_row_count": int(design.shape[0]),
        "first_boundary": float(upper[0]),
    }


class IpGrowthCusumMethod:
    """Parameter-drift diagnostic for one industrial-production autoregression.

    Registration, for the integrator, inside ``default_method_registry``::

        registry.register(IpGrowthCusumMethod())
    """

    method_id = IP_GROWTH_CUSUM
    method_version = METHOD_VERSION

    def implementation_hash(self) -> str:
        return implementation_hash()

    def required_dataset_ids(self) -> tuple[str, ...]:
        return (INDUSTRIAL_PRODUCTION_DATASET_ID,)

    def dependency(self) -> MethodDependency:
        return bind_dependency(
            self.required_dataset_ids(),
            frequency=("monthly",),
            minimum_history=(
                f"{MINIMUM_GROWTH_MONTHS} contiguous monthly log-growth observations "
                f"for an autoregression of lag {PREDECLARED_LAG} with a constant"
            ),
            parameter_policy="none",
            new_observation_requires_recalculation=True,
            refit_is_different_command=False,
        )

    def accepted_config_payload(self) -> dict[str, object]:
        return dict(PUBLISHED_CONFIG)

    def parse_config(self, payload: dict[str, object]) -> IpGrowthCusumConfig:
        return IpGrowthCusumConfig.model_validate(payload)

    def config_hash(self, config: BaseModel) -> str:
        if not isinstance(config, IpGrowthCusumConfig):
            raise TypeError("expected IpGrowthCusumConfig")
        return MethodParameterDocument(
            config_id=config.config_id,
            label=config.label,
            scalars={
                "transformation": "monthly_log_growth",
                "predeclared_lag": str(PREDECLARED_LAG),
                "regression": "constant_plus_one_lag",
                "procedure": "statsmodels.stats.diagnostic.recursive_olsresiduals",
                "alpha": str(BOUNDARY_ALPHA),
                "lamda": "0.0",
            },
        ).config_hash()

    def run(self, context: MethodContext, config: BaseModel) -> MethodExecutionResult:
        if not isinstance(config, IpGrowthCusumConfig):
            raise TypeError("expected IpGrowthCusumConfig")
        if context.analysis_mode != AnalysisMode.LATEST_REVISED:
            return _insufficient(
                "These levels are dated on latest_revised observations. "
                "A point-in-time request was not dated.",
            )
        series = context.inputs_by_dataset.get(INDUSTRIAL_PRODUCTION_DATASET_ID)
        if not series:
            return _insufficient(
                "No latest-revised industrial production observations were available.",
            )
        levels = _eligible_levels(series)
        if not levels:
            return _insufficient(
                "No eligible latest-revised industrial production level was available.",
            )
        sample = contiguous_monthly_log_growth(levels)
        if len(sample.values) < MINIMUM_GROWTH_MONTHS:
            return _insufficient(
                "The contiguous monthly log-growth sample is shorter than "
                f"{MINIMUM_GROWTH_MONTHS} months.",
            )
        try:
            estimated = cusum_from_growth(sample.values)
        except (ValueError, np.linalg.LinAlgError):
            return _insufficient("The CUSUM did not return a finite result.")
        calculation = _calculation(estimated, sample.growth_months, sample.excluded_growth_months)
        observation_ids = tuple(
            series[month].observation_id for month in sample.level_months if month in series
        )
        return MethodExecutionResult(
            sufficiency="sufficient",
            calculation=calculation,
            observation_ids=observation_ids,
            assumptions=_assumptions(sample.excluded_growth_months),
            limitations=_limitations(),
            missing_reason=None,
            statistical_interpretation=_interpretation(calculation),
            causal_hypothesis="none",
            investment_implication="no_action",
            narrative=_narrative(calculation),
        )


def _calculation(
    estimated: Mapping[str, object],
    growth_months: Sequence[date],
    excluded: int,
) -> dict[str, object]:
    residual_count = int(estimated["recursive_residual_count"])
    start_index = PREDECLARED_LAG + REGRESSOR_COUNT
    end_index = start_index + residual_count - 1
    if end_index != len(growth_months) - 1:
        raise RuntimeError("the CUSUM does not end on the last growth month")
    extreme = int(estimated["extreme_index"])
    extreme_month = growth_months[start_index + extreme]
    coefficients = estimated["coefficients"]
    if not isinstance(coefficients, np.ndarray):
        raise TypeError("expected the full-sample coefficients")
    crosses = estimated["crosses_five_percent_boundary"] is True
    return {
        "sufficient": True,
        "method_id": IP_GROWTH_CUSUM,
        "publication_allowed": PUBLICATION_ALLOWED,
        "input_vintage": "latest_revised",
        "dataset_id": INDUSTRIAL_PRODUCTION_DATASET_ID,
        "transformation": "monthly_log_growth",
        "transformation_function": "contiguous_monthly_log_growth",
        "predeclared_lag": PREDECLARED_LAG,
        "lag_was_selected_by_an_information_criterion": False,
        "constant_included": True,
        "constant_column": "first",
        "regressor_count": REGRESSOR_COUNT,
        "parameter_drift_diagnostic": True,
        "chow_test": False,
        "bai_perron_mean_shift": False,
        "local_projection": False,
        "selected_break_date": None,
        "growth_start": growth_months[0].isoformat(),
        "growth_end": growth_months[-1].isoformat(),
        "growth_month_count": len(growth_months),
        "excluded_growth_months": excluded,
        "regression_row_count": int(estimated["regression_row_count"]),
        "recursive_residual_count": residual_count,
        "cusum_start": growth_months[start_index].isoformat(),
        "cusum_end": growth_months[end_index].isoformat(),
        "statsmodels_function": "statsmodels.stats.diagnostic.recursive_olsresiduals",
        "statsmodels_call": {
            "skip": None,
            "lamda": 0.0,
            "alpha": BOUNDARY_ALPHA,
            "order_by": None,
        },
        "boundary_alpha": BOUNDARY_ALPHA,
        "boundary_coefficient": BOUNDARY_COEFFICIENT,
        "boundary_step_starts_at": 0,
        "leading_cusum_point_dropped": True,
        "crosses_five_percent_boundary": crosses,
        "maximum_absolute_cusum": _figure(abs(float(estimated["extreme_cusum"]))),
        "extreme_cusum": _figure(float(estimated["extreme_cusum"])),
        "boundary_at_extreme": _figure(float(estimated["boundary_at_extreme"])),
        "extreme_period": extreme_month.isoformat(),
        "first_boundary": _figure(float(estimated["first_boundary"])),
        "full_sample_constant": _figure(float(coefficients[0])),
        "full_sample_lag_coefficient": _figure(float(coefficients[1])),
    }


def _figure(value: float) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("a stored figure must be finite")
    return float(f"{number:.8g}")


def _eligible_levels(series: Mapping[date, EconomicObservation]) -> dict[date, float]:
    levels: dict[date, float] = {}
    for period, observation in series.items():
        if not _level_is_eligible(observation):
            continue
        value = float(observation.decimal_value())
        if math.isfinite(value) and value > 0:
            levels[period] = value
    return levels


def _level_is_eligible(observation: EconomicObservation) -> bool:
    return (
        observation.dataset_id == INDUSTRIAL_PRODUCTION_DATASET_ID
        and observation.series_provenance == SeriesProvenance.LATEST_REVISED
        and observation.quality_status == QualityStatus.OBSERVED
        and observation.frequency == Frequency.MONTHLY
        and observation.seasonal_adjustment == SeasonalAdjustment.SEASONALLY_ADJUSTED
        and observation.unit == LEVEL_UNIT
        and observation.period_start.day == 1
    )


def _assumptions(excluded: int) -> tuple[str, ...]:
    assumptions = [
        "The modelled series is the monthly natural log-growth of adjacent positive levels.",
        (
            f"The lag is predeclared at {PREDECLARED_LAG}. "
            "An information criterion does not choose it."
        ),
        "The regression includes a constant in the first column and then that lag.",
        (
            "Recursive residuals and the boundary are the return from "
            "statsmodels.stats.diagnostic.recursive_olsresiduals with skip None, "
            "lamda 0, alpha 0.95 and order_by None."
        ),
        (
            "The comparison drops the first returned cumulative-sum point and uses "
            "the returned boundary, whose step index starts at 0."
        ),
        "A crossing is a cumulative sum strictly outside that boundary.",
    ]
    if excluded:
        assumptions.append(
            "Growth months outside the longest contiguous run were left out. "
            "Gaps were not interpolated.",
        )
    return tuple(assumptions)


def _limitations() -> tuple[str, ...]:
    return (
        "Publication allowed is false.",
        "The input is latest revised log-growth. This is not a real-time stability test.",
        "The lag is predeclared. The diagnostic does not choose another lag.",
        NO_BREAK_DATE,
        "Staying inside the boundary is a result, as is crossing it.",
        "A Chow test is not estimated.",
        "A Bai-Perron mean shift is not estimated.",
        "A local projection is not estimated.",
        NO_CAUSAL_CLAIM,
    )


def _interpretation(calculation: Mapping[str, object]) -> str:
    if calculation["crosses_five_percent_boundary"] is True:
        decision = "crosses"
    else:
        decision = "stays inside"
    return (
        f"The CUSUM of recursive residuals {decision} the five percent boundary. "
        f"The largest absolute CUSUM is {calculation['maximum_absolute_cusum']} "
        f"in {calculation['extreme_period']}, where the boundary is "
        f"{calculation['boundary_at_extreme']}. "
        f"The autoregression uses predeclared lag {PREDECLARED_LAG} and a constant. "
        f"{NO_BREAK_DATE} {NO_CAUSAL_CLAIM}"
    )


def _narrative(calculation: Mapping[str, object]) -> str:
    if calculation["crosses_five_percent_boundary"] is True:
        decision = "crosses"
    else:
        decision = "stays inside"
    return (
        "CUSUM of recursive residuals for the industrial-production log-growth "
        f"autoregression. The path {decision} the five percent boundary. "
        f"{NO_BREAK_DATE} Publication allowed is false."
    )


def _insufficient(reason: str) -> MethodExecutionResult:
    return MethodExecutionResult(
        sufficiency="insufficient",
        calculation={
            "method_id": IP_GROWTH_CUSUM,
            "publication_allowed": PUBLICATION_ALLOWED,
            "transformation": "monthly_log_growth",
            "predeclared_lag": PREDECLARED_LAG,
            "chow_test": False,
            "bai_perron_mean_shift": False,
            "local_projection": False,
            "selected_break_date": None,
        },
        observation_ids=(),
        assumptions=(
            "The modelled series would have been monthly log-growth with predeclared lag 1.",
        ),
        limitations=("Publication allowed is false.", NO_BREAK_DATE),
        missing_reason=reason,
        statistical_interpretation="The CUSUM was not computed.",
        causal_hypothesis="none",
        investment_implication="insufficient_evidence",
        narrative=f"Industrial-production CUSUM incomplete. Reason: {reason}",
    )
