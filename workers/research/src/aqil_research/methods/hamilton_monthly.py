"""Monthly industrial-production Markov switching.

This is not a reproduction of Hamilton 1989 quarterly US GNP. The series is
the stored G.17 industrial production index, transformed to monthly
log-growth. Estimation uses the full latest-revised sample. It is not a
real-time assessment.

Two regimes. The mean switches. Autoregressive coefficients, when the chosen
lag is positive, and the innovation variance do not switch. Transition
probabilities are constant. Lag length is chosen from {0, 1, 2, 3, 4} by BIC
on one common comparison sample. Regime 0 in the stored output is the lower
estimated mean. That ordering is a label normalisation, not a recession name.

Smoothed probabilities use future observations. Filtered probabilities use
growth through the month being classified, but the parameters are estimated
on the full sample, so neither path is what an observer could have known at
the time.
"""

from __future__ import annotations

import hashlib
import math
import warnings
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

import numpy as np
from pydantic import BaseModel, ConfigDict, Field
from statsmodels.tools.sm_exceptions import ConvergenceWarning
from statsmodels.tsa.regime_switching.markov_autoregression import MarkovAutoregression
from statsmodels.tsa.regime_switching.markov_regression import MarkovRegression

from aqil_research.contracts.observation import AnalysisMode
from aqil_research.methods.bry_boschan_monthly import (
    G17_DATASET_ID,
    G17InputPoint,
    assess_g17_level_input,
)
from aqil_research.methods.bry_boschan_spencer15 import (
    NBER_CHRONOLOGY_CITATION,
    NBER_REFERENCE_TURNS,
)
from aqil_research.methods.parameters import MethodParameterDocument
from aqil_research.methods.protocol import MethodContext, MethodExecutionResult

METHOD_ID = "HAMILTON_MONTHLY_REGIME_SWITCHING"
METHOD_VERSION = "1.0.0"
PUBLICATION_ALLOWED = False

REGIME_COUNT = 2
CANDIDATE_LAGS = (0, 1, 2, 3, 4)
INFORMATION_CRITERION = "bic"
TREND = "c"
SWITCHING_TREND = True
SWITCHING_AR = False
SWITCHING_VARIANCE = False
SWITCHING_EXOG = False
MISSING = "raise"
OPTIMIZER = "bfgs"
COVARIANCE_TYPE = "approx"
SEARCH_REPS = 0
SEARCH_ITER = 5
SEARCH_SCALE = 1.0
EM_SCREENING_ITERATIONS = 8
BFGS_STARTS_KEPT = 3
BFGS_MAXITER = 200
MEAN_SPLIT_SCALES = (1.0, 0.5)
STAY_PROBABILITY_STARTS = ((0.90, 0.10), (0.70, 0.30), (0.95, 0.05))
QUANTILE_SPLITS = (0.25, 0.75)
AR_START_CLIP = 0.8
MINIMUM_MODELLED_MONTHS = 60
MEAN_SEPARATION_Z = 2.0
TRANSITION_MARGIN = 1e-4
OCCUPATION_FLOOR = 0.02
PROBABILITY_TOLERANCE = 1e-8
PROBABILITY_SUM_TOLERANCE = 1e-6

RECOVERY_SEED = 20261030
RECOVERY_OBSERVATIONS = 2000
RECOVERY_BURN_IN = 100
RECOVERY_LOW_MEAN = -0.8
RECOVERY_HIGH_MEAN = 0.6
RECOVERY_AR = 0.25
RECOVERY_VARIANCE = 0.25
RECOVERY_STAY_LOW = 0.90
RECOVERY_STAY_HIGH = 0.93
RECOVERY_ORDER = 1

VARIANT_STATEMENT = (
    "This is a monthly industrial production variant. It is not a reproduction "
    "of Hamilton 1989 quarterly US GNP."
)
FILTERED_PROBABILITY_NOTE = (
    "Filtered probabilities use growth through that month and parameters "
    "estimated on the full sample. The parameters use later months, so these "
    "probabilities are not real-time and not what an observer could have known "
    "at the time."
)
SMOOTHED_PROBABILITY_NOTE = (
    "Smoothed probabilities use the whole growth sample, including future "
    "observations. They are not real-time and not what an observer could have "
    "known at the time."
)
QUALIFICATION_STATEMENT = (
    "A retrospective full-sample fit is not an operational qualification and "
    "not an empirical qualification."
)
NBER_DIAGNOSTIC_STATEMENT = (
    "Comparison with NBER dates is a retrospective diagnostic. It does not "
    "gate the method and it is not identification."
)
CAUSAL_HYPOTHESIS = "No causal mechanism is established."

HAMILTON_MONTHLY_PUBLISHED = {
    "config_id": "hamilton_monthly_ip_v1",
    "label": "Monthly industrial production log-growth, two regimes, lag chosen by BIC",
}


class HamiltonMonthlyConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    config_id: str = Field(min_length=1)
    label: str = Field(min_length=1)


class RegimeEstimationError(RuntimeError):
    """The declared estimator could not produce a usable fit."""


@dataclass(frozen=True, slots=True)
class LagScore:
    lag: int
    log_likelihood: float
    parameter_count: int
    modelled_month_count: int
    bic: float
    library_bic: float
    aic: float


@dataclass(frozen=True, slots=True)
class RegimeFit:
    order: int
    converged: bool
    log_likelihood: float
    parameter_count: int
    bic: float
    library_bic: float
    aic: float
    modelled_periods: tuple[date, ...]
    lower_mean: float
    higher_mean: float
    innovation_variance: float
    autoregressive: tuple[float, ...]
    standard_errors: dict[str, float | None]
    transition_matrix: tuple[tuple[float, float], tuple[float, float]]
    expected_durations: tuple[float, float]
    filtered: tuple[tuple[float, float], ...]
    smoothed: tuple[tuple[float, float], ...]
    labels_swapped: bool
    optimizer_warnings: tuple[str, ...]
    mean_difference_variance: float | None
    screened_start_count: int
    successful_screen_count: int


