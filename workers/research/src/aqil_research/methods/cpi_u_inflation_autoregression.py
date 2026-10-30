"""CPI-U inflation autoregression and an ordinary least squares persistence summary.

Predeclared specification
-------------------------
Series: ``bls.cu.CUSR0000SA0`` (CPI-U, seasonally adjusted, 1982-84=100).
Vintage: ``latest_revised`` only. This is not a real-time claim.
Transformation: the monthly natural log change of adjacent positive levels.
    Gaps are not filled. The longest contiguous monthly run is used.
Model: AR(p) with a constant, estimated by ordinary least squares.
Lag: chosen by AIC over p = 1, ..., 12. The maximum lag is 12.
    Every candidate is estimated on the common sample that starts after
    observation 12, so the information criterion compares the same rows.
    Ties keep the smaller lag. An intercept-only model is not a candidate.
AIC formula on that common sample: n * log(RSS / n) + 2 * (p + 1).
Persistence: the sum of the OLS autoregressive coefficients, excluding the
    intercept. Andrews and Chen (1994) are the literature for summarising
    persistence by that sum. This figure is the ordinary least squares sum.
    It is not the Andrews–Chen median-unbiased estimator.
Forecast qualification: none. No historical-mean comparison is computed, so
    the result is not empirically qualified as a forecast.
Publication: ``publication_allowed`` is false. The investment implication is
    ``no_action`` when the regression is estimated, otherwise
    ``insufficient_evidence``.

Library check, statsmodels 0.15.0 and NumPy 2.5.4 as locked in ``uv.lock``
---------------------------------------------------------------------------
``AutoReg.fit`` estimates parameters with ``statsmodels`` ``OLS``.
The default trend is ``"c"`` (a constant). The default ``hold_back`` is the
model's own maximum lag. ``ar_select_order`` defaults to ``ic="bic"``, also
scores an intercept-only model, and, when ``hold_back`` is left unset, refits
the chosen lag on the longer lag-specific sample. Those defaults are not this
specification. Coefficients reported here are the common-sample OLS estimates.
``AutoRegResults.aic`` adds ``n * (log(2 * pi) + 1)`` to
``n * log(RSS / n) + 2 * (p + 1)``. On a common sample that constant does not
change the selected lag.

This is not the twelve-month percent-change rank in ``prices_and_policy``.
"""

from __future__ import annotations

import hashlib
import math
import warnings
from collections.abc import Mapping
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
from aqil_research.methods.parameters import MethodParameterDocument
from aqil_research.methods.prices_and_policy import CPI_DATASET_ID, CPI_UNIT
from aqil_research.methods.protocol import (
    MethodContext,
    MethodDependency,
    MethodExecutionResult,
    bind_dependency,
)

CPI_U_INFLATION_AUTREGRESSION = "CPI_U_INFLATION_AUTREGRESSION"
METHOD_VERSION = "1.0.0"
PUBLICATION_ALLOWED = False

MAX_LAG = 12
# Common-sample rows are T - 12. AR(12) has 13 coefficients, so T - 12 >= 14
# and T >= 26. That is the minimum this module enforces.
MINIMUM_GROWTH_MONTHS = MAX_LAG + MAX_LAG + 2
COEFFICIENT_DIGITS = 8
AIC_DIGITS = 6

LOCKED_STATSMODELS = "0.15.0"
LOCKED_NUMPY = "2.5.4"

QUALIFICATION_STATEMENT = (
    "Not empirically qualified as a forecast. "
    "No predeclared historical-mean comparison was computed."
)
ANDREWS_CHEN_NOTE = (
    "Andrews and Chen (1994) are the literature for summarising persistence "
    "by the sum of the autoregressive coefficients. The stored figure is the "
    "ordinary least squares sum. It is not the Andrews–Chen median-unbiased estimator."
)

PUBLISHED_CONFIG = {
    "config_id": "cpi-u-inflation-autoregression-v1",
    "label": "CPI-U monthly log-change autoregression and OLS persistence",
}


class CpiUInflationAutoregressionConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    config_id: str = Field(min_length=1)
    label: str = Field(min_length=1)


