"""Numerical checks for intercept-only Bai–Perron mean shifts."""

from __future__ import annotations

import json
import math
from datetime import UTC, date, datetime
from decimal import Decimal
from itertools import combinations
from pathlib import Path

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
from aqil_research.methods.bai_perron_mean_shifts import (
    BIC_FORMULA,
    DATE_STATUS,
    SEGMENT_FLOOR,
    BaiPerronMeanShiftsConfig,
    BaiPerronMeanShiftsMethod,
    minimum_segment_length,
    schwarz_bic,
    select_mean_shifts,
)
from aqil_research.methods.bry_boschan_monthly import G17_DATASET_ID
from aqil_research.methods.protocol import MethodContext
from aqil_research.methods.registry import MethodRegistry, default_method_registry

METHOD_PATH = (
    Path(__file__).parents[1] / "src" / "aqil_research" / "methods" / "bai_perron_mean_shifts.py"
)


def test_module_does_not_call_a_change_point_library() -> None:
    source = METHOD_PATH.read_text(encoding="utf-8")
    assert "ruptures" not in source
    assert BIC_FORMULA in source


def test_schwarz_bic_matches_the_mean_shift_penalty() -> None:
    residual = 50.0
    breaks = 1
    sample_size = 100
    expected = math.log(residual / sample_size)
    expected += (2 * breaks + 1) * math.log(sample_size) / sample_size
    assert schwarz_bic(residual, breaks, sample_size) == pytest.approx(expected)
    assert schwarz_bic(0.0, 0, sample_size) == -math.inf


def test_minimum_segment_length_uses_the_frozen_trim() -> None:
    assert minimum_segment_length(100) == SEGMENT_FLOOR
    assert minimum_segment_length(160) == 24
    assert minimum_segment_length(200) == 30
    assert minimum_segment_length(1292) == 193


def test_dynamic_programme_matches_enumeration() -> None:
    values = np.array(
        [
            0.2,
            -0.4,
            0.1,
            0.0,
            -0.2,
            0.3,
            0.15,
            -0.05,
            1.4,
            1.1,
            1.6,
            0.9,
            1.3,
            1.2,
            1.5,
            1.0,
            -0.8,
            -1.1,
            -0.6,
            -0.9,
            -1.0,
            -0.7,
            -1.2,
            -0.5,
            0.4,
            0.2,
            0.6,
            0.1,
            0.5,
            0.3,
        ],
        dtype=np.float64,
    )
    length = 6
    selection = select_mean_shifts(values, minimum_segment_length=length, max_breaks=2)
    by_count = {item.break_count: item for item in selection.candidates}
    assert set(by_count) == {0, 1, 2}
    assert by_count[0].sum_of_squared_residuals == pytest.approx(_full_ssr(values))
    for break_count in (1, 2):
        starts, residual = _enumerate(values, length, break_count)
        fitted = by_count[break_count]
        assert fitted.regime_start_indices == starts
        assert fitted.sum_of_squared_residuals == pytest.approx(residual)
        assert fitted.parameter_count == 2 * break_count + 1


def test_seeded_gaussian_single_break_is_recovered() -> None:
    sample_size = 240
    break_at = 120
    length = minimum_segment_length(sample_size)
    sharp = np.random.default_rng(20261030).normal(0.0, 1.0, size=sample_size)
    sharp[break_at:] += 8.0
    sharp_fit = select_mean_shifts(sharp, minimum_segment_length=length, max_breaks=5)
    assert sharp_fit.selected.break_count == 1
    assert sharp_fit.selected.regime_start_indices == (0, break_at)

    noisy = np.random.default_rng(20261030).normal(0.0, 1.0, size=sample_size)
    noisy[break_at:] += 4.0
    noisy_fit = select_mean_shifts(noisy, minimum_segment_length=length, max_breaks=5)
    assert noisy_fit.selected.break_count == 1
    dated = noisy_fit.selected.regime_start_indices[1]
    assert abs(dated - break_at) == 1


def test_no_break_series_selects_zero_more_often_than_not() -> None:
    """Twenty of 21 seeded draws select no break. One selects one break.

    The penalty is the published formula. It is not retuned to remove that draw.
    """

    sample_size = 240
    replications = 21
    length = minimum_segment_length(sample_size)
    generator = np.random.default_rng(20261030)
    counts: dict[int, int] = {}
    for _ in range(replications):
        values = generator.normal(0.0, 1.0, size=sample_size)
        selected = select_mean_shifts(
            values,
            minimum_segment_length=length,
            max_breaks=5,
        ).selected.break_count
        counts[selected] = counts.get(selected, 0) + 1
    assert counts == {0: 20, 1: 1}
    assert counts[0] > replications / 2


def test_break_count_is_capped_at_five() -> None:
    generator = np.random.default_rng(7)
    sample_size = 200
    values = generator.normal(size=sample_size)
    for start in range(0, sample_size, 20):
        values[start : start + 20] += start / 10
    selection = select_mean_shifts(values, minimum_segment_length=24, max_breaks=5)
    assert selection.feasible_break_count_before_cap > 5
    assert {item.break_count for item in selection.candidates} == {0, 1, 2, 3, 4, 5}
    assert selection.selected.break_count <= 5


def test_constant_series_keeps_the_smaller_break_count() -> None:
    selection = select_mean_shifts(np.zeros(80), minimum_segment_length=24, max_breaks=2)
    assert selection.selected.break_count == 0
    assert all(
        math.isinf(item.schwarz_bic) and item.schwarz_bic < 0 for item in selection.candidates
    )


