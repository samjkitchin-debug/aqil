"""Synthetic proof that a historical decision date excludes a later vintage.

The values below are fixture inputs. They are not stored observations and they
are not a published rate.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from aqil_research.contracts.observation import (
    AnalysisMode,
    AvailabilityPrecision,
    QualityStatus,
    SeriesProvenance,
)
from aqil_research.vintages.asof import AsOfSelectionError, select_as_of_series
from fixtures.observation_factory import DATASET_ID, make_observation, month_start, utc_dt

PERIOD = month_start(2024, 1)


def _pair():
    early = make_observation(
        period_start=PERIOD,
        raw_value="1.0",
        provider_vintage_date=month_start(2024, 2).replace(day=5),
        earliest_model_available_at=utc_dt(2024, 2, 6),
        observation_id="early-vintage",
    )
    late = make_observation(
        period_start=PERIOD,
        raw_value="2.0",
        provider_vintage_date=month_start(2024, 3).replace(day=5),
        earliest_model_available_at=utc_dt(2024, 3, 6),
        observation_id="later-vintage",
    )
    return early, late


def test_point_in_time_excludes_a_vintage_not_yet_available() -> None:
    early, late = _pair()
    selected = select_as_of_series(
        (early, late),
        DATASET_ID,
        utc_dt(2024, 2, 20),
        AnalysisMode.POINT_IN_TIME,
    )
    assert list(selected) == [PERIOD]
    assert selected[PERIOD].observation_id == "early-vintage"
    assert selected[PERIOD].raw_value == "1.0"


def test_a_later_decision_date_includes_the_revision() -> None:
    early, late = _pair()
    selected = select_as_of_series(
        (early, late),
        DATASET_ID,
        utc_dt(2024, 3, 6),
        AnalysisMode.POINT_IN_TIME,
    )
    assert selected[PERIOD].observation_id == "later-vintage"
    assert selected[PERIOD].raw_value == "2.0"


def test_availability_at_the_decision_instant_is_included() -> None:
    _early, late = _pair()
    selected = select_as_of_series(
        (late,),
        DATASET_ID,
        utc_dt(2024, 3, 6),
        AnalysisMode.POINT_IN_TIME,
    )
    assert selected[PERIOD].observation_id == "later-vintage"


def test_one_hour_before_availability_excludes_the_revision() -> None:
    _early, late = _pair()
    selected = select_as_of_series(
        (late,),
        DATASET_ID,
        datetime(2024, 3, 6, 11, 0, tzinfo=late.earliest_model_available_at.tzinfo),
        AnalysisMode.POINT_IN_TIME,
    )
    assert selected == {}


def test_latest_revised_rows_are_excluded_from_point_in_time() -> None:
    row = make_observation(
        period_start=PERIOD,
        raw_value="9.0",
        provider_vintage_date=month_start(2024, 2).replace(day=5),
        series_provenance=SeriesProvenance.LATEST_REVISED,
        availability_precision=AvailabilityPrecision.UNKNOWN,
        observation_id="latest-only",
    )
    selected = select_as_of_series(
        (row,),
        DATASET_ID,
        utc_dt(2026, 1, 1),
        AnalysisMode.POINT_IN_TIME,
    )
    assert selected == {}


def test_latest_revised_mode_keeps_the_newer_vintage_and_drops_a_retraction() -> None:
    older = make_observation(
        period_start=PERIOD,
        raw_value="1.0",
        provider_vintage_date=month_start(2024, 2).replace(day=5),
        series_provenance=SeriesProvenance.LATEST_REVISED,
        availability_precision=AvailabilityPrecision.UNKNOWN,
        observation_id="older-revised",
    )
    newer = make_observation(
        period_start=PERIOD,
        raw_value="2.0",
        provider_vintage_date=month_start(2024, 3).replace(day=5),
        series_provenance=SeriesProvenance.LATEST_REVISED,
        availability_precision=AvailabilityPrecision.UNKNOWN,
        observation_id="newer-revised",
    )
    retracted = make_observation(
        period_start=PERIOD,
        raw_value="8.0",
        provider_vintage_date=month_start(2024, 4).replace(day=5),
        series_provenance=SeriesProvenance.LATEST_REVISED,
        availability_precision=AvailabilityPrecision.UNKNOWN,
        quality_status=QualityStatus.RETRACTED,
        observation_id="retracted-revised",
    )
    selected = select_as_of_series(
        (older, newer, retracted),
        DATASET_ID,
        utc_dt(2024, 5, 1),
        AnalysisMode.LATEST_REVISED,
    )
    assert selected[PERIOD].observation_id == "newer-revised"


def test_another_dataset_and_a_naive_decision_time_are_refused() -> None:
    early, _late = _pair()
    other = early.model_copy(update={"dataset_id": "other.dataset", "observation_id": "other"})
    selected = select_as_of_series(
        (other,),
        DATASET_ID,
        utc_dt(2024, 3, 1),
        AnalysisMode.POINT_IN_TIME,
    )
    assert selected == {}
    with pytest.raises(AsOfSelectionError, match="timezone-aware"):
        select_as_of_series((), DATASET_ID, datetime(2024, 1, 1), AnalysisMode.POINT_IN_TIME)
