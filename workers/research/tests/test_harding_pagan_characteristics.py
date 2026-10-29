"""Harding–Pagan phase, amplitude, and concordance from Spencer-15 dates."""

from __future__ import annotations

import math
from datetime import UTC, date, datetime
from decimal import Decimal

from aqil_research.contracts.observation import (
    AnalysisMode,
    AvailabilityPrecision,
    EconomicObservation,
    Frequency,
    QualityStatus,
    SeasonalAdjustment,
    SeriesProvenance,
)
from aqil_research.methods.bry_boschan_monthly import G17_DATASET_ID
from aqil_research.methods.bry_boschan_spencer15 import date_spencer15_variant
from aqil_research.methods.harding_pagan_characteristics import (
    COINCIDENT_LEVEL_SERIES,
    HARDING_PAGAN_CHARACTERISTICS,
    HARDING_PAGAN_CHARACTERISTICS_PUBLISHED,
    PHASE_RULE,
    HardingPaganCharacteristicsMethod,
    LevelInputPoint,
    assess_coincident_level_input,
    build_characteristics,
    concordance_index,
    expansion_contraction_states,
    phase_rows,
)
from aqil_research.methods.protocol import MethodContext

RETRIEVED = datetime(2026, 10, 25, 8, 0, tzinfo=UTC)
PAYROLL = "bls.ce.CES0000000001"
INCOME = "bea.nipa.T20600.W875RX"
SALES = "bea.nipa.U002BU.KPMT"


