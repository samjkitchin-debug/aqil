"""Synthetic observation builders for offline regression tests."""

from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import uuid4

from aqil_research.contracts.observation import (
    AvailabilityPrecision,
    EconomicObservation,
    Frequency,
    QualityStatus,
    SeasonalAdjustment,
    SeriesProvenance,
)

DATASET_ID = "bls.ln.LNS14000000"
SOURCE_ID = "bls_cps_unemployment_rate"
RIGHTS_RECORD_ID = "bls_cps_unemployment_rate"
PROVIDER_ID = "bls"
ADAPTER_VERSION = "synthetic_fixture_v1"


def utc_dt(year: int, month: int, day: int, hour: int = 12) -> datetime:
    return datetime(year, month, day, hour, 0, 0, tzinfo=UTC)


def month_start(year: int, month: int) -> date:
    return date(year, month, 1)


def make_observation(
    *,
    period_start: date,
    raw_value: str,
    provider_vintage_date: date,
    series_provenance: SeriesProvenance = SeriesProvenance.PROVIDER_VINTAGE,
    availability_precision: AvailabilityPrecision = AvailabilityPrecision.DATE,
    earliest_model_available_at: datetime | None = None,
    source_release_at: datetime | None = None,
    quality_status: QualityStatus = QualityStatus.OBSERVED,
    observation_id: str | None = None,
) -> EconomicObservation:
    retrieved = utc_dt(
        provider_vintage_date.year,
        provider_vintage_date.month,
        min(provider_vintage_date.day + 1, 28),
    )
    return EconomicObservation(
        observation_id=observation_id or str(uuid4()),
        dataset_id=DATASET_ID,
        provider_id=PROVIDER_ID,
        source_id=SOURCE_ID,
        rights_record_id=RIGHTS_RECORD_ID,
        period_start=period_start,
        frequency=Frequency.MONTHLY,
        geography="US",
        unit="percent",
        seasonal_adjustment=SeasonalAdjustment.SEASONALLY_ADJUSTED,
        raw_value=raw_value,
        quality_status=quality_status,
        series_provenance=series_provenance,
        provider_vintage_date=provider_vintage_date,
        availability_precision=availability_precision,
        earliest_model_available_at=earliest_model_available_at,
        source_release_at=source_release_at,
        retrieved_at=retrieved,
        first_seen_at=retrieved,
        adapter_version=ADAPTER_VERSION,
    )


def _add_months(anchor: date, delta: int) -> date:
    year = anchor.year + (anchor.month - 1 + delta) // 12
    month = (anchor.month - 1 + delta) % 12 + 1
    return date(year, month, 1)


def constant_unemployment_series(
    start: date,
    months: int,
    value: str,
) -> tuple[EconomicObservation, ...]:
    rows: list[EconomicObservation] = []
    cursor = start
    for _ in range(months):
        vintage = _add_months(cursor, 1)
        rows.append(
            make_observation(
                period_start=cursor,
                raw_value=value,
                provider_vintage_date=date(vintage.year, vintage.month, 5),
            ),
        )
        cursor = _add_months(cursor, 1)
    return tuple(rows)
