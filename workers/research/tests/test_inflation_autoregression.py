"""CPI-U inflation autoregression. Synthetic series only."""

from __future__ import annotations

import json
import math
from datetime import UTC, date, datetime

import numpy as np
import pytest
from pydantic import ValidationError

from aqil_research.contracts.observation import (
    AnalysisMode,
    AvailabilityPrecision,
    EconomicObservation,
    Frequency,
    QualityStatus,
    SeasonalAdjustment,
    SeriesProvenance,
)
from aqil_research.methods.inflation_autoregression import (
    AIC_EQUATION,
    AUTOREGRESSION_EQUATION,
    CPI_DATASET_ID,
    CPI_UNIT,
    HALF_LIFE_EQUATION,
    HOLDOUT_MONTHS,
    HORIZONS,
    INFLATION_AUTOREGRESSION,
    MAX_LAG,
    MIN_ESTIMATION_MONTHS,
    MINIMUM_GROWTH_MONTHS,
    NOT_A_PRODUCT_FORECAST,
    NOT_A_TAYLOR_RULE,
    NOT_QUALIFIED,
    PERSISTENCE_EQUATION,
    PUBLICATION_ALLOWED,
    TRANSFORMATION_EQUATION,
    InflationAutoregressionMethod,
    aic_value,
    beat_historical_mean,
    inflation_autoregression_from_growth,
    iterated_forecast,
    persistence_summary,
    select_inflation_lag,
    trailing_monthly_log_change,
)
from aqil_research.methods.protocol import MethodContext
from aqil_research.pipeline.execute_method import execution_refusal


def test_contract_is_latest_revised_and_refit_is_rejected() -> None:
    method = InflationAutoregressionMethod()
    dependency = method.dependency()
    assert method.method_id == INFLATION_AUTOREGRESSION
    assert PUBLICATION_ALLOWED is False
    assert method.required_dataset_ids() == (CPI_DATASET_ID,)
    assert dependency.source_series == (CPI_DATASET_ID,)
    assert dependency.frequency == ("monthly",)
    assert dependency.vintage_class == "latest_revised"
    assert dependency.parameter_policy == "none"
    assert dependency.depends_on_method_ids == ()
    assert dependency.new_observation_requires_recalculation is True
    assert dependency.refit_is_different_command is False
    assert str(MINIMUM_GROWTH_MONTHS) in dependency.minimum_history
    assert execution_refusal(method, refit=True) is not None
    assert execution_refusal(method, refit=False) is None
    assert len(method.implementation_hash()) == 64
    assert method.implementation_hash() == InflationAutoregressionMethod().implementation_hash()
    payload = method.accepted_config_payload()
    assert "selected_lag" not in payload
    assert "lag" not in payload
    config = method.parse_config(payload)
    assert method.config_hash(config) == method.config_hash(config)
    with pytest.raises(ValidationError):
        method.parse_config({**payload, "execution_mode": "refit"})


def test_logarithmic_change_is_the_adjacent_difference_and_does_not_bridge_a_gap() -> None:
    months = _months(date(2000, 1, 1), 8)
    levels = {
        months[0]: 100.0,
        months[1]: 100.0 * math.exp(0.02),
        months[2]: 100.0 * math.exp(0.05),
        months[3]: 100.0 * math.exp(0.05),
        months[5]: 120.0,
        months[6]: 120.0 * math.exp(-0.01),
        months[7]: 120.0 * math.exp(-0.01),
    }
    sample = trailing_monthly_log_change(levels)
    assert sample.growth_months == (months[6], months[7])
    assert sample.values == pytest.approx((-0.01, 0.0))
    assert months[1] not in sample.growth_months
    assert sample.excluded_growth_months == 3
    full = trailing_monthly_log_change(
        {
            months[0]: 100.0,
            months[1]: 100.0 * math.exp(0.02),
            months[2]: 100.0 * math.exp(0.05),
            months[3]: 100.0 * math.exp(0.05),
        },
    )
    assert full.values == pytest.approx((0.02, 0.03, 0.0))


