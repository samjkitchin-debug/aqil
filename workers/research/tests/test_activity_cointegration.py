"""Activity-level Engle-Granger cointegration. Fixture series only."""

from __future__ import annotations

import json
import math
from datetime import UTC, date, datetime

import numpy as np
import pytest
from statsmodels.tsa.stattools import coint

from aqil_research.contracts.observation import (
    AnalysisMode,
    AvailabilityPrecision,
    EconomicObservation,
    Frequency,
    QualityStatus,
    SeasonalAdjustment,
    SeriesProvenance,
)
from aqil_research.methods.activity_cointegration import (
    ACTIVITY_LEVEL_COINTEGRATION,
    INDUSTRIAL_PRODUCTION_DATASET_ID,
    MINIMUM_OVERLAP_MONTHS,
    NO_CAUSAL_CLAIM,
    PAYROLL_DATASET_ID,
    PAYROLL_UNIT,
    PUBLICATION_ALLOWED,
    PUBLISHED_CONFIG,
    SIGNIFICANCE,
    UNITS,
    ActivityLevelCointegrationMethod,
    activity_cointegration_from_log_levels,
    longest_contiguous_overlap,
    residual_adf_max_lag,
)
from aqil_research.methods.protocol import MethodContext
from aqil_research.methods.registry import default_method_registry

COINTEGRATED_SEED = 7
COINTEGRATED_COUNT = 240
INDEPENDENT_SEED = 11
INDEPENDENT_COUNT = 240


def test_dependency_is_latest_revised_with_no_parameter_policy() -> None:
    method = ActivityLevelCointegrationMethod()
    dependency = method.dependency()
    assert method.method_id == ACTIVITY_LEVEL_COINTEGRATION
    assert PUBLICATION_ALLOWED is False
    assert SIGNIFICANCE == 0.05
    assert MINIMUM_OVERLAP_MONTHS == 120
    assert method.required_dataset_ids() == (
        INDUSTRIAL_PRODUCTION_DATASET_ID,
        PAYROLL_DATASET_ID,
    )
    assert dependency.source_series == method.required_dataset_ids()
    assert dependency.frequency == ("monthly",)
    assert dependency.vintage_class == "latest_revised"
    assert dependency.parameter_policy == "none"
    assert dependency.depends_on_method_ids == ()
    assert dependency.new_observation_requires_recalculation is True
    assert dependency.refit_is_different_command is False
    assert PAYROLL_UNIT == "thousands"
    assert method.implementation_hash()
    assert method.config_hash(method.parse_config(dict(PUBLISHED_CONFIG)))
    registered = default_method_registry().get(ACTIVITY_LEVEL_COINTEGRATION)
    assert registered.method_id == ACTIVITY_LEVEL_COINTEGRATION
    assert registered.dependency().parameter_policy == "none"


def test_a_cointegrated_pair_rejects_no_cointegration_at_five_percent() -> None:
    left, right = _cointegrated_logs(COINTEGRATED_SEED, COINTEGRATED_COUNT)
    result = activity_cointegration_from_log_levels(left, right)
    library = coint(
        left,
        right,
        trend="c",
        method="aeg",
        maxlag=residual_adf_max_lag(COINTEGRATED_COUNT),
        autolag="aic",
        return_results=False,
    )
    assert result["growth_rates_used"] is False
    assert result["granger_causality"] is False
    assert result["vector_autoregression"] is False
    assert result["causal_claim"] is False
    assert result["publication_allowed"] is False
    assert result["significance"] == SIGNIFICANCE
    assert result["statistic"] == pytest.approx(float(library[0]))
    assert result["p_value"] == pytest.approx(float(library[1]))
    assert result["critical_value_five_percent"] == pytest.approx(float(library[2][1]))
    assert float(library[0]) < float(library[2][1])
    assert float(library[1]) < SIGNIFICANCE
    assert result["rejects_no_cointegration_at_five_percent"] is True
    assert result["first_stage"]["constant_included"] is True
    assert result["first_stage"]["slope"] == pytest.approx(0.4, abs=0.05)
    assert result["second_stage"]["regression"] == "no_constant_no_trend"
    assert result["second_stage"]["lag_rule"] == "aic"
    assert 0 <= result["second_stage"]["used_lag"] <= result["second_stage"]["max_lag"]
    assert result["second_stage"]["ordinary_adf_p_value_used"] is False
    encoded = json.dumps(result)
    assert "NaN" not in encoded
    assert "Infinity" not in encoded


def test_independent_random_walks_do_not_reject_no_cointegration() -> None:
    left, right = _independent_logs(INDEPENDENT_SEED, INDEPENDENT_COUNT)
    result = activity_cointegration_from_log_levels(left, right)
    library = coint(
        left,
        right,
        trend="c",
        method="aeg",
        maxlag=None,
        autolag="aic",
        return_results=False,
    )
    assert result["statistic"] == pytest.approx(float(library[0]))
    assert result["critical_value_five_percent"] == pytest.approx(float(library[2][1]))
    assert float(library[0]) > float(library[2][1])
    assert float(library[1]) >= SIGNIFICANCE
    assert result["rejects_no_cointegration_at_five_percent"] is False
    assert result["statsmodels_call"]["maxlag"] == residual_adf_max_lag(INDEPENDENT_COUNT)