def _month(index: int) -> date:
    return date(2000 + (index // 12), (index % 12) + 1, 1)


def _observation(
    dataset_id: str,
    period: date,
    value: str,
    *,
    unit: str,
) -> EconomicObservation:
    return EconomicObservation(
        observation_id=f"{dataset_id}-{period.isoformat()}",
        dataset_id=dataset_id,
        provider_id="test",
        source_id="test_source",
        rights_record_id="test_source",
        period_start=period,
        frequency=Frequency.MONTHLY,
        geography="US",
        unit=unit,
        seasonal_adjustment=SeasonalAdjustment.SEASONALLY_ADJUSTED,
        raw_value=value,
        quality_status=QualityStatus.OBSERVED,
        series_provenance=SeriesProvenance.LATEST_REVISED,
        provider_vintage_date=date(2026, 10, 17),
        availability_precision=AvailabilityPrecision.UNKNOWN,
        retrieved_at=RETRIEVED,
        first_seen_at=RETRIEVED,
        adapter_version="harding_pagan_characteristics_test_v1",
    )


def _points(
    dataset_id: str,
    periods: tuple[date, ...],
    *,
    unit: str,
    value: str = "100",
    mode: str = "live",
) -> tuple[LevelInputPoint, ...]:
    return tuple(
        LevelInputPoint(
            observation=_observation(dataset_id, period, value, unit=unit),
            collection_mode=mode,
        )
        for period in periods
    )


def test_phase_rule_dates_expansion_after_a_trough_through_the_peak() -> None:
    trough = date(2000, 1, 1)
    peak = date(2000, 4, 1)
    states = expansion_contraction_states((peak,), (trough,))
    assert states is not None
    assert date(2000, 1, 1) not in states
    assert states[date(2000, 2, 1)] == "expansion"
    assert states[date(2000, 3, 1)] == "expansion"
    assert states[date(2000, 4, 1)] == "expansion"
    assert "After a trough" in PHASE_RULE
    assert "up to the next peak" in PHASE_RULE


def test_duration_is_months_and_amplitude_is_the_percent_change() -> None:
    trough = date(2000, 1, 1)
    peak = date(2000, 4, 1)
    later_trough = date(2000, 7, 1)
    levels = (
        (trough, Decimal(100)),
        (peak, Decimal(110)),
        (later_trough, Decimal(99)),
    )
    rows = phase_rows(levels, (peak,), (trough, later_trough))
    assert rows is not None
    assert rows[0]["phase"] == "expansion"
    assert rows[0]["duration_months"] == 3
    assert rows[0]["amplitude_percent"] == "10.0000"
    assert rows[1]["phase"] == "contraction"
    assert rows[1]["duration_months"] == 3
    assert rows[1]["amplitude_percent"] == "-10.0000"


def test_concordance_is_the_share_of_months_in_the_same_phase() -> None:
    expansion = {
        date(2000, 2, 1): "expansion",
        date(2000, 3, 1): "expansion",
        date(2000, 4, 1): "expansion",
    }
    mixed = {
        date(2000, 2, 1): "expansion",
        date(2000, 3, 1): "expansion",
        date(2000, 4, 1): "contraction",
    }
    opposite = {month: "contraction" for month in expansion}
    same = concordance_index(expansion, expansion)
    partial = concordance_index(expansion, mixed)
    none = concordance_index(expansion, opposite)
    assert same["same_phase_months"] == 3
    assert same["compared_months"] == 3
    assert same["concordance"] == "1.000000"
    assert partial["same_phase_months"] == 2
    assert partial["compared_months"] == 3
    assert partial["concordance"] == "0.666667"
    assert none["concordance"] == "0.000000"


def test_non_alternating_turns_are_not_forced_into_a_phase() -> None:
    peaks = (date(2000, 3, 1), date(2000, 5, 1))
    assert expansion_contraction_states(peaks, ()) is None
    assert phase_rows(((date(2000, 3, 1), Decimal(1)),), peaks, ()) is None


def test_a_gap_fixture_or_growth_rate_is_not_dated() -> None:
    payroll_gap = assess_coincident_level_input(
        PAYROLL,
        _points(PAYROLL, (date(2000, 1, 1), date(2000, 3, 1)), unit="thousands"),
    )
    assert payroll_gap.eligible is False
    assert any("2000-02-01" in reason for reason in payroll_gap.reasons)

    fixture = assess_coincident_level_input(
        INCOME,
        _points(
            INCOME,
            (date(2000, 1, 1),),
            unit="millions_chained_2017_dollars",
            mode="fixture",
        ),
    )
    assert fixture.eligible is False
    assert any("fixture" in reason for reason in fixture.reasons)

    growth = assess_coincident_level_input(
        SALES,
        _points(SALES, (date(2000, 1, 1),), unit="millions_chained_2017_dollars"),
        representation="twelve_month_percent_change",
    )
    assert growth.eligible is False
    assert any("non-level" in reason for reason in growth.reasons)

    wrong_unit = assess_coincident_level_input(
        PAYROLL,
        _points(PAYROLL, (date(2000, 1, 1),), unit="percent_change"),
    )
    assert wrong_unit.eligible is False
    assert any("level unit" in reason for reason in wrong_unit.reasons)

    g17_fixture = assess_coincident_level_input(
        G17_DATASET_ID,
        _points(G17_DATASET_ID, (date(2000, 1, 1),), unit="index_2017_100", mode="fixture"),
    )
    assert g17_fixture.eligible is False
    assert any("fixture" in reason for reason in g17_fixture.reasons)


def _sine(months: int = 240) -> tuple[tuple[date, Decimal], ...]:
    levels: list[tuple[date, Decimal]] = []
    for index in range(months):
        raw = 100 + 40 * math.sin(2 * math.pi * index / 48)
        levels.append((_month(index), Decimal(str(raw))))
    return tuple(levels)


def test_method_dates_eligible_levels_and_records_an_ineligible_series() -> None:
    levels = _sine()
    expected = date_spencer15_variant(levels)
    units = {spec.dataset_id: spec.level_unit for spec in COINCIDENT_LEVEL_SERIES}
    points = {
        dataset_id: tuple(
            LevelInputPoint(
                observation=_observation(
                    dataset_id,
                    period,
                    format(value, "f"),
                    unit=units[dataset_id],
                ),
                collection_mode="live",
            )
            for period, value in levels
        )
        for dataset_id in (G17_DATASET_ID, INCOME, PAYROLL)
    }
    sales_periods = tuple(period for period, _value in levels if period != date(2000, 6, 1))
    points[SALES] = _points(
        SALES,
        sales_periods,
        unit=units[SALES],
    )
    calculation = build_characteristics(points)
    assert calculation["publication_allowed"] is False
    assert calculation["chronology_class"] == "retrospective_full_sample"
    assert calculation["input_revision"] == "latest_revised"
    assert calculation["quarterly_bbq_implemented"] is False
    assert calculation["bbq_run_on_monthly_g17"] is False
    assert calculation["nber_recession_chronology"] is False
    series = {row["dataset_id"]: row for row in calculation["series"]}
    assert series[G17_DATASET_ID]["eligible"] is True
    assert series[G17_DATASET_ID]["peaks"] == [item.isoformat() for item in expected.peaks]
    assert series[G17_DATASET_ID]["troughs"] == [item.isoformat() for item in expected.troughs]
    assert series[INCOME]["nber_recession_chronology"] is False
    assert series[PAYROLL]["nber_recession_chronology"] is False
    assert series[SALES]["eligible"] is False
    assert series[SALES]["dated"] is False
    assert series[SALES]["peaks"] == []
    assert "not NBER recession dates" in str(series[PAYROLL]["description"])
    sales_pairs = [
        pair
        for pair in calculation["concordance"]
        if pair["left_dataset_id"] == SALES or pair["right_dataset_id"] == SALES
    ]
    assert sales_pairs
    assert all(pair["computed"] is False for pair in sales_pairs)
    income_payroll = next(
        pair
        for pair in calculation["concordance"]
        if {pair["left_dataset_id"], pair["right_dataset_id"]} == {INCOME, PAYROLL}
    )
    assert income_payroll["computed"] is True
    assert income_payroll["concordance"] == "1.000000"

    context = MethodContext(
        inputs_by_dataset={
            dataset_id: {point.observation.period_start: point.observation for point in rows}
            for dataset_id, rows in points.items()
        },
        evaluation_period=levels[-1][0],
        analysis_mode=AnalysisMode.LATEST_REVISED,
        primary_dataset_id=G17_DATASET_ID,
    )
    method = HardingPaganCharacteristicsMethod()
    assert method.method_id == HARDING_PAGAN_CHARACTERISTICS
    result = method.run(
        context,
        method.parse_config(dict(HARDING_PAGAN_CHARACTERISTICS_PUBLISHED)),
    )
    assert result.sufficiency == "sufficient"
    assert result.calculation is not None
    assert result.calculation["publication_allowed"] is False
    assert "NBER recession" in result.narrative
    assert "BBQ" not in result.narrative
    assert "contemporaneous recession call" in result.narrative


def test_a_point_in_time_request_is_not_dated() -> None:
    method = HardingPaganCharacteristicsMethod()
    context = MethodContext(
        inputs_by_dataset={},
        evaluation_period=date(2000, 1, 1),
        analysis_mode=AnalysisMode.POINT_IN_TIME,
        primary_dataset_id=G17_DATASET_ID,
    )
    result = method.run(
        context,
        method.parse_config(dict(HARDING_PAGAN_CHARACTERISTICS_PUBLISHED)),
    )
    assert result.sufficiency == "insufficient"
    assert result.calculation is not None
    assert result.calculation["publication_allowed"] is False
    assert result.calculation["quarterly_bbq_implemented"] is False
