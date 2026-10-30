"""CPI-U inflation autoregression on the monthly logarithmic change.

One series: bls.cu.CUSR0000SA0, latest_revised index levels. The modelled series is

    pi_t = ln(P_t) - ln(P_{t-1})

for adjacent months. That is the month-on-month logarithmic change. It is not
annualised, and it is not the twelve-month price rank in prices and policy.

The autoregression is

    pi_t = c + phi_1 pi_{t-1} + ... + phi_p pi_{t-p} + e_t

Lag order follows the autoregressive benchmark's rule: AIC on a common sample,
maximum lag 12, and the smaller lag when AIC ties. BIC is not a second selector.
The last 24 growth months are a held-out tail. The lag, the coefficients, and
the historical-mean benchmark are estimated on the preceding months only.

Persistence is the sum of the slope coefficients. A half-life is reported only
when that sum is strictly between 0 and 1. The selected lag is stored in the
calculation. It is not a frozen parameter version. Parameter policy is none.
Refit is rejected.

A held-out win against the historical mean is the only path to empirical
qualification. Qualification is still not a product forecast. publication_allowed
stays false. This is not a Taylor rule.
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
from aqil_research.methods.protocol import (
    MethodContext,
    MethodDependency,
    MethodExecutionResult,
    bind_dependency,
)

INFLATION_AUTOREGRESSION = "INFLATION_AUTOREGRESSION"
METHOD_VERSION = "0.1.0"
PUBLICATION_ALLOWED = False
CPI_DATASET_ID = "bls.cu.CUSR0000SA0"
CPI_UNIT = "1982-84=100"

MAX_LAG = 12
MIN_ESTIMATION_MONTHS = 120
HOLDOUT_MONTHS = 24
HORIZONS = (1, 12)
MINIMUM_GROWTH_MONTHS = MIN_ESTIMATION_MONTHS + HOLDOUT_MONTHS

TRANSFORMATION_EQUATION = "pi_t = ln(P_t) - ln(P_{t-1})"
AUTOREGRESSION_EQUATION = "pi_t = c + phi_1*pi_{t-1} + ... + phi_p*pi_{t-p} + e_t"
AIC_EQUATION = "n * ln(RSS / n) + 2 * (p + 1)"
PERSISTENCE_EQUATION = "persistence = phi_1 + ... + phi_p"
HALF_LIFE_EQUATION = "ln(0.5) / ln(persistence), only when 0 < persistence < 1"

NOT_A_PRODUCT_FORECAST = "This is a retrospective calculation, not a product forecast."
NOT_QUALIFIED = "The method is not empirically qualified as a forecast."
NOT_A_TAYLOR_RULE = "This is not a Taylor rule."
NOT_THE_TWELVE_MONTH_RANK = (
    "This is not the twelve-month CPI-U price rank. "
    "The modelled series is the monthly logarithmic change."
)

PUBLISHED_CONFIG = {
    "config_id": "inflation-autoregression-v1",
    "label": "CPI-U inflation autoregression",
}


class InflationAutoregressionConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    config_id: str = Field(min_length=1)
    label: str = Field(min_length=1)


@dataclass(frozen=True, slots=True)
class LogChangeSample:
    growth_months: tuple[date, ...]
    values: tuple[float, ...]
    level_months: tuple[date, ...]
    excluded_growth_months: int


def implementation_hash() -> str:
    payload = "|".join(
        (
            INFLATION_AUTOREGRESSION,
            METHOD_VERSION,
            TRANSFORMATION_EQUATION,
            AUTOREGRESSION_EQUATION,
            AIC_EQUATION,
            PERSISTENCE_EQUATION,
            HALF_LIFE_EQUATION,
            f"max-lag-{MAX_LAG}",
            f"min-estimation-{MIN_ESTIMATION_MONTHS}",
            f"holdout-{HOLDOUT_MONTHS}",
            f"horizons-{','.join(str(horizon) for horizon in HORIZONS)}",
            "aic-common-sample",
            "smaller-lag-on-tie",
            "bic-not-used",
            "no-annualisation",
            "no-second-difference",
            "no-full-sample-standardisation",
            "parameter-policy-none",
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


def trailing_monthly_log_change(levels: Mapping[date, float]) -> LogChangeSample:
    """Natural log difference of adjacent positive levels. Gaps are not filled.

    The returned run is the contiguous monthly sequence that ends at the latest
    growth month. An earlier run is not substituted.
    """
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
    chosen_months = [candidates[-1][0]]
    for month, _value in reversed(candidates[:-1]):
        if next_month(month) != chosen_months[-1]:
            break
        chosen_months.append(month)
    chosen_months.reverse()
    chosen_set = set(chosen_months)
    values = tuple(value for month, value in candidates if month in chosen_set)
    months = tuple(chosen_months)
    return LogChangeSample(
        growth_months=months,
        values=values,
        level_months=(previous_month(months[0]), *months),
        excluded_growth_months=len(candidates) - len(months),
    )


def aic_value(rss: float, sample_size: int, lag: int) -> float:
    """AIC = n ln(RSS/n) + 2(p+1) on the common sample."""
    if sample_size <= lag + 1 or not math.isfinite(rss) or rss < 0:
        return math.inf
    if rss == 0:
        return -math.inf
    return sample_size * math.log(rss / sample_size) + 2 * (lag + 1)


def select_inflation_lag(growth: np.ndarray) -> tuple[int, np.ndarray, float]:
    """AIC on a common sample. Ties keep the smaller lag. The maximum lag is 12."""
    values = np.asarray(growth, dtype=float)
    if int(values.size) <= MAX_LAG + MAX_LAG + 1:
        raise ValueError("the estimation window is too short for lag selection")
    best_lag = 1
    best_aic = math.inf
    best_coefficients: np.ndarray | None = None
    sample_size = int(values.size) - MAX_LAG
    for lag in range(1, MAX_LAG + 1):
        coefficients, rss = _fit_rss(values, lag)
        aic = aic_value(rss, sample_size, lag)
        if aic < best_aic:
            best_aic = aic
            best_lag = lag
            best_coefficients = coefficients
    if best_coefficients is None or not np.all(np.isfinite(best_coefficients)):
        raise ValueError("autoregressive coefficients are not finite")
    return best_lag, best_coefficients, best_aic


def persistence_summary(coefficients: np.ndarray) -> dict[str, object]:
    """Sum of slope coefficients. Half-life only when that sum is in (0, 1)."""
    slopes = np.asarray(coefficients[1:], dtype=float)
    rounded_slopes = [round(float(value), 8) for value in slopes]
    total = round(float(sum(rounded_slopes)), 8)
    half_life = _half_life_months(total)
    return {
        "equation": PERSISTENCE_EQUATION,
        "half_life_equation": HALF_LIFE_EQUATION,
        "sum_of_autoregressive_coefficients": total,
        "half_life_months": None if half_life is None else round(half_life, 6),
        "half_life_defined": half_life is not None,
        "includes_intercept": False,
    }


def beat_historical_mean(
    *,
    autoregressive_mae: float,
    autoregressive_rmse: float,
    historical_mean_mae: float,
    historical_mean_rmse: float,
) -> bool:
    """Both scores must be strictly lower. A tie is not a win."""
    scores = (
        autoregressive_mae,
        autoregressive_rmse,
        historical_mean_mae,
        historical_mean_rmse,
    )
    if not all(math.isfinite(score) for score in scores):
        return False
    return autoregressive_mae < historical_mean_mae and autoregressive_rmse < historical_mean_rmse


def iterated_forecast(history: np.ndarray, coefficients: np.ndarray, horizon: int) -> list[float]:
    """Iterate the fitted equation. Later steps use predicted values as lags."""
    values = [float(value) for value in history]
    intercept = float(coefficients[0])
    phis = [float(value) for value in coefficients[1:]]
    forecasts: list[float] = []
    for _step in range(horizon):
        predicted = intercept
        for index, phi in enumerate(phis, start=1):
            predicted += phi * values[-index]
        if not math.isfinite(predicted):
            predicted = math.inf
        values.append(predicted)
        forecasts.append(predicted)
    return forecasts


def inflation_autoregression_from_growth(growth: Sequence[float]) -> dict[str, object]:
    """Fit on the pre-holdout sample and score the held-out tail.

    The tail is not used to choose the lag, the coefficients, or the historical mean.
    Later origins inside the tail use realised lags with those fixed coefficients.
    """
    values = np.asarray(list(growth), dtype=float)
    if values.size < MINIMUM_GROWTH_MONTHS or not np.all(np.isfinite(values)):
        return _insufficient_payload(
            "The monthly logarithmic-change sample is shorter than the predeclared "
            f"minimum of {MINIMUM_GROWTH_MONTHS} months.",
        )
    estimation_end = int(values.size) - HOLDOUT_MONTHS
    estimation = values[:estimation_end]
    if estimation.size < MIN_ESTIMATION_MONTHS:
        return _insufficient_payload(
            "The estimation sample is shorter than the predeclared minimum of "
            f"{MIN_ESTIMATION_MONTHS} months.",
        )
    try:
        lag, coefficients, aic = select_inflation_lag(estimation)
    except ValueError:
        return _insufficient_payload("The autoregression did not return finite coefficients.")
    historical_mean = float(estimation.mean())
    if not math.isfinite(historical_mean):
        return _insufficient_payload("The estimation-sample mean was not finite.")
    horizons = [
        _horizon_score(horizon, values, estimation_end, coefficients, historical_mean)
        for horizon in HORIZONS
    ]
    if any(row["origin_count"] == 0 for row in horizons):
        return _insufficient_payload("The held-out tail did not cover the predeclared horizons.")
    qualified = all(row["beat_historical_mean"] is True for row in horizons)
    persistence = persistence_summary(coefficients)
    return {
        "sufficient": True,
        **_identity_flags(),
        "modelled_transformation": "monthly_log_change",
        "transformation_equation": TRANSFORMATION_EQUATION,
        "autoregression_equation": AUTOREGRESSION_EQUATION,
        "annualised": False,
        "second_difference_applied": False,
        "full_sample_standardisation": False,
        "twelve_month_price_rank": False,
        "estimation_sample_excludes_holdout": True,
        "growth_month_count": int(values.size),
        "estimation_month_count": int(estimation.size),
        "holdout_month_count": HOLDOUT_MONTHS,
        "selected_lag": int(lag),
        "intercept": round(float(coefficients[0]), 8),
        "autoregressive_coefficients": [round(float(value), 8) for value in coefficients[1:]],
        "aic": round(aic, 6) if math.isfinite(aic) else None,
        "historical_mean": round(historical_mean, 8),
        "persistence": persistence,
        "empirically_qualified_as_forecast": qualified,
        "qualification_statement": _qualification_statement(qualified, horizons),
        "predeclared": {
            "max_lag": MAX_LAG,
            "min_estimation_months": MIN_ESTIMATION_MONTHS,
            "holdout_months": HOLDOUT_MONTHS,
            "horizons": list(HORIZONS),
            "information_criterion": "aic",
            "aic_equation": AIC_EQUATION,
            "bic_used_for_selection": False,
            "tie_break": "smaller_lag",
            "common_sample_starts_after_max_lag": True,
            "benchmark": "historical_mean_of_the_estimation_sample",
            "window": "pre_holdout_sample_with_realised_lags_in_the_tail",
        },
        "horizons": horizons,
    }


class InflationAutoregressionMethod:
    """Retrospective CPI-U inflation autoregression.

    Registration, for the integrator, inside ``default_method_registry``::

        registry.register(InflationAutoregressionMethod())

    Refit is rejected. Parameter policy is none, and ``refit_is_different_command``
    is false. The selected lag stays in the calculation.
    """

    method_id = INFLATION_AUTOREGRESSION
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
                f"{MINIMUM_GROWTH_MONTHS} contiguous monthly logarithmic changes "
                f"({MIN_ESTIMATION_MONTHS} estimation months and a "
                f"{HOLDOUT_MONTHS}-month held-out tail)"
            ),
            parameter_policy="none",
            depends_on_method_ids=(),
            new_observation_requires_recalculation=True,
            refit_is_different_command=False,
        )

    def accepted_config_payload(self) -> dict[str, object]:
        return dict(PUBLISHED_CONFIG)

    def parse_config(self, payload: dict[str, object]) -> InflationAutoregressionConfig:
        return InflationAutoregressionConfig.model_validate(payload)

    def config_hash(self, config: BaseModel) -> str:
        if not isinstance(config, InflationAutoregressionConfig):
            raise TypeError("expected InflationAutoregressionConfig")
        return MethodParameterDocument(
            config_id=config.config_id,
            label=config.label,
            scalars={
                "transformation": "monthly_log_change",
                "information_criterion": "aic",
                "max_lag": str(MAX_LAG),
                "holdout_months": str(HOLDOUT_MONTHS),
                "min_estimation_months": str(MIN_ESTIMATION_MONTHS),
                "parameter_policy": "none",
            },
        ).config_hash()

    def run(self, context: MethodContext, config: BaseModel) -> MethodExecutionResult:
        if not isinstance(config, InflationAutoregressionConfig):
            raise TypeError("expected InflationAutoregressionConfig")
        if context.analysis_mode != AnalysisMode.LATEST_REVISED:
            return _insufficient(
                "These levels are dated on latest_revised observations. "
                "A point-in-time request was not dated.",
            )
        series = context.inputs_by_dataset.get(CPI_DATASET_ID)
        if not series:
            return _insufficient("No latest-revised CPI-U observations were available.")
        levels = _eligible_levels(series, context.evaluation_period)
        if not levels:
            return _insufficient("No eligible latest-revised CPI-U level was available.")
        sample = trailing_monthly_log_change(levels)
        if len(sample.values) < MINIMUM_GROWTH_MONTHS:
            return _insufficient(
                "The contiguous monthly logarithmic-change sample ending at the latest "
                f"growth month is shorter than the predeclared minimum of "
                f"{MINIMUM_GROWTH_MONTHS} months.",
            )
        calculation = inflation_autoregression_from_growth(sample.values)
        if calculation.get("sufficient") is not True:
            reason = calculation.get("reason")
            return _insufficient(
                reason
                if isinstance(reason, str)
                else "The inflation autoregression was not computed.",
            )
        calculation = _with_sample_identity(calculation, sample)
        observation_ids = tuple(
            series[month].observation_id for month in sample.level_months if month in series
        )
        return MethodExecutionResult(
            sufficiency="sufficient",
            calculation=calculation,
            observation_ids=observation_ids,
            assumptions=_assumptions(sample),
            limitations=_limitations(calculation),
            missing_reason=None,
            statistical_interpretation=_interpretation(calculation),
            causal_hypothesis="none",
            investment_implication="no_action",
            narrative=_narrative(calculation),
        )


def _eligible_levels(
    series: Mapping[date, EconomicObservation],
    evaluation_period: date,
) -> dict[date, float]:
    levels: dict[date, float] = {}
    for period, observation in series.items():
        if period > evaluation_period or not _level_is_eligible(period, observation):
            continue
        value = float(observation.decimal_value())
        if math.isfinite(value) and value > 0:
            levels[period] = value
    return levels


def _level_is_eligible(period: date, observation: EconomicObservation) -> bool:
    return (
        period.day == 1
        and observation.period_start == period
        and observation.dataset_id == CPI_DATASET_ID
        and observation.series_provenance == SeriesProvenance.LATEST_REVISED
        and observation.quality_status == QualityStatus.OBSERVED
        and observation.frequency == Frequency.MONTHLY
        and observation.seasonal_adjustment == SeasonalAdjustment.SEASONALLY_ADJUSTED
        and observation.unit == CPI_UNIT
    )


def _half_life_months(persistence: float) -> float | None:
    if not math.isfinite(persistence) or persistence <= 0.0 or persistence >= 1.0:
        return None
    return math.log(0.5) / math.log(persistence)


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


def _fit_rss(growth: np.ndarray, lag: int) -> tuple[np.ndarray, float]:
    design, target = _design(growth, lag, MAX_LAG, int(growth.size))
    coefficients, _, _, _ = np.linalg.lstsq(design, target, rcond=None)
    if coefficients.shape != (lag + 1,) or not np.all(np.isfinite(coefficients)):
        raise ValueError("autoregressive coefficients are not finite")
    residuals = target - design @ coefficients
    return coefficients, float(residuals @ residuals)


def _horizon_score(
    horizon: int,
    growth: np.ndarray,
    estimation_end: int,
    coefficients: np.ndarray,
    historical_mean: float,
) -> dict[str, object]:
    autoregressive_errors: list[float] = []
    baseline_errors: list[float] = []
    last_origin = int(growth.size) - horizon + 1
    for origin_end in range(estimation_end, last_origin):
        predicted = iterated_forecast(growth[:origin_end], coefficients, horizon)[horizon - 1]
        actual = float(growth[origin_end + horizon - 1])
        autoregressive_errors.append(actual - predicted)
        baseline_errors.append(actual - historical_mean)
    autoregressive = np.asarray(autoregressive_errors, dtype=float)
    baseline = np.asarray(baseline_errors, dtype=float)
    finite = (
        autoregressive.size > 0
        and autoregressive.size == baseline.size
        and bool(np.all(np.isfinite(autoregressive)))
        and bool(np.all(np.isfinite(baseline)))
    )
    if not finite:
        return {
            "horizon_months": horizon,
            "origin_count": int(autoregressive.size),
            "scores_finite": False,
            "mae": None,
            "rmse": None,
            "historical_mean_mae": None,
            "historical_mean_rmse": None,
            "beat_historical_mean": False,
        }
    autoregressive_mae = float(np.mean(np.abs(autoregressive)))
    autoregressive_rmse = float(np.sqrt(np.mean(np.square(autoregressive))))
    baseline_mae = float(np.mean(np.abs(baseline)))
    baseline_rmse = float(np.sqrt(np.mean(np.square(baseline))))
    return {
        "horizon_months": horizon,
        "origin_count": int(autoregressive.size),
        "scores_finite": True,
        "mae": round(autoregressive_mae, 8),
        "rmse": round(autoregressive_rmse, 8),
        "historical_mean_mae": round(baseline_mae, 8),
        "historical_mean_rmse": round(baseline_rmse, 8),
        "beat_historical_mean": beat_historical_mean(
            autoregressive_mae=autoregressive_mae,
            autoregressive_rmse=autoregressive_rmse,
            historical_mean_mae=baseline_mae,
            historical_mean_rmse=baseline_rmse,
        ),
    }


def _qualification_statement(qualified: bool, horizons: list[dict[str, object]]) -> str:
    detail = _horizon_sentence(horizons)
    shared = (
        f"{detail} {NOT_A_PRODUCT_FORECAST} {NOT_A_TAYLOR_RULE} "
        "The calculation is retrospective and uses latest_revised observations. "
        "Publication allowed is false."
    )
    if qualified:
        return shared
    return f"{detail} {NOT_QUALIFIED} {NOT_A_PRODUCT_FORECAST} {NOT_A_TAYLOR_RULE} " + (
        "The calculation is retrospective and uses latest_revised observations. "
        "Publication allowed is false."
    )


def _horizon_sentence(horizons: list[dict[str, object]]) -> str:
    parts: list[str] = []
    for horizon in horizons:
        months = horizon["horizon_months"]
        label = "one-month" if months == 1 else f"{months}-month"
        if horizon["beat_historical_mean"] is True:
            parts.append(
                f"The {label} held-out horizon beat the historical mean on both "
                "mean absolute error and root mean squared error.",
            )
        else:
            parts.append(f"The {label} held-out horizon did not beat the historical mean.")
    return " ".join(parts)


def _with_sample_identity(
    calculation: dict[str, object],
    sample: LogChangeSample,
) -> dict[str, object]:
    calculation["growth_start"] = sample.growth_months[0].isoformat()
    calculation["growth_end"] = sample.growth_months[-1].isoformat()
    calculation["excluded_growth_months"] = sample.excluded_growth_months
    calculation["dataset_id"] = CPI_DATASET_ID
    return calculation


def _assumptions(sample: LogChangeSample) -> tuple[str, ...]:
    assumptions = [
        "The modelled series is the monthly natural logarithmic change in CPI-U.",
        TRANSFORMATION_EQUATION,
        "The logarithmic change is not annualised and is not differenced again.",
        NOT_THE_TWELVE_MONTH_RANK,
        (
            "Lag order is chosen by AIC on a common sample that starts after the "
            f"maximum lag of {MAX_LAG}. Ties keep the smaller lag. BIC is not used."
        ),
        AIC_EQUATION,
        AUTOREGRESSION_EQUATION,
        (
            f"The last {HOLDOUT_MONTHS} growth months are held out. The lag, the "
            "coefficients, and the historical mean use only the preceding months."
        ),
        (
            "Origins inside the held-out tail use realised lags. They do not "
            "re-estimate the coefficients."
        ),
        PERSISTENCE_EQUATION,
        HALF_LIFE_EQUATION,
        (
            "A horizon beats the historical mean only when both mean absolute error "
            "and root mean squared error are strictly lower. A tie is not a win."
        ),
        "Parameter policy is none. The selected lag is not a frozen parameter version.",
        "Refit is rejected.",
        NOT_A_TAYLOR_RULE,
        "Inputs are latest_revised observations on or before the evaluation period.",
    ]
    if sample.excluded_growth_months:
        assumptions.append(
            "Growth months before the latest contiguous run were left out. "
            "Gaps were not interpolated.",
        )
    return tuple(assumptions)


def _limitations(calculation: Mapping[str, object]) -> tuple[str, ...]:
    limitations = [
        "Publication allowed is false.",
        NOT_A_PRODUCT_FORECAST,
        NOT_A_TAYLOR_RULE,
        NOT_THE_TWELVE_MONTH_RANK,
        "Refit is rejected because the parameter policy is none.",
        "The selected lag is stored in this calculation and is not a parameter version.",
        "Revision sensitivity is blocked because the input is latest_revised.",
        "The autoregressive polynomial is not constrained to be stationary.",
    ]
    if calculation.get("empirically_qualified_as_forecast") is not True:
        limitations.append(NOT_QUALIFIED)
    return tuple(limitations)


def _interpretation(calculation: Mapping[str, object]) -> str:
    lag = calculation["selected_lag"]
    persistence = calculation["persistence"]
    if isinstance(persistence, dict) and persistence.get("half_life_defined") is True:
        persistence_sentence = (
            "The sum of the autoregressive coefficients on the estimation sample is "
            f"{persistence['sum_of_autoregressive_coefficients']}. "
            f"The half-life is {persistence['half_life_months']} months."
        )
    elif isinstance(persistence, dict):
        persistence_sentence = (
            "The sum of the autoregressive coefficients on the estimation sample is "
            f"{persistence['sum_of_autoregressive_coefficients']}. "
            "A half-life is not defined for that sum."
        )
    else:
        persistence_sentence = "The persistence summary was not available."
    statement = calculation["qualification_statement"]
    return (
        f"The in-sample lag chosen by AIC, with a maximum of {MAX_LAG}, is {lag}. "
        f"That lag was selected on the pre-holdout sample. {persistence_sentence} {statement}"
    )


def _narrative(calculation: Mapping[str, object]) -> str:
    statement = calculation["qualification_statement"]
    lag = calculation["selected_lag"]
    return (
        f"CPI-U inflation autoregression on the monthly logarithmic change. "
        f"The selected lag is {lag}. Parameter policy is none. Refit is rejected. "
        f"{statement}"
    )


def _identity_flags() -> dict[str, object]:
    return {
        "method_id": INFLATION_AUTOREGRESSION,
        "publication_allowed": PUBLICATION_ALLOWED,
        "product_forecast": False,
        "taylor_rule": False,
        "retrospective": True,
        "input_vintage": "latest_revised",
        "parameter_policy": "none",
        "refit_rejected": True,
    }


def _insufficient_payload(reason: str) -> dict[str, object]:
    return {
        "sufficient": False,
        "reason": reason,
        **_identity_flags(),
        "twelve_month_price_rank": False,
        "second_difference_applied": False,
        "annualised": False,
        "empirically_qualified_as_forecast": False,
    }


def _insufficient(reason: str) -> MethodExecutionResult:
    return MethodExecutionResult(
        sufficiency="insufficient",
        calculation={
            **_identity_flags(),
            "twelve_month_price_rank": False,
            "empirically_qualified_as_forecast": False,
            "annualised": False,
            "second_difference_applied": False,
        },
        observation_ids=(),
        assumptions=(
            "The modelled series would have been the monthly logarithmic change in CPI-U.",
            NOT_THE_TWELVE_MONTH_RANK,
            NOT_A_TAYLOR_RULE,
        ),
        limitations=(
            "Publication allowed is false.",
            NOT_A_PRODUCT_FORECAST,
            NOT_A_TAYLOR_RULE,
            "Refit is rejected because the parameter policy is none.",
        ),
        missing_reason=reason,
        statistical_interpretation="The inflation autoregression was not computed.",
        causal_hypothesis="none",
        investment_implication="insufficient_evidence",
        narrative=(
            f"CPI-U inflation autoregression incomplete. Reason: {reason} "
            f"{NOT_A_TAYLOR_RULE} {NOT_QUALIFIED} {NOT_A_PRODUCT_FORECAST}"
        ),
    )
