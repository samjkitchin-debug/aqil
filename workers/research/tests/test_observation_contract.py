from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from aqil_research.contracts.observation import (
    AvailabilityPrecision,
    SeriesProvenance,
    model_available_at,
)
from fixtures.observation_factory import make_observation, month_start


def test_date_only_availability_starts_day_after_vintage() -> None:
    row = make_observation(
        period_start=month_start(2024, 5),
        raw_value="3.7",
        provider_vintage_date=date(2024, 6, 15),
        availability_precision=AvailabilityPrecision.DATE,
    )
    available = model_available_at(row)
    assert available == datetime(2024, 6, 16, 0, 0, 0, tzinfo=UTC)


def test_latest_revised_has_no_model_availability() -> None:
    row = make_observation(
        period_start=month_start(2024, 1),
        raw_value="3.7",
        provider_vintage_date=date(2024, 2, 1),
        series_provenance=SeriesProvenance.LATEST_REVISED,
        availability_precision=AvailabilityPrecision.UNKNOWN,
    )
    assert model_available_at(row) is None


def test_rejects_non_finite_raw_value() -> None:
    with pytest.raises(ValueError, match="finite"):
        make_observation(
            period_start=month_start(2024, 1),
            raw_value="NaN",
            provider_vintage_date=date(2024, 2, 1),
        )


def test_decimal_value_parses() -> None:
    row = make_observation(
        period_start=month_start(2024, 1),
        raw_value="4.125",
        provider_vintage_date=date(2024, 2, 1),
    )
    assert row.decimal_value() == Decimal("4.125")
