"""Parse the official Bank Rate CSV into EconomicObservation 1.0 rows."""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from aqil_research.adapters.boe_bank_rate.constants import (
    ACCESS_URL,
    ADAPTER_ID,
    ADAPTER_VERSION,
    DATASET_ID,
    FREQUENCY_LABEL,
    GEOGRAPHY,
    PROVIDER_ID,
    RIGHTS_RECORD_ID,
    SERIES_CODE,
    SERIES_DESCRIPTION,
    SOURCE_ID,
    UNIT_TEXT,
    VINTAGE_CLASS,
)
from aqil_research.adapters.boe_bank_rate.stability import observation_id
from aqil_research.contracts.observation import (
    AvailabilityPrecision,
    EconomicObservation,
    Frequency,
    QualityStatus,
    SeasonalAdjustment,
    SeriesProvenance,
)

OBSERVATION_ADAPTER_VERSION = f"{ADAPTER_ID}:{ADAPTER_VERSION}"
UNAVAILABLE = frozenset({"", ".."})
DAY_TOKEN = re.compile(r"^(\d{1,2}) ([A-Za-z]{3}) (\d{4})$")
MONTHS = {
    "Jan": 1,
    "Feb": 2,
    "Mar": 3,
    "Apr": 4,
    "May": 5,
    "Jun": 6,
    "Jul": 7,
    "Aug": 8,
    "Sep": 9,
    "Oct": 10,
    "Nov": 11,
    "Dec": 12,
}


@dataclass(frozen=True, slots=True)
class BoeBankRateParseResult:
    observations: tuple[EconomicObservation, ...]
    omitted_periods: tuple[str, ...]
    series_key: str
    compiler_sentence: str
    unit: str
    seasonal_adjustment: str
    frequency: str
    vintage_class: str


def parse_boe_bank_rate_csv(
    text: str,
    *,
    retrieved_at: datetime,
) -> BoeBankRateParseResult:
    """Map the current CSV to observations. Missing days are omitted, not filled."""
    description, table = _split_tables(text)
    _require_description(description)
    reader = csv.DictReader(io.StringIO(table))
    if reader.fieldnames is None:
        raise ValueError("Bank Rate CSV has no observation header")
    reader.fieldnames = [name.strip() if name else "" for name in reader.fieldnames]
    for column in ("DATE", "SERIES", "VALUE"):
        if column not in reader.fieldnames:
            raise ValueError(f"Bank Rate CSV is missing columns: {column}")

    observations: list[EconomicObservation] = []
    omitted: list[str] = []
    seen_values: dict[str, str] = {}
    data_rows = 0
    for row in reader:
        if not any((value or "").strip() for value in row.values()):
            continue
        data_rows += 1
        series = (row.get("SERIES") or "").strip()
        if series != SERIES_CODE:
            raise ValueError(
                f"SERIES is {series or 'blank'}; refusing a series that is not {SERIES_CODE}",
            )
        period_token = (row.get("DATE") or "").strip()
        period_start = _day(period_token)
        if period_start is None:
            raise ValueError(f"unparseable daily period {period_token}")
        value_raw = (row.get("VALUE") or "").strip()
        if value_raw in UNAVAILABLE:
            omitted.append(period_token)
            continue
        parsed = _finite_decimal(period_token, value_raw)
        previous = seen_values.get(period_start.isoformat())
        if previous is not None:
            if Decimal(previous) != parsed:
                raise ValueError(
                    f"{period_token}: more than one value; this file is not classified "
                    "as a vintage panel",
                )
            continue
        seen_values[period_start.isoformat()] = value_raw
        vintage = retrieved_at.date()
        observations.append(
            EconomicObservation(
                observation_id=observation_id(period_start, vintage),
                dataset_id=DATASET_ID,
                provider_id=PROVIDER_ID,
                source_id=SOURCE_ID,
                rights_record_id=RIGHTS_RECORD_ID,
                period_start=period_start,
                frequency=Frequency.DAILY,
                geography=GEOGRAPHY,
                unit=UNIT_TEXT,
                seasonal_adjustment=SeasonalAdjustment.UNKNOWN,
                raw_value=value_raw,
                quality_status=QualityStatus.OBSERVED,
                series_provenance=SeriesProvenance.LATEST_REVISED,
                provider_vintage_date=vintage,
                source_release_at=retrieved_at,
                earliest_model_available_at=None,
                availability_precision=AvailabilityPrecision.UNKNOWN,
                retrieved_at=retrieved_at,
                first_seen_at=retrieved_at,
                source_locator=ACCESS_URL,
                adapter_version=OBSERVATION_ADAPTER_VERSION,
            ),
        )
    if data_rows == 0:
        raise ValueError("Bank Rate CSV has no data rows")
    observations.sort(key=lambda item: item.period_start)
    return BoeBankRateParseResult(
        observations=tuple(observations),
        omitted_periods=tuple(omitted),
        series_key=SERIES_CODE,
        compiler_sentence=SERIES_DESCRIPTION,
        unit=UNIT_TEXT,
        seasonal_adjustment="not stated",
        frequency=FREQUENCY_LABEL,
        vintage_class=VINTAGE_CLASS,
    )


def _split_tables(text: str) -> tuple[str, str]:
    marker = "DATE,SERIES,VALUE"
    if marker not in text:
        raise ValueError("Bank Rate CSV has no observation table")
    description, _, table = text.partition(marker)
    return description, f"{marker}{table}"


def _require_description(description: str) -> None:
    reader = csv.DictReader(io.StringIO(description))
    if reader.fieldnames is None:
        raise ValueError("Bank Rate CSV has no series description")
    reader.fieldnames = [name.strip() if name else "" for name in reader.fieldnames]
    found = False
    for row in reader:
        if not any((value or "").strip() for value in row.values()):
            continue
        series = (row.get("SERIES") or "").strip()
        label = (row.get("DESCRIPTION") or "").strip()
        if series == SERIES_CODE and label == SERIES_DESCRIPTION:
            found = True
            continue
        if series or label:
            raise ValueError(
                f"description is {series} {label}; refusing a series that is not {SERIES_CODE}",
            )
    if not found:
        raise ValueError(f"refusing a file that does not describe {SERIES_CODE}")


def _day(period: str) -> date | None:
    match = DAY_TOKEN.match(period)
    if match is None:
        return None
    month = MONTHS.get(match.group(2).title())
    if month is None:
        return None
    day = int(match.group(1))
    year = int(match.group(3))
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _finite_decimal(period: str, value_raw: str) -> Decimal:
    try:
        parsed = Decimal(value_raw)
    except InvalidOperation as exc:
        raise ValueError(f"{period}: non-numeric value") from exc
    if not parsed.is_finite():
        raise ValueError(f"{period}: non-finite value")
    return parsed
