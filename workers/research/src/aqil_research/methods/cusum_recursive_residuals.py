"""CUSUM of recursive residuals for one industrial-production autoregression.

The series is the monthly natural log-growth of ``fed.g17.IP.B50001.S``,
from ``contiguous_monthly_log_growth`` in the autoregressive benchmark.
That module is not modified, and its lag is not selected again.

The autoregressive benchmark chooses a lag by AIC. The chosen lag is not a
constant in that module, so this diagnostic predeclares lag 12. That is the
benchmark's maximum lag, not a second selected model.

The regression is

    g_t = c + φ_1 g_{t-1} + ... + φ_12 g_{t-12} + e_t

with a column of ones. Recursive residuals follow Brown, Durbin and Evans
(1975): one-step prediction errors scaled by the leverage factor, starting
after the first 13 rows. No ridge term is added. The scale is the unbiased
standard deviation of those recursive residuals, the same divisor
statsmodels uses for ``rresid_scaled[skip:]`` when ``lamda`` is 0.

The CUSUM is the cumulative sum of the standardised one-step residuals.
The five percent boundary at step j, with j starting at 1, is

    0.948 * sqrt(n) + 2 * 0.948 * j / sqrt(n).

``statsmodels.stats.diagnostic.recursive_olsresiduals`` returns a CUSUM that
starts with the initial in-sample residual and a boundary whose step index
starts at 0. This method does not use that returned CUSUM. A crossing is an
absolute CUSUM strictly outside the boundary above. Staying inside is also
a result. No break date is selected.

``publication_allowed`` stays false.
"""

from __future__ import annotations

import hashlib
import math
from collections.abc import Mapping, Sequence
from datetime import date

import numpy as np
from pydantic import BaseModel, ConfigDict, Field
from statsmodels.regression.linear_model import OLS

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

CUSUM_RECURSIVE_RESIDUALS = "CUSUM_RECURSIVE_RESIDUALS"
METHOD_VERSION = "1.0.0"
PUBLICATION_ALLOWED = False

# The benchmark's AIC lag is computed from the sample. It is not a constant.
PREDECLARED_LAG = 12
BOUNDARY_COEFFICIENT = 0.948
BOUNDARY_SIGNIFICANCE = 0.05
REGRESSOR_COUNT = PREDECLARED_LAG + 1
MINIMUM_GROWTH_MONTHS = PREDECLARED_LAG + 2 * REGRESSOR_COUNT
BOUNDARY_SOURCE = "Brown, Durbin and Evans (1975) five percent CUSUM boundary"
NOT_A_BREAK_CATALOGUE = "No break date is selected."
NO_CAUSAL_CLAIM = "No causal mechanism is established."

PUBLISHED_CONFIG = {
    "config_id": "cusum-recursive-residuals-v1",
    "label": "CUSUM of the industrial production log-growth autoregression",
}


class CusumRecursiveResidualsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    config_id: str = Field(min_length=1)
    label: str = Field(min_length=1)