class LogChangeSample:
    """Contiguous monthly log changes and the levels that produced them."""

    __slots__ = ("excluded_growth_months", "growth_months", "level_months", "values")

    def __init__(
        self,
        growth_months: tuple[date, ...],
        values: tuple[float, ...],
        level_months: tuple[date, ...],
        excluded_growth_months: int,
    ) -> None:
        self.growth_months = growth_months
        self.values = values
        self.level_months = level_months
        self.excluded_growth_months = excluded_growth_months


def implementation_hash() -> str:
    payload = "|".join(
        (
            CPI_U_INFLATION_AUTREGRESSION,
            METHOD_VERSION,
            "monthly-log-change",
            "ols",
            "aic",
            f"max-lag-{MAX_LAG}",
            f"min-growth-{MINIMUM_GROWTH_MONTHS}",
            "common-sample-after-max-lag",
            "lags-1-through-12",
            "smaller-lag-on-a-tie",
            "persistence-ols-sum",
            "not-andrews-chen-median-unbiased",
            "no-historical-mean-comparison",
            "latest-revised",
        ),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def previous_month(month_start: date) -> date:
    if month_start.month == 1:
        return date(month_start.year - 1, 12, 1)
    return date(month_start.year, month_start.month - 1, 1)


def next_month(month_start: date) -> date:
    if month_start.month == 12:
        return date(month_start.year + 1, 1, 1)
    return date(month_start.year, month_start.month + 1, 1)


def persistence_sum(coefficients: np.ndarray) -> float:
    """Sum of the autoregressive coefficients. The intercept is column 0."""
    if coefficients.size < 2:
        raise ValueError("an autoregression needs an intercept and at least one lag")
    return float(np.sum(coefficients[1:]))


def ols_ar_coefficients(
    growth: np.ndarray,
    lag: int,
    *,
    sample_start: int,
) -> np.ndarray:
    """OLS of an AR(lag) with a constant. Column 0 is the intercept.

    ``sample_start`` is the first target index. It must be at least ``lag``.
    """
    design, target = _design(growth, lag, sample_start, int(growth.size))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        fitted = OLS(target, design).fit()
    coefficients = np.asarray(fitted.params, dtype=float)
    if coefficients.shape != (lag + 1,) or not np.all(np.isfinite(coefficients)):
        raise ValueError("autoregressive coefficients are not finite")
    return coefficients


def select_ar_lag_by_aic(growth: np.ndarray) -> tuple[int, np.ndarray, float]:
    """AIC on the common sample. Ties keep the smaller lag. Maximum lag is 12."""
    values = np.asarray(growth, dtype=float)
    if int(values.size) < MINIMUM_GROWTH_MONTHS or not np.all(np.isfinite(values)):
        raise ValueError("the log-change sample is shorter than the predeclared minimum")
    best_lag: int | None = None
    best_aic = math.inf
    best_coefficients: np.ndarray | None = None
    sample_size = int(values.size) - MAX_LAG
    for lag in range(1, MAX_LAG + 1):
        try:
            coefficients, rss = _fit_common_sample(values, lag)
        except ValueError:
            continue
        aic = _aic_value(rss, sample_size, lag)
        if aic < best_aic:
            best_aic = aic
            best_lag = lag
            best_coefficients = coefficients
    if best_lag is None or best_coefficients is None:
        raise ValueError("autoregressive coefficients are not finite")
    return best_lag, best_coefficients, best_aic


def autoregression_from_log_changes(growth: np.ndarray) -> dict[str, object]:
    """Fit the predeclared AR on one monthly log-change series."""
    values = np.asarray(growth, dtype=float)
    if int(values.size) < MINIMUM_GROWTH_MONTHS or not np.all(np.isfinite(values)):
        return _insufficient_payload(
            "The monthly log-change sample is shorter than the predeclared "
            f"minimum of {MINIMUM_GROWTH_MONTHS} months.",
        )
    try:
        lag, coefficients, aic = select_ar_lag_by_aic(values)
    except ValueError:
        return _insufficient_payload("The autoregression did not return finite coefficients.")
    phis = [float(coefficients[index]) for index in range(1, lag + 1)]
    persistence = persistence_sum(coefficients)
    return {
        "sufficient": True,
        "method_id": CPI_U_INFLATION_AUTREGRESSION,
        "publication_allowed": PUBLICATION_ALLOWED,
        "real_time_claim": False,
        "product_forecast": False,
        "empirically_qualified_as_forecast": False,
        "qualification_statement": QUALIFICATION_STATEMENT,
        "input_vintage": "latest_revised",
        "dataset_id": CPI_DATASET_ID,
        "modelled_transformation": "monthly_log_change",
        "estimator": "ols",
        "trend": "constant",
        "persistence_estimator": "ols_sum_of_ar_coefficients",
        "andrews_chen_median_unbiased": False,
        "andrews_chen_1994": ANDREWS_CHEN_NOTE,
        "growth_month_count": int(values.size),
        "common_sample_rows": int(values.size) - MAX_LAG,
        "aic_lag": lag,
        "aic": None if not math.isfinite(aic) else _rounded(aic, AIC_DIGITS),
        "intercept": _rounded(float(coefficients[0]), COEFFICIENT_DIGITS),
        "ar_coefficients": [
            {"lag": index, "coefficient": _rounded(phi, COEFFICIENT_DIGITS)}
            for index, phi in enumerate(phis, start=1)
        ],
        "persistence": _rounded(persistence, COEFFICIENT_DIGITS),
        "predeclared": _predeclared(),
        "library_defaults": _library_defaults(),
    }


def contiguous_monthly_log_changes(levels: Mapping[date, float]) -> LogChangeSample:
    """Natural log difference of adjacent positive levels. Gaps are not filled."""
    eligible = {
        month: value
        for month, value in levels.items()
        if month.day == 1 and math.isfinite(value) and value > 0
    }
    candidates: list[tuple[date, float]] = []
    for month in sorted(eligible):
        prior = previous_month(month)
        prior_value = eligible.get(prior)
        if prior_value is None:
            continue
        candidates.append((month, math.log(eligible[month]) - math.log(prior_value)))
    if not candidates:
        return LogChangeSample((), (), (), 0)
    chosen = _longest_run([month for month, _value in candidates])
    chosen_set = set(chosen)
    values = tuple(value for month, value in candidates if month in chosen_set)
    months = tuple(chosen)
    level_months = (previous_month(months[0]), *months)
    return LogChangeSample(
        growth_months=months,
        values=values,
        level_months=level_months,
        excluded_growth_months=len(candidates) - len(months),
    )


class CpiUInflationAutoregressionMethod:
    """CPI-U monthly log-change autoregression.

    Registration, inside ``default_method_registry``::

        registry.register(CpiUInflationAutoregressionMethod())
    """

    method_id = CPI_U_INFLATION_AUTREGRESSION
    method_version = METHOD_VERSION

    def implementation_hash(self) -> str:
        return implementation_hash()

    def required_dataset_ids(self) -> tuple[str, ...]:
        return (CPI_DATASET_ID,)

    def dependency(self) -> MethodDependency:
        return bind_dependency(
            self.required_dataset_ids(),
            frequency=("monthly",),
            minimum_history=(
                f"{MINIMUM_GROWTH_MONTHS} contiguous monthly log changes "
                f"({MINIMUM_GROWTH_MONTHS + 1} CPI-U levels)"
            ),
            parameter_policy="none",
            new_observation_requires_recalculation=True,
            refit_is_different_command=False,
        )

    def accepted_config_payload(self) -> dict[str, object]:
        return dict(PUBLISHED_CONFIG)

    def parse_config(self, payload: dict[str, object]) -> CpiUInflationAutoregressionConfig:
        return CpiUInflationAutoregressionConfig.model_validate(payload)

    def config_hash(self, config: BaseModel) -> str:
        if not isinstance(config, CpiUInflationAutoregressionConfig):
            raise TypeError("expected CpiUInflationAutoregressionConfig")
        return MethodParameterDocument(
            config_id=config.config_id,
            label=config.label,
            scalars={
                "transformation": "monthly_log_change",
                "estimator": "ols",
                "information_criterion": "aic",
                "max_lag": str(MAX_LAG),
                "minimum_growth_months": str(MINIMUM_GROWTH_MONTHS),
                "persistence": "ols_sum_of_ar_coefficients",
            },
        ).config_hash()

    def run(self, context: MethodContext, config: BaseModel) -> MethodExecutionResult:
        if not isinstance(config, CpiUInflationAutoregressionConfig):
            raise TypeError("expected CpiUInflationAutoregressionConfig")
        if context.analysis_mode != AnalysisMode.LATEST_REVISED:
            return _insufficient(
                "These levels are dated on latest_revised observations. "
                "A point-in-time request was not dated.",
            )
        series = context.inputs_by_dataset.get(CPI_DATASET_ID)
        if not series:
            return _insufficient("No latest-revised CPI-U observations were available.")
        series = {
            period: row for period, row in series.items() if period <= context.evaluation_period
        }
        levels = _eligible_levels(series)
        if not levels:
            return _insufficient("No eligible latest-revised CPI-U level was available.")
        sample = contiguous_monthly_log_changes(levels)
        if len(sample.values) < MINIMUM_GROWTH_MONTHS:
            return _insufficient(
                "The contiguous monthly log-change sample is shorter than the "
                f"predeclared minimum of {MINIMUM_GROWTH_MONTHS} months.",
            )
        calculation = autoregression_from_log_changes(np.asarray(sample.values, dtype=float))
        if calculation.get("sufficient") is not True:
            reason = calculation.get("reason")
            return _insufficient(
                reason if isinstance(reason, str) else "The autoregression was not computed.",
            )
        calculation["growth_start"] = sample.growth_months[0].isoformat()
        calculation["growth_end"] = sample.growth_months[-1].isoformat()
        calculation["excluded_growth_months"] = sample.excluded_growth_months
        observation_ids = tuple(
            series[month].observation_id for month in sample.level_months if month in series
        )
        return MethodExecutionResult(
            sufficiency="sufficient",
            calculation=calculation,
            observation_ids=observation_ids,
            assumptions=_assumptions(sample),
            limitations=_limitations(),
            missing_reason=None,
            statistical_interpretation=_interpretation(calculation),
            causal_hypothesis="none",
            investment_implication="no_action",
            narrative=_narrative(calculation),
        )


def _predeclared() -> dict[str, object]:
    return {
        "max_lag": MAX_LAG,
        "minimum_growth_months": MINIMUM_GROWTH_MONTHS,
        "lags_considered": "1 through 12",
        "information_criterion": "aic",
        "aic_formula": "n * log(rss / n) + 2 * (p + 1)",
        "common_sample": True,
        "common_sample_starts_after_lag": MAX_LAG,
        "tie_rule": "smaller_lag",
        "trend": "constant",
        "estimator": "ols",
        "persistence": "sum of the OLS autoregressive coefficients, excluding the intercept",
    }


def _library_defaults() -> dict[str, object]:
    return {
        "statsmodels": LOCKED_STATSMODELS,
        "numpy": LOCKED_NUMPY,
        "autoreg_fit_estimator": "OLS",
        "autoreg_default_trend": "c",
        "ar_select_order_default_ic": "bic",
        "specification_uses_default_ar_select_order": False,
        "reported_coefficients": "ols_on_the_common_sample",
    }


def _design(
    growth: np.ndarray,
    lag: int,
    start: int,
    end: int,
) -> tuple[np.ndarray, np.ndarray]:
    if lag < 1 or lag > MAX_LAG or start < lag or end <= start:
        raise ValueError("the autoregressive sample is too short")
    row_count = end - start
    design = np.empty((row_count, lag + 1), dtype=float)
    design[:, 0] = 1.0
    for index in range(1, lag + 1):
        design[:, index] = growth[start - index : end - index]
    return design, growth[start:end]


def _fit_common_sample(growth: np.ndarray, lag: int) -> tuple[np.ndarray, float]:
    design, target = _design(growth, lag, MAX_LAG, int(growth.size))
    coefficients = ols_ar_coefficients(growth, lag, sample_start=MAX_LAG)
    residuals = target - design @ coefficients
    rss = float(residuals @ residuals)
    if not math.isfinite(rss):
        raise ValueError("the residual sum of squares is not finite")
    return coefficients, rss


def _aic_value(rss: float, sample_size: int, lag: int) -> float:
    """AIC = n log(RSS/n) + 2(p+1) on the common sample."""
    if sample_size <= lag + 1 or not math.isfinite(rss) or rss < 0:
        return math.inf
    if rss == 0:
        return -math.inf
    return sample_size * math.log(rss / sample_size) + 2 * (lag + 1)


def _rounded(value: float, digits: int) -> float:
    rounded = round(float(value), digits)
    if rounded == 0:
        return 0.0
    return rounded


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
        observation.dataset_id == CPI_DATASET_ID
        and observation.series_provenance == SeriesProvenance.LATEST_REVISED
        and observation.quality_status == QualityStatus.OBSERVED
        and observation.frequency == Frequency.MONTHLY
        and observation.seasonal_adjustment == SeasonalAdjustment.SEASONALLY_ADJUSTED
        and observation.unit == CPI_UNIT
        and observation.period_start.day == 1
    )


