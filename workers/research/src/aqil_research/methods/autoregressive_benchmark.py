"""Autoregressive benchmark for industrial production monthly log-growth.

One series: fed.g17.IP.B50001.S, latest_revised levels. The modelled series is
the monthly natural log-growth. An augmented Dickey-Fuller check is recorded.
The log-growth is not differenced again.

Lag order is chosen by AIC on a common sample, with a maximum lag of 12.
Rolling-origin forecasts use an expanding window. Each origin selects its lag
from that window only. The benchmark is the historical mean of the same window.
Nothing is standardised on the full sample.

A better in-sample fit is not forecast skill. This is a validation baseline,
not a product forecast. publication_allowed stays false.
"""

from __future__ import annotations

import hashlib
import math
import warnings
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date

import numpy as np
from pydantic import BaseModel, ConfigDict, Field
from statsmodels.stats.diagnostic import acorr_ljungbox
from statsmodels.tsa.stattools import adfuller

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

AUTOREGRESSIVE_BENCHMARK = "AUTOREGRESSIVE_BENCHMARK"
METHOD_VERSION = "0.1.0"
PUBLICATION_ALLOWED = False
INDUSTRIAL_PRODUCTION_DATASET_ID = "fed.g17.IP.B50001.S"
LEVEL_UNIT = "index_2017_100"

MAX_LAG = 12
MIN_ESTIMATION_MONTHS = 120
HORIZONS = (1, 12)
LJUNG_BOX_LAG = 24
ADF_MAX_LAG = 12
ADF_SIGNIFICANCE = 0.05
MINIMUM_GROWTH_MONTHS = MIN_ESTIMATION_MONTHS + max(HORIZONS)

NOT_A_PRODUCT_FORECAST = "This is a validation baseline, not a product forecast."
NOT_QUALIFIED = "The method is not empirically qualified as a forecast."
IN_SAMPLE_IS_NOT_SKILL = "A better in-sample fit is not forecast skill."

PUBLISHED_CONFIG = {
    "config_id": "autoregressive-benchmark-v1",
    "label": "Autoregressive benchmark for industrial production log-growth",
}


class AutoregressiveBenchmarkConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    config_id: str = Field(min_length=1)
    label: str = Field(min_length=1)


@dataclass(frozen=True, slots=True)
class LogGrowthSample:
    growth_months: tuple[date, ...]
    values: tuple[float, ...]
    level_months: tuple[date, ...]
    excluded_growth_months: int


