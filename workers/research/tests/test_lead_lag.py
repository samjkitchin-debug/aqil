"""Lead-lag cross-correlations on monthly log-growth. Fixture series only."""

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
from aqil_research.methods.lead_lag import (
    BARTLETT_TRUNCATION,
    CRITICAL_VALUE,
    DATASET_IDS,
    EARLY_SUBSAMPLE,
    ILLUSTRATED_BREAK,
    LATE_SUBSAMPLE,
    LEAD_LAG_CROSS_CORRELATION,
    MIN_SUBSAMPLE_GROWTH_MONTHS,
    NOT_A_STRUCTURAL_LEAD,
    PUBLICATION_ALLOWED,
    PUBLISHED_CONFIG,
    SIGN_CONVENTION,
    TRANSFORMATION,
    UNITS,
    LeadLagCrossCorrelationMethod,
    balanced_monthly_log_growth,
    bartlett_long_run_variance,
    bartlett_standard_error,
    cross_correlations,
    distinguishable_from_zero,
    lead_lag_from_growth,
    windows_avoid_illustrated_break,
)
from aqil_research.methods.protocol import MethodContext
from aqil_research.methods.registry import default_method_registry
from aqil_research.workflow.lead_lag_reading import _LiveObservationStore


def test_predeclared_windows_avoid_the_illustrated_break() -> None:
    assert LEAD_LAG_CROSS_CORRELATION == "LEAD_LAG_CROSS_CORRELATION"
    assert PUBLICATION_ALLOWED is False
    assert TRANSFORMATION == "monthly_log_growth"
    assert BARTLETT_TRUNCATION == 24
    assert CRITICAL_VALUE == 1.96
    assert MIN_SUBSAMPLE_GROWTH_MONTHS == 60
    assert windows_avoid_illustrated_break() is True
    assert EARLY_SUBSAMPLE.end < ILLUSTRATED_BREAK.start
    assert LATE_SUBSAMPLE.start > ILLUSTRATED_BREAK.end
    assert EARLY_SUBSAMPLE.end < LATE_SUBSAMPLE.start
    assert SIGN_CONVENTION == "Positive lag means the second series lags the first."


def test_positive_lag_means_the_second_series_lags_the_first() -> None:
    generator = np.random.default_rng(7)
    first = generator.normal(size=80)
    second = np.concatenate([np.zeros(3), first[:-3]])
    rows = {row.lag: row for row in cross_correlations(first, second)}
    assert rows[3].correlation == pytest.approx(1.0)
    assert rows[3].distinguishable_from_zero is True
    assert abs(rows[0].correlation) < 0.99
    assert rows[-3].correlation != pytest.approx(1.0)


def test_bartlett_errors_use_both_autocorrelations_and_not_an_iid_error() -> None:
    long_run = bartlett_long_run_variance((1.0, 0.5), (1.0, 0.5))
    assert long_run == pytest.approx(1.5)
    overlap = 100
    standard_error = math.sqrt(1.5 / overlap)
    iid_error = math.sqrt(1 / overlap)
    assert standard_error > iid_error
    correlation = 0.2
    assert abs(correlation) > CRITICAL_VALUE * iid_error
    assert distinguishable_from_zero(correlation, standard_error) is False
    assert bartlett_long_run_variance((1.0, -0.8), (1.0, 0.9)) is None
    assert distinguishable_from_zero(0.99, None) is False


def test_bartlett_standard_error_widens_for_persistent_series() -> None:
    generator = np.random.default_rng(4)
    size = 400
    first = np.zeros(size)
    second = np.zeros(size)
    first_shocks = generator.normal(size=size)
    second_shocks = generator.normal(size=size)
    for index in range(1, size):
        first[index] = 0.9 * first[index - 1] + first_shocks[index]
        second[index] = 0.9 * second[index - 1] + second_shocks[index]
    standard_error = bartlett_standard_error(first, second, size)
    iid_error = math.sqrt(1 / size)
    assert standard_error is not None
    assert standard_error > iid_error * 2


