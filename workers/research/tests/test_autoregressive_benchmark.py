"""Autoregressive benchmark on monthly log-growth. Fixture series only."""

from __future__ import annotations

import json
import math
from datetime import UTC, date, datetime

import numpy as np
import pytest

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
    ADF_MAX_LAG,
    AUTOREGRESSIVE_BENCHMARK,
    HORIZONS,
    INDUSTRIAL_PRODUCTION_DATASET_ID,
    LEVEL_UNIT,
    LJUNG_BOX_LAG,
    MAX_LAG,
    MIN_ESTIMATION_MONTHS,
    MINIMUM_GROWTH_MONTHS,
    NOT_A_PRODUCT_FORECAST,
    NOT_QUALIFIED,
    PUBLICATION_ALLOWED,
    PUBLISHED_CONFIG,
    AutoregressiveBenchmarkMethod,
    beat_historical_mean,
    benchmark_from_growth,
    contiguous_monthly_log_growth,
    select_ar_lag,
)
from aqil_research.methods.protocol import MethodContext
from aqil_research.methods.registry import default_method_registry
from aqil_research.workflow.autoregressive_benchmark_reading import (
    _LiveObservationStore,
)


def test_predeclared_design_stays_unpublished() -> None:
    assert AUTOREGRESSIVE_BENCHMARK == "AUTOREGRESSIVE_BENCHMARK"
    assert PUBLICATION_ALLOWED is False
    assert MAX_LAG == 12
    assert MIN_ESTIMATION_MONTHS == 120
    assert HORIZONS == (1, 12)
    assert LJUNG_BOX_LAG == 24
    assert ADF_MAX_LAG == 12
    assert MINIMUM_GROWTH_MONTHS == 132


def test_log_growth_is_the_first_difference_and_does_not_bridge_a_gap() -> None:
    months = _months(date(2000, 1, 1), 10)
    levels = {month: float(100 + index) for index, month in enumerate(months)}
    del levels[months[5]]
    sample = contiguous_monthly_log_growth(levels)
    assert sample.growth_months == tuple(months[1:5])
    assert months[5] not in sample.growth_months
    assert months[7] not in sample.growth_months
    expected = tuple(
        math.log(levels[month]) - math.log(levels[_previous(month)])
        for month in sample.growth_months
    )
    assert sample.values == pytest.approx(expected)
    assert len(sample.values) == len(sample.growth_months)


def test_scores_use_the_window_mean_and_ignore_later_observations() -> None:
    growth = np.concatenate([np.full(120, 0.01), np.full(40, 0.05)])
    altered = growth.copy()
    altered[120:] = 5.0
    original = benchmark_from_growth(growth, include_origins=True)
    changed = benchmark_from_growth(altered, include_origins=True)
    assert original["second_difference_applied"] is False
    assert original["full_sample_standardisation"] is False
    assert original["publication_allowed"] is False
    assert original["product_forecast"] is False
    assert "origins" not in benchmark_from_growth(growth)
    first = original["origins"][0]
    assert first["estimation_length"] == MIN_ESTIMATION_MONTHS
    assert first["historical_mean"] == pytest.approx(0.01)
    assert first["historical_mean"] != pytest.approx(float(growth.mean()))
    changed_first = changed["origins"][0]["forecasts"]
    for horizon in ("1", "12"):
        assert (
            changed_first[horizon]["autoregressive"]
            == (first["forecasts"][horizon]["autoregressive"])
        )
        assert (
            changed_first[horizon]["historical_mean"]
            == (first["forecasts"][horizon]["historical_mean"])
        )
        assert changed_first[horizon]["actual"] != first["forecasts"][horizon]["actual"]
    for origin in original["origins"]:
        length = int(origin["estimation_length"])
        assert length >= MIN_ESTIMATION_MONTHS
        assert origin["historical_mean"] == pytest.approx(float(growth[:length].mean()))
        assert 1 <= int(origin["selected_lag"]) <= MAX_LAG
        for horizon, forecast in origin["forecasts"].items():
            assert length + int(horizon) <= len(growth)
            assert forecast["historical_mean"] == pytest.approx(float(growth[:length].mean()))


def test_a_tie_does_not_beat_the_historical_mean() -> None:
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


def test_aic_selects_inside_the_maximum_lag() -> None:
    generator = np.random.default_rng(0)
    shocks = generator.normal(0.0, 0.01, size=800)
    growth = np.zeros(800)
    for index in range(2, 800):
        growth[index] = 0.4 * growth[index - 1] - 0.2 * growth[index - 2] + shocks[index]
    lag, _coefficients, _aic = select_ar_lag(growth)
    assert lag == 2
    assert lag <= MAX_LAG


def test_stationary_log_growth_is_not_differenced_again() -> None:
    generator = np.random.default_rng(1)
    growth = generator.normal(0.001, 0.01, size=240)
    result = benchmark_from_growth(growth)
    assert result["second_difference_applied"] is False
    assert result["modelled_transformation"] == "monthly_log_growth"
    stationarity = result["stationarity"]
    assert stationarity["computed"] is True
    assert stationarity["rejected_unit_root_at_five_percent"] is True
    assert stationarity["second_difference_applied"] is False
    assert result["in_sample"]["residual_diagnostic"]["lag"] == LJUNG_BOX_LAG
    assert result["in_sample"]["lag_is_not_reused_for_rolling_forecasts"] is True
    assert 1 <= result["in_sample_aic_lag"] <= MAX_LAG
    horizons = {row["horizon_months"]: row for row in result["horizons"]}
    assert set(horizons) == {1, 12}
    assert horizons[1]["origin_count"] == 240 - 1 - MIN_ESTIMATION_MONTHS + 1
    qualified = result["empirically_qualified_as_forecast"]
    beats = [row["beat_historical_mean"] for row in result["horizons"]]
    assert qualified is all(beats)
    statement = result["qualification_statement"]
    assert NOT_A_PRODUCT_FORECAST in statement
    if qualified:
        assert NOT_QUALIFIED not in statement
    else:
        assert NOT_QUALIFIED in statement
    encoded = json.dumps(result)
    assert "NaN" not in encoded
    assert "Infinity" not in encoded


