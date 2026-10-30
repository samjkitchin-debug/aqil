"""Engle-Granger cointegration of industrial production and payroll employment.

Both series enter as natural logarithms of latest-revised levels:
``fed.g17.IP.B50001.S`` and ``bls.ce.CES0000000001``. The normalisation is
predeclared. Log industrial production is the left-hand side. Log payroll
employment is the right-hand side, with a constant. That ordering is not a
causal ordering.

The named procedure is ``statsmodels.tsa.stattools.coint`` (statsmodels
0.15). The call is::

    coint(
        log_industrial_production,
        log_payroll_employment,
        trend="c",
        method="aeg",
        maxlag=residual_adf_max_lag(n),
        autolag="aic",
        return_results=False,
    )

``trend="c"``, ``method="aeg"`` and ``autolag="aic"`` are the statsmodels
defaults. ``method="aeg"`` is the augmented Engle-Granger two-step test:
ordinary least squares with the requested trend, then an augmented
Dickey-Fuller test on the residual. Inside ``coint`` the residual regression
is ``regression="n"`` (no constant and no trend), and the p-value and
critical values are the MacKinnon response surface for the number of series
and the first-stage trend. ``return_results=False`` keeps the tuple return.

``maxlag=None`` is the statsmodels default. Passing ``None`` makes
``adfuller`` use the Schwert ceiling below. This method passes that ceiling
explicitly so the lag rule is part of the method. For these samples the
explicit ceiling matches ``maxlag=None``.

The null is no cointegration. The predeclared size is five percent. The
test rejects when the returned statistic is strictly below the five percent
critical value from ``coint``. A failure to reject is stored as the result.

The result describes co-movement in revised log levels. Granger causality
on growth rates is not estimated. A vector autoregression is not estimated.
No causal claim is made. ``publication_allowed`` stays false.
"""

from __future__ import annotations

import hashlib
import math
from collections.abc import Mapping, Sequence
from datetime import date

import numpy as np
from pydantic import BaseModel, ConfigDict, Field
from statsmodels.regression.linear_model import OLS
from statsmodels.tsa.stattools import adfuller, coint

from aqil_research.contracts.observation import (
    AnalysisMode,
    EconomicObservation,
    Frequency,
    QualityStatus,
    SeasonalAdjustment,
    SeriesProvenance,
)
from aqil_research.methods.parameters import MethodParameterDocument
from aqil_research.methods.protocol import (
    MethodContext,
    MethodDependency,
    MethodExecutionResult,
    bind_dependency,
)

ACTIVITY_LEVEL_COINTEGRATION = "ACTIVITY_LEVEL_COINTEGRATION"
METHOD_VERSION = "0.1.0"
PUBLICATION_ALLOWED = False

INDUSTRIAL_PRODUCTION_DATASET_ID = "fed.g17.IP.B50001.S"
PAYROLL_DATASET_ID = "bls.ce.CES0000000001"
INDUSTRIAL_PRODUCTION_UNIT = "index_2017_100"
PAYROLL_UNIT = "thousands"
DATASET_IDS = (INDUSTRIAL_PRODUCTION_DATASET_ID, PAYROLL_DATASET_ID)
UNITS = {
    INDUSTRIAL_PRODUCTION_DATASET_ID: INDUSTRIAL_PRODUCTION_UNIT,
    PAYROLL_DATASET_ID: PAYROLL_UNIT,
}
LABELS = {
    INDUSTRIAL_PRODUCTION_DATASET_ID: "Industrial production",
    PAYROLL_DATASET_ID: "Total nonfarm payroll employment",
}

MINIMUM_OVERLAP_MONTHS = 120
SIGNIFICANCE = 0.05
COINTEGRATION_TREND = "c"
COINTEGRATION_METHOD = "aeg"
RESIDUAL_AUTO_LAG = "aic"
RESIDUAL_REGRESSION = "n"
NO_CAUSAL_CLAIM = "No causal claim is made."

