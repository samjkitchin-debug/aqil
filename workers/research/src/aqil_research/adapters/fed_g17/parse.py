"""Parse the Board G.17 total industrial production index into observations."""

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

SERIES_ID = "G17/IP_MARKET_GROUPS/IP.B50001.S"
SERIES_NAME = "IP.B50001.S"
DATASET_ID = "fed.g17.IP.B50001.S"
SOURCE_ID = "federal_reserve_g17_total_ip"
RIGHTS_RECORD_ID = "federal_reserve_g17_total_ip"
PROVIDER_ID = "federal_reserve_board"
UNIT = "index_2017_100"
BOARD_UNIT_LABEL = "Index:_2017_100"
BOARD_DESCRIPTION = "Total index; s.a. IP"

MONTH_PERIOD = re.compile(r"^(\d{4})-(\d{2})$")
OMITTED_TOKENS = frozenset({"nd", "na", "n/a", "n.a."})


@dataclass(frozen=True, slots=True)
class FedG17ParseResult:
    observations: tuple[EconomicObservation, ...]
    warnings: tuple[str, ...]


def is_omitted_token(value: str) -> bool:
    """Return whether a cell is ND, blank, or NA and must not be stored."""
    token = value.strip()
    return token == "" or token.casefold() in OMITTED_TOKENS


def month_period_start(period: str) -> date | None:
    match = MONTH_PERIOD.match(period.strip())
    if match is None:
        return None
    year = int(match.group(1))
    month = int(match.group(2))
    if month < 1 or month > 12:
        return None
    return date(year, month, 1)


def g17_observation_id(
    period_start: date,
    vintage: date,
    disambiguator: str = "",
) -> str:
    """Stable id for one month and stored vintage. A disambiguator separates a same-day change."""
    key = f"{SERIES_ID}:{period_start.isoformat()}:{vintage.isoformat()}"
    if disambiguator:
        key = f"{key}:{disambiguator}"
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]
    return f"g17-{period_start.strftime('%Y%m')}-{digest}"


def parse_g17_payload(
    payload: dict[str, object],
    *,
    adapter_version: str,
    retrieved_at: datetime,
    collection_vintage_date: date,
) -> FedG17ParseResult:
    """Map a G.17 bundle to latest-revised observations. ND, blank, and NA are omitted."""
    series_id = str(payload.get("series_id", ""))
    if series_id and series_id != SERIES_ID:
        raise ValueError(f"unexpected series id {series_id}")
    rows = payload.get("observations")
    if not isinstance(rows, list) or not rows:
        raise ValueError("observations list missing from G.17 payload")

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
        if warning:
            warnings.append(warning)
        if obs is not None:
            observations.append(obs)
    if not observations:
        raise ValueError("no usable G.17 observations after parsing")
    return FedG17ParseResult(observations=tuple(observations), warnings=tuple(warnings))


def _row_to_observation(
    item: dict[str, object],
    *,
    adapter_version: str,
    retrieved_at: datetime,
    collection_vintage_date: date,
) -> tuple[EconomicObservation | None, str | None]:
    period_raw = str(item.get("period", "")).strip()
    period_start = month_period_start(period_raw)
    if period_start is None:
        return None, f"skipped unparseable period {period_raw}"

    value_raw = str(item.get("value", "")).strip()
    if is_omitted_token(value_raw):
        return None, f"{period_raw}: omitted {value_raw or 'blank'} (not zero)"

    try:
        Decimal(value_raw)
    except InvalidOperation:
        return None, f"{period_raw}: non-numeric value {value_raw}"

    vintage_raw = item.get("vintage")
    provider_vintage = (
        date.fromisoformat(str(vintage_raw)) if vintage_raw else collection_vintage_date
    )
    source_release = _optional_datetime(item.get("source_release_at"))
    default_id = g17_observation_id(period_start, provider_vintage)
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
            frequency=Frequency.MONTHLY,
            geography="US",
            unit=UNIT,
            seasonal_adjustment=SeasonalAdjustment.SEASONALLY_ADJUSTED,
            raw_value=value_raw,
            quality_status=QualityStatus.OBSERVED,
            series_provenance=SeriesProvenance.LATEST_REVISED,
            provider_vintage_date=provider_vintage,
            earliest_model_available_at=None,
            availability_precision=AvailabilityPrecision.UNKNOWN,
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