def test_a_short_or_gappy_sample_is_not_forced() -> None:
    months = _months(date(1997, 1, 1), 24)
    growth = {
        dataset_id: tuple(float(index) for index in range(len(months)))
        for dataset_id in DATASET_IDS
    }
    short = lead_lag_from_growth(months, growth)
    assert short["sufficient"] is False
    assert short["iid_standard_errors_used"] is False
    gappy = list(months) + _months(date(2000, 1, 1), 80)
    refused = lead_lag_from_growth(
        gappy,
        {dataset_id: tuple(range(len(gappy))) for dataset_id in DATASET_IDS},
    )
    assert refused["sufficient"] is False
    levels = {
        dataset_id: {
            month: 100.0 + index for index, month in enumerate(_months(date(2000, 1, 1), 12))
        }
        for dataset_id in DATASET_IDS
    }
    hole = _months(date(2000, 1, 1), 12)[6]
    del levels[DATASET_IDS[0]][hole]
    balanced_months, _aligned, excluded = balanced_monthly_log_growth(levels)
    assert hole not in balanced_months
    assert _months(date(2000, 1, 1), 12)[7] not in balanced_months
    assert excluded > 0
    assert all(
        right == _next(left)
        for left, right in zip(balanced_months, balanced_months[1:], strict=False)
    )


def test_subsamples_skip_when_short_and_a_repeated_lag_can_agree() -> None:
    months = _months(date(1997, 1, 1), 276)
    generator = np.random.default_rng(5)
    production = generator.normal(size=len(months))
    income = np.concatenate([np.zeros(3), production[:-3]])
    sales = generator.normal(size=len(months))
    payroll = generator.normal(size=len(months))
    growth = {
        DATASET_IDS[0]: production,
        DATASET_IDS[1]: income,
        DATASET_IDS[2]: sales,
        DATASET_IDS[3]: payroll,
    }
    result = lead_lag_from_growth(months, growth)
    assert result["publication_allowed"] is False
    assert result["three_month_growth_used"] is False
    assert result["iid_standard_errors_used"] is False
    assert result["fixed_leading_indicator_assigned"] is False
    assert result["subsamples_overlap_illustrated_break"] is False
    pair = next(
        row
        for row in result["pairs"]
        if row["first_dataset_id"] == DATASET_IDS[0] and row["second_dataset_id"] == DATASET_IDS[1]
    )
    assert pair["strongest_absolute_correlation"]["lag"] == 3
    assert pair["strongest_absolute_correlation"]["distinguishable_from_zero"] is True
    assert pair["same_peak_lag_in_both_subsamples"] is True
    statuses = {row["window"]: row["status"] for row in pair["subsamples"]}
    assert statuses[EARLY_SUBSAMPLE.name] == "computed"
    assert statuses[LATE_SUBSAMPLE.name] == "computed"
    peaks = [
        peak
        for peak in result["distinguishable_peaks"]
        if peak["first_dataset_id"] == DATASET_IDS[0]
        and peak["second_dataset_id"] == DATASET_IDS[1]
    ]
    assert any(
        peak["lag"] == 3 and peak["correlation"] == pytest.approx(1.0, abs=1e-6) for peak in peaks
    )
    late_only = _months(date(2018, 1, 1), 70)
    skipped = lead_lag_from_growth(
        late_only,
        {dataset_id: generator.normal(size=len(late_only)) for dataset_id in DATASET_IDS},
    )
    early = skipped["pairs"][0]["subsamples"][0]
    assert early["status"] == "skipped"
    assert "below the predeclared minimum" in early["reason"]


