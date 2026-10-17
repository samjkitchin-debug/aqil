"""Map EconomicObservation rows to and from PostgreSQL."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from aqil_research.contracts.observation import (
    AvailabilityPrecision,
    EconomicObservation,
    Frequency,
    QualityStatus,
    SeasonalAdjustment,
    SeriesProvenance,
)


def release_identity_key(
    source_release_at: datetime | None,
    retrieved_at: datetime,
) -> str:
    if source_release_at is not None:
        return source_release_at.isoformat()
    return retrieved_at.isoformat()


def observation_to_insert_params(
    observation: EconomicObservation,
    retrieval_id: UUID,
) -> dict[str, Any]:
    return {
        "p_observation_id": observation.observation_id,
        "p_retrieval_id": retrieval_id,
        "p_dataset_id": observation.dataset_id,
        "p_provider_id": observation.provider_id,
        "p_source_id": observation.source_id,
        "p_rights_record_id": observation.rights_record_id,
        "p_period_start": observation.period_start,
        "p_period_end": observation.period_end,
        "p_frequency": observation.frequency.value,
        "p_geography": observation.geography,
        "p_unit": observation.unit,
        "p_seasonal_adjustment": observation.seasonal_adjustment.value,
        "p_raw_value": observation.raw_value,
        "p_quality_status": observation.quality_status.value,
        "p_series_provenance": observation.series_provenance.value,
        "p_provider_vintage_date": observation.provider_vintage_date,
        "p_source_release_at": observation.source_release_at,
        "p_earliest_model_available_at": observation.earliest_model_available_at,
        "p_availability_precision": observation.availability_precision.value,
        "p_retrieved_at": observation.retrieved_at,
        "p_first_seen_at": observation.first_seen_at,
        "p_source_locator": observation.source_locator,
        "p_adapter_version": observation.adapter_version,
        "p_supersedes_observation_id": observation.supersedes_observation_id,
    }


def row_to_observation(row: tuple[Any, ...], columns: list[str]) -> EconomicObservation:
    data = dict(zip(columns, row, strict=True))
    return EconomicObservation(
        observation_id=data["observation_id"],
        dataset_id=data["dataset_id"],
        provider_id=data["provider_id"],
        source_id=data["source_id"],
        rights_record_id=data["rights_record_id"],
        period_start=data["period_start"],
        period_end=data["period_end"],
        frequency=Frequency(data["frequency"]),
        geography=data["geography"],
        unit=data["unit"],
        seasonal_adjustment=SeasonalAdjustment(data["seasonal_adjustment"]),
        raw_value=data["raw_value"],
        quality_status=QualityStatus(data["quality_status"]),
        series_provenance=SeriesProvenance(data["series_provenance"]),
        provider_vintage_date=data["provider_vintage_date"],
        source_release_at=_ensure_utc(data.get("source_release_at")),
        earliest_model_available_at=_ensure_utc(data.get("earliest_model_available_at")),
        availability_precision=AvailabilityPrecision(data["availability_precision"]),
        retrieved_at=_ensure_utc(data["retrieved_at"]),
        first_seen_at=_ensure_utc(data["first_seen_at"]),
        source_locator=data.get("source_locator"),
        adapter_version=data["adapter_version"],
        supersedes_observation_id=data.get("supersedes_observation_id"),
    )


def _ensure_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