def test_method_payload_is_retrospective_and_unpublished() -> None:
    periods = [_add_months(date(2000, 1, 1), offset) for offset in range(80)]
    levels = [Decimal("100") * (Decimal("1.002") ** offset) for offset in range(80)]
    series = {
        period: _observation(period, level) for period, level in zip(periods, levels, strict=True)
    }
    result = BaiPerronMeanShiftsMethod().run(
        MethodContext(
            inputs_by_dataset={G17_DATASET_ID: series},
            evaluation_period=periods[-1],
            analysis_mode=AnalysisMode.LATEST_REVISED,
            primary_dataset_id=G17_DATASET_ID,
        ),
        BaiPerronMeanShiftsConfig.model_validate(
            {
                "config_id": "bai_perron_mean_shifts_v1",
                "label": (
                    "Intercept-only mean shifts in monthly log-growth of industrial production"
                ),
            },
        ),
    )
    assert result.sufficiency == "sufficient"
    assert result.calculation is not None
    assert result.calculation["date_status"] == DATE_STATUS
    assert result.calculation["publication_allowed"] is False
    assert result.calculation["forecast"] is False
    assert result.calculation["advance_prediction"] is False
    assert result.calculation["general_bai_perron_regressor_model_implemented"] is False
    assert result.calculation["bic_formula"] == BIC_FORMULA
    assert result.calculation["break_count"] == 0
    assert result.calculation["confidence_intervals_reported"] is False
    assert result.investment_implication == "no_action"
    json.dumps(result.calculation)
    assert "not a forecast" in result.narrative


def test_point_in_time_and_non_positive_levels_are_insufficient() -> None:
    period = date(2000, 1, 1)
    series = {period: _observation(period, Decimal("100"))}
    method = BaiPerronMeanShiftsMethod()
    config = BaiPerronMeanShiftsConfig(config_id="bai_perron_mean_shifts_v1", label="Mean shifts")
    point_in_time = method.run(
        MethodContext(
            inputs_by_dataset={G17_DATASET_ID: series},
            evaluation_period=period,
            analysis_mode=AnalysisMode.POINT_IN_TIME,
            primary_dataset_id=G17_DATASET_ID,
        ),
        config,
    )
    assert point_in_time.sufficiency == "insufficient"
    levels = {
        _add_months(date(2000, 1, 1), offset): _observation(
            _add_months(date(2000, 1, 1), offset),
            Decimal("0") if offset == 3 else Decimal("100"),
        )
        for offset in range(6)
    }
    non_positive = method.run(
        MethodContext(
            inputs_by_dataset={G17_DATASET_ID: levels},
            evaluation_period=max(levels),
            analysis_mode=AnalysisMode.LATEST_REVISED,
            primary_dataset_id=G17_DATASET_ID,
        ),
        config,
    )
    assert non_positive.sufficiency == "insufficient"
    assert non_positive.calculation is not None
    assert non_positive.calculation["publication_allowed"] is False


def test_local_registry_call_resolves_the_method() -> None:
    registry = MethodRegistry()
    registry.register(BaiPerronMeanShiftsMethod())
    assert registry.get("BAI_PERRON_MEAN_SHIFTS").method_version == "1.0.0"
    assert default_method_registry().get("BAI_PERRON_MEAN_SHIFTS").method_version == "1.0.0"


def _enumerate(values: np.ndarray, length: int, break_count: int) -> tuple[tuple[int, ...], float]:
    sample_size = int(values.shape[0])
    best_starts: tuple[int, ...] | None = None
    best_residual = math.inf
    for cuts in combinations(range(length, sample_size - length + 1), break_count):
        starts = (0, *cuts)
        bounds = (*starts, sample_size)
        gaps = (bounds[index + 1] - bounds[index] for index in range(len(bounds) - 1))
        if any(gap < length for gap in gaps):
            continue
        residual = _partition_ssr(values, (*starts, sample_size))
        if residual < best_residual:
            best_residual = residual
            best_starts = starts
    if best_starts is None:
        raise AssertionError("enumeration found no admissible partition")
    return best_starts, best_residual


def _partition_ssr(values: np.ndarray, bounds: tuple[int, ...]) -> float:
    residual = 0.0
    for index in range(len(bounds) - 1):
        segment = values[bounds[index] : bounds[index + 1]]
        residual += float(np.sum((segment - segment.mean()) ** 2))
    return residual


def _full_ssr(values: np.ndarray) -> float:
    return float(np.sum((values - values.mean()) ** 2))


def _add_months(month_start: date, months: int) -> date:
    index = month_start.year * 12 + (month_start.month - 1) + months
    year, month_index = divmod(index, 12)
    return date(year, month_index + 1, 1)


def _observation(period: date, value: Decimal) -> EconomicObservation:
    retrieved = datetime(2026, 10, 25, 8, 0, tzinfo=UTC)
    return EconomicObservation(
        observation_id=f"g17-{period.isoformat()}",
        dataset_id=G17_DATASET_ID,
        provider_id="federal_reserve_board",
        source_id="federal_reserve_g17_total_ip",
        rights_record_id="federal_reserve_g17_total_ip",
        period_start=period,
        frequency=Frequency.MONTHLY,
        geography="US",
        unit="index_2017_100",
        seasonal_adjustment=SeasonalAdjustment.SEASONALLY_ADJUSTED,
        raw_value=format(value, "f"),
        quality_status=QualityStatus.OBSERVED,
        series_provenance=SeriesProvenance.LATEST_REVISED,
        provider_vintage_date=date(2026, 10, 17),
        availability_precision=AvailabilityPrecision.UNKNOWN,
        retrieved_at=retrieved,
        first_seen_at=retrieved,
        adapter_version="bai_perron_mean_shift_test_v1",
    )
