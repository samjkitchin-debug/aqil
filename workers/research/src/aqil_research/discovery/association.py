"""Association statistics. The primary test is the Newey–West slope."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import statsmodels.api as sm
from scipy import stats


class AssociationError(Exception):
    """Raised when a predeclared statistic cannot be estimated."""


@dataclass(frozen=True, slots=True)
class Association:
    n: int
    pearson_r: float
    pearson_p: float
    spearman_r: float
    spearman_p: float
    intercept: float
    slope: float
    slope_se: float
    slope_p: float
    maxlags: int
    bootstrap_low: float | None
    bootstrap_high: float | None


def benjamini_hochberg(p_values: list[float]) -> list[float]:
    """Benjamini–Hochberg adjusted p-values in the original order."""
    count = len(p_values)
    if count == 0:
        return []
    order = sorted(range(count), key=lambda index: p_values[index])
    adjusted = [1.0] * count
    running = 1.0
    for rank_from_end, index in enumerate(reversed(order), start=1):
        original_rank = count - rank_from_end + 1
        raw = p_values[index] * count / original_rank
        running = min(running, raw)
        adjusted[index] = min(running, 1.0)
    return adjusted


def ols_hac(
    x_values: list[float], y_values: list[float], *, maxlags: int
) -> tuple[float, float, float, float]:
    """Intercept, slope, slope standard error, and two-sided slope p-value."""
    if len(x_values) != len(y_values):
        raise AssociationError("the signal and the return must have the same length")
    count = len(x_values)
    if count < 3:
        raise AssociationError("fewer than three pairs")
    if maxlags < 0 or maxlags >= count - 1:
        raise AssociationError("the predeclared Newey-West lag is not supported by this sample")
    signal = np.asarray(x_values, dtype=float)
    outcome = np.asarray(y_values, dtype=float)
    if float(np.nanstd(signal)) == 0.0 or float(np.nanstd(outcome)) == 0.0:
        raise AssociationError("a constant series has no slope")
    if not np.isfinite(signal).all() or not np.isfinite(outcome).all():
        raise AssociationError("a non-finite value was refused")
    fitted = sm.OLS(outcome, sm.add_constant(signal)).fit(
        cov_type="HAC",
        cov_kwds={"maxlags": maxlags},
    )
    return (
        float(fitted.params[0]),
        float(fitted.params[1]),
        float(fitted.bse[1]),
        float(fitted.pvalues[1]),
    )


def added_slope_p(
    y_values: list[float],
    baseline: list[float],
    added: list[float],
    *,
    maxlags: int,
    collinear_abs: float,
) -> tuple[float, float]:
    """P-value and slope of the added regressor. Collinear cousins are refused."""
    if len(y_values) != len(baseline) or len(y_values) != len(added):
        raise AssociationError("the compared series must have the same length")
    count = len(y_values)
    if count < 3 or maxlags < 0 or maxlags >= count - 1:
        raise AssociationError("the predeclared Newey-West lag is not supported by this sample")
    outcome = np.asarray(y_values, dtype=float)
    first = np.asarray(baseline, dtype=float)
    second = np.asarray(added, dtype=float)
    correlation = stats.pearsonr(first, second)
    if not np.isfinite(correlation.statistic) or abs(float(correlation.statistic)) >= collinear_abs:
        raise AssociationError("collinear cousins are one group")
    fitted = sm.OLS(outcome, sm.add_constant(np.column_stack([first, second]))).fit(
        cov_type="HAC",
        cov_kwds={"maxlags": maxlags},
    )
    return float(fitted.pvalues[2]), float(fitted.params[2])


def _correlation(x_values: list[float], y_values: list[float]) -> tuple[float, float, float, float]:
    pearson = stats.pearsonr(x_values, y_values)
    spearman = stats.spearmanr(x_values, y_values)
    values = (
        float(pearson.statistic),
        float(pearson.pvalue),
        float(spearman.statistic),
        float(spearman.pvalue),
    )
    if not all(np.isfinite(value) for value in values):
        raise AssociationError("a correlation was undefined")
    return values


def block_bootstrap_slope(
    x_values: list[float],
    y_values: list[float],
    *,
    block: int,
    replicates: int,
    seed: int,
    maxlags: int,
) -> tuple[float, float]:
    """Percentile interval for the ordinary-least-squares slope under a circular block bootstrap."""
    count = len(x_values)
    if block < 1 or block > count:
        raise AssociationError("the bootstrap block does not fit this sample")
    generator = np.random.default_rng(seed)
    signal = np.asarray(x_values, dtype=float)
    outcome = np.asarray(y_values, dtype=float)
    slopes: list[float] = []
    starts = np.arange(count)
    for _ in range(replicates):
        drawn: list[int] = []
        while len(drawn) < count:
            start = int(generator.choice(starts))
            for offset in range(block):
                drawn.append((start + offset) % count)
                if len(drawn) == count:
                    break
        index = np.asarray(drawn, dtype=int)
        try:
            _intercept, slope, _se, _p = ols_hac(
                signal[index].tolist(),
                outcome[index].tolist(),
                maxlags=maxlags,
            )
        except AssociationError:
            continue
        slopes.append(slope)
    if len(slopes) < replicates:
        raise AssociationError("the block bootstrap did not complete the predeclared replicates")
    ordered = np.sort(np.asarray(slopes, dtype=float))
    low = float(np.quantile(ordered, 0.025))
    high = float(np.quantile(ordered, 0.975))
    return low, high


def associate(
    x_values: list[float],
    y_values: list[float],
    *,
    maxlags: int,
    block: int,
    replicates: int,
    seed: int,
) -> Association:
    pearson_r, pearson_p, spearman_r, spearman_p = _correlation(x_values, y_values)
    intercept, slope, slope_se, slope_p = ols_hac(x_values, y_values, maxlags=maxlags)
    low, high = block_bootstrap_slope(
        x_values,
        y_values,
        block=block,
        replicates=replicates,
        seed=seed,
        maxlags=maxlags,
    )
    return Association(
        n=len(x_values),
        pearson_r=pearson_r,
        pearson_p=pearson_p,
        spearman_r=spearman_r,
        spearman_p=spearman_p,
        intercept=intercept,
        slope=slope,
        slope_se=slope_se,
        slope_p=slope_p,
        maxlags=maxlags,
        bootstrap_low=low,
        bootstrap_high=high,
    )


def claim_class(
    *,
    is_null_control: bool,
    below_floor: bool,
    statistical_bar: bool,
    bh_rejects: bool,
    holdout_confirms: bool,
    economic_advantage: bool,
    bootstrap_excludes_zero: bool,
    forward_frozen: bool,
) -> str:
    """Map a cell onto one evidence class. A null control cannot be promoted."""
    if is_null_control or below_floor or forward_frozen:
        return "not_claimed"
    if (
        economic_advantage
        and statistical_bar
        and bh_rejects
        and holdout_confirms
        and bootstrap_excludes_zero
    ):
        return "economically_useful"
    if statistical_bar and bh_rejects and holdout_confirms and bootstrap_excludes_zero:
        return "statistically_supported"
    return "exploratory"