def implementation_hash() -> str:
    payload = "|".join(
        (
            CUSUM_RECURSIVE_RESIDUALS,
            METHOD_VERSION,
            "monthly-log-growth",
            f"predeclared-lag-{PREDECLARED_LAG}",
            "ols-with-constant",
            "brown-durbin-evans-one-step",
            "no-ridge",
            f"boundary-{BOUNDARY_COEFFICIENT}",
            "boundary-step-starts-at-1",
            "variance-ddof-1",
            "no-break-date-selection",
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


def recursive_residuals(design: np.ndarray, target: np.ndarray) -> np.ndarray:
    """One-step Brown-Durbin-Evans residuals. The first k rows only initialise.

    ``k`` is the number of columns, including the constant. The initial
    inverse has no ridge term. Later rows update that inverse. The returned
    residuals exclude the in-sample residual of the initial block.
    """

    exog = np.asarray(design, dtype=np.float64)
    endog = np.asarray(target, dtype=np.float64)
    if exog.ndim != 2 or endog.ndim != 1 or exog.shape[0] != endog.shape[0]:
        raise ValueError("the design and the target must have the same number of rows")
    nobs, nvars = exog.shape
    if nobs <= nvars:
        raise ValueError("recursive residuals need more rows than regressors")
    if not np.all(exog[:, 0] == 1.0):
        raise ValueError("column 0 must be the constant")
    initial = exog[:nvars]
    if int(np.linalg.matrix_rank(initial)) < nvars:
        raise ValueError("the initial regressor block is singular")
    xtxi = np.linalg.inv(initial.T @ initial)
    beta = xtxi @ (initial.T @ endog[:nvars])
    scaled = np.empty(nobs - nvars, dtype=np.float64)
    for offset, row in enumerate(range(nvars, nobs)):
        xi = exog[row]
        tmp = xtxi @ xi
        ft = 1.0 + float(xi @ tmp)
        if ft <= 0.0 or not math.isfinite(ft):
            raise ValueError("the recursive leverage is not positive")
        residi = float(endog[row] - xi @ beta)
        scaled[offset] = residi / math.sqrt(ft)
        xtxi = xtxi - np.outer(tmp, tmp) / ft
        beta = beta + tmp * (residi / ft)
    if not np.isfinite(scaled).all():
        raise ValueError("a recursive residual is not finite")
    return scaled


def conventional_boundary(residual_count: int) -> np.ndarray:
    """Five percent boundary with the step index starting at 1."""

    if residual_count < 2:
        raise ValueError("the CUSUM needs at least two recursive residuals")
    steps = np.arange(1, residual_count + 1, dtype=np.float64)
    width = math.sqrt(residual_count)
    return BOUNDARY_COEFFICIENT * width + (2.0 * BOUNDARY_COEFFICIENT * steps / width)


def cusum_from_growth(growth: Sequence[float]) -> dict[str, object]:
    """CUSUM for the predeclared lag. Crossing and not crossing are both results."""

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
    scaled = recursive_residuals(design, target)
    if scaled.size < 2:
        raise ValueError("the CUSUM needs at least two recursive residuals")
    sigma2 = float(scaled.var(ddof=1))
    if not math.isfinite(sigma2) or sigma2 <= 0.0:
        raise ValueError("the recursive-residual variance is not positive")
    sigma = math.sqrt(sigma2)
    cusum = np.cumsum(scaled / sigma)
    boundary = conventional_boundary(int(scaled.size))
    excess = np.abs(cusum) - boundary
    crosses = bool(np.any(excess > 0.0))
    extreme = int(np.argmax(np.abs(cusum)))
    return {
        "scaled_residuals": scaled,
        "cusum": cusum,
        "boundary": boundary,
        "crosses_conventional_boundary": crosses,
        "extreme_index": extreme,
        "extreme_cusum": float(cusum[extreme]),
        "extreme_boundary": float(boundary[extreme]),
        "sigma": sigma,
        "coefficients": coefficients,
        "regression_row_count": int(design.shape[0]),
    }


class CusumRecursiveResidualsMethod:
    """Parameter-stability diagnostic for the predeclared production autoregression."""

    method_id = CUSUM_RECURSIVE_RESIDUALS
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
                f"{MINIMUM_GROWTH_MONTHS} contiguous monthly log-growth observations, "
                f"so an autoregression of lag {PREDECLARED_LAG} with a constant has "
                "an initial block and at least as many recursive residuals"
            ),
            parameter_policy="none",
            new_observation_requires_recalculation=True,
            refit_is_different_command=False,
        )

    def accepted_config_payload(self) -> dict[str, object]:
        return dict(PUBLISHED_CONFIG)

    def parse_config(self, payload: dict[str, object]) -> CusumRecursiveResidualsConfig:
        return CusumRecursiveResidualsConfig.model_validate(payload)

    def config_hash(self, config: BaseModel) -> str:
        if not isinstance(config, CusumRecursiveResidualsConfig):
            raise TypeError("expected CusumRecursiveResidualsConfig")
        return MethodParameterDocument(
            config_id=config.config_id,
            label=config.label,
            scalars={
                "transformation": "monthly_log_growth",
                "predeclared_lag": str(PREDECLARED_LAG),
                "regression": "constant_plus_lags",
                "cusum": "brown_durbin_evans_recursive_residuals",
                "boundary": f"{BOUNDARY_COEFFICIENT}_five_percent",
            },
        ).config_hash()

    def run(self, context: MethodContext, config: BaseModel) -> MethodExecutionResult:
        if not isinstance(config, CusumRecursiveResidualsConfig):
            raise TypeError("expected CusumRecursiveResidualsConfig")
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
            causal_hypothesis=NO_CAUSAL_CLAIM,
            investment_implication="no_action",
            narrative=_narrative(calculation),
        )


