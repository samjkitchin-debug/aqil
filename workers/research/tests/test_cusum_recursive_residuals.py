"""CUSUM of recursive residuals. Fixture series only."""

from __future__ import annotations

import math
from datetime import UTC, date, datetime
from pathlib import Path

import numpy as np
import pytest
from statsmodels.regression.linear_model import OLS
from statsmodels.stats.diagnostic import recursive_olsresiduals

from aqil_research.contracts.observation import (
    AnalysisMode,
    AvailabilityPrecision,
    EconomicObservation,
    Frequency,
    QualityStatus,
    SeasonalAdjustment,
    SeriesProvenance,
)
from aqil_research.methods.autoregressive_benchmark import (
    INDUSTRIAL_PRODUCTION_DATASET_ID,
    LEVEL_UNIT,
    MAX_LAG,
    contiguous_monthly_log_growth,
)
from aqil_research.methods.cusum_recursive_residuals import (
    BOUNDARY_COEFFICIENT,
    CUSUM_RECURSIVE_RESIDUALS,
    MINIMUM_GROWTH_MONTHS,
    NOT_A_BREAK_CATALOGUE,
    PREDECLARED_LAG,
    PUBLICATION_ALLOWED,
    PUBLISHED_CONFIG,
    CusumRecursiveResidualsMethod,
    autoregressive_design,
    conventional_boundary,
    cusum_from_growth,
    recursive_residuals,
)
from aqil_research.methods.protocol import MethodContext
from aqil_research.methods.registry import default_method_registry


def test_lag_12_is_predeclared_because_the_benchmark_lag_is_not_a_constant() -> None:
    assert CUSUM_RECURSIVE_RESIDUALS == "CUSUM_RECURSIVE_RESIDUALS"
    assert PUBLICATION_ALLOWED is False
    assert PUBLISHED_CONFIG["config_id"] == "cusum-recursive-residuals-v1"
    assert PREDECLARED_LAG == 12
    assert PREDECLARED_LAG == MAX_LAG
    assert BOUNDARY_COEFFICIENT == 0.948
    assert MINIMUM_GROWTH_MONTHS == 38
    text = Path(cusum_from_growth.__code__.co_filename).read_text(encoding="utf-8")
    assert "select_ar_lag" not in text
    assert "local_projection" not in text.lower()
    assert "chow" not in text.lower()


def test_first_recursive_residual_matches_an_independent_calculation() -> None:
    growth = np.random.default_rng(3).normal(0.0, 0.01, size=180)
    design, target = autoregressive_design(growth, PREDECLARED_LAG)
    assert np.all(design[:, 0] == 1.0)
    assert design.shape[1] == PREDECLARED_LAG + 1
    hand = _hand_first_recursive_residual(design, target)
    scaled = recursive_residuals(design, target)
    assert scaled[0] == pytest.approx(hand)
    fitted = OLS(target, design).fit()
    library = recursive_olsresiduals(fitted, skip=None, lamda=0.0, alpha=0.95)
    library_scaled = library[4][design.shape[1] :]
    assert scaled == pytest.approx(library_scaled)
    without_constant = _hand_first_recursive_residual(design[:, 1:], target)
    assert scaled[0] != pytest.approx(without_constant)
    estimated = cusum_from_growth(growth)
    assert estimated["crosses_conventional_boundary"] is False
    independent_crosses = _crosses(library_scaled)
    assert estimated["crosses_conventional_boundary"] is independent_crosses
    boundary = conventional_boundary(len(scaled))
    paper = 0.948 * math.sqrt(len(scaled)) + 2 * 0.948 * np.arange(1, len(scaled) + 1) / math.sqrt(
        len(scaled),
    )
    assert boundary == pytest.approx(paper)
    assert boundary[0] > 0.948 * math.sqrt(len(scaled))


def test_an_early_mean_shift_crosses_and_a_short_sample_does_not_run() -> None:
    generator = np.random.default_rng(4)
    growth = generator.normal(0.0, 0.01, size=240)
    growth[30:] += 0.3
    estimated = cusum_from_growth(growth)
    design, target = autoregressive_design(growth, PREDECLARED_LAG)
    fitted = OLS(target, design).fit()
    library_scaled = recursive_olsresiduals(fitted, lamda=0.0, alpha=0.95)[4][design.shape[1] :]
    assert estimated["crosses_conventional_boundary"] is True
    assert estimated["crosses_conventional_boundary"] is _crosses(library_scaled)
    with pytest.raises(ValueError, match="below 38"):
        cusum_from_growth(np.zeros(MINIMUM_GROWTH_MONTHS - 1))


