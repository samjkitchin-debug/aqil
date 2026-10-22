"""Parse Board H.8 series B1001NCBA into canonical observations.

The Board file is one current release. It is latest-revised, not a vintage
panel. None of Sahm, SLOOS, Census advance orders, MACRO_CONDITIONS_PANEL, or
PERIOD_LEVEL_CHANGE consumes fed.h8.B1001NCBA. Sahm and PERIOD_LEVEL_CHANGE
require bls.ln.LNS14000000. SLOOS requires fed.sloos.SUBLPDCILS_N.Q. Census
advance orders requires census.m3.adv.MDM.NO. MACRO_CONDITIONS_PANEL requires
those three dataset ids.
"""

from __future__ import annotations

import hashlib
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

SERIES_ID = "B1001NCBA"
DATASET_ID = "fed.h8.B1001NCBA"
SOURCE_ID = "federal_reserve_h8_bank_credit"
RIGHTS_RECORD_ID = "federal_reserve_h8_bank_credit"
PROVIDER_ID = "federal_reserve_board"
UNIT = "usd_millions"
EXPECTED_DESCRIPTION = "Bank credit, all commercial banks, seasonally adjusted"

# Board frequency code 19 is weekly, Wednesday. The value is not resampled.
WEEKLY_WEDNESDAY_CODE = "19"


@dataclass(frozen=True, slots=True)
class FedH8ParseResult:
    observations: tuple[EconomicObservation, ...]
    omitted_periods: tuple[str, ...]
    warnings: tuple[str, ...]


def parse_h8_payload(
    payload: dict[str, object],
    *,
    adapter_version: str,
    retrieved_at: datetime,
    collection_vintage_date: date,
) -> FedH8ParseResult:
    """Map one H.8 bundle to latest-revised weekly observations."""
    series_id = str(payload.get("series_id", ""))
    if series_id and series_id != SERIES_ID:
        raise ValueError(f"unexpected series id {series_id}")
    description = str(payload.get("description", ""))
    if description and description != EXPECTED_DESCRIPTION:
        raise ValueError(f"unexpected series description {description}")
    rows = payload.get("observations")
    if not isinstance(rows, list) or not rows:
        raise ValueError("observations list missing from H.8 payload")
    omitted = _omitted_periods(payload.get("omitted_periods"))

    warnings: list[str] = [f"{period}: omitted (not stored as zero)" for period in omitted]
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
        observations.append(obs)
    if not observations:
        raise ValueError("no usable H.8 observations after parsing")
    return FedH8ParseResult(
        observations=tuple(observations),
        omitted_periods=omitted,
        warnings=tuple(warnings),
    )


def h8_observation_id(
    period_start: date,
    vintage: date,
    disambiguator: str = "",
) -> str:
    """Stable id for one week and vintage. A disambiguator separates a same-day change."""
    key = f"{SERIES_ID}:{period_start.isoformat()}:{vintage.isoformat()}"
    if disambiguator:
        key = f"{key}:{disambiguator}"
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]
    return f"h8-{period_start.strftime('%Y%m%d')}-{digest}"


def _row_to_observation(
    item: dict[str, object],
    *,
    adapter_version: str,
    retrieved_at: datetime,
    collection_vintage_date: date,
) -> tuple[EconomicObservation | None, str | None]:
    period_raw = str(item.get("period", "")).strip()
    period_start = _week_start(period_raw)
    if period_start is None:
        return None, f"skipped unparseable period {period_raw}"

    value_raw = str(item.get("value", "")).strip()
    if not _finite_decimal(value_raw):
        return None, f"{period_raw}: omitted non-numeric value (not stored as zero)"

    vintage_raw = item.get("vintage")
    provider_vintage = (
        date.fromisoformat(str(vintage_raw)) if vintage_raw else collection_vintage_date
    )
    row_retrieved = _optional_datetime(item.get("retrieved_at")) or retrieved_at
    first_seen = _optional_datetime(item.get("first_seen_at")) or row_retrieved
    source_release = _optional_datetime(item.get("source_release_at")) or row_retrieved
    default_id = h8_observation_id(period_start, provider_vintage)
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
            frequency=Frequency.WEEKLY,
            geography="US",
            unit=UNIT,
            seasonal_adjustment=SeasonalAdjustment.SEASONALLY_ADJUSTED,
            raw_value=value_raw,
            quality_status=QualityStatus.OBSERVED,
            series_provenance=SeriesProvenance.LATEST_REVISED,
            provider_vintage_date=provider_vintage,
            earliest_model_available_at=None,
            availability_precision=AvailabilityPrecision.UNKNOWN,
            retrieved_at=row_retrieved,
            first_seen_at=first_seen,
            source_release_at=source_release,
            source_locator=locator,
            adapter_version=adapter_version,
        ),
        None,
    )


def _finite_decimal(value: str) -> bool:
    try:
        parsed = Decimal(value)
    except InvalidOperation:
        return False
    return parsed.is_finite()


def _optional_datetime(value: object) -> datetime | None:
    if value is None or value == "":
        return None
    parsed = datetime.fromisoformat(str(value))
    if parsed.tzinfo is None:
        raise ValueError("observation timestamps must be timezone-aware")
    return parsed


def _week_start(period: str) -> date | None:
    try:
        return date.fromisoformat(period)
    except ValueError:
        return None


def _omitted_periods(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(str(period) for period in value if str(period).strip())