def test_aic_formula_common_sample_ols_and_the_smaller_lag_on_a_tie() -> None:
    assert aic_value(0.5, 100, 3) == pytest.approx(100 * math.log(0.5 / 100) + 2 * (3 + 1))
    assert aic_value(0.0, 100, 1) == -math.inf
    zeros = np.zeros(160)
    lag, coefficients, aic = select_inflation_lag(zeros[:MIN_ESTIMATION_MONTHS])
    assert lag == 1
    assert coefficients == pytest.approx([0.0, 0.0])
    assert aic == -math.inf
    generator = np.random.default_rng(0)
    shocks = generator.normal(0.0, 0.01, size=800)
    growth = np.zeros(800)
    for index in range(2, 800):
        growth[index] = 0.4 * growth[index - 1] - 0.2 * growth[index - 2] + shocks[index]
    selected, fitted, _aic = select_inflation_lag(growth)
    assert selected == 2
    assert selected <= MAX_LAG
    start = MAX_LAG
    design = np.ones((growth.size - start, selected + 1))
    for column in range(1, selected + 1):
        design[:, column] = growth[start - column : growth.size - column]
    expected, _, _, _ = np.linalg.lstsq(design, growth[start:], rcond=None)
    assert fitted == pytest.approx(expected)


def test_persistence_half_life_and_the_iterated_equation() -> None:
    summary = persistence_summary(np.array([0.0, 0.5]))
    assert summary["equation"] == PERSISTENCE_EQUATION
    assert summary["half_life_equation"] == HALF_LIFE_EQUATION
    assert summary["sum_of_autoregressive_coefficients"] == pytest.approx(0.5)
    assert summary["half_life_months"] == pytest.approx(1.0)
    assert summary["half_life_defined"] is True
    assert summary["includes_intercept"] is False
    undefined = persistence_summary(np.array([0.2, 1.2]))
    assert undefined["half_life_defined"] is False
    assert undefined["half_life_months"] is None
    negative = persistence_summary(np.array([0.0, -0.4]))
    assert negative["half_life_defined"] is False
    path = iterated_forecast(np.array([1.0, 2.0]), np.array([0.0, 0.5, -0.2]), 2)
    assert path == pytest.approx([0.8, 0.0])


def test_a_tie_does_not_beat_the_historical_mean_or_qualify() -> None:
    assert (
        beat_historical_mean(
            autoregressive_mae=1.0,
            autoregressive_rmse=1.0,
            historical_mean_mae=1.0,
            historical_mean_rmse=1.0,
        )
        is False
    )
    assert (
        beat_historical_mean(
            autoregressive_mae=0.9,
            autoregressive_rmse=1.1,
            historical_mean_mae=1.0,
            historical_mean_rmse=1.0,
        )
        is False
    )
    assert (
        beat_historical_mean(
            autoregressive_mae=0.9,
            autoregressive_rmse=0.9,
            historical_mean_mae=1.0,
            historical_mean_rmse=1.0,
        )
        is True
    )
    result = inflation_autoregression_from_growth(np.zeros(MINIMUM_GROWTH_MONTHS))
    assert result["sufficient"] is True
    assert result["selected_lag"] == 1
    assert result["historical_mean"] == pytest.approx(0.0)
    assert result["estimation_month_count"] == MIN_ESTIMATION_MONTHS
    assert result["holdout_month_count"] == HOLDOUT_MONTHS
    assert result["annualised"] is False
    assert result["second_difference_applied"] is False
    assert result["full_sample_standardisation"] is False
    assert result["twelve_month_price_rank"] is False
    assert result["taylor_rule"] is False
    assert result["product_forecast"] is False
    assert result["publication_allowed"] is False
    assert result["retrospective"] is True
    assert result["input_vintage"] == "latest_revised"
    assert result["parameter_policy"] == "none"
    assert result["refit_rejected"] is True
    assert result["transformation_equation"] == TRANSFORMATION_EQUATION
    assert result["autoregression_equation"] == AUTOREGRESSION_EQUATION
    assert result["predeclared"]["information_criterion"] == "aic"
    assert result["predeclared"]["aic_equation"] == AIC_EQUATION
    assert result["predeclared"]["bic_used_for_selection"] is False
    horizons = {row["horizon_months"]: row for row in result["horizons"]}
    assert set(horizons) == set(HORIZONS)
    assert horizons[1]["origin_count"] == HOLDOUT_MONTHS
    assert horizons[12]["origin_count"] == HOLDOUT_MONTHS - 12 + 1
    assert horizons[1]["mae"] == pytest.approx(0.0)
    assert horizons[1]["historical_mean_mae"] == pytest.approx(0.0)
    assert horizons[1]["beat_historical_mean"] is False
    assert result["empirically_qualified_as_forecast"] is False
    assert result["empirically_qualified_as_forecast"] is all(
        row["beat_historical_mean"] is True for row in result["horizons"]
    )
    assert NOT_QUALIFIED in result["qualification_statement"]
    assert NOT_A_PRODUCT_FORECAST in result["qualification_statement"]
    assert NOT_A_TAYLOR_RULE in result["qualification_statement"]
    json.dumps(result, allow_nan=False)