def test_a_gap_is_not_interpolated() -> None:
    months = _months(date(2000, 1, 1), 8)
    left = {month: float(index + 10) for index, month in enumerate(months)}
    right = {month: float(index + 20) for index, month in enumerate(months)}
    del left[months[4]]
    chosen, left_logs, right_logs, excluded = longest_contiguous_overlap(left, right)
    assert chosen == tuple(months[:4])
    assert excluded == 3
    assert left_logs == tuple(math.log(left[month]) for month in chosen)
    assert right_logs == tuple(math.log(right[month]) for month in chosen)


def test_method_stores_the_log_level_result_on_latest_revised_levels() -> None:
    method = ActivityLevelCointegrationMethod()
    config = method.parse_config(dict(PUBLISHED_CONFIG))
    left, right = _cointegrated_logs(COINTEGRATED_SEED, 150)
    result = method.run(_context(_levels(left, right)), config)
    assert result.sufficiency == "sufficient"
    assert result.calculation is not None
    assert result.calculation["publication_allowed"] is False
    assert result.calculation["input_vintage"] == "latest_revised"
    assert result.calculation["transformation"] == "natural_log_levels"
    assert result.calculation["rejects_no_cointegration_at_five_percent"] is True
    assert result.calculation["left_dataset_id"] == INDUSTRIAL_PRODUCTION_DATASET_ID
    assert result.calculation["right_dataset_id"] == PAYROLL_DATASET_ID
    assert result.investment_implication == "no_action"
    assert result.causal_hypothesis == "none"
    assert NO_CAUSAL_CLAIM in result.narrative
    assert "Granger causality on growth rates is not estimated." in result.limitations
    assert "A vector autoregression is not estimated." in result.limitations
    assert len(result.observation_ids) == 300
    refused = method.run(
        _context(_levels(left, right), analysis_mode=AnalysisMode.POINT_IN_TIME),
        config,
    )
    assert refused.sufficiency == "insufficient"
    assert refused.investment_implication == "insufficient_evidence"
    assert refused.calculation["publication_allowed"] is False
    vintage = _levels(left, right, provenance=SeriesProvenance.PROVIDER_VINTAGE)
    assert method.run(_context(vintage), config).sufficiency == "insufficient"
    short_left, short_right = _cointegrated_logs(1, 24)
    short = method.run(_context(_levels(short_left, short_right)), config)
    assert short.sufficiency == "insufficient"
    assert short.calculation["publication_allowed"] is False


def _cointegrated_logs(seed: int, count: int) -> tuple[np.ndarray, np.ndarray]:
    """Random walk plus a stationary gap. The gap scale is small enough to reject."""

    generator = np.random.default_rng(seed)
    payroll = np.cumsum(generator.normal(0.0, 1.0, size=count))
    production = 1.5 + 0.4 * payroll + generator.normal(0.0, 0.15, size=count)
    return production, payroll


def _independent_logs(seed: int, count: int) -> tuple[np.ndarray, np.ndarray]:
    generator = np.random.default_rng(seed)
    production = np.cumsum(generator.normal(size=count))
    payroll = np.cumsum(generator.normal(size=count))
    return production, payroll


def _levels(
    production: np.ndarray,
    payroll: np.ndarray,
    *,
    provenance: SeriesProvenance = SeriesProvenance.LATEST_REVISED,
) -> dict[str, dict[date, EconomicObservation]]:
    months = _months(date(1990, 1, 1), int(production.size))
    return {
        INDUSTRIAL_PRODUCTION_DATASET_ID: {
            month: _observation(
                INDUSTRIAL_PRODUCTION_DATASET_ID,
                month,
                math.exp(float(production[index])),
                provenance=provenance,
            )
            for index, month in enumerate(months)
        },
        PAYROLL_DATASET_ID: {
            month: _observation(
                PAYROLL_DATASET_ID,
                month,
                math.exp(float(payroll[index]) + 8.0),
                provenance=provenance,
            )
            for index, month in enumerate(months)
        },
    }


def _context(
    inputs: dict[str, dict[date, EconomicObservation]],
    *,
    analysis_mode: AnalysisMode = AnalysisMode.LATEST_REVISED,
) -> MethodContext:
    return MethodContext(
        inputs_by_dataset=inputs,
        evaluation_period=max(inputs[INDUSTRIAL_PRODUCTION_DATASET_ID]),
        analysis_mode=analysis_mode,
        primary_dataset_id=INDUSTRIAL_PRODUCTION_DATASET_ID,
    )


def _observation(
    dataset_id: str,
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
        observation_id=f"{dataset_id}-{period.isoformat()}",
        dataset_id=dataset_id,
        provider_id="test",
        source_id="test",
        rights_record_id="test",
        period_start=period,
        frequency=Frequency.MONTHLY,
        geography="US",
        unit=UNITS[dataset_id],
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
