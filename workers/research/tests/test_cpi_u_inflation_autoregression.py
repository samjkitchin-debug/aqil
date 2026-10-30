"""CPI-U log-change autoregression. Hand-checked ordinary least squares only."""

from __future__ import annotations

import inspect
import json
import math
from datetime import UTC, date, datetime

import numpy as np
import pytest
import statsmodels
from statsmodels.tsa.ar_model import AutoReg, ar_select_order

from aqil_research.contracts.observation import (
    AnalysisMode,
    AvailabilityPrecision,
    EconomicObservation,
    Frequency,
    QualityStatus,
    SeasonalAdjustment,
    SeriesProvenance,
)
from aqil_research.methods.cpi_u_inflation_autoregression import (
    ANDREWS_CHEN_NOTE,
    CPI_U_INFLATION_AUTREGRESSION,
    LOCKED_NUMPY,
    LOCKED_STATSMODELS,
    MAX_LAG,
    MINIMUM_GROWTH_MONTHS,
    PUBLICATION_ALLOWED,
    PUBLISHED_CONFIG,
    QUALIFICATION_STATEMENT,
    CpiUInflationAutoregressionMethod,
    autoregression_from_log_changes,
    contiguous_monthly_log_changes,
    ols_ar_coefficients,
    persistence_sum,
    select_ar_lag_by_aic,
)
from aqil_research.methods.prices_and_policy import CPI_DATASET_ID, CPI_UNIT
from aqil_research.methods.protocol import MethodContext
from aqil_research.methods.registry import default_method_registry


def test_locked_library_defaults_are_ols_with_a_constant_and_bic_lag_search() -> None:
    assert statsmodels.__version__ == LOCKED_STATSMODELS
    assert np.__version__ == LOCKED_NUMPY
    assert inspect.signature(ar_select_order).parameters["ic"].default == "bic"
    assert inspect.signature(AutoReg.__init__).parameters["trend"].default == "c"


def test_ols_matches_the_normal_equations_and_statsmodels() -> None:
    # Four equations, lag 1, sample starting at the first lag:
    #   2 = c + phi * 1
    #   3 = c + phi * 2
    #   2 = c + phi * 3
    #   4 = c + phi * 2
    # X'X = [[4, 8], [8, 18]], X'y = [11, 22], determinant 8.
    # beta = (1/8) * [18*11 - 8*22, -8*11 + 4*22] = [2.75, 0].
    growth = np.array([1.0, 2.0, 3.0, 2.0, 4.0])
    coefficients = ols_ar_coefficients(growth, lag=1, sample_start=1)
    assert coefficients == pytest.approx([2.75, 0.0])
    assert persistence_sum(coefficients) == pytest.approx(0.0)
    explicit = AutoReg(growth, lags=1, trend="c", hold_back=1).fit().params
    default_trend = AutoReg(growth, lags=1, hold_back=1).fit().params
    assert explicit == pytest.approx(coefficients)
    assert default_trend == pytest.approx(explicit)


def test_exact_ar1_persistence_is_the_single_coefficient() -> None:
    # y_t = 0.5 * y_{t-1} with no intercept. Powers of one half are exact in binary.
    growth = np.array([1.0, 0.5, 0.25, 0.125, 0.0625])
    coefficients = ols_ar_coefficients(growth, lag=1, sample_start=1)
    assert coefficients == pytest.approx([0.0, 0.5])
    assert persistence_sum(coefficients) == pytest.approx(0.5)


def test_exact_ar2_persistence_is_the_sum_of_the_two_coefficients() -> None:
    # y_t = 0.2 * y_{t-1} + 0.3 * y_{t-2}. The OLS sum is 0.5, not a median-unbiased estimate.
    growth = np.zeros(40)
    growth[0] = 1.0
    growth[1] = 0.5
    for index in range(2, growth.size):
        growth[index] = 0.2 * growth[index - 1] + 0.3 * growth[index - 2]
    coefficients = ols_ar_coefficients(growth, lag=2, sample_start=MAX_LAG)
    assert coefficients == pytest.approx([0.0, 0.2, 0.3])
    assert persistence_sum(coefficients) == pytest.approx(0.5)
    library = AutoReg(growth, lags=2, trend="c", hold_back=MAX_LAG).fit().params
    assert library == pytest.approx(coefficients)


def test_aic_on_the_common_sample_matches_statsmodels() -> None:
    generator = np.random.default_rng(4)
    shocks = generator.normal(0.0, 0.01, size=80)
    growth = np.zeros(80)
    for index in range(2, growth.size):
        growth[index] = 0.4 * growth[index - 1] - 0.2 * growth[index - 2] + shocks[index]
    lag, coefficients, _aic = select_ar_lag_by_aic(growth)
    scores: list[tuple[float, int]] = []
    for candidate in range(1, MAX_LAG + 1):
        fitted = AutoReg(growth, lags=candidate, trend="c", hold_back=MAX_LAG).fit()
        scores.append((float(fitted.aic), candidate))
    library_lag = min(scores)[1]
    assert lag == library_lag
    assert lag <= MAX_LAG
    library = AutoReg(growth, lags=lag, trend="c", hold_back=MAX_LAG).fit().params
    assert coefficients == pytest.approx(np.asarray(library, dtype=float))


