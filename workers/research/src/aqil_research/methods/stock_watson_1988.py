"""1988 Stock–Watson coincident factor. Not the 1989 employee-hours model.

Working paper 2772, pages 6–8 and 16–17: log differences, standardised to
mean zero and unit variance, factor innovation variance 1, factor
autoregression of order 2, diagonal idiosyncratic autoregressions of order
2, and a contemporaneous loading in every equation. The fourth series in
that paper is nonagricultural payroll employment, not employee-hours.

The real manufacturing-and-trade sales series is not stored. This module
does not estimate a factor from Aqil observations.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

SPECIFICATION_ID = "STOCK_WATSON_COINCIDENT_1988"
FACTOR_AR_ORDER = 2
IDIOSYNCRATIC_AR_ORDER = 2
FACTOR_INNOVATION_VARIANCE = 1.0
PUBLICATION_ALLOWED = False

REQUIRED_DATASET_IDS = (
    "fed.g17.IP.B50001.S",
    "bea.nipa.T20600.personal_income_ex_transfers.chained_2017",
    "census.mtis.TOTBUS.SM.real_1982",
    "bls.ce.CES0000000001",
)


class StockWatsonPanelBlocked(RuntimeError):
    """The 1988 four-series panel is not available for estimation."""


@dataclass(frozen=True, slots=True)
class CoincidentDraw:
    """One simulated path. The filter is not used to build it."""

    observations: tuple[tuple[float, ...], ...]
    factor: tuple[float, ...]


def assert_real_panel_available(stored_dataset_ids: set[str]) -> None:
    """Refuse a real-data estimate until every 1988 input is stored."""
    missing = [item for item in REQUIRED_DATASET_IDS if item not in stored_dataset_ids]
    if missing:
        raise StockWatsonPanelBlocked(
            "1988 coincident estimation is blocked. Missing "
            + ", ".join(missing)
            + ". Nominal Census sales are not the 1982-dollar sales series."
        )


def simulate_coincident_path(
    *,
    periods: int,
    loadings: tuple[float, float, float, float],
    factor_ar: tuple[float, float],
    idiosyncratic_ar: tuple[tuple[float, float], ...],
    idiosyncratic_innovation_scale: tuple[float, float, float, float],
    seed: int,
) -> CoincidentDraw:
    """Draw a path from the 1988 transition. This is not the Kalman filter."""
    if periods < 8:
        raise ValueError("the synthetic path needs at least eight months")
    if len(idiosyncratic_ar) != 4:
        raise ValueError("four idiosyncratic equations are required")
    generator = random.Random(seed)
    factor = [0.0, 0.0]
    idiosyncratic = [[0.0, 0.0] for _ in range(4)]
    rows: list[tuple[float, ...]] = []
    factor_path: list[float] = []
    for _ in range(periods):
        shock = generator.gauss(0.0, math.sqrt(FACTOR_INNOVATION_VARIANCE))
        current = factor_ar[0] * factor[-1] + factor_ar[1] * factor[-2] + shock
        factor.append(current)
        factor_path.append(current)
        observed: list[float] = []
        for index, loading in enumerate(loadings):
            first, second = idiosyncratic_ar[index]
            noise = generator.gauss(0.0, idiosyncratic_innovation_scale[index])
            value = first * idiosyncratic[index][-1] + second * idiosyncratic[index][-2] + noise
            idiosyncratic[index].append(value)
            observed.append(loading * current + value)
        rows.append(tuple(observed))
    return CoincidentDraw(observations=tuple(rows), factor=tuple(factor_path))


def gaussian_log_likelihood_parts(
    observations: tuple[tuple[float, ...], ...],
    *,
    loadings: tuple[float, float, float, float],
    factor_ar: tuple[float, float],
    idiosyncratic_ar: tuple[tuple[float, float], ...],
    idiosyncratic_innovation_scale: tuple[float, float, float, float],
) -> float:
    """Kalman likelihood for the frozen 1988 orders. Means are already zero."""
    if any(scale <= 0 for scale in idiosyncratic_innovation_scale):
        return -math.inf
    if abs(factor_ar[0]) + abs(factor_ar[1]) >= 1.95:
        return -math.inf
    state_count = 10
    transition = _zeros(state_count)
    transition[0][0] = factor_ar[0]
    transition[0][1] = factor_ar[1]
    transition[1][0] = 1.0
    shock = _zeros(state_count)
    shock[0][0] = FACTOR_INNOVATION_VARIANCE
    for index, (first, second) in enumerate(idiosyncratic_ar):
        level = 2 + 2 * index
        lag = level + 1
        transition[level][level] = first
        transition[level][lag] = second
        transition[lag][level] = 1.0
        shock[level][level] = idiosyncratic_innovation_scale[index] ** 2
    observation_map = _zeros_rect(4, state_count)
    for index, loading in enumerate(loadings):
        level = 2 + 2 * index
        observation_map[index][0] = loading
        observation_map[index][level] = 1.0
    mean = [0.0] * state_count
    covariance = _identity(state_count, scale=1.0)
    total = 0.0
    contributions: list[float] = []
    for row in observations:
        predicted_mean = _matvec(transition, mean)
        predicted_covariance = _add(
            _sandwich(transition, covariance),
            shock,
        )
        forecast = _matvec_rect(observation_map, predicted_mean)
        residual = [row[index] - forecast[index] for index in range(4)]
        innovation_covariance = _sandwich_rect(observation_map, predicted_covariance)
        determinant, precision, ok = _invert_4(innovation_covariance)
        if not ok or determinant <= 1e-12:
            return -math.inf
        quadratic = _quad(residual, precision)
        contribution = -0.5 * (4 * math.log(2 * math.pi) + math.log(determinant) + quadratic)
        contributions.append(contribution)
        total += contribution
        gain = _gain(predicted_covariance, observation_map, precision)
        mean = [
            predicted_mean[index] + sum(gain[index][j] * residual[j] for j in range(4))
            for index in range(state_count)
        ]
        covariance = _joseph(predicted_covariance, gain, observation_map, innovation_covariance)
    return total, contributions


def gaussian_log_likelihood(*args, **kwargs) -> float:
    total, _contributions = gaussian_log_likelihood_parts(*args, **kwargs)
    return total


def _zeros(size: int) -> list[list[float]]:
    return [[0.0] * size for _ in range(size)]


def _zeros_rect(rows: int, columns: int) -> list[list[float]]:
    return [[0.0] * columns for _ in range(rows)]


def _identity(size: int, *, scale: float) -> list[list[float]]:
    matrix = _zeros(size)
    for index in range(size):
        matrix[index][index] = scale
    return matrix


def _matvec(matrix: list[list[float]], vector: list[float]) -> list[float]:
    return [
        sum(matrix[row][col] * vector[col] for col in range(len(vector)))
        for row in range(len(matrix))
    ]


def _matvec_rect(matrix: list[list[float]], vector: list[float]) -> list[float]:
    return [sum(row[col] * vector[col] for col in range(len(vector))) for row in matrix]


def _add(left: list[list[float]], right: list[list[float]]) -> list[list[float]]:
    return [
        [left[row][col] + right[row][col] for col in range(len(left))] for row in range(len(left))
    ]


def _sandwich(transition: list[list[float]], covariance: list[list[float]]) -> list[list[float]]:
    size = len(transition)
    temp = _zeros(size)
    for row in range(size):
        for col in range(size):
            temp[row][col] = sum(transition[row][k] * covariance[k][col] for k in range(size))
    result = _zeros(size)
    for row in range(size):
        for col in range(size):
            result[row][col] = sum(temp[row][k] * transition[col][k] for k in range(size))
    return result


def _sandwich_rect(
    observation_map: list[list[float]],
    covariance: list[list[float]],
) -> list[list[float]]:
    width = len(covariance)
    temp = _zeros_rect(4, width)
    for row in range(4):
        for col in range(width):
            temp[row][col] = sum(observation_map[row][k] * covariance[k][col] for k in range(width))
    result = _zeros(4)
    for row in range(4):
        for col in range(4):
            result[row][col] = sum(temp[row][k] * observation_map[col][k] for k in range(width))
    return result


def _invert_4(matrix: list[list[float]]) -> tuple[float, list[list[float]], bool]:
    size = 4
    working = [
        row[:] + [1.0 if row_index == col else 0.0 for col in range(size)]
        for row_index, row in enumerate(matrix)
    ]
    determinant = 1.0
    for col in range(size):
        pivot = max(range(col, size), key=lambda row: abs(working[row][col]))
        if abs(working[pivot][col]) < 1e-12:
            return 0.0, _zeros(size), False
        if pivot != col:
            working[col], working[pivot] = working[pivot], working[col]
            determinant = -determinant
        scale = working[col][col]
        determinant *= scale
        working[col] = [value / scale for value in working[col]]
        for row in range(size):
            if row == col:
                continue
            factor = working[row][col]
            working[row] = [
                working[row][index] - factor * working[col][index] for index in range(size * 2)
            ]
    inverse = [row[size:] for row in working]
    return determinant, inverse, True


def _quad(residual: list[float], precision: list[list[float]]) -> float:
    intermediate = _matvec(precision, residual)
    return sum(residual[index] * intermediate[index] for index in range(4))


def _gain(
    covariance: list[list[float]],
    observation_map: list[list[float]],
    precision: list[list[float]],
) -> list[list[float]]:
    width = len(covariance)
    cross = _zeros_rect(width, 4)
    for row in range(width):
        for col in range(4):
            cross[row][col] = sum(
                covariance[row][k] * observation_map[col][k] for k in range(width)
            )
    gain = _zeros_rect(width, 4)
    for row in range(width):
        for col in range(4):
            gain[row][col] = sum(cross[row][k] * precision[k][col] for k in range(4))
    return gain


def _joseph(
    covariance: list[list[float]],
    gain: list[list[float]],
    observation_map: list[list[float]],
    innovation_covariance: list[list[float]],
) -> list[list[float]]:
    """P - K H P, then add a symmetry projection. The innovation covariance is not reapplied."""
    del innovation_covariance
    width = len(covariance)
    kh = _zeros(width)
    for row in range(width):
        for col in range(width):
            kh[row][col] = sum(gain[row][k] * observation_map[k][col] for k in range(4))
    updated = _zeros(width)
    for row in range(width):
        for col in range(width):
            updated[row][col] = covariance[row][col] - sum(
                kh[row][k] * covariance[k][col] for k in range(width)
            )
    for row in range(width):
        for col in range(row, width):
            value = 0.5 * (updated[row][col] + updated[col][row])
            if row == col and value < 1e-12:
                value = 1e-12
            updated[row][col] = value
            updated[col][row] = value
    return updated
