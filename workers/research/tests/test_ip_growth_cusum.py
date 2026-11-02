"""CUSUM of recursive residuals for industrial-production log growth. Fixture series only."""

from __future__ import annotations

import math
from datetime import UTC, date, datetime

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
from aqil_research.methods.autoregressive_benchmark import LEVEL_UNIT
from aqil_research.methods.ip_growth_cusum import (
    BOUNDARY_ALPHA,
    BOUNDARY_COEFFICIENT,
    INDUSTRIAL_PRODUCTION_DATASET_ID,
    IP_GROWTH_CUSUM,
    MINIMUM_GROWTH_MONTHS,
    NO_BREAK_DATE,
    PREDECLARED_LAG,
    PUBLICATION_ALLOWED,
    PUBLISHED_CONFIG,
    IpGrowthCusumMethod,
    autoregressive_design,
    cusum_from_growth,
)
from aqil_research.methods.protocol import MethodContext
from aqil_research.methods.registry import default_method_registry

STABLE_SEED = 0
SHIFT_SEED = 7
SAMPLE_SIZE = 240
SHIFT_AT = 25
SHOCK_SCALE = 0.01


def test_dependency_is_latest_revised_with_no_parameter_policy() -> None:
    method = IpGrowthCusumMethod()
    dependency = method.dependency()
    assert method.method_id == IP_GROWTH_CUSUM
    assert PUBLICATION_ALLOWED is False
    assert PREDECLARED_LAG == 1
    assert BOUNDARY_ALPHA == 0.95
    assert BOUNDARY_COEFFICIENT == 0.948
    assert MINIMUM_GROWTH_MONTHS == 120
    assert method.required_dataset_ids() == (INDUSTRIAL_PRODUCTION_DATASET_ID,)
    assert dependency.source_series == (INDUSTRIAL_PRODUCTION_DATASET_ID,)
    assert dependency.frequency == ("monthly",)
    assert dependency.vintage_class == "latest_revised"
    assert dependency.parameter_policy == "none"
    assert dependency.depends_on_method_ids == ()
    assert dependency.new_observation_requires_recalculation is True
    assert dependency.refit_is_different_command is False
    assert method.implementation_hash()
    assert method.config_hash(method.parse_config(dict(PUBLISHED_CONFIG)))
    registered = default_method_registry().get(IP_GROWTH_CUSUM)
    assert registered.method_id == IP_GROWTH_CUSUM
    assert registered.dependency().parameter_policy == "none"


def test_a_stable_autoregression_stays_inside_the_boundary() -> None:
    growth = _autoregression(phi_before=0.4, phi_after=0.4, seed=STABLE_SEED, break_at=SAMPLE_SIZE)
    result = cusum_from_growth(growth)
    path, upper = _library_path(growth)
    assert result["crosses_five_percent_boundary"] is False
    assert result["crosses_five_percent_boundary"] is _crosses(path, upper)
    assert result["recursive_residual_count"] == len(path)
    assert result["first_boundary"] == pytest.approx(float(upper[0]))
    assert float(upper[0]) == pytest.approx(BOUNDARY_COEFFICIENT * math.sqrt(len(path)))
    assert result["boundary_at_extreme"] == pytest.approx(
        float(upper[int(result["extreme_index"])])
    )
    assert abs(float(result["extreme_cusum"])) < float(result["boundary_at_extreme"])


def test_a_lag_coefficient_shift_crosses_the_boundary() -> None:
    growth = _autoregression(
        phi_before=0.85,
        phi_after=-0.85,
        seed=SHIFT_SEED,
        break_at=SHIFT_AT,
    )
    result = cusum_from_growth(growth)
    path, upper = _library_path(growth)
    assert result["crosses_five_percent_boundary"] is True
    assert result["crosses_five_percent_boundary"] is _crosses(path, upper)
    assert abs(float(result["extreme_cusum"])) > float(result["boundary_at_extreme"])
    with pytest.raises(ValueError, match="below 120"):
        cusum_from_growth(np.zeros(MINIMUM_GROWTH_MONTHS - 1))