def _assumptions(sample: LogChangeSample) -> tuple[str, ...]:
    assumptions = [
        "The modelled series is the monthly natural log change of adjacent CPI-U levels.",
        "The input is latest_revised. It is not a real-time vintage.",
        (
            "Lag order is chosen by AIC on a common sample that starts after the "
            f"maximum lag of {MAX_LAG}. Candidates are AR(1) through AR(12). "
            "Ties keep the smaller lag."
        ),
        "The regression is ordinary least squares with a constant.",
        ANDREWS_CHEN_NOTE,
        QUALIFICATION_STATEMENT,
    ]
    if sample.excluded_growth_months:
        assumptions.append(
            "Log-change months outside the longest contiguous run were left out. "
            "Gaps were not interpolated.",
        )
    return tuple(assumptions)


def _limitations() -> tuple[str, ...]:
    return (
        "Publication allowed is false.",
        "The reading uses today's revised CPI-U file and is not a real-time claim.",
        QUALIFICATION_STATEMENT,
        ANDREWS_CHEN_NOTE,
        "The autoregressive polynomial is not constrained to be stationary.",
        "This is not the twelve-month percent-change rank of CPI-U.",
    )


def _interpretation(calculation: Mapping[str, object]) -> str:
    lag = calculation["aic_lag"]
    persistence = calculation["persistence"]
    return (
        f"The monthly log change of CPI-U is an AR({lag}) chosen by AIC "
        f"with a maximum lag of {MAX_LAG}. "
        f"The ordinary least squares sum of the autoregressive coefficients is {persistence}. "
        f"{ANDREWS_CHEN_NOTE} {QUALIFICATION_STATEMENT}"
    )


