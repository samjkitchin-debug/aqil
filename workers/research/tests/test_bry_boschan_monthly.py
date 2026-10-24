"""G.17 input contract and the blocked Bry–Boschan specification.

Expected turning-point dates are not produced. The dating function raises
because chapter 2 does not print the Spencer weights.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from aqil_research.contracts.observation import (
    AvailabilityPrecision,
    EconomicObservation,
    Frequency,
    QualityStatus,
    SeasonalAdjustment,
    SeriesProvenance,
)
from aqil_research.methods.bry_boschan_monthly import (
    BRY_BOSCHAN_MONTHLY_1971,
    DATING_BLOCKER,
    G17_DATASET_ID,
    BryBoschanSpecificationBlocked,
    G17InputPoint,
    assess_g17_level_input,
    date_specific_cycles,
    frozen_spec,
)

RETRIEVED = datetime(2026, 10, 25, 8, 0, tzinfo=UTC)


def _observation(
    period: date,
    value: str = "100.0",
    *,
    unit: str = "index_2017_100",
    seasonal: SeasonalAdjustment = SeasonalAdjustment.SEASONALLY_ADJUSTED,
    frequency: Frequency = Frequency.MONTHLY,
    provenance: SeriesProvenance = SeriesProvenance.LATEST_REVISED,
    dataset_id: str = G17_DATASET_ID,
) -> EconomicObservation:
    return EconomicObservation(
        observation_id=f"g17-{period.isoformat()}",
        dataset_id=dataset_id,
        provider_id="federal_reserve_board",
        source_id="federal_reserve_g17_total_ip",
        rights_record_id="federal_reserve_g17_total_ip",
        period_start=period,
        frequency=frequency,
        geography="US",
        unit=unit,
        seasonal_adjustment=seasonal,
        raw_value=value,
        quality_status=QualityStatus.OBSERVED,
        series_provenance=provenance,
        provider_vintage_date=date(2026, 10, 17),
        availability_precision=AvailabilityPrecision.UNKNOWN,
        retrieved_at=RETRIEVED,
        first_seen_at=RETRIEVED,
        adapter_version="bry_boschan_input_contract_v1",
    )


def _points(
    periods: tuple[date, ...],
    *,
    mode: str = "live",
    **kwargs: object,
) -> tuple[G17InputPoint, ...]:
    return tuple(
        G17InputPoint(
            observation=_observation(period, **kwargs),  # type: ignore[arg-type]
            collection_mode=mode,
        )
        for period in periods
    )


def test_frozen_spec_records_the_chapter_gap() -> None:
    spec = frozen_spec()
    assert spec.version == BRY_BOSCHAN_MONTHLY_1971
    assert spec.outlier_control_limit == Decimal("3.5")
    assert spec.twelve_month_neighbourhood_months == 5
    assert spec.minimum_cycle_months == 15
    assert spec.minimum_phase_months == 5
    assert spec.endpoint_ban_months == 6
    assert spec.spencer_weights is None
    assert spec.twelve_month_alignment is None
    assert spec.publication_allowed is False
    assert spec.quarterly_bbq_is_a_parameter is False


def test_dating_is_refused_without_invented_weights() -> None:
    levels = (
        (date(1919, 1, 1), Decimal("10")),
        (date(1919, 2, 1), Decimal("12")),
        (date(1919, 3, 1), Decimal("9")),
    )
    with pytest.raises(BryBoschanSpecificationBlocked, match="Spencer coefficients"):
        date_specific_cycles(levels)
    assert "not invented" in DATING_BLOCKER


def test_contiguous_live_level_index_is_eligible() -> None:
    periods = (date(1919, 1, 1), date(1919, 2, 1), date(1919, 3, 1))
    assessment = assess_g17_level_input(_points(periods))
    assert assessment.eligible is True
    assert assessment.reasons == ()
    assert assessment.sample_start == date(1919, 1, 1)
    assert assessment.sample_end == date(1919, 3, 1)
    assert assessment.month_count == 3


def test_a_gap_is_ineligible_and_not_filled() -> None:
    periods = (date(1919, 1, 1), date(1919, 3, 1))
    assessment = assess_g17_level_input(_points(periods))
    assert assessment.eligible is False
    assert any("1919-02-01" in reason for reason in assessment.reasons)


def test_a_fixture_retrieval_is_ineligible() -> None:
    assessment = assess_g17_level_input(
        _points((date(1919, 1, 1),), mode="fixture"),
    )
    assert assessment.eligible is False
    assert any("fixture" in reason for reason in assessment.reasons)


def test_a_growth_rate_representation_is_ineligible() -> None:
    assessment = assess_g17_level_input(
        _points((date(1919, 1, 1),)),
        representation="twelve_month_percent_change",
    )
    assert assessment.eligible is False
    assert any("non-level" in reason for reason in assessment.reasons)


def test_a_non_level_unit_is_ineligible() -> None:
    assessment = assess_g17_level_input(
        _points((date(1919, 1, 1),), unit="percent_change"),
    )
    assert assessment.eligible is False
    assert any("level index" in reason for reason in assessment.reasons)


def test_not_seasonally_adjusted_input_is_ineligible() -> None:
    assessment = assess_g17_level_input(
        _points(
            (date(1919, 1, 1),),
            seasonal=SeasonalAdjustment.NOT_SEASONALLY_ADJUSTED,
        ),
    )
    assert assessment.eligible is False
    assert any("does not seasonally adjust" in reason for reason in assessment.reasons)


def test_a_non_finite_raw_value_cannot_enter() -> None:
    with pytest.raises(ValidationError, match="finite"):
        _observation(date(1919, 1, 1), value="NaN")