def test_method_uses_log_growth_and_reports_either_outcome() -> None:
    method = IpGrowthCusumMethod()
    config = method.parse_config(dict(PUBLISHED_CONFIG))
    stable = _autoregression(phi_before=0.4, phi_after=0.4, seed=STABLE_SEED, break_at=SAMPLE_SIZE)
    shift = _autoregression(
        phi_before=0.85,
        phi_after=-0.85,
        seed=SHIFT_SEED,
        break_at=SHIFT_AT,
    )
    stable_result = method.run(_context(_levels(stable)), config)
    shift_result = method.run(_context(_levels(shift)), config)
    assert stable_result.sufficiency == "sufficient"
    assert shift_result.sufficiency == "sufficient"
    assert stable_result.calculation is not None
    assert shift_result.calculation is not None
    assert stable_result.calculation["publication_allowed"] is False
    assert stable_result.calculation["input_vintage"] == "latest_revised"
    assert stable_result.calculation["dataset_id"] == INDUSTRIAL_PRODUCTION_DATASET_ID
    assert stable_result.calculation["transformation"] == "monthly_log_growth"
    assert stable_result.calculation["predeclared_lag"] == PREDECLARED_LAG
    assert stable_result.calculation["lag_was_selected_by_an_information_criterion"] is False
    assert stable_result.calculation["constant_included"] is True
    assert stable_result.calculation["parameter_drift_diagnostic"] is True
    assert stable_result.calculation["chow_test"] is False
    assert stable_result.calculation["bai_perron_mean_shift"] is False
    assert stable_result.calculation["local_projection"] is False
    assert stable_result.calculation["selected_break_date"] is None
    assert stable_result.calculation["statsmodels_call"] == {
        "skip": None,
        "lamda": 0.0,
        "alpha": 0.95,
        "order_by": None,
    }
    assert stable_result.calculation["crosses_five_percent_boundary"] is False
    assert shift_result.calculation["crosses_five_percent_boundary"] is True
    assert (
        stable_result.calculation["crosses_five_percent_boundary"]
        is (cusum_from_growth(stable)["crosses_five_percent_boundary"])
    )
    assert (
        shift_result.calculation["crosses_five_percent_boundary"]
        is (cusum_from_growth(shift)["crosses_five_percent_boundary"])
    )
    assert stable_result.investment_implication == "no_action"
    assert stable_result.causal_hypothesis == "none"
    assert NO_BREAK_DATE in stable_result.narrative
    assert "A Chow test is not estimated." in stable_result.limitations
    assert "A Bai-Perron mean shift is not estimated." in stable_result.limitations
    assert "A local projection is not estimated." in stable_result.limitations
    refused = method.run(
        _context(_levels(stable), analysis_mode=AnalysisMode.POINT_IN_TIME),
        config,
    )
    assert refused.sufficiency == "insufficient"
    assert refused.investment_implication == "insufficient_evidence"
    assert refused.calculation["publication_allowed"] is False
    short = _autoregression(phi_before=0.2, phi_after=0.2, seed=1, break_at=40, count=40)
    assert method.run(_context(_levels(short)), config).sufficiency == "insufficient"
    vintage = {
        month: _observation(month, 100.0, provenance=SeriesProvenance.PROVIDER_VINTAGE)
        for month in _months(date(1980, 1, 1), MINIMUM_GROWTH_MONTHS + 1)
    }
    assert (
        method.run(
            _context({INDUSTRIAL_PRODUCTION_DATASET_ID: vintage}),
            config,
        ).sufficiency
        == "insufficient"
    )


def _autoregression(
    *,
    phi_before: float,
    phi_after: float,
    seed: int,
    break_at: int,
    count: int = SAMPLE_SIZE,
) -> np.ndarray:
    """Autoregression with a zero intercept. Only the lag coefficient can change."""

    generator = np.random.default_rng(seed)
    shocks = generator.normal(0.0, SHOCK_SCALE, size=count)
    growth = np.zeros(count)
    for index in range(1, count):
        phi = phi_before if index < break_at else phi_after
        growth[index] = phi * growth[index - 1] + shocks[index]
    return growth


def _library_path(growth: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    design, target = autoregressive_design(growth, PREDECLARED_LAG)
    fitted = OLS(target, design).fit()
    cusum, boundary = recursive_olsresiduals(
        fitted,
        skip=None,
        lamda=0.0,
        alpha=BOUNDARY_ALPHA,
        order_by=None,
    )[5:]
    return np.asarray(cusum[1:], dtype=float), np.asarray(boundary[1], dtype=float)


def _crosses(path: np.ndarray, upper: np.ndarray) -> bool:
    return bool(np.any(np.abs(path) > upper))


def _levels(growth: np.ndarray) -> dict[str, dict[date, EconomicObservation]]:
    months = _months(date(1980, 1, 1), int(growth.size) + 1)
    log_level = math.log(100.0) + np.concatenate((np.zeros(1), np.cumsum(growth)))
    return {
        INDUSTRIAL_PRODUCTION_DATASET_ID: {
            month: _observation(month, math.exp(float(log_level[index])))
            for index, month in enumerate(months)
        },
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


def _observation(
    period: date,
    value: float,
    *,
    provenance: SeriesProvenance = SeriesProvenance.LATEST_REVISED,
) -> EconomicObservation:
    retrieved = datetime(2026, 8, 1, tzinfo=UTC)
    precision = (
        AvailabilityPrecision.UNKNOWN
        if provenance == SeriesProvenance.LATEST_REVISED
        else AvailabilityPrecision.DATE
    )
    return EconomicObservation(
        observation_id=f"{INDUSTRIAL_PRODUCTION_DATASET_ID}-{period.isoformat()}-{provenance.value}",
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
        series_provenance=provenance,
        provider_vintage_date=period,
        availability_precision=precision,
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
