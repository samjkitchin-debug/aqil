"""Parse Federal Reserve SLOOS series SUBLPDCILS_N.Q into canonical observations."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from aqil_research.contracts.observation import (
    AvailabilityPrecision,
    EconomicObservation,
    Frequency,
    QualityStatus,
    SeasonalAdjustment,
    SeriesProvenance,
)

SERIES_ID = "SUBLPDCILS_N.Q"
DATASET_ID = "fed.sloos.SUBLPDCILS_N.Q"
SOURCE_ID = "federal_reserve_sloos_cil"
RIGHTS_RECORD_ID = "federal_reserve_sloos_cil"
PROVIDER_ID = "federal_reserve_board"

QUARTER_PERIOD = re.compile(r"^(\d{4})-Q([1-4])$")
NA_TOKENS = frozenset({"n.a.", "na", "n/a", "#", "."})


@dataclass(frozen=True, slots=True)
class FedSloosParseResult:
    observations: tuple[EconomicObservation, ...]
    warnings: tuple[str, ...]


def parse_sloos_payload(
    payload: dict[str, object],
    *,
    adapter_version: str,
    retrieved_at: datetime,
    collection_vintage_date: date,
) -> FedSloosParseResult:
    """Map a SLOOS bundle to observations (one row per period per provider vintage)."""
    series_id = str(payload.get("series_id", ""))
    if series_id and series_id != SERIES_ID:
        raise ValueError(f"unexpected series id {series_id}")
    rows = payload.get("observations")
    if not isinstance(rows, list) or not rows:
        raise ValueError("observations list missing from SLOOS payload")

    warnings: list[str] = []
    observations: list[EconomicObservation] = []
    for index, item in enumerate(rows, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"observation {index} is not an object")
        obs, warning = _row_to_observation(
            item,
            adapter_version=adapter_version,
            retrieved_at=retrieved_at,
            collection_vintage_date=collection_vintage_date,
        )
        if obs is None:
            if warning:
                warnings.append(warning)
            continue
        if warning:
            warnings.append(warning)
        observations.append(obs)
    if not observations:
        raise ValueError("no usable SLOOS observations after parsing")
    return FedSloosParseResult(observations=tuple(observations), warnings=tuple(warnings))


def _row_to_observation(
    item: dict[str, object],
    *,
    adapter_version: str,
    retrieved_at: datetime,
    collection_vintage_date: date,
) -> tuple[EconomicObservation | None, str | None]:
    period_raw = str(item.get("period", "")).strip()
    period_start = _quarter_start(period_raw)
    if period_start is None:
        return None, f"skipped unparseable period {period_raw}"

    value_raw = str(item.get("value", "")).strip()
    if value_raw.lower() in NA_TOKENS or value_raw == "":
        return None, f"{period_raw}: treated n.a. as missing (not zero)"

    try:
        Decimal(value_raw)
    except InvalidOperation:
        return None, f"{period_raw}: non-numeric value {value_raw}"

    vintage_raw = item.get("vintage")
    revision_basis = str(item.get("revision_basis", "")).strip()
    source_release = _optional_datetime(item.get("source_release_at"))
    if revision_basis == "latest_revised" or not vintage_raw:
        provider_vintage = (
            date.fromisoformat(str(vintage_raw)) if vintage_raw else collection_vintage_date
        )
        provenance = SeriesProvenance.LATEST_REVISED
        earliest = None
        availability = AvailabilityPrecision.UNKNOWN
    else:
        provider_vintage = date.fromisoformat(str(vintage_raw))
        provenance = SeriesProvenance.PROVIDER_VINTAGE
        model_available = item.get("earliest_model_available_at")
        earliest = (
            datetime.fromisoformat(str(model_available)) if model_available is not None else None
        )
        availability = AvailabilityPrecision.TIMESTAMP if earliest else AvailabilityPrecision.DATE

    default_id = _observation_id(period_start, provider_vintage)
    observation_id = str(item.get("observation_id") or default_id)
    source_locator = item.get("source_locator")
    locator = str(source_locator) if source_locator else None

    return (
        EconomicObservation(
            observation_id=observation_id,
            dataset_id=DATASET_ID,
            provider_id=PROVIDER_ID,
            source_id=SOURCE_ID,
            rights_record_id=RIGHTS_RECORD_ID,
            period_start=period_start,
            frequency=Frequency.QUARTERLY,
            geography="US",
            unit="percent_net_tightening",
            seasonal_adjustment=SeasonalAdjustment.NOT_SEASONALLY_ADJUSTED,
            raw_value=value_raw,
            quality_status=QualityStatus.OBSERVED,
            series_provenance=provenance,
            provider_vintage_date=provider_vintage,
            earliest_model_available_at=earliest,
            availability_precision=availability,
            retrieved_at=retrieved_at,
            first_seen_at=retrieved_at,
            source_release_at=source_release,
            source_locator=locator,
            adapter_version=adapter_version,
        ),
        None,
    )


def _optional_datetime(value: object) -> datetime | None:
    if value is None or value == "":
        return None
    parsed = datetime.fromisoformat(str(value))
    if parsed.tzinfo is None:
        raise ValueError("source_release_at must be timezone-aware")
    return parsed


def _quarter_start(period: str) -> date | None:
    match = QUARTER_PERIOD.match(period.upper().replace(" ", ""))
    if not match:
        return None
    year = int(match.group(1))
    quarter = int(match.group(2))
    month = (quarter - 1) * 3 + 1
    return date(year, month, 1)


def sloos_observation_id(
    period_start: date,
    vintage: date,
    disambiguator: str = "",
) -> str:
    """Stable id for one period and vintage. A disambiguator separates a same-day change."""
    key = f"{SERIES_ID}:{period_start.isoformat()}:{vintage.isoformat()}"
    if disambiguator:
        key = f"{key}:{disambiguator}"
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]
    return f"sloos-{period_start.strftime('%Y%m')}-{digest}"


def _observation_id(period_start: date, vintage: date) -> str:
    return sloos_observation_id(period_start, vintage)
