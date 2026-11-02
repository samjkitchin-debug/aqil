"""Independent statsmodels check of the 1988 diagonal AR(2) structure."""

from __future__ import annotations

import re

import numpy as np
from statsmodels.tsa.statespace.dynamic_factor import DynamicFactor

from aqil_research.methods.stock_watson_1988 import (
    simulate_coincident_path,
)
from aqil_research.methods.stock_watson_1988_fit import _filtered_factor, smoothed_factor

LOADINGS = (0.7, 0.5, 0.4, 0.6)
FACTOR_AR = (0.4, 0.1)
IDIOSYNCRATIC = ((0.2, -0.1), (0.1, 0.0), (-0.2, 0.05), (0.15, 0.05))
SCALES = (0.5, 0.6, 0.45, 0.55)


def _params(model, loadings, factor_ar, idiosyncratic, scales):
    values = np.zeros(len(model.param_names))
    for index, name in enumerate(model.param_names):
        if name.startswith("loading.f1.y"):
            values[index] = loadings[int(name[-1]) - 1]
        elif name.startswith("sigma2.y"):
            values[index] = scales[int(name[-1]) - 1] ** 2
        elif name == "L1.f1.f1":
            values[index] = factor_ar[0]
        elif name == "L2.f1.f1":
            values[index] = factor_ar[1]
        else:
            match = re.search(r"L([12])\.e\(y(\d)\)", name)
            series = int(match.group(2)) - 1
            lag = int(match.group(1)) - 1
            values[index] = idiosyncratic[series][lag]
    return values


def test_statsmodels_matches_aqil_after_the_initial_state_dies_out() -> None:
    draw = simulate_coincident_path(
        periods=60,
        loadings=LOADINGS,
        factor_ar=FACTOR_AR,
        idiosyncratic_ar=IDIOSYNCRATIC,
        idiosyncratic_innovation_scale=SCALES,
        seed=7,
    )
    endog = np.asarray(draw.observations, dtype=float)
    model = DynamicFactor(
        endog,
        k_factors=1,
        factor_order=2,
        error_order=2,
        error_var=False,
        error_cov_type="diagonal",
    )
    mapped = _params(model, LOADINGS, FACTOR_AR, IDIOSYNCRATIC, SCALES)
    model.ssm.initialize_known(np.zeros(model.k_states), np.eye(model.k_states))
    filtered = model.filter(mapped)
    aqil_path = np.asarray(
        _filtered_factor(
            draw.observations,
            loadings=LOADINGS,
            factor_ar=FACTOR_AR,
            idiosyncratic_ar=IDIOSYNCRATIC,
            idiosyncratic_innovation_scale=SCALES,
        )
    )
    gap = np.max(np.abs(filtered.filtered_state[0, 20:] - aqil_path[20:]))
    assert gap < 1e-8
    smoothed = model.smooth(mapped)
    aqil_smoothed = np.asarray(
        smoothed_factor(
            draw.observations,
            loadings=LOADINGS,
            factor_ar=FACTOR_AR,
            idiosyncratic_ar=IDIOSYNCRATIC,
            idiosyncratic_innovation_scale=SCALES,
        )
    )
    smooth_gap = np.max(np.abs(smoothed.smoothed_state[0, 20:] - aqil_smoothed[20:]))
    assert smooth_gap < 1e-8
    assert abs(aqil_path[0] - aqil_smoothed[0]) > 1e-4
    # The first observations absorb the identity initial covariance. After that
    # the filtered factors match. The total likelihood can still differ by the
    # burn-in, so the acceptance check is the post-burn-in path.
