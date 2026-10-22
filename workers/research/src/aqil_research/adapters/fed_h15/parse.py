"""Parse one bound H.15 series into EconomicObservation schema 1.0."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date, datetime

from aqil_research.adapters.fed_h15.series import PROVIDER_ID, UNIT, H15Series
from aqil_research.contracts.observation import (
    AvailabilityPrecision,
    EconomicObservation,
    Frequency,
    QualityStatus,
    SeasonalAdjustment,
    SeriesProvenance,
)


@dataclass(frozen=True, slots=True)
class H15ParseResult:
    observations: tuple[EconomicObservation, ...]


def parse_h15_payload(
    payload: dict[str, object],
    *,
    series: H15Series,
    adapter_version: str,
    retrieved_at: datetime,
    collection_vintage_date: date,
) -> H15ParseResult:
    """Map latest-revised monthly rows. This file is not a vintage panel."""
    series_name = str(payload.get("series_name", ""))
    if series_name != series.series_name:
        raise ValueError(f"unexpected series id {series_name}")
    rows = payload.get("observations")
    if not isinstance(rows, list) or not rows:
        raise ValueError("observations list missing from H.15 payload")

    observations: list[EconomicObservation] = []
    for index, item in enumerate(rows, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"observation {index} is not an object")
        observations.append(
            _row_to_observation(
                item,
                series=series,
                adapter_version=adapter_version,
                retrieved_at=retrieved_at,
                collection_vintage_date=collection_vintage_date,
            ),
        )
    return H15ParseResult(observations=tuple(observations))


def h15_observation_id(
    series: H15Series,
    period_start: date,
    vintage: date,
    disambiguator: str = "",
) -> str:
    """Stable id for one period and collection date. A disambiguator separates a change."""
    key = f"{series.series_name}:{period_start.isoformat()}:{vintage.isoformat()}"
    if disambiguator:
        key = f"{key}:{disambiguator}"
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]
    return f"h15-{series.id_token}-{period_start.strftime('%Y%m')}-{digest}"


def _row_to_observation(
    item: dict[str, object],
    *,
    series: H15Series,
    adapter_version: str,
    retrieved_at: datetime,
    collection_vintage_date: date,
) -> EconomicObservation:
    period_start = date.fromisoformat(str(item.get("period", "")))
    period_end_raw = item.get("period_end")
    period_end = date.fromisoformat(str(period_end_raw)) if period_end_raw else None
    vintage_raw = item.get("vintage")
    provider_vintage = (
        date.fromisoformat(str(vintage_raw)) if vintage_raw else collection_vintage_date
    )
    source_release = _optional_datetime(item.get("source_release_at")) or retrieved_at
    default_id = h15_observation_id(series, period_start, provider_vintage)
    observation_id = str(item.get("observation_id") or default_id)
    locator = item.get("source_locator")
    return EconomicObservation(
        observation_id=observation_id,
        dataset_id=series.dataset_id,
        provider_id=PROVIDER_ID,
        source_id=series.source_id,
        rights_record_id=series.source_id,
        period_start=period_start,
        period_end=period_end,
        frequency=Frequency.MONTHLY,
        geography="US",
        unit=UNIT,
        seasonal_adjustment=SeasonalAdjustment.UNKNOWN,
        raw_value=str(item.get("value", "")).strip(),
        quality_status=QualityStatus.OBSERVED,
        series_provenance=SeriesProvenance.LATEST_REVISED,
        provider_vintage_date=provider_vintage,
        earliest_model_available_at=None,
        availability_precision=AvailabilityPrecision.UNKNOWN,
        retrieved_at=retrieved_at,
        first_seen_at=retrieved_at,
        source_release_at=source_release,
        source_locator=str(locator) if locator else None,
        adapter_version=adapter_version,
    )


def _optional_datetime(value: object) -> datetime | None:
    if value is None or value == "":
        return None
    parsed = datetime.fromisoformat(str(value))
    if parsed.tzinfo is None:
        raise ValueError("source_release_at must be timezone-aware")
    return parsed