def _narrative(calculation: Mapping[str, object]) -> str:
    lag = calculation["aic_lag"]
    persistence = calculation["persistence"]
    return (
        "CPI-U monthly log-change autoregression on the latest revised index. "
        f"AIC selects lag {lag}. "
        f"The ordinary least squares persistence summary is {persistence}. "
        f"{QUALIFICATION_STATEMENT} Publication allowed is false."
    )


def _insufficient_payload(reason: str) -> dict[str, object]:
    return {
        "sufficient": False,
        "reason": reason,
        "method_id": CPI_U_INFLATION_AUTREGRESSION,
        "publication_allowed": PUBLICATION_ALLOWED,
        "real_time_claim": False,
        "product_forecast": False,
        "empirically_qualified_as_forecast": False,
        "qualification_statement": QUALIFICATION_STATEMENT,
        "andrews_chen_median_unbiased": False,
        "persistence_estimator": "ols_sum_of_ar_coefficients",
    }


def _insufficient(reason: str) -> MethodExecutionResult:
    return MethodExecutionResult(
        sufficiency="insufficient",
        calculation={
            "method_id": CPI_U_INFLATION_AUTREGRESSION,
            "publication_allowed": PUBLICATION_ALLOWED,
            "real_time_claim": False,
            "product_forecast": False,
            "empirically_qualified_as_forecast": False,
            "qualification_statement": QUALIFICATION_STATEMENT,
            "andrews_chen_median_unbiased": False,
            "dataset_id": CPI_DATASET_ID,
            "input_vintage": "latest_revised",
        },
        observation_ids=(),
        assumptions=(
            "The modelled series would have been the monthly log change of CPI-U.",
            ANDREWS_CHEN_NOTE,
        ),
        limitations=_limitations(),
        missing_reason=reason,
        statistical_interpretation="The CPI-U inflation autoregression was not computed.",
        causal_hypothesis="none",
        investment_implication="insufficient_evidence",
        narrative=f"CPI-U inflation autoregression incomplete. Reason: {reason}",
    )