PUBLISHED_CONFIG = {
    "config_id": "activity-level-cointegration-v1",
    "label": (
        "Engle-Granger cointegration of industrial production and payroll employment log levels"
    ),
}


class ActivityLevelCointegrationConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    config_id: str = Field(min_length=1)
    label: str = Field(min_length=1)


def implementation_hash() -> str:
    payload = "|".join(
        (
            ACTIVITY_LEVEL_COINTEGRATION,
            METHOD_VERSION,
            "log-levels",
            "coint-aeg-trend-c",
            "autolag-aic",
            "schwert-max-lag-explicit",
            "residual-regression-n",
            f"significance-{SIGNIFICANCE}",
            f"minimum-overlap-{MINIMUM_OVERLAP_MONTHS}",
            "decision-statistic-below-five-percent-critical-value",
            "ip-on-payroll",
            "no-growth-rates",
            "no-granger-causality",
            "no-var",
        ),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def residual_adf_max_lag(observation_count: int) -> int:
    """Schwert ceiling ``adfuller`` uses when ``maxlag`` is omitted.

    The formula is ``ceil(12 * (n / 100) ** 0.25)``, capped at
    ``n // 2 - 1``. The cap is ``nobs // 2 - ntrend - 1`` with ``ntrend``
    equal to 0, which is the residual regression ``coint`` uses. ``n`` is
    the length of the cointegrating residual.
    """

    if observation_count < 3:
        raise ValueError("the residual sample is too short for a lag ceiling")
    ceiling = int(math.ceil(12.0 * (observation_count / 100.0) ** 0.25))
    cap = observation_count // 2 - 1
    if cap < 0:
        raise ValueError("the residual sample is too short for a lag ceiling")
    return min(cap, ceiling)


def activity_cointegration_from_log_levels(
    industrial_production: Sequence[float],
    payroll_employment: Sequence[float],
) -> dict[str, object]:
    """Augmented Engle-Granger test. The first argument is log industrial production.

    The statistic, p-value and critical values are the values returned by
    ``statsmodels.tsa.stattools.coint``. The ordinary Dickey-Fuller p-value
    on the residual is not the decision.
    """

    y_values = np.asarray(list(industrial_production), dtype=np.float64)
    x_values = np.asarray(list(payroll_employment), dtype=np.float64)
    if y_values.ndim != 1 or x_values.ndim != 1 or y_values.shape != x_values.shape:
        raise ValueError("the two log-level samples must be the same length")
    if y_values.size < MINIMUM_OVERLAP_MONTHS:
        raise ValueError(
            f"the overlap has {y_values.size} months, below {MINIMUM_OVERLAP_MONTHS}",
        )
    if not np.isfinite(y_values).all() or not np.isfinite(x_values).all():
        raise ValueError("log levels must be finite")
    exog = np.column_stack((x_values, np.ones(y_values.shape[0], dtype=np.float64)))
    fitted = OLS(y_values, exog).fit()
    slope = float(fitted.params[0])
    intercept = float(fitted.params[1])
    r_squared = float(fitted.rsquared)
    if not all(math.isfinite(value) for value in (slope, intercept, r_squared)):
        raise ValueError("the cointegrating regression did not return finite coefficients")
    max_lag = residual_adf_max_lag(int(y_values.size))
    coint_result = coint(
        y_values,
        x_values,
        trend=COINTEGRATION_TREND,
        method=COINTEGRATION_METHOD,
        maxlag=max_lag,
        autolag=RESIDUAL_AUTO_LAG,
        return_results=False,
    )
    statistic = float(coint_result[0])
    p_value = float(coint_result[1])
    critical_values = coint_result[2]
    five_percent = float(critical_values[1])
    if not all(math.isfinite(value) for value in (statistic, p_value, five_percent)):
        raise ValueError("the Engle-Granger statistic is not finite")
    adf_statistic, _ordinary_p, used_lag, adf_observations, _ordinary_crit, _ic = adfuller(
        np.asarray(fitted.resid, dtype=np.float64),
        maxlag=max_lag,
        regression=RESIDUAL_REGRESSION,
        autolag=RESIDUAL_AUTO_LAG,
        result_object=False,
    )
    if not math.isclose(statistic, float(adf_statistic), rel_tol=1e-8, abs_tol=1e-8):
        raise ValueError("the named Engle-Granger statistic and the residual test disagree")
    rejects = statistic < five_percent
    return {
        "sufficient": True,
        "method_id": ACTIVITY_LEVEL_COINTEGRATION,
        "publication_allowed": PUBLICATION_ALLOWED,
        "transformation": "natural_log_levels",
        "growth_rates_used": False,
        "granger_causality": False,
        "vector_autoregression": False,
        "causal_claim": False,
        "normalisation": "log industrial production on log payroll employment with a constant",
        "observation_count": int(y_values.size),
        "statsmodels_function": "statsmodels.tsa.stattools.coint",
        "statsmodels_call": {
            "trend": COINTEGRATION_TREND,
            "method": COINTEGRATION_METHOD,
            "maxlag_rule": "schwert_ceiling_for_residual_regression_n",
            "maxlag": int(max_lag),
            "autolag": RESIDUAL_AUTO_LAG,
            "return_results": False,
        },
        "first_stage": {
            "estimator": "ordinary_least_squares",
            "statsmodels_function": "statsmodels.regression.linear_model.OLS",
            "constant_included": True,
            "constant_column": "last",
            "left_hand_side": INDUSTRIAL_PRODUCTION_DATASET_ID,
            "right_hand_side": PAYROLL_DATASET_ID,
            "slope": _figure(slope),
            "intercept": _figure(intercept),
            "r_squared": _figure(r_squared),
        },
        "second_stage": {
            "test": "augmented_dickey_fuller_on_the_residual",
            "regression": "no_constant_no_trend",
            "lag_rule": "aic",
            "max_lag_rule": "schwert_ceiling_for_residual_regression_n",
            "max_lag": int(max_lag),
            "used_lag": int(used_lag),
            "adf_observation_count": int(adf_observations),
            "statistic": _figure(statistic),
            "ordinary_adf_p_value_used": False,
        },
        "null_hypothesis": "no_cointegration",
        "significance": SIGNIFICANCE,
        "decision_rule": "statistic_strictly_below_the_five_percent_critical_value",
        "rejects_no_cointegration_at_five_percent": bool(rejects),
        "statistic": _figure(statistic),
        "p_value": _figure(p_value),
        "critical_value_one_percent": _figure(float(critical_values[0])),
        "critical_value_five_percent": _figure(five_percent),
        "critical_value_ten_percent": _figure(float(critical_values[2])),
        "critical_value_source": (
            "Five percent critical value returned by statsmodels.tsa.stattools.coint "
            "for trend c. The MacKinnon response surface inside that function is "
            "not the ordinary augmented Dickey-Fuller critical value."
        ),
    }


def next_month(month_start: date) -> date:
    if month_start.month == 12:
        return date(month_start.year + 1, 1, 1)
    return date(month_start.year, month_start.month + 1, 1)


def longest_contiguous_overlap(
    left: Mapping[date, float],
    right: Mapping[date, float],
) -> tuple[tuple[date, ...], tuple[float, ...], tuple[float, ...], int]:
    """Earliest longest month where both positive levels exist. No interpolation."""

    overlap = sorted(set(left) & set(right))
    chosen = _longest_run(overlap)
    if not chosen:
        return (), (), (), len(overlap)
    left_values = tuple(math.log(left[month]) for month in chosen)
    right_values = tuple(math.log(right[month]) for month in chosen)
    return tuple(chosen), left_values, right_values, len(overlap) - len(chosen)


class ActivityLevelCointegrationMethod:
    """Engle-Granger test on revised log levels of production and payrolls.

    Registration, for the integrator, inside ``default_method_registry``::

        registry.register(ActivityLevelCointegrationMethod())
    """

    method_id = ACTIVITY_LEVEL_COINTEGRATION
    method_version = METHOD_VERSION

    def implementation_hash(self) -> str:
        return implementation_hash()

    def required_dataset_ids(self) -> tuple[str, ...]:
        return DATASET_IDS

    def dependency(self) -> MethodDependency:
        return bind_dependency(
            self.required_dataset_ids(),
            frequency=("monthly",),
            minimum_history=(
                f"{MINIMUM_OVERLAP_MONTHS} contiguous months of positive "
                "latest-revised levels for both series"
            ),
            parameter_policy="none",
            new_observation_requires_recalculation=True,
            refit_is_different_command=False,
        )

    def accepted_config_payload(self) -> dict[str, object]:
        return dict(PUBLISHED_CONFIG)

    def parse_config(self, payload: dict[str, object]) -> ActivityLevelCointegrationConfig:
        return ActivityLevelCointegrationConfig.model_validate(payload)

    def config_hash(self, config: BaseModel) -> str:
        if not isinstance(config, ActivityLevelCointegrationConfig):
            raise TypeError("expected ActivityLevelCointegrationConfig")
        return MethodParameterDocument(
            config_id=config.config_id,
            label=config.label,
            scalars={
                "transformation": "natural_log_levels",
                "left_hand_side": INDUSTRIAL_PRODUCTION_DATASET_ID,
                "right_hand_side": PAYROLL_DATASET_ID,
                "procedure": "statsmodels.tsa.stattools.coint",
                "trend": COINTEGRATION_TREND,
                "method": COINTEGRATION_METHOD,
                "lag_rule": "aic_up_to_schwert_ceiling",
                "significance": str(SIGNIFICANCE),
            },
        ).config_hash()

    def run(self, context: MethodContext, config: BaseModel) -> MethodExecutionResult:
        if not isinstance(config, ActivityLevelCointegrationConfig):
            raise TypeError("expected ActivityLevelCointegrationConfig")
        if context.analysis_mode != AnalysisMode.LATEST_REVISED:
            return _insufficient(
                "These levels are dated on latest_revised observations. "
                "A point-in-time request was not dated.",
            )
        levels: dict[str, dict[date, float]] = {}
        series_by_dataset: dict[str, Mapping[date, EconomicObservation]] = {}
        for dataset_id in DATASET_IDS:
            series = context.inputs_by_dataset.get(dataset_id)
            if not series:
                return _insufficient(f"No observations were available for {LABELS[dataset_id]}.")
            series_by_dataset[dataset_id] = series
            extracted = _eligible_levels(dataset_id, series)
            if not extracted:
                return _insufficient(
                    f"No eligible latest-revised level was available for {LABELS[dataset_id]}.",
                )
            levels[dataset_id] = extracted
        months, left, right, excluded = longest_contiguous_overlap(
            levels[INDUSTRIAL_PRODUCTION_DATASET_ID],
            levels[PAYROLL_DATASET_ID],
        )
        if len(months) < MINIMUM_OVERLAP_MONTHS:
            return _insufficient(
                "The contiguous overlap of positive log levels is shorter than "
                f"{MINIMUM_OVERLAP_MONTHS} months.",
            )
        try:
            calculation = activity_cointegration_from_log_levels(left, right)
        except (ValueError, np.linalg.LinAlgError):
            return _insufficient("The Engle-Granger test did not return a finite result.")
        calculation = {
            **calculation,
            "sample_start": months[0].isoformat(),
            "sample_end": months[-1].isoformat(),
            "excluded_overlap_months": excluded,
            "left_dataset_id": INDUSTRIAL_PRODUCTION_DATASET_ID,
            "right_dataset_id": PAYROLL_DATASET_ID,
            "input_vintage": "latest_revised",
        }
        return MethodExecutionResult(
            sufficiency="sufficient",
            calculation=calculation,
            observation_ids=_observation_ids(series_by_dataset, months),
            assumptions=_assumptions(excluded),
            limitations=_limitations(),
            missing_reason=None,
            statistical_interpretation=_interpretation(calculation),
            causal_hypothesis="none",
            investment_implication="no_action",
            narrative=_narrative(calculation),
        )


def _figure(value: float) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("a stored figure must be finite")
    return float(f"{number:.8g}")


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
    months: Sequence[date],
) -> tuple[str, ...]:
    identifiers: list[str] = []
    for dataset_id in DATASET_IDS:
        series = series_by_dataset[dataset_id]
        for month in months:
            observation = series.get(month)
            if observation is not None:
                identifiers.append(observation.observation_id)
    return tuple(identifiers)