def test_the_held_out_tail_does_not_choose_the_lag_or_the_mean() -> None:
    growth = np.concatenate([np.full(MIN_ESTIMATION_MONTHS, 0.01), np.full(HOLDOUT_MONTHS, 0.05)])
    result = inflation_autoregression_from_growth(growth)
    assert result["historical_mean"] == pytest.approx(0.01)
    assert result["historical_mean"] != pytest.approx(float(growth.mean()))
    assert result["estimation_sample_excludes_holdout"] is True
    generator = np.random.default_rng(4)
    shocks = generator.normal(0.0, 0.01, size=240)
    persistent = np.zeros(240)
    for index in range(1, 240):
        persistent[index] = 0.8 * persistent[index - 1] + shocks[index]
    original = inflation_autoregression_from_growth(persistent)
    altered = persistent.copy()
    altered[-HOLDOUT_MONTHS:] = 5.0
    changed = inflation_autoregression_from_growth(altered)
    assert original["selected_lag"] == changed["selected_lag"]
    assert original["autoregressive_coefficients"] == changed["autoregressive_coefficients"]
    assert original["intercept"] == changed["intercept"]
    assert original["historical_mean"] == changed["historical_mean"]
    assert original["horizons"][0]["mae"] != changed["horizons"][0]["mae"]
    assert original["empirically_qualified_as_forecast"] is all(
        row["beat_historical_mean"] is True for row in original["horizons"]
    )
    assert original["product_forecast"] is False
    assert original["publication_allowed"] is False
    assert original["taylor_rule"] is False
    one_month = next(row for row in original["horizons"] if row["horizon_months"] == 1)
    assert one_month["beat_historical_mean"] is True
    assert one_month["mae"] < one_month["historical_mean_mae"]
    assert one_month["rmse"] < one_month["historical_mean_rmse"]
    if original["empirically_qualified_as_forecast"] is True:
        assert NOT_QUALIFIED not in original["qualification_statement"]
    else:
        assert NOT_QUALIFIED in original["qualification_statement"]
    assert NOT_A_PRODUCT_FORECAST in original["qualification_statement"]
    json.dumps(original, allow_nan=False)


def test_short_empty_and_gapped_samples_stay_insufficient_and_unqualified() -> None:
    method = InflationAutoregressionMethod()
    config = method.parse_config(method.accepted_config_payload())
    assert method.run(_context({}), config).sufficiency == "insufficient"
    short_months = _months(date(2010, 1, 1), 10)
    short = {month: _observation(month, 100.0 + index) for index, month in enumerate(short_months)}
    short_result = method.run(_context(short), config)
    assert short_result.sufficiency == "insufficient"
    assert short_result.calculation["publication_allowed"] is False
    assert short_result.calculation["taylor_rule"] is False
    assert short_result.calculation["empirically_qualified_as_forecast"] is False
    assert short_result.calculation["product_forecast"] is False
    assert NOT_A_TAYLOR_RULE in short_result.narrative
    assert NOT_QUALIFIED in short_result.narrative
    gapped_months = _months(date(2000, 1, 1), 160)
    gapped = {month: _observation(month, 100.0) for month in gapped_months}
    del gapped[gapped_months[150]]
    gapped_result = method.run(_context(gapped), config)
    assert gapped_result.sufficiency == "insufficient"
    assert "144" in (gapped_result.missing_reason or "")
    assert gapped_result.calculation["empirically_qualified_as_forecast"] is False
    short_growth = inflation_autoregression_from_growth(np.zeros(MINIMUM_GROWTH_MONTHS - 1))
    assert short_growth["sufficient"] is False


