"""Maximum-likelihood refit of the 1988 coincident factor on a prepared panel."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy.optimize import minimize

from aqil_research.methods.stock_watson_1988 import gaussian_log_likelihood

SPECIFICATION_ID = "STOCK_WATSON_COINCIDENT_1988_MODERN_REFIT"


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


def fit_coincident_factor(panel: list[list[float]]) -> FittedCoincidentFactor:
    """Estimate the frozen 1988 orders. panel columns are already standardised growth rates."""
    if len(panel) != 4:
        raise ValueError("the 1988 model has four series")
    length = len(panel[0])
    if length < 36 or any(len(series) != length for series in panel):
        raise ValueError("the four series must share at least 36 growth-rate months")
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
        if loadings[0] <= 0:
            return 1e6
        if not _stationary_ar2(*phi) or any(
            not _stationary_ar2(first, second) for first, second in idiosyncratic
        ):
            return 1e6
        if scales[0] <= 0.05 or any(scale <= 0.02 for scale in scales):
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

    starts = [
        np.array(
            [
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
            ]
        ),
        np.array(
            [
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
            ]
        ),
    ]
    best = None
    for start in starts:
        result = minimize(
            objective, start, method="L-BFGS-B", options={"maxiter": 40, "ftol": 1e-6}
        )
        if best is None or result.fun < best.fun:
            best = result
    assert best is not None
    phi, loadings, idiosyncratic, scales = unpack(best.x)
    if loadings[0] < 0:
        loadings = tuple(-value for value in loadings)
        # A negative industrial-production loading is flipped so the factor sign matches production.
    filtered = _filtered_factor(
        observations,
        loadings=loadings,  # type: ignore[arg-type]
        factor_ar=phi,
        idiosyncratic_ar=idiosyncratic,
        idiosyncratic_innovation_scale=scales,  # type: ignore[arg-type]
    )
    return FittedCoincidentFactor(
        log_likelihood=-float(best.fun) if best.fun < 1e5 else float("-inf"),
        loadings=loadings,  # type: ignore[arg-type]
        factor_ar=phi,
        idiosyncratic_ar=idiosyncratic,
        idiosyncratic_scale=scales,  # type: ignore[arg-type]
        filtered_factor=tuple(filtered),
        converged=bool(best.success),
        message=str(best.message),
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
