"""Confirm JTS000000000000000JOL from the official JT files and normalise monthly values."""

from __future__ import annotations

import calendar
import hashlib
import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from aqil_research.adapters.bls_jolts.constants import (
    ADAPTER_ID,
    AREA_CODE,
    BEGIN_YEAR,
    DATA_URL,
    DATAELEMENT_CODE,
    DATASET_ID,
    INDUSTRY_CODE,
    PROVIDER_ID,
    RATELEVEL_CODE,
    RIGHTS_RECORD_ID,
    SEASONAL_CODE,
    SERIES_ID,
    SIZECLASS_CODE,
    SOURCE_ID,
    STATE_CODE,
    UNIT,
)
from aqil_research.contracts.observation import (
    AvailabilityPrecision,
    EconomicObservation,
    Frequency,
    QualityStatus,
    SeasonalAdjustment,
    SeriesProvenance,
)

MONTH_PERIOD = re.compile(r"^M(0[1-9]|1[0-2])$")
BLANK_VALUES = frozenset({"", "-", ".", "na", "n/a"})


class JoltsBindingError(ValueError):
    """The official JT files do not confirm the total nonfarm job-openings series."""


@dataclass(frozen=True, slots=True)
class JoltsBinding:
    begin: date
    end: date


@dataclass(frozen=True, slots=True)
class JoltsExtract:
    rows: tuple[dict[str, object], ...]
    omitted_periods: tuple[str, ...]


def confirm_jolts_binding(
    series_text: str,
    seasonal_text: str,
    industry_text: str,
    dataelement_text: str,
    ratelevel_text: str,
) -> JoltsBinding:
    """Bind only when jt.series and the JT code tables agree."""
    series_row = _required_row(_table(series_text), "series_id", SERIES_ID, "jt.series")
    if series_row.get("seasonal") != SEASONAL_CODE:
        raise JoltsBindingError("jt.series seasonal code is not S")
    if series_row.get("industry_code") != INDUSTRY_CODE:
        raise JoltsBindingError("jt.series industry is not total nonfarm (000000)")
    if series_row.get("state_code") != STATE_CODE:
        raise JoltsBindingError("jt.series state code is not the national total")
    if series_row.get("area_code") != AREA_CODE:
        raise JoltsBindingError("jt.series area code is not the national total")
    if series_row.get("sizeclass_code") != SIZECLASS_CODE:
        raise JoltsBindingError("jt.series size class is not the all-sizes total")
    if series_row.get("dataelement_code") != DATAELEMENT_CODE:
        raise JoltsBindingError("jt.series data element is not job openings (JO)")
    if series_row.get("ratelevel_code") != RATELEVEL_CODE:
        raise JoltsBindingError("jt.series rate/level code is not level (L)")
    if series_row.get("begin_year") != BEGIN_YEAR:
        raise JoltsBindingError("jt.series does not start in 2000")

    seasonal_row = _required_row(
        _table(seasonal_text),
        "seasonal_code",
        SEASONAL_CODE,
        "jt.seasonal",
    )
    if seasonal_row.get("seasonal_text", "").casefold() != "seasonally adjusted":
        raise JoltsBindingError("jt.seasonal does not describe S as seasonally adjusted")

    industry_row = _required_row(
        _table(industry_text),
        "industry_code",
        INDUSTRY_CODE,
        "jt.industry",
    )
    if industry_row.get("industry_text", "").casefold() != "total nonfarm":
        raise JoltsBindingError("jt.industry does not describe 000000 as total nonfarm")

    element_row = _required_row(
        _table(dataelement_text),
        "dataelement_code",
        DATAELEMENT_CODE,
        "jt.dataelement",
    )
    if element_row.get("dataelement_text", "").casefold() != "job openings":
        raise JoltsBindingError("jt.dataelement does not describe JO as job openings")

    level_row = _required_row(
        _table(ratelevel_text),
        "ratelevel_code",
        RATELEVEL_CODE,
        "jt.ratelevel",
    )
    level_text = level_row.get("ratelevel_text", "").casefold()
    if "thousands" not in level_text or "level" not in level_text:
        raise JoltsBindingError("jt.ratelevel does not describe L as a level in thousands")

    begin = _month_start(series_row.get("begin_year", ""), series_row.get("begin_period", ""))
    end = _month_start(series_row.get("end_year", ""), series_row.get("end_period", ""))
    if begin is None or end is None or end < begin:
        raise JoltsBindingError("jt.series begin and end are not a monthly span")
    return JoltsBinding(begin=begin, end=end)


def extract_jolts_rows(data_text: str, binding: JoltsBinding) -> JoltsExtract:
    """Keep one series from the job-openings file. Omit blanks. Do not interpolate."""
    present: dict[date, dict[str, object]] = {}
    omitted: list[str] = []
    omitted_months: set[date] = set()
    for row in _table(data_text):
        if row.get("series_id") != SERIES_ID:
            continue
        year = row.get("year", "")
        period = row.get("period", "")
        label = f"{year}-{period}"
        if not MONTH_PERIOD.match(period) or not year.isdigit():
            omitted.append(f"{label}: non-monthly period omitted")
            continue
        period_start = date(int(year), int(period[1:]), 1)
        raw = row.get("value", "").strip()
        if raw.casefold() in BLANK_VALUES:
            omitted.append(f"{period_start.isoformat()}: blank value omitted")
            omitted_months.add(period_start)
            continue
        try:
            canonical = _canonical_decimal(raw)
        except (InvalidOperation, ValueError):
            omitted.append(f"{period_start.isoformat()}: non-numeric value omitted")
            omitted_months.add(period_start)
            continue
        item = {
            "period": period_start.isoformat(),
            "value": canonical,
            "footnote": row.get("footnote_codes", "").strip(),
        }
        existing = present.get(period_start)
        if existing is not None and existing["value"] != canonical:
            raise JoltsBindingError(
                f"contradictory values for {period_start.isoformat()} in one JT file",
            )
        present[period_start] = item

    for month in _months(binding.begin, binding.end):
        if month in present or month in omitted_months:
            continue
        omitted.append(f"{month.isoformat()}: absent from file")
    rows = tuple(present[month] for month in sorted(present))
    return JoltsExtract(rows=rows, omitted_periods=tuple(omitted))