def test_log_change_is_the_natural_log_difference_and_does_not_bridge_a_gap() -> None:
    january = date(2000, 1, 1)
    february = date(2000, 2, 1)
    april = date(2000, 4, 1)
    sample = contiguous_monthly_log_changes({january: 100.0, february: 110.0, april: 120.0})
    assert sample.growth_months == (february,)
    assert sample.values == pytest.approx((math.log(110.0) - math.log(100.0),))
    assert april not in sample.growth_months


def test_a_short_sample_is_not_estimated_and_stays_unpublished() -> None:
    short = autoregression_from_log_changes(np.full(MINIMUM_GROWTH_MONTHS - 1, 0.01))
    assert short["sufficient"] is False
    assert short["publication_allowed"] is False
    assert short["empirically_qualified_as_forecast"] is False
    assert short["andrews_chen_median_unbiased"] is False
    assert short["qualification_statement"] == QUALIFICATION_STATEMENT


def test_method_reports_the_ols_sum_on_latest_revised_levels_only() -> None:
    method = CpiUInflationAutoregressionMethod()
    config = method.parse_config(dict(PUBLISHED_CONFIG))
    assert method.method_id == CPI_U_INFLATION_AUTREGRESSION
    assert PUBLICATION_ALLOWED is False
    assert method.accepted_config_payload()["config_id"] == "cpi-u-inflation-autoregression-v1"
    dependency = method.dependency()
    assert dependency.source_series == (CPI_DATASET_ID,)
    assert dependency.vintage_class == "latest_revised"
    assert str(MINIMUM_GROWTH_MONTHS) in dependency.minimum_history
    assert dependency.parameter_policy == "none"
    assert dependency.refit_is_different_command is False
    registered = default_method_registry().get(CPI_U_INFLATION_AUTREGRESSION)
    assert registered.method_id == CPI_U_INFLATION_AUTREGRESSION
    growth = np.array([0.5**index for index in range(MINIMUM_GROWTH_MONTHS)])
    months = _months(date(2000, 1, 1), len(growth) + 1)
    log_levels = np.empty(len(months))
    log_levels[0] = math.log(100.0)
    log_levels[1:] = math.log(100.0) + np.cumsum(growth)
    series = {
        month: _observation(month, float(math.exp(log_levels[index])))
        for index, month in enumerate(months)
    }
    result = method.run(_context(series), config)
    assert result.sufficiency == "sufficient"
    assert result.investment_implication == "no_action"
    assert result.causal_hypothesis == "none"
    calculation = result.calculation
    assert calculation is not None
    assert calculation["publication_allowed"] is False
    assert calculation["real_time_claim"] is False
    assert calculation["empirically_qualified_as_forecast"] is False
    assert calculation["qualification_statement"] == QUALIFICATION_STATEMENT
    assert calculation["andrews_chen_median_unbiased"] is False
    assert calculation["persistence_estimator"] == "ols_sum_of_ar_coefficients"
    assert calculation["modelled_transformation"] == "monthly_log_change"
    assert calculation["aic_lag"] == 1
    assert calculation["persistence"] == pytest.approx(0.5)
    assert ANDREWS_CHEN_NOTE in result.statistical_interpretation
    assert "median-unbiased" in result.limitations[3]
    encoded = json.dumps(calculation)
    assert "NaN" not in encoded
    assert "Infinity" not in encoded
    refused = method.run(_context(series, analysis_mode=AnalysisMode.POINT_IN_TIME), config)
    assert refused.sufficiency == "insufficient"
    assert refused.investment_implication == "insufficient_evidence"
    assert refused.calculation is not None
    assert refused.calculation["publication_allowed"] is False


def _context(
    series: dict[date, EconomicObservation],
    *,
    analysis_mode: AnalysisMode = AnalysisMode.LATEST_REVISED,
) -> MethodContext:
    return MethodContext(
        inputs_by_dataset={CPI_DATASET_ID: series},
        evaluation_period=max(series),
        analysis_mode=analysis_mode,
        primary_dataset_id=CPI_DATASET_ID,
    )


def _observation(period: date, value: float) -> EconomicObservation:
    retrieved = datetime(2026, 8, 1, tzinfo=UTC)
    return EconomicObservation(
        observation_id=f"cpi-{period.isoformat()}",
        dataset_id=CPI_DATASET_ID,
        provider_id="test",
        source_id="test",
        rights_record_id="test",
        period_start=period,
        frequency=Frequency.MONTHLY,
        geography="US",
        unit=CPI_UNIT,
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
