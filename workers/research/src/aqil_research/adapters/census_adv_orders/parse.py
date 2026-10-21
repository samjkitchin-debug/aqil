"""Parse Census M3 advance durable goods new orders (MDM / NO)."""

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

DATASET_ID = "census.m3.adv.MDM.NO"
SOURCE_ID = "census_adv_durable_goods"
RIGHTS_RECORD_ID = "census_adv_durable_goods"
PROVIDER_ID = "census_bureau"
CATEGORY_CODE = "MDM"
DATA_TYPE_CODE = "NO"

MONTH_PERIOD = re.compile(r"^(\d{4})-(\d{2})$")
NA_TOKENS = frozenset({"n.a.", "na", "n/a", "(x)", "-", ""})


@dataclass(frozen=True, slots=True)
class CensusAdvParseResult:
    observations: tuple[EconomicObservation, ...]
    warnings: tuple[str, ...]


def parse_census_adv_payload(
    payload: list[list[str]] | dict[str, object],
    *,
    adapter_version: str,
    retrieved_at: datetime,
    collection_vintage_date: date,
    vintage_date: date | None = None,
    earliest_model_available_at: datetime | None = None,
) -> CensusAdvParseResult:
    """Parse Census timeseries JSON (header row + data rows) into observations."""
    rows = _normalise_rows(payload)
    if len(rows) < 2:
        raise ValueError("Census payload must include a header row and data")

    header = [cell.strip().lower() for cell in rows[0]]
    try:
        value_idx = header.index("cell_value")
        time_idx = header.index("time")
    except ValueError as exc:
        raise ValueError("Census payload missing cell_value or time column") from exc

    category_idx = header.index("category_code") if "category_code" in header else None
    datatype_idx = header.index("data_type_code") if "data_type_code" in header else None

    warnings: list[str] = []
    observations: list[EconomicObservation] = []
    provider_vintage = vintage_date or collection_vintage_date

    for line_no, row in enumerate(rows[1:], start=2):
        if len(row) <= max(value_idx, time_idx):
            warnings.append(f"row {line_no}: truncated")
            continue
        if category_idx is not None and row[category_idx].strip() != CATEGORY_CODE:
            continue
        if datatype_idx is not None and row[datatype_idx].strip() != DATA_TYPE_CODE:
            continue
        period_start = _month_start(row[time_idx].strip())
        if period_start is None:
            warnings.append(f"row {line_no}: bad time {row[time_idx]}")
            continue
        value_raw = row[value_idx].strip()
        if value_raw.lower() in NA_TOKENS:
            warnings.append(f"{row[time_idx]}: n.a. treated as missing")
            continue
        try:
            Decimal(value_raw)
        except InvalidOperation:
            warnings.append(f"row {line_no}: non-numeric {value_raw}")
            continue

        obs_id = _observation_id(period_start, provider_vintage)
        provenance = (
            SeriesProvenance.PROVIDER_VINTAGE
            if vintage_date is not None
            else SeriesProvenance.LATEST_REVISED
        )
        observations.append(
            EconomicObservation(
                observation_id=obs_id,
                dataset_id=DATASET_ID,
                provider_id=PROVIDER_ID,
                source_id=SOURCE_ID,
                rights_record_id=RIGHTS_RECORD_ID,
                period_start=period_start,
                frequency=Frequency.MONTHLY,
                geography="US",
                unit="millions_usd_seasonally_adjusted",
                seasonal_adjustment=SeasonalAdjustment.SEASONALLY_ADJUSTED,
                raw_value=value_raw,
                quality_status=QualityStatus.OBSERVED,
                series_provenance=provenance,
                provider_vintage_date=provider_vintage,
                earliest_model_available_at=earliest_model_available_at,
                availability_precision=(
                    AvailabilityPrecision.TIMESTAMP
                    if earliest_model_available_at
                    else AvailabilityPrecision.DATE
                ),
                retrieved_at=retrieved_at,
                first_seen_at=retrieved_at,
                adapter_version=adapter_version,
            ),
        )

    if not observations:
        raise ValueError("no Census MDM NO observations parsed")
    return CensusAdvParseResult(observations=tuple(observations), warnings=tuple(warnings))


def _normalise_rows(payload: list[list[str]] | dict[str, object]) -> list[list[str]]:
    if isinstance(payload, list):
        return [[str(cell) for cell in row] for row in payload]
    if isinstance(payload, dict):
        bundled = payload.get("data")
        if isinstance(bundled, list):
            return [[str(cell) for cell in row] for row in bundled]
    raise ValueError("Census payload must be a list of rows or {data: [...]}")


def _month_start(period: str) -> date | None:
    match = MONTH_PERIOD.match(period)
    if not match:
        return None
    year = int(match.group(1))
    month = int(match.group(2))
    if month < 1 or month > 12:
        return None
    return date(year, month, 1)


def _observation_id(period_start: date, vintage: date) -> str:
    key = f"MDM:NO:{period_start.isoformat()}:{vintage.isoformat()}"
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]
    return f"census-mdm-no-{period_start.strftime('%Y%m')}-{digest}"
