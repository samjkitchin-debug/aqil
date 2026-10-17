"""Economic observation v1 — original provider values, not derived features."""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Frequency(StrEnum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"


class SeasonalAdjustment(StrEnum):
    SEASONALLY_ADJUSTED = "seasonally_adjusted"
    NOT_SEASONALLY_ADJUSTED = "not_seasonally_adjusted"
    UNKNOWN = "unknown"


class QualityStatus(StrEnum):
    OBSERVED = "observed"
    MISSING = "missing"
    CONTESTED = "contested"
    RETRACTED = "retracted"


class SeriesProvenance(StrEnum):
    """How this row may be used in historical analysis."""

    PROVIDER_VINTAGE = "provider_vintage"
    LATEST_REVISED = "latest_revised"
    AQIL_ARCHIVED = "aqil_archived"


class AvailabilityPrecision(StrEnum):
    TIMESTAMP = "timestamp"
    DATE = "date"
    UNKNOWN = "unknown"


class AnalysisMode(StrEnum):
    POINT_IN_TIME = "point_in_time"
    LATEST_REVISED = "latest_revised"


def model_available_at(
    observation: EconomicObservation,
) -> datetime | None:
    """Earliest UTC instant the observation may enter a point-in-time view."""
    if observation.series_provenance == SeriesProvenance.LATEST_REVISED:
        return None
    if observation.earliest_model_available_at is not None:
        return observation.earliest_model_available_at
    if observation.availability_precision == AvailabilityPrecision.DATE:
        return datetime.combine(
            observation.provider_vintage_date + timedelta(days=1),
            time.min,
            tzinfo=UTC,
        )
    return None


class EconomicObservation(BaseModel):
    """One provider vintage of one economic period. Retrieval time is not publication time."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = Field(default="1.0")
    observation_id: str = Field(min_length=1)
    dataset_id: str = Field(min_length=1)
    provider_id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    rights_record_id: str = Field(min_length=1)
    period_start: date
    period_end: date | None = None
    frequency: Frequency
    geography: str = Field(min_length=1)
    unit: str = Field(min_length=1)
    seasonal_adjustment: SeasonalAdjustment
    raw_value: str
    quality_status: QualityStatus
    series_provenance: SeriesProvenance
    provider_vintage_date: date
    source_release_at: datetime | None = None
    earliest_model_available_at: datetime | None = None
    availability_precision: AvailabilityPrecision
    retrieved_at: datetime
    first_seen_at: datetime
    source_locator: str | None = None
    adapter_version: str = Field(min_length=1)
    supersedes_observation_id: str | None = None

    @field_validator("schema_version")
    @classmethod
    def schema_is_v1(cls, value: str) -> str:
        if value != "1.0":
            raise ValueError("observation schema_version must be 1.0")
        return value

    @field_validator(
        "retrieved_at", "first_seen_at", "source_release_at", "earliest_model_available_at"
    )
    @classmethod
    def utc_aware(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("timestamps must be timezone-aware (UTC)")
        return value.astimezone(UTC)

    @field_validator("raw_value")
    @classmethod
    def finite_decimal_string(cls, value: str) -> str:
        try:
            parsed = Decimal(value)
        except InvalidOperation as exc:
            raise ValueError("raw_value must be a finite decimal string") from exc
        if not parsed.is_finite():
            raise ValueError("raw_value must be finite")
        return value

    @model_validator(mode="after")
    def period_and_provenance_rules(self) -> Self:
        if self.period_end is not None and self.period_end < self.period_start:
            raise ValueError("period_end cannot precede period_start")
        if self.first_seen_at > self.retrieved_at:
            raise ValueError("first_seen_at cannot be after retrieved_at")
        if self.source_release_at is not None and self.source_release_at > self.retrieved_at:
            raise ValueError("source_release_at cannot be after retrieved_at")
        if (
            self.earliest_model_available_at is not None
            and self.source_release_at is not None
            and self.earliest_model_available_at < self.source_release_at
        ):
            raise ValueError(
                "earliest_model_available_at cannot precede source_release_at",
            )

        if self.series_provenance == SeriesProvenance.LATEST_REVISED:
            if self.earliest_model_available_at is not None:
                raise ValueError("latest_revised rows must not claim a model availability time")
            if self.availability_precision != AvailabilityPrecision.UNKNOWN:
                raise ValueError("latest_revised rows must use availability_precision unknown")
        elif self.series_provenance == SeriesProvenance.PROVIDER_VINTAGE:
            if self.availability_precision == AvailabilityPrecision.UNKNOWN:
                raise ValueError(
                    "provider_vintage requires date or timestamp availability precision"
                )
            if self.earliest_model_available_at is None and (
                self.availability_precision != AvailabilityPrecision.DATE
            ):
                raise ValueError(
                    "provider_vintage requires earliest_model_available_at or date precision"
                )
        elif self.series_provenance == SeriesProvenance.AQIL_ARCHIVED:
            if self.earliest_model_available_at is None:
                raise ValueError("aqil_archived rows require earliest_model_available_at")

        return self

    def decimal_value(self) -> Decimal:
        return Decimal(self.raw_value)

    def vintage_identity(self) -> tuple[str, date, date, str]:
        """Stable key for one release of one period (disambiguates same calendar dates)."""
        if self.source_release_at is not None:
            release_key = self.source_release_at.isoformat()
        else:
            release_key = self.retrieved_at.isoformat()
        return (self.dataset_id, self.period_start, self.provider_vintage_date, release_key)