def _calculation(
    estimated: Mapping[str, object],
    growth_months: Sequence[date],
    excluded: int,
) -> dict[str, object]:
    cusum = estimated["cusum"]
    if not isinstance(cusum, np.ndarray):
        raise TypeError("expected the CUSUM path")
    start_index = 2 * PREDECLARED_LAG + 1
    end_index = start_index + int(cusum.size) - 1
    if end_index != len(growth_months) - 1:
        raise RuntimeError("the CUSUM does not end on the last growth month")
    extreme = int(estimated["extreme_index"])
    extreme_month = growth_months[start_index + extreme]
    coefficients = estimated["coefficients"]
    if not isinstance(coefficients, np.ndarray):
        raise TypeError("expected the full-sample coefficients")
    crosses = estimated["crosses_conventional_boundary"] is True
    return {
        "sufficient": True,
        "method_id": CUSUM_RECURSIVE_RESIDUALS,
        "publication_allowed": PUBLICATION_ALLOWED,
        "input_vintage": "latest_revised",
        "dataset_id": INDUSTRIAL_PRODUCTION_DATASET_ID,
        "transformation": "monthly_log_growth",
        "transformation_function": "contiguous_monthly_log_growth",
        "predeclared_lag": PREDECLARED_LAG,
        "lag_was_selected_by_aic": False,
        "lag_declaration": (
            "Lag 12 is predeclared. The autoregressive benchmark selects its lag "
            "by AIC, and that selected lag is not a constant in code."
        ),
        "constant_included": True,
        "constant_column": "first",
        "regressor_count": REGRESSOR_COUNT,
        "selected_break_date": None,
        "growth_start": growth_months[0].isoformat(),
        "growth_end": growth_months[-1].isoformat(),
        "growth_month_count": len(growth_months),
        "excluded_growth_months": excluded,
        "regression_row_count": int(estimated["regression_row_count"]),
        "recursive_residual_count": int(cusum.size),
        "cusum_start": growth_months[start_index].isoformat(),
        "cusum_end": growth_months[end_index].isoformat(),
        "boundary_coefficient": BOUNDARY_COEFFICIENT,
        "boundary_significance": BOUNDARY_SIGNIFICANCE,
        "boundary_source": BOUNDARY_SOURCE,
        "boundary_step_starts_at": 1,
        "statsmodels_returned_cusum_used": False,
        "crosses_conventional_boundary": crosses,
        "maximum_absolute_cusum": _figure(abs(float(estimated["extreme_cusum"]))),
        "extreme_cusum": _figure(float(estimated["extreme_cusum"])),
        "boundary_at_extreme": _figure(float(estimated["extreme_boundary"])),
        "extreme_period": extreme_month.isoformat(),
        "recursive_residual_sigma": _figure(float(estimated["sigma"])),
        "full_sample_constant": _figure(float(coefficients[0])),
        "full_sample_lag_coefficients": [_figure(float(value)) for value in coefficients[1:]],
        "full_sample_coefficient_role": (
            "Coefficients of the predeclared regression whose stability is being tested. "
            "They are not a selected forecasting model."
        ),
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
        "The modelled series is the monthly natural log-growth from the autoregressive benchmark.",
        (
            f"The lag is predeclared at {PREDECLARED_LAG}. "
            "The benchmark's AIC lag is not a constant, so it is not reused."
        ),
        "The regression includes a constant in the first column and then the twelve lags.",
        (
            "Recursive residuals are one-step Brown, Durbin and Evans residuals. "
            "The initial block has one row per regressor. No ridge term is added."
        ),
        "The scale is the unbiased standard deviation of those recursive residuals.",
        (
            f"The five percent boundary uses {BOUNDARY_COEFFICIENT} "
            "and a step index that starts at 1."
        ),
        "A crossing is an absolute CUSUM strictly outside that boundary.",
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
        (
            "Lag 12 is predeclared because the benchmark's selected lag is not a constant. "
            "This diagnostic does not choose another lag."
        ),
        NOT_A_BREAK_CATALOGUE,
        "Staying inside the boundary is a result, as is crossing it.",
        "The full-sample coefficients describe the regression under test. They are not a forecast.",
        NO_CAUSAL_CLAIM,
    )


def _interpretation(calculation: Mapping[str, object]) -> str:
    if calculation["crosses_conventional_boundary"] is True:
        decision = "crosses"
    else:
        decision = "does not cross"
    return (
        f"The CUSUM of recursive residuals {decision} the five percent boundary. "
        f"The largest absolute CUSUM is {calculation['maximum_absolute_cusum']} "
        f"in {calculation['extreme_period']}, where the boundary is "
        f"{calculation['boundary_at_extreme']}. "
        f"The autoregression uses predeclared lag {PREDECLARED_LAG} and a constant. "
        f"{NOT_A_BREAK_CATALOGUE} {NO_CAUSAL_CLAIM}"
    )


def _narrative(calculation: Mapping[str, object]) -> str:
    if calculation["crosses_conventional_boundary"] is True:
        decision = "crosses"
    else:
        decision = "does not cross"
    return (
        "CUSUM of recursive residuals for the predeclared industrial-production "
        f"log-growth autoregression. The path {decision} the five percent boundary. "
        f"{NOT_A_BREAK_CATALOGUE} Publication allowed is false."
    )


def _insufficient(reason: str) -> MethodExecutionResult:
    return MethodExecutionResult(
        sufficiency="insufficient",
        calculation={
            "method_id": CUSUM_RECURSIVE_RESIDUALS,
            "publication_allowed": PUBLICATION_ALLOWED,
            "transformation": "monthly_log_growth",
            "predeclared_lag": PREDECLARED_LAG,
            "lag_was_selected_by_aic": False,
            "selected_break_date": None,
        },
        observation_ids=(),
        assumptions=(
            "The modelled series would have been monthly log-growth with predeclared lag 12.",
        ),
        limitations=("Publication allowed is false.", NOT_A_BREAK_CATALOGUE),
        missing_reason=reason,
        statistical_interpretation="The CUSUM was not computed.",
        causal_hypothesis=NO_CAUSAL_CLAIM,
        investment_implication="insufficient_evidence",
        narrative=f"CUSUM incomplete. Reason: {reason}",
    )
