"""Confirm CES0000000001 from the official CE files and normalise monthly values."""

from __future__ import annotations

import calendar
import hashlib
import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from aqil_research.adapters.bls_payrolls.constants import (
    ADAPTER_ID,
    DATA_TYPE_CODE,
    DATA_URL,
    DATASET_ID,
    INDUSTRY_CODE,
    PROVIDER_ID,
    RIGHTS_RECORD_ID,
    SEASONAL_CODE,
    SERIES_ID,
    SOURCE_ID,
    SUPERSECTOR_CODE,
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


class PayrollBindingError(ValueError):
    """The official CE files do not confirm the total nonfarm payroll series."""


@dataclass(frozen=True, slots=True)
class PayrollBinding:
    begin: date
    end: date


@dataclass(frozen=True, slots=True)
class PayrollExtract:
    rows: tuple[dict[str, object], ...]
    omitted_periods: tuple[str, ...]


def confirm_payroll_binding(
    series_text: str,
    datatype_text: str,
    seasonal_text: str,
) -> PayrollBinding:
    """Bind only when ce.series, ce.datatype, and ce.seasonal agree."""
    series_row = _required_row(_table(series_text), "series_id", SERIES_ID, "ce.series")
    if series_row.get("supersector_code") != SUPERSECTOR_CODE:
        raise PayrollBindingError("ce.series supersector is not total nonfarm (00)")
    if series_row.get("industry_code") != INDUSTRY_CODE:
        raise PayrollBindingError("ce.series industry code is not 00000000")
    if series_row.get("data_type_code") != DATA_TYPE_CODE:
        raise PayrollBindingError("ce.series data type is not 01")
    if series_row.get("seasonal") != SEASONAL_CODE:
        raise PayrollBindingError("ce.series seasonal code is not S")
    title = series_row.get("series_title", "").casefold()
    if "not seasonally adjusted" in title or "seasonally adjusted" not in title:
        raise PayrollBindingError("ce.series title is not seasonally adjusted")
    if "total nonfarm" not in title or "thousands" not in title:
        raise PayrollBindingError("ce.series title is not total nonfarm employment in thousands")

    datatype_row = _required_row(
        _table(datatype_text),
        "data_type_code",
        DATA_TYPE_CODE,
        "ce.datatype",
    )
    datatype_text_value = datatype_row.get("data_type_text", "").casefold()
    if "thousands" not in datatype_text_value or "employees" not in datatype_text_value:
        raise PayrollBindingError(
            "ce.datatype does not describe data type 01 as employees, thousands"
        )

    seasonal_row = _required_row(
        _table(seasonal_text),
        "seasonal_code",
        SEASONAL_CODE,
        "ce.seasonal",
    )
    if seasonal_row.get("seasonal_text", "").casefold() != "seasonally adjusted":
        raise PayrollBindingError("ce.seasonal does not describe S as seasonally adjusted")

    begin = _month_start(series_row.get("begin_year", ""), series_row.get("begin_period", ""))
    end = _month_start(series_row.get("end_year", ""), series_row.get("end_period", ""))
    if begin is None or end is None or end < begin:
        raise PayrollBindingError("ce.series begin and end are not a monthly span")
    return PayrollBinding(begin=begin, end=end)


def extract_payroll_rows(data_text: str, binding: PayrollBinding) -> PayrollExtract:
    """Keep finite monthly values for this series. Omit blanks. Do not interpolate."""
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
            raise PayrollBindingError(
                f"contradictory values for {period_start.isoformat()} in one CE file",
            )
        present[period_start] = item

    for month in _months(binding.begin, binding.end):
        if month in present or month in omitted_months:
            continue
        omitted.append(f"{month.isoformat()}: absent from file")
    rows = tuple(present[month] for month in sorted(present))
    return PayrollExtract(rows=rows, omitted_periods=tuple(omitted))


def observations_from_payload(
    payload: dict[str, object],
    *,
    retrieved_at: datetime,
    adapter_version: str,
) -> tuple[EconomicObservation, ...]:
    """Map a stabilised payload to schema 1.0 latest-revised observations."""
    rows = payload.get("observations")
    if not isinstance(rows, list):
        raise PayrollBindingError("payroll payload has no observations")
    observations: list[EconomicObservation] = []
    for item in rows:
        if not isinstance(item, dict):
            raise PayrollBindingError("payroll observation is not an object")
        observations.append(
            _observation(item, retrieved_at=retrieved_at, adapter_version=adapter_version),
        )
    if not observations:
        raise PayrollBindingError("no usable payroll observations")
    return tuple(observations)


def payroll_observation_id(
    period_start: date,
    vintage: date,
    disambiguator: str = "",
) -> str:
    """Stable id for one period and vintage. A disambiguator separates a same-day change."""
    key = f"{SERIES_ID}:{period_start.isoformat()}:{vintage.isoformat()}"
    if disambiguator:
        key = f"{key}:{disambiguator}"
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]
    return f"ces-{period_start.strftime('%Y%m')}-{digest}"


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
        observation_id = payroll_observation_id(period_start, provider_vintage)
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
        raise PayrollBindingError("CE file is empty")
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
    raise PayrollBindingError(f"{value} is not in {filename}")


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
        raise PayrollBindingError("payroll timestamps must be timezone-aware")
    return parsed
