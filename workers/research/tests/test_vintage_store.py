from datetime import UTC, datetime

import pytest

from aqil_research.contracts.observation import (
    AnalysisMode,
    AvailabilityPrecision,
    SeriesProvenance,
)
from aqil_research.vintages.store import InMemoryObservationStore, VintageConflictError
from fixtures.observation_factory import (
    DATASET_ID,
    constant_unemployment_series,
    make_observation,
    month_start,
)


def test_idempotent_append_and_conflict_detection() -> None:
    store = InMemoryObservationStore()
    row = make_observation(
        period_start=month_start(2024, 1),
        raw_value="3.7",
        provider_vintage_date=datetime(2024, 2, 1).date(),
    )
    first = store.append(row)
    second = store.append(row)
    assert first.inserted == 1
    assert second.unchanged == 1

    revised = make_observation(
        period_start=month_start(2024, 1),
        raw_value="3.8",
        provider_vintage_date=datetime(2024, 2, 1).date(),
        observation_id="different-id",
    )
    with pytest.raises(VintageConflictError):
        store.append(revised)


def test_empty_batch_does_not_delete() -> None:
    store = InMemoryObservationStore()
    row = make_observation(
        period_start=month_start(2024, 1),
        raw_value="3.7",
        provider_vintage_date=datetime(2024, 2, 1).date(),
    )
    store.append(row)
    store.append_many(())
    assert len(store.all_observations()) == 1


def test_point_in_time_excludes_future_vintage_and_latest_revised() -> None:
    store = InMemoryObservationStore()
    pit_row = make_observation(
        period_start=month_start(2024, 1),
        raw_value="3.7",
        provider_vintage_date=datetime(2024, 3, 1).date(),
    )
    latest_only = make_observation(
        period_start=month_start(2024, 2),
        raw_value="3.9",
        provider_vintage_date=datetime(2024, 12, 1).date(),
        series_provenance=SeriesProvenance.LATEST_REVISED,
        availability_precision=AvailabilityPrecision.UNKNOWN,
    )
    store.append_many((pit_row, latest_only))

    early = datetime(2024, 3, 1, 23, 59, tzinfo=UTC)
    view = store.as_of(DATASET_ID, early, AnalysisMode.POINT_IN_TIME)
    assert month_start(2024, 1) not in view
    assert month_start(2024, 2) not in view

    after = datetime(2024, 3, 2, 0, 0, tzinfo=UTC)
    view = store.as_of(DATASET_ID, after, AnalysisMode.POINT_IN_TIME)
    assert view[month_start(2024, 1)].raw_value == "3.7"
    assert month_start(2024, 2) not in view

    latest_view = store.as_of(DATASET_ID, after, AnalysisMode.LATEST_REVISED)
    assert latest_view[month_start(2024, 2)].raw_value == "3.9"


def test_revision_does_not_change_earlier_as_of_analysis() -> None:
    store = InMemoryObservationStore()
    jan_v1 = make_observation(
        period_start=month_start(2024, 1),
        raw_value="3.7",
        provider_vintage_date=datetime(2024, 2, 1).date(),
    )
    jan_v2 = make_observation(
        period_start=month_start(2024, 1),
        raw_value="3.8",
        provider_vintage_date=datetime(2024, 3, 1).date(),
    )
    store.append_many((jan_v1, jan_v2))

    before_revision = datetime(2024, 3, 1, 12, 0, tzinfo=UTC)
    early_view = store.as_of(DATASET_ID, before_revision, AnalysisMode.POINT_IN_TIME)
    after_revision = datetime(2024, 3, 2, 12, 0, tzinfo=UTC)
    late_view = store.as_of(DATASET_ID, after_revision, AnalysisMode.POINT_IN_TIME)

    assert early_view[month_start(2024, 1)].raw_value == "3.7"
    assert late_view[month_start(2024, 1)].raw_value == "3.8"


def test_snapshot_hash_is_order_independent() -> None:
    rows_a = constant_unemployment_series(month_start(2023, 10), 3, "4.0")
    rows_b = tuple(reversed(rows_a))
    store_a = InMemoryObservationStore()
    store_b = InMemoryObservationStore()
    store_a.append_many(rows_a)
    store_b.append_many(rows_b)
    from aqil_research.vintages.store import content_snapshot_hash

    assert content_snapshot_hash(store_a.all_observations()) == content_snapshot_hash(
        store_b.all_observations(),
    )