def implementation_hash() -> str:
    payload = "|".join(
        (
            AUTOREGRESSIVE_BENCHMARK,
            METHOD_VERSION,
            f"max-lag-{MAX_LAG}",
            f"min-estimation-{MIN_ESTIMATION_MONTHS}",
            f"horizons-{','.join(str(horizon) for horizon in HORIZONS)}",
            f"ljung-box-{LJUNG_BOX_LAG}",
            f"adf-max-lag-{ADF_MAX_LAG}",
            "aic-common-sample",
            "expanding-window",
            "historical-mean-same-window",
            "no-second-difference",
            "no-full-sample-standardisation",
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


def contiguous_monthly_log_growth(levels: Mapping[date, float]) -> LogGrowthSample:
    """Natural log difference of adjacent positive levels. Gaps are not filled.

    The returned run is the earliest longest contiguous monthly sequence.
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
        return LogGrowthSample((), (), (), 0)
    chosen = _longest_run([month for month, _value in candidates])
    chosen_set = set(chosen)
    values = tuple(value for month, value in candidates if month in chosen_set)
    months = tuple(month for month in chosen)
    level_months = (previous_month(months[0]), *months)
    return LogGrowthSample(
        growth_months=months,
        values=values,
        level_months=level_months,
        excluded_growth_months=len(candidates) - len(months),
    )


def benchmark_from_growth(
    growth: Sequence[float],
    *,
    include_origins: bool = False,
) -> dict[str, object]:
    """Fit and score one log-growth series. Does not difference the series."""
    values = np.asarray(list(growth), dtype=float)
    if values.size < MINIMUM_GROWTH_MONTHS or not np.all(np.isfinite(values)):
        return _insufficient_payload(
            "The monthly log-growth sample is shorter than the predeclared "
            f"minimum of {MINIMUM_GROWTH_MONTHS} months.",
        )
    try:
        lag, coefficients, aic = select_ar_lag(values)
        residuals = in_sample_residuals(values, lag, coefficients)
        evaluation = rolling_origin_evaluation(values, include_origins=include_origins)
    except ValueError:
        return _insufficient_payload("The autoregression did not return finite coefficients.")
    if not evaluation["horizons"]:
        return _insufficient_payload("Rolling-origin scores were not available.")
    qualified = all(horizon["beat_historical_mean"] is True for horizon in evaluation["horizons"])
    stationarity = augmented_dickey_fuller(values)
    diagnostic = ljung_box(residuals, lag)
    payload: dict[str, object] = {
        "sufficient": True,
        "method_id": AUTOREGRESSIVE_BENCHMARK,
        "publication_allowed": PUBLICATION_ALLOWED,
        "product_forecast": False,
        "validation_baseline": True,
        "modelled_transformation": "monthly_log_growth",
        "second_difference_applied": False,
        "full_sample_standardisation": False,
        "in_sample_fit_is_not_forecast_skill": True,
        "empirically_qualified_as_forecast": qualified,
        "qualification_statement": _qualification_statement(qualified, evaluation["horizons"]),
        "growth_month_count": int(values.size),
        "full_sample_mean": round(float(values.mean()), 8),
        "predeclared": {
            "max_lag": MAX_LAG,
            "min_estimation_months": MIN_ESTIMATION_MONTHS,
            "horizons": list(HORIZONS),
            "ljung_box_lag": LJUNG_BOX_LAG,
            "adf_max_lag": ADF_MAX_LAG,
            "adf_significance": ADF_SIGNIFICANCE,
            "information_criterion": "aic",
            "window": "expanding",
            "benchmark": "historical_mean_of_the_estimation_window",
        },
        "stationarity": stationarity,
        "in_sample": {
            "aic_lag": lag,
            "aic": round(aic, 6) if math.isfinite(aic) else None,
            "lag_is_not_reused_for_rolling_forecasts": True,
            "residual_diagnostic": diagnostic,
        },
        "in_sample_aic_lag": lag,
        "forecast_evaluation": evaluation["summary"],
        "horizons": evaluation["horizons"],
        "forecast_lag_counts": evaluation["forecast_lag_counts"],
        "modal_origin_lag": evaluation["modal_origin_lag"],
        "first_origin_historical_mean": evaluation["first_origin_historical_mean"],
    }
    if include_origins:
        payload["origins"] = evaluation["origins"]
    return payload


def select_ar_lag(growth: np.ndarray) -> tuple[int, np.ndarray, float]:
    """AIC on a common sample. Ties keep the smaller lag. The maximum lag is 12."""
    if int(growth.size) <= MAX_LAG + MAX_LAG + 1:
        raise ValueError("the estimation window is too short for lag selection")
    best_lag = 1
    best_aic = math.inf
    best_coefficients: np.ndarray | None = None
    sample_size = int(growth.size) - MAX_LAG
    for lag in range(1, MAX_LAG + 1):
        coefficients, rss = _fit_rss(growth, lag)
        aic = _aic_value(rss, sample_size, lag)
        if aic < best_aic:
            best_aic = aic
            best_lag = lag
            best_coefficients = coefficients
    if best_coefficients is None or not np.all(np.isfinite(best_coefficients)):
        raise ValueError("autoregressive coefficients are not finite")
    return best_lag, best_coefficients, best_aic


def in_sample_residuals(
    growth: np.ndarray,
    lag: int,
    coefficients: np.ndarray,
) -> np.ndarray:
    design, target = _design(growth, lag, MAX_LAG, int(growth.size))
    return target - design @ coefficients


def augmented_dickey_fuller(growth: np.ndarray) -> dict[str, object]:
    """Record the check. Never difference the log-growth as a result of it."""
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            statistic, p_value, used_lag, observation_count, critical, _icbest = adfuller(
                np.asarray(growth, dtype=float),
                maxlag=ADF_MAX_LAG,
                regression="c",
                autolag="AIC",
            )
        statistic_f = float(statistic)
        p_value_f = float(p_value)
        if not math.isfinite(statistic_f) or not math.isfinite(p_value_f):
            raise ValueError("non-finite augmented Dickey-Fuller result")
    except (ValueError, np.linalg.LinAlgError):
        return {
            "computed": False,
            "test": "augmented_dickey_fuller",
            "regression": "constant",
            "max_lag": ADF_MAX_LAG,
            "autolag": "AIC",
            "second_difference_applied": False,
            "reason": "The augmented Dickey-Fuller check did not return a result.",
        }
    return {
        "computed": True,
        "test": "augmented_dickey_fuller",
        "regression": "constant",
        "max_lag": ADF_MAX_LAG,
        "autolag": "AIC",
        "statistic": round(statistic_f, 6),
        "p_value": round(p_value_f, 6),
        "used_lag": int(used_lag),
        "observation_count": int(observation_count),
        "critical_value_five_percent": round(float(critical["5%"]), 6),
        "rejected_unit_root_at_five_percent": p_value_f < ADF_SIGNIFICANCE,
        "second_difference_applied": False,
        "null_hypothesis": "The monthly log-growth has a unit root.",
    }


def ljung_box(residuals: np.ndarray, model_df: int) -> dict[str, object]:
    """Ljung-Box at the predeclared lag. A rejection does not add lags or differences."""
    residual_values = np.asarray(residuals, dtype=float)
    base = {
        "test": "ljung_box",
        "lag": LJUNG_BOX_LAG,
        "model_df": model_df,
    }
    if (
        residual_values.size <= LJUNG_BOX_LAG
        or model_df >= LJUNG_BOX_LAG
        or not np.all(np.isfinite(residual_values))
        or float(residual_values @ residual_values) <= 1e-18
    ):
        return {
            **base,
            "computed": False,
            "reason": "The Ljung-Box check was not computed for these residuals.",
        }
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            table = acorr_ljungbox(
                residual_values,
                lags=[LJUNG_BOX_LAG],
                model_df=model_df,
                return_df=True,
            )
        statistic = float(table["lb_stat"].iloc[0])
        p_value = float(table["lb_pvalue"].iloc[0])
    except (ValueError, np.linalg.LinAlgError, KeyError, IndexError):
        statistic = math.nan
        p_value = math.nan
    if not math.isfinite(statistic) or not math.isfinite(p_value):
        return {
            **base,
            "computed": False,
            "reason": "The Ljung-Box check did not return a result.",
        }
    return {
        **base,
        "computed": True,
        "statistic": round(statistic, 6),
        "p_value": round(p_value, 6),
        "rejects_uncorrelated_residuals_at_five_percent": p_value < ADF_SIGNIFICANCE,
    }


def rolling_origin_evaluation(
    growth: np.ndarray,
    *,
    include_origins: bool = False,
) -> dict[str, object]:
    """Expanding windows. Forecasts use only growth observations inside the window."""
    sample_size = int(growth.size)
    errors = {horizon: {"autoregressive": [], "historical_mean": []} for horizon in HORIZONS}
    lag_counts = {lag: 0 for lag in range(1, MAX_LAG + 1)}
    origins: list[dict[str, object]] = []
    first_origin_historical_mean: float | None = None
    for estimation_length in range(MIN_ESTIMATION_MONTHS, sample_size):
        window = growth[:estimation_length]
        lag, coefficients, _aic = select_ar_lag(window)
        lag_counts[lag] += 1
        historical_mean = float(window.mean())
        if first_origin_historical_mean is None:
            first_origin_historical_mean = historical_mean
        path = _iterate_forecast(window, coefficients, max(HORIZONS))
        origin_forecasts: dict[str, dict[str, float]] = {}
        for horizon in HORIZONS:
            target_index = estimation_length + horizon - 1
            if target_index >= sample_size:
                continue
            actual = float(growth[target_index])
            predicted = path[horizon - 1]
            errors[horizon]["autoregressive"].append(actual - predicted)
            errors[horizon]["historical_mean"].append(actual - historical_mean)
            origin_forecasts[str(horizon)] = {
                "autoregressive": predicted,
                "historical_mean": historical_mean,
                "actual": actual,
            }
        if include_origins:
            origins.append(
                {
                    "estimation_length": estimation_length,
                    "selected_lag": lag,
                    "historical_mean": historical_mean,
                    "forecasts": origin_forecasts,
                },
            )
    horizons = [_horizon_score(horizon, errors[horizon]) for horizon in HORIZONS]
    counts = [{"lag": lag, "origins": count} for lag, count in lag_counts.items() if count > 0]
    modal = max(counts, key=lambda row: (row["origins"], -int(row["lag"])))
    return {
        "summary": {
            "window": "expanding",
            "min_estimation_months": MIN_ESTIMATION_MONTHS,
            "benchmark": "historical_mean_of_the_estimation_window",
            "full_sample_standardisation": False,
            "lag_selected_inside_each_origin": True,
        },
        "horizons": horizons,
        "forecast_lag_counts": counts,
        "modal_origin_lag": int(modal["lag"]),
        "first_origin_historical_mean": (
            None if first_origin_historical_mean is None else round(first_origin_historical_mean, 8)
        ),
        "origins": origins,
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


class AutoregressiveBenchmarkMethod:
    """Validation baseline for one industrial production autoregression.

    Registration, for the integrator, inside ``default_method_registry``::

        registry.register(AutoregressiveBenchmarkMethod())
    """

    method_id = AUTOREGRESSIVE_BENCHMARK
    method_version = METHOD_VERSION

    def implementation_hash(self) -> str:
        return implementation_hash()

    def required_dataset_ids(self) -> tuple[str, ...]:
        return (INDUSTRIAL_PRODUCTION_DATASET_ID,)

    def parse_config(self, payload: dict[str, object]) -> AutoregressiveBenchmarkConfig:
        return AutoregressiveBenchmarkConfig.model_validate(payload)

    def config_hash(self, config: BaseModel) -> str:
        if not isinstance(config, AutoregressiveBenchmarkConfig):
            raise TypeError("expected AutoregressiveBenchmarkConfig")
        return MethodParameterDocument(
            config_id=config.config_id,
            label=config.label,
            scalars={"transformation": "monthly_log_growth"},
        ).config_hash()

    def run(self, context: MethodContext, config: BaseModel) -> MethodExecutionResult:
        if not isinstance(config, AutoregressiveBenchmarkConfig):
            raise TypeError("expected AutoregressiveBenchmarkConfig")
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
                "The contiguous monthly log-growth sample is shorter than the "
                f"predeclared minimum of {MINIMUM_GROWTH_MONTHS} months.",
            )
        calculation = benchmark_from_growth(sample.values)
        if calculation.get("sufficient") is not True:
            reason = calculation.get("reason")
            return _insufficient(
                reason
                if isinstance(reason, str)
                else "The autoregressive benchmark was not computed.",
            )
        calculation = _with_sample_identity(calculation, sample)
        observation_ids = tuple(
            series[month].observation_id for month in sample.level_months if month in series
        )
        interpretation = _interpretation(calculation)
        return MethodExecutionResult(
            sufficiency="sufficient",
            calculation=calculation,
            observation_ids=observation_ids,
            assumptions=_assumptions(sample),
            limitations=_limitations(calculation),
            missing_reason=None,
            statistical_interpretation=interpretation,
            causal_hypothesis="none",
            investment_implication="no_action",
            narrative=_narrative(calculation),
        )


def _eligible_levels(
    series: Mapping[date, EconomicObservation],
) -> dict[date, float]:
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


def _aic_value(rss: float, sample_size: int, lag: int) -> float:
    """AIC = n log(RSS/n) + 2(p+1) on the common sample."""
    if sample_size <= lag + 1 or not math.isfinite(rss) or rss < 0:
        return math.inf
    if rss == 0:
        return -math.inf
    return sample_size * math.log(rss / sample_size) + 2 * (lag + 1)


def _iterate_forecast(window: np.ndarray, coefficients: np.ndarray, horizon: int) -> list[float]:
    history = [float(value) for value in window]
    intercept = float(coefficients[0])
    phis = [float(value) for value in coefficients[1:]]
    forecasts: list[float] = []
    for _step in range(horizon):
        predicted = intercept
        for index, phi in enumerate(phis, start=1):
            predicted += phi * history[-index]
        if not math.isfinite(predicted):
            predicted = math.inf
        history.append(predicted)
        forecasts.append(predicted)
    return forecasts


def _horizon_score(horizon: int, pair: dict[str, list[float]]) -> dict[str, object]:
    autoregressive = np.asarray(pair["autoregressive"], dtype=float)
    baseline = np.asarray(pair["historical_mean"], dtype=float)
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
    if qualified:
        return (
            f"{detail} {IN_SAMPLE_IS_NOT_SKILL} {NOT_A_PRODUCT_FORECAST} "
            "Publication allowed is false."
        )
    return (
        f"{detail} {NOT_QUALIFIED} {IN_SAMPLE_IS_NOT_SKILL} {NOT_A_PRODUCT_FORECAST} "
        "Publication allowed is false."
    )


def _horizon_sentence(horizons: list[dict[str, object]]) -> str:
    parts: list[str] = []
    for horizon in horizons:
        months = horizon["horizon_months"]
        label = "one-month" if months == 1 else f"{months}-month"
        if horizon["beat_historical_mean"] is True:
            parts.append(
                f"The {label} horizon beat the historical mean on both "
                "mean absolute error and root mean squared error.",
            )
        else:
            parts.append(f"The {label} horizon did not beat the historical mean.")
    return " ".join(parts)


def _with_sample_identity(
    calculation: dict[str, object],
    sample: LogGrowthSample,
) -> dict[str, object]:
    calculation["growth_start"] = sample.growth_months[0].isoformat()
    calculation["growth_end"] = sample.growth_months[-1].isoformat()
    calculation["excluded_growth_months"] = sample.excluded_growth_months
    calculation["input_vintage"] = "latest_revised"
    calculation["dataset_id"] = INDUSTRIAL_PRODUCTION_DATASET_ID
    return calculation


def _assumptions(sample: LogGrowthSample) -> tuple[str, ...]:
    assumptions = [
        "The modelled series is the monthly natural log-growth of adjacent levels.",
        "The augmented Dickey-Fuller check does not cause a second difference.",
        (
            "Lag order is chosen by AIC on a common sample that starts after the "
            f"maximum lag of {MAX_LAG}. Ties keep the smaller lag."
        ),
        (
            "Each rolling origin selects its lag inside that origin's estimation "
            "window. The full-sample lag is not reused for those forecasts."
        ),
        (
            f"The estimation window starts at {MIN_ESTIMATION_MONTHS} growth months "
            "and then expands. The historical mean is the arithmetic mean of that "
            "same window."
        ),
        (
            "A horizon beats the historical mean only when both mean absolute error "
            "and root mean squared error are strictly lower."
        ),
        "Forecasts are not standardised on the full sample.",
    ]
    if sample.excluded_growth_months:
        assumptions.append(
            "Growth months outside the longest contiguous run were left out. "
            "Gaps were not interpolated.",
        )
    return tuple(assumptions)


def _limitations(calculation: Mapping[str, object]) -> tuple[str, ...]:
    limitations = [
        "Publication allowed is false.",
        NOT_A_PRODUCT_FORECAST,
        IN_SAMPLE_IS_NOT_SKILL,
        "The autoregressive polynomial is not constrained to be stationary.",
        "Revision sensitivity is blocked because the input is latest_revised.",
    ]
    diagnostic = calculation["in_sample"]
    if isinstance(diagnostic, dict):
        residual = diagnostic.get("residual_diagnostic")
        if (
            isinstance(residual, dict)
            and residual.get("rejects_uncorrelated_residuals_at_five_percent") is True
        ):
            limitations.append(
                "Ljung-Box rejects uncorrelated residuals at the predeclared lag. "
                "The lag was not increased to chase that diagnostic, and the "
                "log-growth was not differenced again.",
            )
    if calculation.get("empirically_qualified_as_forecast") is not True:
        limitations.append(NOT_QUALIFIED)
    return tuple(limitations)


def _interpretation(calculation: Mapping[str, object]) -> str:
    stationarity = calculation["stationarity"]
    if isinstance(stationarity, dict) and stationarity.get("computed") is True:
        if stationarity.get("rejected_unit_root_at_five_percent") is True:
            check = (
                "The augmented Dickey-Fuller check rejects a unit root in the "
                "monthly log-growth at the five percent level. "
                "The log-growth was not differenced again."
            )
        else:
            check = (
                "The augmented Dickey-Fuller check does not reject a unit root in "
                "the monthly log-growth at the five percent level. "
                "The log-growth was not differenced again."
            )
    else:
        check = (
            "The augmented Dickey-Fuller check did not return a result. "
            "The log-growth was not differenced again."
        )
    lag = calculation["in_sample_aic_lag"]
    statement = calculation["qualification_statement"]
    return (
        f"{check} The in-sample lag chosen by AIC, with a maximum of {MAX_LAG}, "
        f"is {lag}. That lag is not reused for the rolling-origin forecasts. "
        f"Ljung-Box is recorded at lag {LJUNG_BOX_LAG}. {statement}"
    )


def _narrative(calculation: Mapping[str, object]) -> str:
    statement = calculation["qualification_statement"]
    return (
        f"Autoregressive benchmark on the monthly log-growth of industrial production. {statement}"
    )


def _insufficient_payload(reason: str) -> dict[str, object]:
    return {
        "sufficient": False,
        "reason": reason,
        "method_id": AUTOREGRESSIVE_BENCHMARK,
        "publication_allowed": PUBLICATION_ALLOWED,
        "product_forecast": False,
        "validation_baseline": True,
        "second_difference_applied": False,
        "full_sample_standardisation": False,
        "empirically_qualified_as_forecast": False,
    }


def _insufficient(reason: str) -> MethodExecutionResult:
    return MethodExecutionResult(
        sufficiency="insufficient",
        calculation={
            "method_id": AUTOREGRESSIVE_BENCHMARK,
            "publication_allowed": PUBLICATION_ALLOWED,
            "product_forecast": False,
            "validation_baseline": True,
            "second_difference_applied": False,
            "empirically_qualified_as_forecast": False,
        },
        observation_ids=(),
        assumptions=(
            "The modelled series would have been monthly log-growth, without a second difference.",
        ),
        limitations=("Publication allowed is false.", NOT_A_PRODUCT_FORECAST),
        missing_reason=reason,
        statistical_interpretation="The autoregressive benchmark was not computed.",
        causal_hypothesis="none",
        investment_implication="insufficient_evidence",
        narrative=f"Autoregressive benchmark incomplete. Reason: {reason}",
    )
