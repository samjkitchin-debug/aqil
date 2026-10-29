"""Maximum-likelihood refit of the 1988 coincident orders on a prepared panel.

The modern refit is STOCK_WATSON_COINCIDENT_1988_MODERN_REFIT on the balanced
panel from January 1997. It is not the CITIBASE 1959–87 payroll specification.
Payroll headcount is not employee-hours. 2017 chained dollars are not 1982 dollars.
The filtered factor is not a smoother, not a real-time vintage, and not a GDP nowcast.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from datetime import date

import numpy as np
from pydantic import BaseModel, ConfigDict, Field
from scipy.optimize import minimize

from aqil_research.contracts.observation import AnalysisMode, SeriesProvenance
from aqil_research.methods.parameters import MethodParameterDocument
from aqil_research.methods.protocol import MethodContext, MethodExecutionResult
from aqil_research.methods.stock_watson_1988 import gaussian_log_likelihood

SPECIFICATION_ID = "STOCK_WATSON_COINCIDENT_1988_MODERN_REFIT"
METHOD_VERSION = "0.1.0"
PUBLICATION_ALLOWED = False
OPERATIONALLY_ACCEPTED = False
GRADIENT_NORM_LIMIT = 1e-3
GRADIENT_STEP = 1e-5
GRADIENT_STEP_WIDE = 1e-4
SAMPLE_START = date(1997, 1, 1)
MODERN_REFIT_DATASETS = (
    "fed.g17.IP.B50001.S",
    "bea.nipa.T20600.W875RX",
    "bea.nipa.U002BU.KPMT",
    "bls.ce.CES0000000001",
)
NOT_THE_CITIBASE_SPECIFICATION = (
    "Payroll headcount is not employee-hours. "
    "2017 chained dollars are not 1982 dollars. "
    "This is not the CITIBASE 1959–87 payroll specification."
)

# Three admissible starts. The third sits near the stored 25 October region
# without being that parameter vector. A caller may add the stored vector.
DEFAULT_STARTS: tuple[tuple[float, ...], ...] = (
    (
        0.4,
        0.1,
        0.6,
        0.5,
        0.4,
        0.5,
        0.2,
        0.0,
        0.1,
        0.0,
        0.1,
        0.0,
        0.2,
        0.0,
        0.5,
        0.5,
        0.5,
        0.5,
    ),
    (
        0.2,
        0.0,
        0.4,
        0.4,
        0.3,
        0.4,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.1,
        0.0,
        0.7,
        0.7,
        0.7,
        0.7,
    ),
    (
        0.2,
        -0.2,
        0.9,
        0.6,
        0.7,
        0.8,
        -0.1,
        -0.15,
        -0.05,
        -0.05,
        -0.15,
        -0.1,
        -0.05,
        0.15,
        0.4,
        0.75,
        0.6,
        0.5,
    ),
)


@dataclass(frozen=True, slots=True)
class FittedCoincidentFactor:
    log_likelihood: float
    loadings: tuple[float, ...]
    factor_ar: tuple[float, float]
    idiosyncratic_ar: tuple[tuple[float, float], ...]
    idiosyncratic_scale: tuple[float, ...]
    filtered_factor: tuple[float, ...]
    converged: bool
    message: str
    gradient_norm: float
    gradient_norm_wide_step: float
    maximum_likelihood_claimed: bool
    starts_evaluated: int
    smoothed_factor: tuple[float, ...]


def _stationary_ar2(first: float, second: float) -> bool:
    """AR(2) stationarity: roots of 1 - a z - b z^2 lie outside the unit circle."""
    return abs(second) < 1.0 and (first + second) < 1.0 and (second - first) < 1.0


def log_difference(levels: list[float]) -> list[float]:
    if any(value <= 0 for value in levels):
        raise ValueError("log differences require positive levels")
    return [
        math.log(levels[index]) - math.log(levels[index - 1]) for index in range(1, len(levels))
    ]


def standardise(values: list[float]) -> tuple[list[float], float, float]:
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / len(values)
    if variance <= 0:
        raise ValueError("a series has no variation")
    scale = math.sqrt(variance)
    return [(value - mean) / scale for value in values], mean, scale


def claims_maximum_likelihood(
    *,
    gradient_norm: float,
    gradient_norm_wide_step: float,
    log_likelihood: float,
    starts_evaluated: int,
) -> bool:
    """L-BFGS success is not enough. Both finite-difference steps must be small."""
    return (
        starts_evaluated >= 2
        and math.isfinite(gradient_norm)
        and math.isfinite(gradient_norm_wide_step)
        and gradient_norm <= GRADIENT_NORM_LIMIT
        and gradient_norm_wide_step <= 1e-2
        and math.isfinite(log_likelihood)
    )


def central_gradient_norm(objective, theta: np.ndarray, step: float) -> float:
    """Euclidean norm of the central difference of the negative log likelihood.

    A step that leaves the admissible region makes the norm infinite. That is
    not a zero gradient.
    """
    if step <= 0:
        raise ValueError("gradient step must be positive")
    origin = np.asarray(theta, dtype=float)
    gradient = np.empty(origin.size, dtype=float)
    for index in range(origin.size):
        forward = origin.copy()
        backward = origin.copy()
        forward[index] += step
        backward[index] -= step
        plus = float(objective(forward))
        minus = float(objective(backward))
        if not math.isfinite(plus) or not math.isfinite(minus) or plus >= 1e5 or minus >= 1e5:
            return math.inf
        gradient[index] = (plus - minus) / (2.0 * step)
    return float(np.linalg.norm(gradient))


def fit_coincident_factor(
    panel: list[list[float]],
    *,
    maxiter: int = 40,
    extra_starts: list[np.ndarray] | tuple[np.ndarray, ...] | None = None,
) -> FittedCoincidentFactor:
    """Estimate the frozen 1988 orders. panel columns are already standardised growth rates.

    More than one start is always used. Optimizer convergence does not by itself
    establish maximum likelihood. The filtered path is computed separately from
    the smoother.
    """
    if len(panel) != 4:
        raise ValueError("the 1988 model has four series")
    length = len(panel[0])
    if length < 36 or any(len(series) != length for series in panel):
        raise ValueError("the four series must share at least 36 growth-rate months")
    if maxiter < 1:
        raise ValueError("maxiter must be at least 1")
    observations = tuple(
        tuple(panel[series][time] for series in range(4)) for time in range(length)
    )

    def unpack(theta: np.ndarray) -> tuple:
        phi = (float(theta[0]), float(theta[1]))
        loadings = tuple(float(value) for value in theta[2:6])
        idiosyncratic = tuple((float(theta[6 + 2 * i]), float(theta[7 + 2 * i])) for i in range(4))
        scales = tuple(float(value) for value in theta[14:18])
        return phi, loadings, idiosyncratic, scales

    def objective(theta: np.ndarray) -> float:
        phi, loadings, idiosyncratic, scales = unpack(theta)
        if not _admissible(phi, loadings, idiosyncratic, scales):
            return 1e6
        likelihood = gaussian_log_likelihood(
            observations,
            loadings=loadings,  # type: ignore[arg-type]
            factor_ar=phi,
            idiosyncratic_ar=idiosyncratic,
            idiosyncratic_innovation_scale=scales,  # type: ignore[arg-type]
        )
        if not math.isfinite(likelihood):
            return 1e6
        return -likelihood

    starts = [np.asarray(start, dtype=float) for start in DEFAULT_STARTS]
    for extra in extra_starts or ():
        vector = np.asarray(extra, dtype=float)
        if vector.shape != (18,):
            raise ValueError("each start has 18 parameters")
        starts.append(vector)
    if len(starts) < 2:
        raise ValueError("estimation requires more than one starting point")
    best = None
    evaluated = 0
    options = {"maxiter": maxiter, "ftol": 1e-12, "gtol": 1e-5}
    for start in starts:
        evaluated += 1
        result = minimize(objective, start, method="L-BFGS-B", options=options)
        if best is None or float(result.fun) < float(best.fun):
            best = result
    assert best is not None
    if float(best.fun) < 1e5:
        evaluated += 1
        refined = minimize(
            objective, np.asarray(best.x, dtype=float), method="L-BFGS-B", options=options
        )
        if float(refined.fun) < float(best.fun):
            best = refined
    phi, loadings, idiosyncratic, scales = unpack(np.asarray(best.x, dtype=float))
    if loadings[0] < 0:
        loadings = tuple(-value for value in loadings)
        # A negative industrial-production loading is flipped so the factor sign matches production.
    admissible = _admissible(phi, loadings, idiosyncratic, scales)
    log_likelihood = -float(best.fun) if float(best.fun) < 1e5 else float("-inf")
    reported = _pack(phi, loadings, idiosyncratic, scales)
    if admissible and math.isfinite(log_likelihood):
        gradient_norm = central_gradient_norm(objective, reported, GRADIENT_STEP)
        gradient_norm_wide = central_gradient_norm(objective, reported, GRADIENT_STEP_WIDE)
    else:
        gradient_norm = math.inf
        gradient_norm_wide = math.inf
    claimed = claims_maximum_likelihood(
        gradient_norm=gradient_norm,
        gradient_norm_wide_step=gradient_norm_wide,
        log_likelihood=log_likelihood,
        starts_evaluated=evaluated,
    )
    filter_kwargs = {
        "loadings": loadings,
        "factor_ar": phi,
        "idiosyncratic_ar": idiosyncratic,
        "idiosyncratic_innovation_scale": scales,
    }
    filtered = tuple(_filtered_factor(observations, **filter_kwargs))
    try:
        smoothed = tuple(smoothed_factor(observations, **filter_kwargs))
    except np.linalg.LinAlgError:
        smoothed = ()
    return FittedCoincidentFactor(
        log_likelihood=log_likelihood,
        loadings=loadings,  # type: ignore[arg-type]
        factor_ar=phi,
        idiosyncratic_ar=idiosyncratic,
        idiosyncratic_scale=scales,  # type: ignore[arg-type]
        filtered_factor=filtered,
        converged=bool(best.success),
        message=str(best.message),
        gradient_norm=gradient_norm,
        gradient_norm_wide_step=gradient_norm_wide,
        maximum_likelihood_claimed=claimed,
        starts_evaluated=evaluated,
        smoothed_factor=smoothed,
    )


def _admissible(phi, loadings, idiosyncratic, scales) -> bool:
    return (
        loadings[0] > 0
        and _stationary_ar2(*phi)
        and all(_stationary_ar2(first, second) for first, second in idiosyncratic)
        and scales[0] > 0.05
        and all(scale > 0.02 for scale in scales)
    )


def _pack(phi, loadings, idiosyncratic, scales) -> np.ndarray:
    values = [phi[0], phi[1], *loadings]
    for first, second in idiosyncratic:
        values.extend((first, second))
    values.extend(scales)
    return np.asarray(values, dtype=float)


def theta_from_calculation(calculation: dict[str, object]) -> np.ndarray:
    """Pack a stored calculation into the estimator's 18-parameter order."""
    factor_ar = calculation["factor_ar"]
    loadings = calculation["loadings_ip_income_sales_payroll"]
    idiosyncratic = calculation["idiosyncratic_ar"]
    scales = calculation["idiosyncratic_scale"]
    if not isinstance(factor_ar, list) or not isinstance(loadings, list):
        raise TypeError("stored factor parameters must be lists")
    if not isinstance(idiosyncratic, list) or not isinstance(scales, list):
        raise TypeError("stored idiosyncratic parameters must be lists")
    return _pack(
        (float(factor_ar[0]), float(factor_ar[1])),
        tuple(float(value) for value in loadings),
        tuple((float(pair[0]), float(pair[1])) for pair in idiosyncratic),
        tuple(float(value) for value in scales),
    )