def test_method_uses_the_benchmark_transformation_and_reports_either_outcome() -> None:
    method = CusumRecursiveResidualsMethod()
    config = method.parse_config(dict(PUBLISHED_CONFIG))
    dependency = method.dependency()
    assert method.required_dataset_ids() == (INDUSTRIAL_PRODUCTION_DATASET_ID,)
    assert dependency.vintage_class == "latest_revised"
    assert dependency.parameter_policy == "none"
    assert dependency.depends_on_method_ids == ()
    assert dependency.refit_is_different_command is False
    assert method.config_hash(config)
    registered = [item.method_id for item in default_method_registry().registered()]
    assert registered[-2] == CUSUM_RECURSIVE_RESIDUALS
    assert registered[-1] == "CONSTANT_MATURITY_SPREAD_RECESSION_PROBIT"
    growth = np.random.default_rng(3).normal(0.0, 0.01, size=180)
    result = method.run(_context(_levels(growth)), config)
    assert result.sufficiency == "sufficient"
    assert result.calculation is not None
    level_map = _level_map(growth)
    sample = contiguous_monthly_log_growth(
        {month: float(observation.decimal_value()) for month, observation in level_map.items()},
    )
    expected = cusum_from_growth(sample.values)
    assert result.calculation["transformation"] == "monthly_log_growth"
    assert result.calculation["predeclared_lag"] == 12
    assert result.calculation["lag_was_selected_by_aic"] is False
    assert result.calculation["constant_included"] is True
    assert result.calculation["selected_break_date"] is None
    assert result.calculation["statsmodels_returned_cusum_used"] is False
    assert result.calculation["publication_allowed"] is False
    assert result.calculation["crosses_conventional_boundary"] is False
    assert (
        result.calculation["crosses_conventional_boundary"]
        is (expected["crosses_conventional_boundary"])
    )
    assert result.calculation["cusum_end"] == sample.growth_months[-1].isoformat()
    assert result.investment_implication == "no_action"
    assert NOT_A_BREAK_CATALOGUE in result.narrative
    assert "break date is selected" in result.statistical_interpretation
    refused = method.run(
        _context(_levels(growth), analysis_mode=AnalysisMode.POINT_IN_TIME),
        config,
    )
    assert refused.sufficiency == "insufficient"
    assert refused.investment_implication == "insufficient_evidence"
    assert refused.calculation["publication_allowed"] is False


def _hand_first_recursive_residual(design: np.ndarray, target: np.ndarray) -> float:
    """Brown-Durbin-Evans residual at the first row after the initial block."""

    regressors = design.shape[1]
    beta = np.linalg.lstsq(design[:regressors], target[:regressors], rcond=None)[0]
    row = design[regressors]
    gram_inverse = np.linalg.inv(design[:regressors].T @ design[:regressors])
    scale = math.sqrt(1.0 + float(row @ gram_inverse @ row))
    return float(target[regressors] - row @ beta) / scale


def _crosses(scaled: np.ndarray) -> bool:
    sigma = math.sqrt(float(scaled.var(ddof=1)))
    cusum = np.cumsum(scaled / sigma)
    count = len(scaled)
    steps = np.arange(1, count + 1, dtype=float)
    boundary = 0.948 * math.sqrt(count) + 2.0 * 0.948 * steps / math.sqrt(count)
    return bool(np.any(np.abs(cusum) > boundary))


def _levels(growth: np.ndarray) -> dict[str, dict[date, EconomicObservation]]:
    return {INDUSTRIAL_PRODUCTION_DATASET_ID: _level_map(growth)}


def _level_map(growth: np.ndarray) -> dict[date, EconomicObservation]:
    months = _months(date(1980, 1, 1), int(growth.size) + 1)
    log_level = math.log(100.0) + np.concatenate((np.zeros(1), np.cumsum(growth)))
    return {
        month: _observation(month, math.exp(float(log_level[index])))
        for index, month in enumerate(months)
    }


def _context(
    inputs: dict[str, dict[date, EconomicObservation]],
    *,
    analysis_mode: AnalysisMode = AnalysisMode.LATEST_REVISED,
) -> MethodContext:
    series = inputs[INDUSTRIAL_PRODUCTION_DATASET_ID]
    return MethodContext(
        inputs_by_dataset=inputs,
        evaluation_period=max(series),
        analysis_mode=analysis_mode,
        primary_dataset_id=INDUSTRIAL_PRODUCTION_DATASET_ID,
    )


def _observation(period: date, value: float) -> EconomicObservation:
    retrieved = datetime(2026, 8, 1, tzinfo=UTC)
    return EconomicObservation(
        observation_id=f"{INDUSTRIAL_PRODUCTION_DATASET_ID}-{period.isoformat()}",
        dataset_id=INDUSTRIAL_PRODUCTION_DATASET_ID,
        provider_id="test",
        source_id="test",
        rights_record_id="test",
        period_start=period,
        frequency=Frequency.MONTHLY,
        geography="US",
        unit=LEVEL_UNIT,
        seasonal_adjustment=SeasonalAdjustment.SEASONALLY_ADJUSTED,
        raw_value=format(value, ".10f"),
        quality_status=QualityStatus.OBSERVED,
        series_provenance=SeriesProvenance.LATEST_REVISED,
        provider_vintage_date=period,
        availability_precision=AvailabilityPrecision.UNKNOWN,
        retrieved_at=retrieved,
        first_seen_at=retrieved,
        adapter_version="test",
    )


def _months(start: date, count: int) -> list[date]:
    months: list[date] = []
    year, month = start.year, start.month
    for _ in range(count):
        months.append(date(year, month, 1))
        month += 1
        if month == 13:
            month = 1
            year += 1
    return months