def _assumptions(excluded: int) -> tuple[str, ...]:
    assumptions = [
        "Both series are natural logarithms of latest-revised levels.",
        (
            "The overlap is the earliest longest contiguous run of months "
            "in which both levels are positive."
        ),
        (
            "The left-hand side is log industrial production. "
            "The right-hand side is log payroll employment, plus a constant."
        ),
        (
            "The procedure is statsmodels.tsa.stattools.coint with trend c, "
            "method aeg, and AIC lag selection up to the Schwert ceiling."
        ),
        (
            "The five percent decision uses the critical value returned by that "
            "function. The statistic must be strictly below it."
        ),
    ]
    if excluded:
        assumptions.append("Months outside that overlap were left out. Gaps were not interpolated.")
    return tuple(assumptions)


def _limitations() -> tuple[str, ...]:
    return (
        "Publication allowed is false.",
        "The inputs are latest revised levels. Revision sensitivity is blocked.",
        "The normalisation is predeclared. The reverse regression was not estimated.",
        "Granger causality on growth rates is not estimated.",
        "A vector autoregression is not estimated.",
        NO_CAUSAL_CLAIM,
        (
            "A failure to reject no-cointegration is the result. "
            "The five percent size was not changed."
        ),
    )


def _interpretation(calculation: Mapping[str, object]) -> str:
    statistic = calculation["statistic"]
    critical = calculation["critical_value_five_percent"]
    second = calculation["second_stage"]
    used_lag = second["used_lag"] if isinstance(second, dict) else None
    if calculation["rejects_no_cointegration_at_five_percent"] is True:
        decision = "rejects no-cointegration at five percent"
    else:
        decision = "does not reject no-cointegration at five percent"
    return (
        f"The Engle-Granger statistic is {statistic}. "
        f"The five percent critical value returned by coint is {critical}. "
        f"The test {decision}. The residual lag chosen by AIC is {used_lag}. "
        "The series are revised log levels. "
        f"{NO_CAUSAL_CLAIM}"
    )