def test_method_uses_levels_through_the_evaluation_month_and_does_not_qualify_a_tie() -> None:
    method = InflationAutoregressionMethod()
    config = method.parse_config(dict(method.accepted_config_payload()))
    first_hash = method.config_hash(config)
    months = _months(date(2000, 1, 1), MINIMUM_GROWTH_MONTHS + 1)
    series = {month: _observation(month, 250.0) for month in months}
    evaluation = months[-1]
    result = method.run(_context(series, evaluation=evaluation), config)
    assert result.sufficiency == "sufficient"
    assert result.calculation is not None
    assert result.investment_implication == "no_action"
    assert result.causal_hypothesis == "none"
    assert result.calculation["publication_allowed"] is False
    assert result.calculation["product_forecast"] is False
    assert result.calculation["taylor_rule"] is False
    assert result.calculation["empirically_qualified_as_forecast"] is False
    assert result.calculation["input_vintage"] == "latest_revised"
    assert result.calculation["retrospective"] is True
    assert result.calculation["dataset_id"] == CPI_DATASET_ID
    assert result.calculation["growth_month_count"] == MINIMUM_GROWTH_MONTHS
    assert result.calculation["growth_end"] == evaluation.isoformat()
    assert result.calculation["selected_lag"] == 1
    assert NOT_QUALIFIED in result.narrative
    assert NOT_A_PRODUCT_FORECAST in result.narrative
    assert NOT_A_TAYLOR_RULE in result.narrative
    assert "rank" not in result.calculation
    assert method.config_hash(config) == first_hash
    later = months[-1]
    extended = dict(series)
    extended[next_month(later)] = _observation(next_month(later), 900.0)
    held = method.run(_context(extended, evaluation=evaluation), config)
    assert held.calculation["growth_end"] == result.calculation["growth_end"]
    assert held.calculation["selected_lag"] == result.calculation["selected_lag"]
    assert held.calculation["historical_mean"] == result.calculation["historical_mean"]
    refused = method.run(_context(series, analysis_mode=AnalysisMode.POINT_IN_TIME), config)
    assert refused.sufficiency == "insufficient"
    assert refused.calculation["publication_allowed"] is False
    assert refused.calculation["empirically_qualified_as_forecast"] is False
    vintage = {
        month: _observation(month, 250.0, provenance=SeriesProvenance.PROVIDER_VINTAGE)
        for month in months
    }
    assert method.run(_context(vintage), config).sufficiency == "insufficient"
    wrong_unit = {month: _observation(month, 250.0, unit="index") for month in months}
    assert method.run(_context(wrong_unit), config).sufficiency == "insufficient"


def _context(
    series: dict[date, EconomicObservation],
    *,
    evaluation: date | None = None,
    analysis_mode: AnalysisMode = AnalysisMode.LATEST_REVISED,
) -> MethodContext:
    return MethodContext(
        inputs_by_dataset={CPI_DATASET_ID: series},
        evaluation_period=evaluation or (max(series) if series else date(2000, 1, 1)),
        analysis_mode=analysis_mode,
        primary_dataset_id=CPI_DATASET_ID,
    )


def _observation(
    period: date,
    value: float,
    *,
    provenance: SeriesProvenance = SeriesProvenance.LATEST_REVISED,
    unit: str = CPI_UNIT,
) -> EconomicObservation:
    retrieved = datetime(2026, 8, 1, tzinfo=UTC)
    precision = (
        AvailabilityPrecision.UNKNOWN
        if provenance == SeriesProvenance.LATEST_REVISED
        else AvailabilityPrecision.DATE
    )
    return EconomicObservation(
        observation_id=f"cpi-{period.isoformat()}-{provenance.value}",
        dataset_id=CPI_DATASET_ID,
        provider_id="test",
        source_id="test",
        rights_record_id="test",
        period_start=period,
        frequency=Frequency.MONTHLY,
        geography="US",
        unit=unit,
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


def next_month(month_start: date) -> date:
    if month_start.month == 12:
        return date(month_start.year + 1, 1, 1)
    return date(month_start.year, month_start.month + 1, 1)