def variant_implementation_hash() -> str:
    payload = "|".join(
        (
            METHOD_ID,
            METHOD_VERSION,
            "candidate_lags=" + ",".join(str(lag) for lag in CANDIDATE_LAGS),
            f"criterion={INFORMATION_CRITERION}",
            "tie_break=smaller_lag",
            f"k_regimes={REGIME_COUNT}",
            f"trend={TREND}",
            f"switching_trend={_flag(SWITCHING_TREND)}",
            f"switching_ar={_flag(SWITCHING_AR)}",
            f"switching_variance={_flag(SWITCHING_VARIANCE)}",
            f"switching_exog={_flag(SWITCHING_EXOG)}",
            "time_varying_transitions=false",
            f"search_reps={SEARCH_REPS}",
            f"em_iterations={EM_SCREENING_ITERATIONS}",
            f"bfgs_starts={BFGS_STARTS_KEPT}",
            f"bfgs_maxiter={BFGS_MAXITER}",
            f"optimizer={OPTIMIZER}",
            f"covariance={COVARIANCE_TYPE}",
            "normalisation=lower_mean_first",
            f"dataset={G17_DATASET_ID}",
            "transformation=monthly_log_growth",
            "not_hamilton_1989_quarterly_us_gnp",
        ),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def switching_specification() -> dict[str, object]:
    """Estimator settings that are passed explicitly to statsmodels."""

    return {
        "regimes": REGIME_COUNT,
        "trend": TREND,
        "switching_trend": SWITCHING_TREND,
        "switching_autoregression": SWITCHING_AR,
        "switching_variance": SWITCHING_VARIANCE,
        "switching_exogenous": SWITCHING_EXOG,
        "exogenous_regressors": False,
        "time_varying_transitions": False,
        "missing": MISSING,
        "optimizer": OPTIMIZER,
        "maximum_iterations": BFGS_MAXITER,
        "covariance": COVARIANCE_TYPE,
        "random_search_repetitions": SEARCH_REPS,
        "random_search_note": (
            "Random start search is off. Starting values come from a fixed "
            "grid, then a fixed number of expectation-maximisation iterations, "
            "then BFGS from the best screened starts."
        ),
        "expectation_maximisation_iterations": EM_SCREENING_ITERATIONS,
        "bfgs_starts_kept": BFGS_STARTS_KEPT,
        "regime_normalisation": "The lower estimated mean is stored first.",
        "estimator": (
            "statsmodels MarkovRegression when the lag is 0, and statsmodels "
            "MarkovAutoregression when the lag is 1, 2, 3, or 4"
        ),
    }


def choose_lag(scores: tuple[LagScore, ...]) -> int:
    """Smallest BIC on the predeclared lag set. An exact tie uses the smaller lag."""

    found = tuple(score.lag for score in scores)
    if tuple(sorted(found)) != CANDIDATE_LAGS:
        raise ValueError("lag scores must be exactly the predeclared set {0, 1, 2, 3, 4}")
    counts = {score.modelled_month_count for score in scores}
    if len(counts) != 1:
        raise ValueError("lag scores must use the same modelled month count")
    return min(scores, key=lambda score: (score.bic, score.lag)).lag


def seeded_parameter_recovery() -> dict[str, object]:
    """Recover a known parameter vector from one seeded simulation.

    The draw is not industrial production and it is not a recession. The check
    is whether the declared estimator can find the parameters that generated
    the series.
    """

    values = _simulate_recovery_series()
    periods = tuple(_month_starts(date(1900, 1, 1), len(values)))
    fit = fit_two_regime(tuple(zip(periods, values, strict=True)), RECOVERY_ORDER)
    truth = {
        "lower_mean": RECOVERY_LOW_MEAN,
        "higher_mean": RECOVERY_HIGH_MEAN,
        "innovation_variance": RECOVERY_VARIANCE,
        "stay_lower_mean": RECOVERY_STAY_LOW,
        "lower_given_higher": 1.0 - RECOVERY_STAY_HIGH,
        "autoregressive_lag_1": RECOVERY_AR,
    }
    stay_lower = fit.transition_matrix[0][0]
    lower_given_higher = fit.transition_matrix[0][1]
    autoregressive = fit.autoregressive[0] if fit.autoregressive else math.nan
    estimate = {
        "lower_mean": fit.lower_mean,
        "higher_mean": fit.higher_mean,
        "innovation_variance": fit.innovation_variance,
        "stay_lower_mean": stay_lower,
        "lower_given_higher": lower_given_higher,
        "autoregressive_lag_1": autoregressive,
    }
    errors = {name: abs(float(estimate[name]) - float(truth[name])) for name in truth}
    diagnosis = _identification(fit)
    return {
        "seed": RECOVERY_SEED,
        "observations": RECOVERY_OBSERVATIONS,
        "burn_in": RECOVERY_BURN_IN,
        "order": RECOVERY_ORDER,
        "data": "seeded simulation",
        "not_a_recession_claim": True,
        "not_hamilton_1989_quarterly_us_gnp": True,
        "specification": switching_specification(),
        "truth": {key: _num(float(value)) for key, value in truth.items()},
        "estimate": {key: _num(float(value)) for key, value in estimate.items()},
        "absolute_errors": {key: _num(value) for key, value in errors.items()},
        "maximum_absolute_error": _num(max(errors.values())),
        "converged": fit.converged,
        "regimes_look_identified": diagnosis["regimes_look_identified"],
        "statement": (
            "Parameter recovery on a seeded simulation is a numerical check. "
            "It is not a claim about recessions."
        ),
    }


def fit_two_regime(
    observations: tuple[tuple[date, float], ...],
    order: int,
) -> RegimeFit:
    """Fit the declared two-regime specification at one lag."""

    if order not in CANDIDATE_LAGS:
        raise RegimeEstimationError(f"lag {order} is outside the predeclared set")
    if len(observations) <= order:
        raise RegimeEstimationError("there are not enough months for this lag")
    periods = tuple(period for period, _value in observations)
    values = np.asarray([value for _period, value in observations], dtype=float)
    if not np.isfinite(values).all():
        raise RegimeEstimationError("log-growth is not finite")
    model = _markov_model(values, order)
    screened, screened_count = _screen_starts(model, values, order)
    if not screened:
        raise RegimeEstimationError("every deterministic start failed during screening")
    best: tuple[tuple[bool, float], object] | None = None
    warnings_seen: list[str] = []
    attempts = screened[:BFGS_STARTS_KEPT]
    for _score, start in attempts:
        try:
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always", ConvergenceWarning)
                result = model.fit(start_params=start, **_fit_keywords())
            warnings_seen.extend(str(item.message) for item in caught)
        except (FloatingPointError, np.linalg.LinAlgError, RuntimeError, ValueError):
            continue
        likelihood = float(result.llf)
        if not math.isfinite(likelihood):
            continue
        converged = bool(result.mle_retvals.get("converged"))
        rank = (converged, likelihood)
        if best is None or rank > best[0]:
            best = (rank, result)
    if best is None:
        raise RegimeEstimationError("BFGS did not return a finite likelihood")
    result = best[1]
    return _fit_from_result(
        result,
        order=order,
        periods=periods,
        optimizer_warnings=tuple(dict.fromkeys(warnings_seen)),
        screened_start_count=screened_count,
        successful_screen_count=len(screened),
    )


class HamiltonMonthlyMethod:
    method_id = METHOD_ID
    method_version = METHOD_VERSION

    def implementation_hash(self) -> str:
        return variant_implementation_hash()

    def required_dataset_ids(self) -> tuple[str, ...]:
        return (G17_DATASET_ID,)

    def parse_config(self, payload: dict[str, object]) -> HamiltonMonthlyConfig:
        return HamiltonMonthlyConfig.model_validate(payload)

    def config_hash(self, config: BaseModel) -> str:
        if not isinstance(config, HamiltonMonthlyConfig):
            raise TypeError("expected HamiltonMonthlyConfig")
        return MethodParameterDocument(
            config_id=config.config_id,
            label=config.label,
            scalars={
                "regimes": str(REGIME_COUNT),
                "candidate_lags": ",".join(str(lag) for lag in CANDIDATE_LAGS),
                "information_criterion": INFORMATION_CRITERION,
                "switching_trend": _flag(SWITCHING_TREND),
                "switching_autoregression": _flag(SWITCHING_AR),
                "switching_variance": _flag(SWITCHING_VARIANCE),
                "switching_exogenous": _flag(SWITCHING_EXOG),
                "trend": TREND,
                "time_varying_transitions": "false",
            },
        ).config_hash()

    def run(self, context: MethodContext, config: BaseModel) -> MethodExecutionResult:
        if not isinstance(config, HamiltonMonthlyConfig):
            raise TypeError("expected HamiltonMonthlyConfig")
        if context.analysis_mode is not AnalysisMode.LATEST_REVISED:
            return _insufficient(
                "The stored G.17 file is latest_revised. This variant does not "
                "estimate a point-in-time path.",
            )
        series = context.inputs_by_dataset.get(G17_DATASET_ID, {})
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
            return _insufficient("; ".join(assessment.reasons) or "G.17 input is ineligible")
        chosen = [
            series[period]
            for period in sorted(series)
            if assessment.sample_start <= period <= assessment.sample_end
        ]
        levels = tuple(
            (observation.period_start, observation.decimal_value()) for observation in chosen
        )
        if any(value <= 0 for _period, value in levels):
            return _insufficient("Log-growth needs a positive industrial production index.")
        growth = _log_growth(levels)
        modelled_floor = CANDIDATE_LAGS[-1] + MINIMUM_MODELLED_MONTHS
        if len(growth) < modelled_floor:
            return _insufficient(
                "The growth sample is shorter than the declared minimum of "
                f"{MINIMUM_MODELLED_MONTHS} modelled months after the longest candidate lag.",
            )
        try:
            scores, comparison_start = _score_lags(growth)
            chosen_lag = choose_lag(scores)
            stored = fit_two_regime(growth, chosen_lag)
        except (RegimeEstimationError, ValueError) as exc:
            return _insufficient(str(exc))
        diagnosis = _identification(stored)
        identified = bool(diagnosis["regimes_look_identified"])
        calculation = _calculation(
            levels=levels,
            growth=growth,
            scores=scores,
            comparison_start=comparison_start,
            chosen_lag=chosen_lag,
            stored=stored,
            diagnosis=diagnosis,
        )
        return MethodExecutionResult(
            sufficiency="sufficient",
            calculation=calculation,
            observation_ids=tuple(observation.observation_id for observation in chosen),
            assumptions=_assumptions(),
            limitations=_limitations(),
            missing_reason=None,
            statistical_interpretation=(
                "Retrospective probabilities that monthly industrial production "
                "log-growth was drawn from the lower-mean or higher-mean regime. "
                "Filtered and smoothed probabilities are different. Smoothed "
                "probabilities use future observations. This is not a real-time "
                "assessment, not a recession date, and not Hamilton 1989 quarterly "
                "US GNP."
            ),
            causal_hypothesis=CAUSAL_HYPOTHESIS,
            investment_implication="no_action",
            narrative=_narrative(chosen_lag, identified),
        )


def _score_lags(
    growth: tuple[tuple[date, float], ...],
) -> tuple[tuple[LagScore, ...], int]:
    comparison_start = CANDIDATE_LAGS[-1]
    scores: list[LagScore] = []
    expected_count: int | None = None
    for lag in CANDIDATE_LAGS:
        window = growth[comparison_start - lag :]
        fit = fit_two_regime(window, lag)
        if fit.modelled_periods[0] != growth[comparison_start][0]:
            raise RegimeEstimationError("lag criteria are not aligned on the same first month")
        if expected_count is None:
            expected_count = len(fit.modelled_periods)
        elif len(fit.modelled_periods) != expected_count:
            raise RegimeEstimationError("lag criteria were not scored on the same month count")
        scores.append(
            LagScore(
                lag=lag,
                log_likelihood=fit.log_likelihood,
                parameter_count=fit.parameter_count,
                modelled_month_count=len(fit.modelled_periods),
                bic=fit.bic,
                library_bic=fit.library_bic,
                aic=fit.aic,
            ),
        )
    return tuple(scores), comparison_start


def _markov_model(values: np.ndarray, order: int) -> MarkovRegression:
    if order == 0:
        return MarkovRegression(
            values,
            k_regimes=REGIME_COUNT,
            trend=TREND,
            exog=None,
            order=0,
            exog_tvtp=None,
            switching_trend=SWITCHING_TREND,
            switching_exog=SWITCHING_EXOG,
            switching_variance=SWITCHING_VARIANCE,
            missing=MISSING,
        )
    return MarkovAutoregression(
        values,
        k_regimes=REGIME_COUNT,
        order=order,
        trend=TREND,
        exog=None,
        exog_tvtp=None,
        switching_ar=SWITCHING_AR,
        switching_trend=SWITCHING_TREND,
        switching_exog=SWITCHING_EXOG,
        switching_variance=SWITCHING_VARIANCE,
        missing=MISSING,
    )


def _fit_keywords() -> dict[str, object]:
    return {
        "transformed": True,
        "method": OPTIMIZER,
        "maxiter": BFGS_MAXITER,
        "full_output": True,
        "disp": False,
        "em_iter": 0,
        "search_reps": SEARCH_REPS,
        "search_iter": SEARCH_ITER,
        "search_scale": SEARCH_SCALE,
        "cov_type": COVARIANCE_TYPE,
    }


def _screen_starts(
    model: MarkovRegression,
    values: np.ndarray,
    order: int,
) -> tuple[list[tuple[float, np.ndarray]], int]:
    starts = _deterministic_starts(model, values, order)
    screened: list[tuple[float, np.ndarray]] = []
    for start in starts:
        try:
            with np.errstate(all="ignore"):
                improved = np.asarray(
                    model._fit_em(  # noqa: SLF001
                        start,
                        transformed=True,
                        maxiter=EM_SCREENING_ITERATIONS,
                        tolerance=0,
                        return_params=True,
                    ),
                    dtype=float,
                )
                likelihood = float(model.loglike(improved, transformed=True))
        except (FloatingPointError, np.linalg.LinAlgError, RuntimeError, ValueError):
            continue
        if math.isfinite(likelihood):
            screened.append((likelihood, improved))
    screened.sort(key=lambda item: item[0], reverse=True)
    return screened, len(starts)


def _deterministic_starts(
    model: MarkovRegression,
    values: np.ndarray,
    order: int,
) -> tuple[np.ndarray, ...]:
    names = [str(name) for name in model.param_names]
    _require_parameter_names(names, order)
    index = {name: position for position, name in enumerate(names)}
    base = np.asarray(model.start_params, dtype=float).copy()
    centre = float(np.mean(values))
    scale = float(np.std(values))
    if scale == 0.0:
        scale = 1e-6
    variance = max(float(np.var(values)), 1e-8)
    low_quantile, high_quantile = (float(item) for item in np.quantile(values, QUANTILE_SPLITS))
    mean_pairs = []
    for width in MEAN_SPLIT_SCALES:
        left = centre - width * scale
        right = centre + width * scale
        mean_pairs.append((left, right))
        mean_pairs.append((right, left))
    mean_pairs.append((low_quantile, high_quantile))
    mean_pairs.append((high_quantile, low_quantile))
    ar_starts = _autoregressive_starts(values, order)
    starts: list[np.ndarray] = []
    for low_mean, high_mean in mean_pairs:
        for stay_low, enter_low in STAY_PROBABILITY_STARTS:
            for autoregressive in ar_starts:
                params = base.copy()
                params[index["p[0->0]"]] = stay_low
                params[index["p[1->0]"]] = enter_low
                params[index["const[0]"]] = low_mean
                params[index["const[1]"]] = high_mean
                params[index["sigma2"]] = variance
                for lag, coefficient in enumerate(autoregressive, start=1):
                    params[index[f"ar.L{lag}"]] = coefficient
                starts.append(params)
    starts.append(base.copy())
    return tuple(starts)


def _autoregressive_starts(values: np.ndarray, order: int) -> tuple[tuple[float, ...], ...]:
    if order == 0:
        return ((),)
    zeros = tuple(0.0 for _ in range(order))
    lagged = [0.0 for _ in range(order)]
    lagged[0] = _clipped_ar1(values)
    return (zeros, tuple(lagged))


def _clipped_ar1(values: np.ndarray) -> float:
    if len(values) < 2:
        return 0.0
    lagged = values[:-1]
    current = values[1:]
    denominator = float(np.dot(lagged, lagged))
    if denominator == 0.0:
        return 0.0
    return float(np.clip(np.dot(lagged, current) / denominator, -AR_START_CLIP, AR_START_CLIP))


def _fit_from_result(
    result: object,
    *,
    order: int,
    periods: tuple[date, ...],
    optimizer_warnings: tuple[str, ...],
    screened_start_count: int,
    successful_screen_count: int,
) -> RegimeFit:
    names = [str(name) for name in result.model.param_names]  # type: ignore[attr-defined]
    _require_parameter_names(names, order)
    params = {
        name: float(value)
        for name, value in zip(names, np.asarray(result.params, dtype=float), strict=True)  # type: ignore[attr-defined]
    }
    bse_values = np.asarray(result.bse, dtype=float)  # type: ignore[attr-defined]
    standard_error_by_name = {
        name: None if not math.isfinite(float(bse_values[index])) else float(bse_values[index])
        for index, name in enumerate(names)
    }
    filtered = np.asarray(result.filtered_marginal_probabilities, dtype=float)  # type: ignore[attr-defined]
    smoothed = np.asarray(result.smoothed_marginal_probabilities, dtype=float)  # type: ignore[attr-defined]
    if filtered.shape != smoothed.shape or filtered.ndim != 2 or filtered.shape[1] != REGIME_COUNT:
        raise RegimeEstimationError(
            "filtered and smoothed probabilities do not have the same two-regime shape",
        )
    transition = np.asarray(result.regime_transition, dtype=float)  # type: ignore[attr-defined]
    if transition.shape == (REGIME_COUNT, REGIME_COUNT, 1):
        transition = transition[:, :, 0]
    if transition.shape != (REGIME_COUNT, REGIME_COUNT):
        raise RegimeEstimationError("the transition matrix is not two by two")
    modelled_periods = periods[order:]
    if len(modelled_periods) != filtered.shape[0] or len(modelled_periods) != int(result.nobs):  # type: ignore[attr-defined]
        raise RegimeEstimationError("modelled months do not match the estimator sample")
    means = np.array([params["const[0]"], params["const[1]"]], dtype=float)
    mean_errors = np.array(
        [
            math.nan
            if standard_error_by_name["const[0]"] is None
            else standard_error_by_name["const[0]"],
            math.nan
            if standard_error_by_name["const[1]"] is None
            else standard_error_by_name["const[1]"],
        ],
        dtype=float,
    )
    transition_errors = np.array(
        [
            math.nan
            if standard_error_by_name["p[0->0]"] is None
            else standard_error_by_name["p[0->0]"],
            math.nan
            if standard_error_by_name["p[1->0]"] is None
            else standard_error_by_name["p[1->0]"],
        ],
        dtype=float,
    )
    library_durations = np.asarray(result.expected_durations, dtype=float).reshape(REGIME_COUNT)  # type: ignore[attr-defined]
    ordered = _order_by_lower_mean(
        means=means,
        mean_errors=mean_errors,
        transition=transition,
        transition_errors=transition_errors,
        filtered=filtered,
        smoothed=smoothed,
        durations=library_durations,
    )
    log_likelihood = float(result.llf)  # type: ignore[attr-defined]
    parameter_count = len(names)
    month_count = len(modelled_periods)
    autoregressive = tuple(params[f"ar.L{lag}"] for lag in range(1, order + 1))
    ar_errors = {
        f"autoregressive_lag_{lag}": standard_error_by_name[f"ar.L{lag}"]
        for lag in range(1, order + 1)
    }
    stored_errors: dict[str, float | None] = {
        "lower_mean": _optional_num(ordered.mean_errors[0]),
        "higher_mean": _optional_num(ordered.mean_errors[1]),
        "innovation_variance": _optional_num(standard_error_by_name["sigma2"]),
        "stay_lower_mean": _optional_num(ordered.transition_errors[0]),
        "lower_given_higher": _optional_num(ordered.transition_errors[1]),
    }
    stored_errors.update(
        {
            key: _optional_num(value) if value is not None else None
            for key, value in ar_errors.items()
        },
    )
    return RegimeFit(
        order=order,
        converged=bool(result.mle_retvals.get("converged")),  # type: ignore[attr-defined]
        log_likelihood=log_likelihood,
        parameter_count=parameter_count,
        bic=bayesian_information_criterion(log_likelihood, parameter_count, month_count),
        library_bic=float(result.bic),  # type: ignore[attr-defined]
        aic=akaike_information_criterion(log_likelihood, parameter_count),
        modelled_periods=modelled_periods,
        lower_mean=float(ordered.means[0]),
        higher_mean=float(ordered.means[1]),
        innovation_variance=params["sigma2"],
        autoregressive=autoregressive,
        standard_errors=stored_errors,
        transition_matrix=_matrix(ordered.transition),
        expected_durations=(float(ordered.durations[0]), float(ordered.durations[1])),
        filtered=_probability_rows(ordered.filtered),
        smoothed=_probability_rows(ordered.smoothed),
        labels_swapped=ordered.swapped,
        optimizer_warnings=optimizer_warnings,
        mean_difference_variance=_mean_difference_variance(result, names),
        screened_start_count=screened_start_count,
        successful_screen_count=successful_screen_count,
    )


@dataclass(frozen=True, slots=True)
class _OrderedRegimes:
    means: np.ndarray
    mean_errors: np.ndarray
    transition: np.ndarray
    transition_errors: np.ndarray
    filtered: np.ndarray
    smoothed: np.ndarray
    durations: np.ndarray
    swapped: bool


def _order_by_lower_mean(
    *,
    means: np.ndarray,
    mean_errors: np.ndarray,
    transition: np.ndarray,
    transition_errors: np.ndarray,
    filtered: np.ndarray,
    smoothed: np.ndarray,
    durations: np.ndarray,
) -> _OrderedRegimes:
    swap = bool(np.isfinite(means).all() and means[0] > means[1])
    order = np.array([1, 0] if swap else [0, 1])
    reordered_transition = transition[np.ix_(order, order)]
    recomputed = _durations(reordered_transition)
    reordered_durations = durations[order]
    if not np.allclose(reordered_durations, recomputed, rtol=1e-6, atol=1e-6, equal_nan=True):
        raise RegimeEstimationError("expected durations do not match the transition matrix")
    if swap:
        # New stay-in-lower equals one minus the old probability of entering the old regime 0
        # from old regime 1. The complement has the same standard error.
        reordered_transition_errors = np.array(
            [transition_errors[1], transition_errors[0]],
            dtype=float,
        )
    else:
        reordered_transition_errors = transition_errors.copy()
    return _OrderedRegimes(
        means=means[order],
        mean_errors=mean_errors[order],
        transition=reordered_transition,
        transition_errors=reordered_transition_errors,
        filtered=filtered[:, order],
        smoothed=smoothed[:, order],
        durations=recomputed,
        swapped=swap,
    )


def _mean_difference_variance(result: object, names: list[str]) -> float | None:
    try:
        covariance = np.asarray(result.cov_params(), dtype=float)  # type: ignore[attr-defined]
        first = names.index("const[0]")
        second = names.index("const[1]")
        variance = float(
            covariance[first, first] + covariance[second, second] - 2.0 * covariance[first, second],
        )
    except (FloatingPointError, np.linalg.LinAlgError, ValueError, AttributeError):
        return None
    return variance


def _durations(transition: np.ndarray) -> np.ndarray:
    stays = np.diag(transition)
    durations = np.empty(REGIME_COUNT, dtype=float)
    for index, stay in enumerate(stays):
        if not math.isfinite(float(stay)) or float(stay) >= 1.0:
            durations[index] = math.inf
        else:
            durations[index] = 1.0 / (1.0 - float(stay))
    return durations


def _identification(fit: RegimeFit) -> dict[str, object]:
    reasons: list[str] = []
    if not fit.converged:
        reasons.append("The optimiser did not report convergence.")
    if not math.isfinite(fit.log_likelihood):
        reasons.append("The log-likelihood is not finite.")
    if not math.isfinite(fit.lower_mean) or not math.isfinite(fit.higher_mean):
        reasons.append("A regime mean is not finite.")
    if not math.isfinite(fit.innovation_variance) or fit.innovation_variance <= 0.0:
        reasons.append("The innovation variance is not positive.")
    if any(not math.isfinite(coefficient) for coefficient in fit.autoregressive):
        reasons.append("An autoregressive coefficient is not finite.")
    separation_z: float | None = None
    difference_variance = fit.mean_difference_variance
    if (
        difference_variance is None
        or not math.isfinite(difference_variance)
        or difference_variance <= 0.0
    ):
        reasons.append("The variance of the mean difference is not positive.")
    else:
        separation_z = abs(fit.higher_mean - fit.lower_mean) / math.sqrt(difference_variance)
        if separation_z < MEAN_SEPARATION_Z:
            reasons.append("The regime means are not separated by two standard errors.")
    transition = np.asarray(fit.transition_matrix, dtype=float)
    if transition.shape != (REGIME_COUNT, REGIME_COUNT):
        reasons.append("The transition matrix is not two by two.")
    else:
        if not np.allclose(transition.sum(axis=0), 1.0, atol=1e-8):
            reasons.append("Transition matrix columns do not sum to one.")
        if np.any((transition <= TRANSITION_MARGIN) | (transition >= 1.0 - TRANSITION_MARGIN)):
            reasons.append(
                "A transition probability is too close to zero or one.",
            )
    for duration in fit.expected_durations:
        if not math.isfinite(duration) or duration <= 1.0:
            reasons.append(
                "An expected regime duration is not a finite stay of more than one month."
            )
            break
    filtered = np.asarray(fit.filtered, dtype=float)
    smoothed = np.asarray(fit.smoothed, dtype=float)
    reasons.extend(_probability_reasons("Filtered", filtered))
    reasons.extend(_probability_reasons("Smoothed", smoothed))
    if smoothed.ndim == 2 and smoothed.shape[1] == REGIME_COUNT and np.isfinite(smoothed).all():
        shares = smoothed.mean(axis=0)
        if float(shares.min()) < OCCUPATION_FLOOR:
            reasons.append(
                "A regime's smoothed probability share is below the occupation floor.",
            )
    unique_reasons = tuple(dict.fromkeys(reasons))
    return {
        "converged": fit.converged,
        "regimes_look_identified": not unique_reasons,
        "reasons": list(unique_reasons),
        "mean_separation_z": None if separation_z is None else _num(separation_z),
        "mean_difference_variance": (
            None
            if difference_variance is None or not math.isfinite(difference_variance)
            else _num(difference_variance)
        ),
        "mean_separation_rule": (
            "Absolute gap between the regime means, divided by the standard error "
            "of that difference from the estimated covariance. The threshold is 2."
        ),
        "occupation_floor": OCCUPATION_FLOOR,
        "transition_margin": TRANSITION_MARGIN,
        "operational": False,
        "empirically_qualified": False,
        "qualification_statement": QUALIFICATION_STATEMENT,
        "optimizer_warnings": list(fit.optimizer_warnings),
    }


def _probability_reasons(label: str, probabilities: np.ndarray) -> list[str]:
    if probabilities.ndim != 2 or probabilities.shape[1] != REGIME_COUNT:
        return [f"{label} probabilities do not have two regimes."]
    if not np.isfinite(probabilities).all():
        return [f"{label} probabilities are not finite."]
    reasons: list[str] = []
    if np.any(probabilities < -PROBABILITY_TOLERANCE) or np.any(
        probabilities > 1.0 + PROBABILITY_TOLERANCE,
    ):
        reasons.append(f"{label} probabilities are outside the unit interval.")
    if not np.allclose(probabilities.sum(axis=1), 1.0, atol=PROBABILITY_SUM_TOLERANCE):
        reasons.append(f"{label} probabilities do not sum to one.")
    return reasons


def _calculation(
    *,
    levels: tuple[tuple[date, Decimal], ...],
    growth: tuple[tuple[date, float], ...],
    scores: tuple[LagScore, ...],
    comparison_start: int,
    chosen_lag: int,
    stored: RegimeFit,
    diagnosis: dict[str, object],
) -> dict[str, object]:
    identified = bool(diagnosis["regimes_look_identified"])
    payload: dict[str, object] = {
        "method_id": METHOD_ID,
        "variant_statement": VARIANT_STATEMENT,
        "not_hamilton_1989_quarterly_us_gnp": True,
        "dataset_id": G17_DATASET_ID,
        "transformation": "monthly difference of natural logs of the level index",
        "revision": AnalysisMode.LATEST_REVISED.value,
        "retrospective_full_sample": True,
        "real_time_assessment": False,
        "publication_allowed": PUBLICATION_ALLOWED,
        "operational": False,
        "empirically_qualified": False,
        "specification": switching_specification(),
        "sample": {
            "level_start": levels[0][0].isoformat(),
            "level_end": levels[-1][0].isoformat(),
            "level_month_count": len(levels),
            "growth_start": growth[0][0].isoformat(),
            "growth_end": growth[-1][0].isoformat(),
            "growth_month_count": len(growth),
            "modelled_start": stored.modelled_periods[0].isoformat(),
            "modelled_end": stored.modelled_periods[-1].isoformat(),
            "modelled_month_count": len(stored.modelled_periods),
        },
        "lag_selection": {
            "candidate_lags": list(CANDIDATE_LAGS),
            "criterion": INFORMATION_CRITERION,
            "criterion_formula": (
                "-2 * log_likelihood + parameter_count * log(modelled_month_count)"
            ),
            "tie_break": "smaller lag",
            "comparison_sample": {
                "rule": (
                    "Every candidate is scored on the growth months that remain "
                    "after the longest candidate lag, so the information criteria "
                    "use the same months."
                ),
                "longest_candidate_lag": CANDIDATE_LAGS[-1],
                "first_modelled_period": growth[comparison_start][0].isoformat(),
                "last_modelled_period": growth[-1][0].isoformat(),
                "modelled_month_count": scores[0].modelled_month_count,
            },
            "stored_fit_sample": (
                "The stored parameters and probabilities are a fresh estimate of "
                "the chosen lag on every stored growth month that lag can use. "
                "Lag selection itself uses the common comparison sample."
            ),
            "values": [
                {
                    "lag": score.lag,
                    "log_likelihood": _num(score.log_likelihood),
                    "parameter_count": score.parameter_count,
                    "modelled_month_count": score.modelled_month_count,
                    "bic": _num(score.bic),
                    "library_bic": _num(score.library_bic),
                    "aic": _num(score.aic),
                }
                for score in scores
            ],
            "chosen_lag": chosen_lag,
        },
        "parameters": {
            "lower_mean": _num(stored.lower_mean),
            "higher_mean": _num(stored.higher_mean),
            "innovation_variance": _num(stored.innovation_variance),
            "autoregressive_coefficients": [_num(value) for value in stored.autoregressive],
            "standard_errors": stored.standard_errors,
            "labels_swapped_to_put_the_lower_mean_first": stored.labels_swapped,
        },
        "transition_matrix": {
            "from_regime": ["lower_mean", "higher_mean"],
            "to_regime": ["lower_mean", "higher_mean"],
            "probabilities": [[_num(value) for value in row] for row in stored.transition_matrix],
            "convention": (
                "Entry [to, from] is the probability of moving from the column "
                "regime to the row regime. Columns sum to one."
            ),
        },
        "expected_regime_durations_months": {
            "lower_mean": _num(stored.expected_durations[0]),
            "higher_mean": _num(stored.expected_durations[1]),
            "formula": "1 / (1 - probability of staying in the regime)",
        },
        "filtered_regime_probabilities_note": FILTERED_PROBABILITY_NOTE,
        "smoothed_regime_probabilities_note": SMOOTHED_PROBABILITY_NOTE,
        "filtered_regime_probabilities": _probability_records(
            stored.modelled_periods,
            stored.filtered,
        ),
        "smoothed_regime_probabilities": _probability_records(
            stored.modelled_periods,
            stored.smoothed,
        ),
        "estimation_diagnosis": diagnosis,
        "nber_retrospective_diagnostic": _nber_diagnostic(
            stored.modelled_periods,
            stored.smoothed,
        ),
        "screened_start_count": stored.screened_start_count,
        "successful_screen_count": stored.successful_screen_count,
        "regimes_look_identified": identified,
    }
    return _json_ready(payload)  # type: ignore[return-value]


def _nber_diagnostic(
    periods: tuple[date, ...],
    smoothed: tuple[tuple[float, float], ...],
) -> dict[str, object]:
    contraction = _nber_contraction_months()
    contraction_values: list[float] = []
    expansion_values: list[float] = []
    for period, probabilities in zip(periods, smoothed, strict=True):
        lower = probabilities[0]
        if period in contraction:
            contraction_values.append(lower)
        else:
            expansion_values.append(lower)
    return {
        "citation": NBER_CHRONOLOGY_CITATION,
        "retrospective_only": True,
        "gates_the_method": False,
        "is_identification": False,
        "contraction_month_rule": (
            "A contraction month is strictly after an NBER peak and up to and "
            "including the following trough."
        ),
        "compared_month_count": len(periods),
        "contraction_month_count": len(contraction_values),
        "expansion_month_count": len(expansion_values),
        "mean_smoothed_lower_mean_probability_in_contraction": _mean(contraction_values),
        "mean_smoothed_lower_mean_probability_in_expansion": _mean(expansion_values),
        "statement": NBER_DIAGNOSTIC_STATEMENT,
    }


def _nber_contraction_months() -> set[date]:
    months: set[date] = set()
    peak: date | None = None
    for kind, month in NBER_REFERENCE_TURNS:
        if kind == "peak":
            peak = month
            continue
        if peak is None:
            continue
        cursor = _next_month(peak)
        while cursor <= month:
            months.add(cursor)
            cursor = _next_month(cursor)
        peak = None
    return months


def _log_growth(
    levels: tuple[tuple[date, Decimal], ...],
) -> tuple[tuple[date, float], ...]:
    growth: list[tuple[date, float]] = []
    for (previous_period, previous), (period, value) in zip(levels, levels[1:], strict=False):
        del previous_period
        change = math.log(float(value)) - math.log(float(previous))
        if not math.isfinite(change):
            raise RegimeEstimationError(f"log-growth for {period.isoformat()} is not finite")
        growth.append((period, change))
    return tuple(growth)


def _simulate_recovery_series() -> np.ndarray:
    generator = np.random.default_rng(RECOVERY_SEED)
    means = np.array([RECOVERY_LOW_MEAN, RECOVERY_HIGH_MEAN])
    stay = np.array([RECOVERY_STAY_LOW, RECOVERY_STAY_HIGH])
    scale = math.sqrt(RECOVERY_VARIANCE)
    total = RECOVERY_OBSERVATIONS + RECOVERY_BURN_IN
    state = np.zeros(total, dtype=int)
    values = np.zeros(total)
    state[0] = 1
    values[0] = means[1]
    for time in range(1, total):
        previous = int(state[time - 1])
        state[time] = previous if generator.random() < stay[previous] else 1 - previous
        current = int(state[time])
        values[time] = (
            means[current]
            + RECOVERY_AR * (values[time - 1] - means[previous])
            + scale * generator.standard_normal()
        )
    return values[RECOVERY_BURN_IN:]


def _probability_records(
    periods: tuple[date, ...],
    probabilities: tuple[tuple[float, float], ...],
) -> list[dict[str, object]]:
    return [
        {
            "period": period.isoformat(),
            "lower_mean": _num(row[0]),
            "higher_mean": _num(row[1]),
        }
        for period, row in zip(periods, probabilities, strict=True)
    ]


def _probability_rows(probabilities: np.ndarray) -> tuple[tuple[float, float], ...]:
    return tuple((float(row[0]), float(row[1])) for row in probabilities)


def _matrix(transition: np.ndarray) -> tuple[tuple[float, float], tuple[float, float]]:
    return (
        (float(transition[0, 0]), float(transition[0, 1])),
        (float(transition[1, 0]), float(transition[1, 1])),
    )


def bayesian_information_criterion(
    log_likelihood: float,
    parameter_count: int,
    month_count: int,
) -> float:
    if month_count <= 0:
        raise ValueError("month count must be positive")
    return -2.0 * log_likelihood + parameter_count * math.log(month_count)


def akaike_information_criterion(log_likelihood: float, parameter_count: int) -> float:
    return -2.0 * log_likelihood + 2.0 * parameter_count


def _require_parameter_names(names: list[str], order: int) -> None:
    expected = {"p[0->0]", "p[1->0]", "const[0]", "const[1]", "sigma2"}
    expected.update(f"ar.L{lag}" for lag in range(1, order + 1))
    if set(names) != expected:
        raise RegimeEstimationError(
            f"estimator parameter names {names} do not match the declared specification",
        )


def _assumptions() -> tuple[str, ...]:
    return (
        VARIANT_STATEMENT,
        "The input is the latest-revised G.17 level index used by Bry-Boschan, "
        "transformed here to a monthly difference of natural logs.",
        "Estimation is retrospective on the stored sample. It is not a real-time assessment.",
        "The mean switches across two regimes. Autoregressive coefficients and the "
        "innovation variance do not switch. Transition probabilities are constant.",
        "Lag length is chosen from 0, 1, 2, 3, and 4 by BIC on a common comparison sample. "
        "An exact BIC tie uses the smaller lag.",
        "The stored regime order puts the lower estimated mean first. That is a label "
        "normalisation, not a recession classification.",
        SMOOTHED_PROBABILITY_NOTE,
        FILTERED_PROBABILITY_NOTE,
    )


def _limitations() -> tuple[str, ...]:
    return (
        VARIANT_STATEMENT,
        "Smoothed probabilities use future observations. They are not a real-time call.",
        QUALIFICATION_STATEMENT,
        NBER_DIAGNOSTIC_STATEMENT,
        "Publication allowed stays false.",
        "If the optimiser does not converge, or the regimes do not look identified, "
        "the diagnosis is stored and the method is not operational.",
    )


def _narrative(chosen_lag: int, identified: bool) -> str:
    if identified:
        qualification = (
            "The regimes look identified on this retrospective fit. "
            "That is not an operational qualification and not an empirical qualification."
        )
    else:
        qualification = (
            "The regimes do not look identified. The diagnosis is stored. "
            "The method is not operational and not empirically qualified."
        )
    return (
        "Two-regime Markov switching was estimated on monthly industrial production "
        "log-growth. This is a monthly industrial production variant. It is not a "
        "reproduction of Hamilton 1989 quarterly US GNP. "
        f"The chosen lag is {chosen_lag} by BIC. "
        "Filtered and smoothed probabilities are stored separately. "
        "Smoothed probabilities use future observations. "
        "This is a retrospective full-sample fit, not a real-time assessment. "
        f"{qualification} Publication allowed is false."
    )


def _insufficient(reason: str) -> MethodExecutionResult:
    return MethodExecutionResult(
        sufficiency="insufficient",
        calculation={
            "method_id": METHOD_ID,
            "variant_statement": VARIANT_STATEMENT,
            "not_hamilton_1989_quarterly_us_gnp": True,
            "publication_allowed": PUBLICATION_ALLOWED,
            "operational": False,
            "empirically_qualified": False,
            "real_time_assessment": False,
        },
        observation_ids=(),
        assumptions=(VARIANT_STATEMENT,),
        limitations=(QUALIFICATION_STATEMENT, "Publication allowed stays false."),
        missing_reason=reason,
        statistical_interpretation="The regime probabilities were not estimated.",
        causal_hypothesis="Unresolved because the inputs were insufficient.",
        investment_implication="insufficient_evidence",
        narrative=f"Regime estimation was not completed. Reason: {reason}",
    )


def _json_ready(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    if isinstance(value, tuple):
        return [_json_ready(item) for item in value]
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            return None
        return _num(value)
    if isinstance(value, np.generic):
        return _json_ready(value.item())
    raise TypeError(f"calculation value {type(value).__name__} is not JSON-ready")


def _num(value: float) -> float:
    return float(f"{float(value):.12g}")


def _optional_num(value: float | None) -> float | None:
    if value is None or not math.isfinite(value):
        return None
    return _num(value)


def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return _num(float(np.mean(values)))


def _flag(value: bool) -> str:
    return "true" if value else "false"


def _next_month(month_start: date) -> date:
    if month_start.month == 12:
        return date(month_start.year + 1, 1, 1)
    return date(month_start.year, month_start.month + 1, 1)


def _month_starts(start: date, count: int) -> tuple[date, ...]:
    return tuple(_shift_month(start, step) for step in range(count))


def _shift_month(start: date, steps: int) -> date:
    index = start.year * 12 + (start.month - 1) + steps
    year, month_zero = divmod(index, 12)
    return date(year, month_zero + 1, 1)