def _filtered_factor(observations, **kwargs) -> list[float]:
    """Reuse the likelihood recursion's filtered factor by a local copy of the update.

    The public likelihood does not return the state. This second pass keeps the
    same transition as gaussian_log_likelihood.
    """
    from aqil_research.methods import stock_watson_1988 as model

    loadings = kwargs["loadings"]
    factor_ar = kwargs["factor_ar"]
    idiosyncratic_ar = kwargs["idiosyncratic_ar"]
    scales = kwargs["idiosyncratic_innovation_scale"]
    state_count = 10
    transition = model._zeros(state_count)
    transition[0][0] = factor_ar[0]
    transition[0][1] = factor_ar[1]
    transition[1][0] = 1.0
    shock = model._zeros(state_count)
    shock[0][0] = 1.0
    for index, (first, second) in enumerate(idiosyncratic_ar):
        level = 2 + 2 * index
        lag = level + 1
        transition[level][level] = first
        transition[level][lag] = second
        transition[lag][level] = 1.0
        shock[level][level] = scales[index] ** 2
    observation_map = model._zeros_rect(4, state_count)
    for index, loading in enumerate(loadings):
        level = 2 + 2 * index
        observation_map[index][0] = loading
        observation_map[index][level] = 1.0
    mean = [0.0] * state_count
    covariance = model._identity(state_count, scale=1.0)
    path: list[float] = []
    for row in observations:
        predicted_mean = model._matvec(transition, mean)
        predicted_covariance = model._add(model._sandwich(transition, covariance), shock)
        forecast = model._matvec_rect(observation_map, predicted_mean)
        residual = [row[index] - forecast[index] for index in range(4)]
        _determinant, precision, ok = model._invert_4(
            model._sandwich_rect(observation_map, predicted_covariance)
        )
        if not ok:
            path.append(float("nan"))
            continue
        gain = model._gain(predicted_covariance, observation_map, precision)
        mean = [
            predicted_mean[index] + sum(gain[index][j] * residual[j] for j in range(4))
            for index in range(state_count)
        ]
        innovation = model._sandwich_rect(observation_map, predicted_covariance)
        covariance = model._joseph(predicted_covariance, gain, observation_map, innovation)
        path.append(mean[0])
    return path