def test_method_wording_does_not_assign_a_lead() -> None:
    method = LeadLagCrossCorrelationMethod()
    config = method.parse_config(dict(PUBLISHED_CONFIG))
    assert method.method_id == LEAD_LAG_CROSS_CORRELATION
    assert (
        default_method_registry().get(LEAD_LAG_CROSS_CORRELATION).method_id
        == LEAD_LAG_CROSS_CORRELATION
    )
    assert method.required_dataset_ids() == DATASET_IDS
    assert method.config_hash(config)
    months = _months(date(1997, 1, 1), 90)
    generator = np.random.default_rng(6)
    inputs = {}
    for dataset_id in DATASET_IDS:
        shocks = generator.normal(0.0, 0.01, size=len(months) - 1)
        log_levels = np.concatenate([[math.log(100.0)], math.log(100.0) + np.cumsum(shocks)])
        inputs[dataset_id] = {
            month: _observation(dataset_id, month, math.exp(log_levels[index]))
            for index, month in enumerate(months)
        }
    result = method.run(_context(inputs), config)
    assert result.sufficiency == "sufficient"
    assert result.calculation is not None
    assert result.calculation["publication_allowed"] is False
    assert result.calculation["transformation"] == "monthly_log_growth"
    assert result.calculation["iid_standard_errors_used"] is False
    assert result.causal_hypothesis == "none"
    assert result.investment_implication == "no_action"
    text = " ".join(
        [
            result.narrative,
            result.statistical_interpretation,
            result.causal_hypothesis,
            *result.assumptions,
            *result.limitations,
        ],
    ).lower()
    assert "causal" not in text
    assert "granger" not in text
    assert "leads the" not in text
    assert "is a leading indicator" not in text
    assert NOT_A_STRUCTURAL_LEAD in result.narrative
    assert SIGN_CONVENTION in result.statistical_interpretation
    encoded = json.dumps(result.calculation)
    assert "NaN" not in encoded
    refused = method.run(
        _context(inputs, analysis_mode=AnalysisMode.POINT_IN_TIME),
        config,
    )
    assert refused.sufficiency == "insufficient"
    assert refused.calculation["publication_allowed"] is False


def test_a_fixture_row_does_not_hide_the_live_month(monkeypatch: pytest.MonkeyPatch) -> None:
    period = date(2020, 1, 1)
    dataset_id = DATASET_IDS[0]
    live = _observation(dataset_id, period, 100.0, observation_id="live-month")
    fixture = _observation(dataset_id, period, 999.0, observation_id="fixture-month")
    fixture = fixture.model_copy(update={"retrieved_at": datetime(2026, 9, 1, tzinfo=UTC)})

    def load(_conn: object, requested: str) -> tuple[EconomicObservation, ...]:
        if requested == dataset_id:
            return (live, fixture)
        return ()

    monkeypatch.setattr(
        "aqil_research.workflow.lead_lag_reading.load_observations_for_dataset",
        load,
    )
    store = _LiveObservationStore(None, frozenset({"fixture-month"}))  # type: ignore[arg-type]
    selected = store.as_of(
        dataset_id,
        datetime(2026, 10, 1, tzinfo=UTC),
        AnalysisMode.LATEST_REVISED,
    )
    assert selected[period].observation_id == "live-month"


def _context(
    inputs: dict[str, dict[date, EconomicObservation]],
    *,
    analysis_mode: AnalysisMode = AnalysisMode.LATEST_REVISED,
) -> MethodContext:
    return MethodContext(
        inputs_by_dataset=inputs,
        evaluation_period=max(inputs[DATASET_IDS[0]]),
        analysis_mode=analysis_mode,
        primary_dataset_id=DATASET_IDS[0],
    )


def _observation(
    dataset_id: str,
    period: date,
    value: float,
    *,
    observation_id: str | None = None,
) -> EconomicObservation:
    retrieved = datetime(2026, 8, 1, tzinfo=UTC)
    return EconomicObservation(
        observation_id=observation_id or f"{dataset_id}-{period.isoformat()}",
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


def _next(month_start: date) -> date:
    if month_start.month == 12:
        return date(month_start.year + 1, 1, 1)
    return date(month_start.year, month_start.month + 1, 1)