def observations_from_payload(
    payload: dict[str, object],
    *,
    retrieved_at: datetime,
    adapter_version: str,
) -> tuple[EconomicObservation, ...]:
    """Map a stabilised payload to schema 1.0 latest-revised observations."""
    rows = payload.get("observations")
    if not isinstance(rows, list):
        raise JoltsBindingError("job-openings payload has no observations")
    observations: list[EconomicObservation] = []
    for item in rows:
        if not isinstance(item, dict):
            raise JoltsBindingError("job-openings observation is not an object")
        observations.append(
            _observation(item, retrieved_at=retrieved_at, adapter_version=adapter_version),
        )
    if not observations:
        raise JoltsBindingError("no usable job-openings observations")
    return tuple(observations)


def jolts_observation_id(
    period_start: date,
    vintage: date,
    disambiguator: str = "",
) -> str:
    """Stable id for one period and vintage. A disambiguator separates a same-day change."""
    key = f"{SERIES_ID}:{period_start.isoformat()}:{vintage.isoformat()}"
    if disambiguator:
        key = f"{key}:{disambiguator}"
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]
    return f"jolts-{period_start.strftime('%Y%m')}-{digest}"


def _observation(
    item: dict[str, object],
    *,
    retrieved_at: datetime,
    adapter_version: str,
) -> EconomicObservation:
    period_start = date.fromisoformat(str(item["period"]))
    raw_value = str(item["value"])
    vintage_raw = item.get("vintage")
    provider_vintage = date.fromisoformat(str(vintage_raw)) if vintage_raw else retrieved_at.date()
    observation_id = str(item.get("observation_id") or "")
    if not observation_id:
        observation_id = jolts_observation_id(period_start, provider_vintage)
    release = _optional_datetime(item.get("source_release_at")) or retrieved_at
    row_retrieved = _optional_datetime(item.get("retrieved_at")) or retrieved_at
    first_seen = _optional_datetime(item.get("first_seen_at")) or row_retrieved
    return EconomicObservation(
        observation_id=observation_id,
        dataset_id=DATASET_ID,
        provider_id=PROVIDER_ID,
        source_id=SOURCE_ID,
        rights_record_id=RIGHTS_RECORD_ID,
        period_start=period_start,
        period_end=_month_end(period_start),
        frequency=Frequency.MONTHLY,
        geography="US",
        unit=UNIT,
        seasonal_adjustment=SeasonalAdjustment.SEASONALLY_ADJUSTED,
        raw_value=raw_value,
        quality_status=QualityStatus.OBSERVED,
        series_provenance=SeriesProvenance.LATEST_REVISED,
        provider_vintage_date=provider_vintage,
        source_release_at=release,
        earliest_model_available_at=None,
        availability_precision=AvailabilityPrecision.UNKNOWN,
        retrieved_at=row_retrieved,
        first_seen_at=first_seen,
        source_locator=f"{DATA_URL}#{SERIES_ID}",
        adapter_version=adapter_version or f"{ADAPTER_ID}:1.0.0",
    )


def _table(text: str) -> list[dict[str, str]]:
    lines = [line for line in text.lstrip("\ufeff").splitlines() if line.strip()]
    if not lines:
        raise JoltsBindingError("JT file is empty")
    header = [part.strip() for part in lines[0].split("\t")]
    rows: list[dict[str, str]] = []
    for line in lines[1:]:
        parts = [part.strip() for part in line.split("\t")]
        if len(parts) < len(header):
            parts.extend([""] * (len(header) - len(parts)))
        rows.append({header[index]: parts[index] for index in range(len(header))})
    return rows


def _required_row(
    rows: list[dict[str, str]],
    key: str,
    value: str,
    filename: str,
) -> dict[str, str]:
    for row in rows:
        if row.get(key) == value:
            return row
    raise JoltsBindingError(f"{value} is not in {filename}")


def _month_start(year: str, period: str) -> date | None:
    if not year.isdigit() or not MONTH_PERIOD.match(period):
        return None
    return date(int(year), int(period[1:]), 1)


def _month_end(start: date) -> date:
    return date(start.year, start.month, calendar.monthrange(start.year, start.month)[1])


def _months(start: date, end: date) -> list[date]:
    months: list[date] = []
    cursor = date(start.year, start.month, 1)
    last = date(end.year, end.month, 1)
    while cursor <= last:
        months.append(cursor)
        if cursor.month == 12:
            cursor = date(cursor.year + 1, 1, 1)
        else:
            cursor = date(cursor.year, cursor.month + 1, 1)
    return months


def _canonical_decimal(raw: str) -> str:
    parsed = Decimal(raw)
    if not parsed.is_finite():
        raise ValueError("non-finite")
    text = format(parsed, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def _optional_datetime(value: object) -> datetime | None:
    if value is None or value == "":
        return None
    parsed = datetime.fromisoformat(str(value))
    if parsed.tzinfo is None:
        raise JoltsBindingError("job-openings timestamps must be timezone-aware")
    return parsed