def _narrative(calculation: Mapping[str, object]) -> str:
    if calculation["rejects_no_cointegration_at_five_percent"] is True:
        decision = "rejects no-cointegration at five percent"
    else:
        decision = "does not reject no-cointegration at five percent"
    return (
        "Engle-Granger test of log industrial production on log payroll employment. "
        f"The test {decision}. "
        "The result describes co-movement in revised log levels. "
        f"{NO_CAUSAL_CLAIM} Publication allowed is false."
    )


def _insufficient(reason: str) -> MethodExecutionResult:
    return MethodExecutionResult(
        sufficiency="insufficient",
        calculation={
            "method_id": ACTIVITY_LEVEL_COINTEGRATION,
            "publication_allowed": PUBLICATION_ALLOWED,
            "transformation": "natural_log_levels",
            "growth_rates_used": False,
            "granger_causality": False,
            "vector_autoregression": False,
            "causal_claim": False,
        },
        observation_ids=(),
        assumptions=("The series would have entered as natural logarithms of levels.",),
        limitations=("Publication allowed is false.", NO_CAUSAL_CLAIM),
        missing_reason=reason,
        statistical_interpretation="The Engle-Granger test was not computed.",
        causal_hypothesis="none",
        investment_implication="insufficient_evidence",
        narrative=f"Activity-level cointegration incomplete. Reason: {reason}",
    )