def smoothed_factor(observations, **kwargs) -> list[float]:
    """Rauch–Tung–Striebel smoother. This is not the filtered coincident index.

    The last smoothed state matches the last filtered state. Earlier months use
    later observations, so they are retrospective and are not a real-time path.
    """
    from aqil_research.methods import stock_watson_1988 as model

    loadings = kwargs["loadings"]
    factor_ar = kwargs["factor_ar"]
    idiosyncratic_ar = kwargs["idiosyncratic_ar"]
    scales = kwargs["idiosyncratic_innovation_scale"]
    state_count = 10
    transition = model._zeros(state_count)
    transition[0][0] = factor_ar[0]
    transition[0][1] = factor_ar[1]
    transition[1][0] = 1.0
    shock = model._zeros(state_count)
    shock[0][0] = 1.0
    for index, (first, second) in enumerate(idiosyncratic_ar):
        level = 2 + 2 * index
        lag = level + 1
        transition[level][level] = first
        transition[level][lag] = second
        transition[lag][level] = 1.0
        shock[level][level] = scales[index] ** 2
    observation_map = model._zeros_rect(4, state_count)
    for index, loading in enumerate(loadings):
        level = 2 + 2 * index
        observation_map[index][0] = loading
        observation_map[index][level] = 1.0
    mean = [0.0] * state_count
    covariance = model._identity(state_count, scale=1.0)
    filtered_means: list[np.ndarray] = []
    filtered_covs: list[np.ndarray] = []
    predicted_means: list[np.ndarray] = []
    predicted_covs: list[np.ndarray] = []
    for row in observations:
        predicted_mean = model._matvec(transition, mean)
        predicted_covariance = model._add(model._sandwich(transition, covariance), shock)
        forecast = model._matvec_rect(observation_map, predicted_mean)
        residual = [row[index] - forecast[index] for index in range(4)]
        _determinant, precision, ok = model._invert_4(
            model._sandwich_rect(observation_map, predicted_covariance)
        )
        if not ok:
            raise np.linalg.LinAlgError("innovation covariance is singular")
        gain = model._gain(predicted_covariance, observation_map, precision)
        mean = [
            predicted_mean[index] + sum(gain[index][j] * residual[j] for j in range(4))
            for index in range(state_count)
        ]
        innovation = model._sandwich_rect(observation_map, predicted_covariance)
        covariance = model._joseph(predicted_covariance, gain, observation_map, innovation)
        filtered_means.append(np.asarray(mean, dtype=float))
        filtered_covs.append(np.asarray(covariance, dtype=float))
        predicted_means.append(np.asarray(predicted_mean, dtype=float))
        predicted_covs.append(np.asarray(predicted_covariance, dtype=float))
    transition_np = np.asarray(transition, dtype=float)
    smoothed_means = [filtered_means[-1]]
    for time in range(len(filtered_means) - 2, -1, -1):
        # Companion lags make this covariance numerically singular. A pseudo-inverse
        # keeps the Rauch–Tung–Striebel gain defined.
        gain = filtered_covs[time] @ transition_np.T @ np.linalg.pinv(predicted_covs[time + 1])
        smoothed_means.append(
            filtered_means[time] + gain @ (smoothed_means[-1] - predicted_means[time + 1])
        )
    smoothed_means.reverse()
    return [float(state[0]) for state in smoothed_means]


class StockWatsonModernRefitConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    config_id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    maxiter: int = Field(default=40, ge=1, le=80)


def modern_refit_implementation_hash() -> str:
    payload = "|".join(
        (
            SPECIFICATION_ID,
            METHOD_VERSION,
            "factor-ar-2",
            "idiosyncratic-ar-2",
            "innovation-variance-1",
            f"gradient-norm-limit-{GRADIENT_NORM_LIMIT}",
            "filtered-distinct-from-smoother",
            "latest-revised",
        )
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class StockWatsonModernRefitMethod:
    """Estimator for the modern refit. Not operationally accepted.

    Registration, for the integrator, inside ``default_method_registry``::

        registry.register(StockWatsonModernRefitMethod())
    """

    method_id = SPECIFICATION_ID
    method_version = METHOD_VERSION

    def implementation_hash(self) -> str:
        return modern_refit_implementation_hash()

    def required_dataset_ids(self) -> tuple[str, ...]:
        return MODERN_REFIT_DATASETS

    def parse_config(self, payload: dict[str, object]) -> StockWatsonModernRefitConfig:
        return StockWatsonModernRefitConfig.model_validate(payload)

    def config_hash(self, config: BaseModel) -> str:
        if not isinstance(config, StockWatsonModernRefitConfig):
            raise TypeError("expected StockWatsonModernRefitConfig")
        return MethodParameterDocument(
            config_id=config.config_id,
            label=config.label,
            scalars={"maxiter": str(config.maxiter)},
        ).config_hash()

    def run(self, context: MethodContext, config: BaseModel) -> MethodExecutionResult:
        if not isinstance(config, StockWatsonModernRefitConfig):
            raise TypeError("expected StockWatsonModernRefitConfig")
        if context.analysis_mode != AnalysisMode.LATEST_REVISED:
            return _insufficient(
                "the modern refit reads a latest-revised panel, not a real-time vintage"
            )
        panel, level_periods, observation_ids = _standardised_panel(context.inputs_by_dataset)
        if panel is None or level_periods is None:
            return _insufficient(
                "the four modern series do not share 36 growth-rate months from January 1997"
            )
        fitted = fit_coincident_factor(panel, maxiter=config.maxiter)
        growth_start = level_periods[1]
        last_growth = level_periods[-1]
        claim = (
            "The gradient condition was met."
            if fitted.maximum_likelihood_claimed
            else "Maximum likelihood is not claimed because the gradient condition failed."
        )
        return MethodExecutionResult(
            sufficiency="sufficient",
            calculation={
                "specification": SPECIFICATION_ID,
                "publication_allowed": PUBLICATION_ALLOWED,
                "operationally_accepted": OPERATIONALLY_ACCEPTED,
                "real_time": False,
                "input_vintage": "latest_revised",
                "sample_levels": [level_periods[0].isoformat(), level_periods[-1].isoformat()],
                "growth_start": growth_start.isoformat(),
                "loadings_ip_income_sales_payroll": list(fitted.loadings),
                "factor_ar": list(fitted.factor_ar),
                "idiosyncratic_ar": [list(pair) for pair in fitted.idiosyncratic_ar],
                "idiosyncratic_scale": list(fitted.idiosyncratic_scale),
                "log_likelihood": fitted.log_likelihood,
                "filtered_factor": list(fitted.filtered_factor),
                "smoothed_factor": list(fitted.smoothed_factor),
                "filtered_factor_is_not_the_smoother": True,
                "gradient_norm": (
                    fitted.gradient_norm if math.isfinite(fitted.gradient_norm) else None
                ),
                "gradient_norm_wide_step": (
                    fitted.gradient_norm_wide_step
                    if math.isfinite(fitted.gradient_norm_wide_step)
                    else None
                ),
                "gradient_step": GRADIENT_STEP,
                "maximum_likelihood_claimed": fitted.maximum_likelihood_claimed,
                "optimizer_converged": fitted.converged,
                "starts_evaluated": fitted.starts_evaluated,
                "not_a_gdp_nowcast": True,
            },
            observation_ids=tuple(observation_ids),
            assumptions=(
                "The panel is the balanced latest-revised sample from January 1997.",
                NOT_THE_CITIBASE_SPECIFICATION,
                "Factor innovation variance is fixed at 1.",
                "Each growth rate is standardised on the estimation sample.",
            ),
            limitations=(
                "publication_allowed is false.",
                "The refit is not operationally accepted.",
                "The filtered factor is not the smoother.",
                "The path is latest revised. It is not a real-time vintage and not a GDP nowcast.",
                claim,
                NOT_THE_CITIBASE_SPECIFICATION,
            ),
            missing_reason=None,
            statistical_interpretation=(
                "Coincident factor on the modern four-series panel through "
                f"{last_growth.isoformat()}. "
                f"{claim} {NOT_THE_CITIBASE_SPECIFICATION} "
                "The filtered values are not smoothed values."
            ),
            causal_hypothesis="none",
            investment_implication="no_action",
            narrative=(
                "Modern refit of the 1988 coincident orders. "
                f"{claim} publication_allowed is false. "
                "The refit is not operationally accepted. "
                f"{NOT_THE_CITIBASE_SPECIFICATION}"
            ),
        )


def _insufficient(reason: str) -> MethodExecutionResult:
    return MethodExecutionResult(
        sufficiency="insufficient",
        calculation=None,
        observation_ids=(),
        assumptions=(NOT_THE_CITIBASE_SPECIFICATION,),
        limitations=("publication_allowed is false.", "The refit is not operationally accepted."),
        missing_reason=reason,
        statistical_interpretation="The modern refit was not estimated.",
        causal_hypothesis="none",
        investment_implication="insufficient_evidence",
        narrative=f"Modern refit incomplete. Reason: {reason}",
    )


def _standardised_panel(
    inputs_by_dataset: dict,
) -> tuple[list[list[float]] | None, list[date] | None, list[str]]:
    series: dict[str, dict[date, tuple[float, str]]] = {}
    for dataset_id in MODERN_REFIT_DATASETS:
        rows = inputs_by_dataset.get(dataset_id)
        if not rows:
            return None, None, []
        series[dataset_id] = {}
        for period, observation in rows.items():
            if period < SAMPLE_START:
                continue
            if observation.series_provenance != SeriesProvenance.LATEST_REVISED:
                continue
            series[dataset_id][period] = (
                float(observation.decimal_value()),
                observation.observation_id,
            )
    months = set.intersection(*(set(series[dataset_id]) for dataset_id in MODERN_REFIT_DATASETS))
    ordered = sorted(months)
    if len(ordered) < 37:
        return None, None, []
    observation_ids: list[str] = []
    panel: list[list[float]] = []
    for dataset_id in MODERN_REFIT_DATASETS:
        levels = [series[dataset_id][period][0] for period in ordered]
        for period in ordered:
            observation_ids.append(series[dataset_id][period][1])
        try:
            growth = log_difference(levels)
            standardised, _mean, _scale = standardise(growth)
        except ValueError:
            return None, None, []
        panel.append(standardised)
    return panel, ordered, observation_ids