def test_a_persistent_series_beats_the_mean_at_one_month() -> None:
    generator = np.random.default_rng(2)
    shocks = generator.normal(0.0, 0.01, size=240)
    growth = np.zeros(240)
    for index in range(1, 240):
        growth[index] = 0.8 * growth[index - 1] + shocks[index]
    result = benchmark_from_growth(growth)
    horizons = {row["horizon_months"]: row for row in result["horizons"]}
    assert horizons[1]["beat_historical_mean"] is True
    assert result["empirically_qualified_as_forecast"] is all(
        row["beat_historical_mean"] for row in result["horizons"]
    )


def test_method_stays_on_latest_revised_levels_and_is_ready_to_register() -> None:
    method = AutoregressiveBenchmarkMethod()
    config = method.parse_config(dict(PUBLISHED_CONFIG))
    assert method.method_id == AUTOREGRESSIVE_BENCHMARK
    assert (
        default_method_registry().get(AUTOREGRESSIVE_BENCHMARK).method_id
        == AUTOREGRESSIVE_BENCHMARK
    )
    assert method.required_dataset_ids() == (INDUSTRIAL_PRODUCTION_DATASET_ID,)
    assert method.config_hash(config)
    months = _months(date(2000, 1, 1), 180)
    generator = np.random.default_rng(3)
    shocks = generator.normal(0.0, 0.01, size=len(months) - 1)
    log_levels = np.concatenate([[math.log(100.0)], math.log(100.0) + np.cumsum(shocks)])
    levels = np.exp(log_levels)
    series = {month: _observation(month, levels[index]) for index, month in enumerate(months)}
    result = method.run(_context(series), config)
    assert result.sufficiency == "sufficient"
    assert result.calculation is not None
    assert result.calculation["publication_allowed"] is False
    assert result.calculation["product_forecast"] is False
    assert result.calculation["second_difference_applied"] is False
    assert result.calculation["growth_month_count"] == len(months) - 1
    assert "origins" not in result.calculation
    assert result.investment_implication == "no_action"
    assert NOT_A_PRODUCT_FORECAST in result.narrative
    assert result.causal_hypothesis == "none"
    refused = method.run(
        _context(series, analysis_mode=AnalysisMode.POINT_IN_TIME),
        config,
    )
    assert refused.sufficiency == "insufficient"
    assert refused.calculation["publication_allowed"] is False
    vintage = {
        month: _observation(
            month,
            100.0,
            provenance=SeriesProvenance.PROVIDER_VINTAGE,
        )
        for month in months
    }
    assert method.run(_context(vintage), config).sufficiency == "insufficient"


def test_a_fixture_row_does_not_hide_the_live_month(monkeypatch: pytest.MonkeyPatch) -> None:
    period = date(2020, 1, 1)
    live = _observation(period, 100.0, observation_id="live-month")
    fixture = _observation(period, 999.0, observation_id="fixture-month")
    fixture = fixture.model_copy(
        update={"retrieved_at": datetime(2026, 9, 1, tzinfo=UTC)},
    )

    def load(_conn: object, dataset_id: str) -> tuple[EconomicObservation, ...]:
        assert dataset_id == INDUSTRIAL_PRODUCTION_DATASET_ID
        return (live, fixture)

    monkeypatch.setattr(
        "aqil_research.workflow.autoregressive_benchmark_reading.load_observations_for_dataset",
        load,
    )
    store = _LiveObservationStore(None, frozenset({"fixture-month"}))  # type: ignore[arg-type]
    selected = store.as_of(
        INDUSTRIAL_PRODUCTION_DATASET_ID,
        datetime(2026, 10, 1, tzinfo=UTC),
        AnalysisMode.LATEST_REVISED,
    )
    assert selected[period].observation_id == "live-month"


def _context(
    series: dict[date, EconomicObservation],
    *,
    analysis_mode: AnalysisMode = AnalysisMode.LATEST_REVISED,
) -> MethodContext:
    return MethodContext(
        inputs_by_dataset={INDUSTRIAL_PRODUCTION_DATASET_ID: series},
        evaluation_period=max(series),
        analysis_mode=analysis_mode,
        primary_dataset_id=INDUSTRIAL_PRODUCTION_DATASET_ID,
    )


def _observation(
    period: date,
    value: float,
    *,
    observation_id: str | None = None,
    provenance: SeriesProvenance = SeriesProvenance.LATEST_REVISED,
) -> EconomicObservation:
    retrieved = datetime(2026, 8, 1, tzinfo=UTC)
    precision = (
        AvailabilityPrecision.UNKNOWN
        if provenance == SeriesProvenance.LATEST_REVISED
        else AvailabilityPrecision.DATE
    )
    return EconomicObservation(
        observation_id=observation_id or f"ip-{period.isoformat()}-{provenance.value}",
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


def _previous(month_start: date) -> date:
    if month_start.month == 1:
        return date(month_start.year - 1, 12, 1)
    return date(month_start.year, month_start.month - 1, 1)
