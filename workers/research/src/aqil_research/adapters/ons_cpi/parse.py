"""Parse the bound ONS CPI CSV. Only monthly rows become observations."""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from aqil_research.adapters.ons_cpi.constants import (
    ACCESS_URL,
    ADAPTER_ID,
    ADAPTER_VERSION,
    DATASET_ID,
    FREQUENCY_LABEL,
    GEOGRAPHY,
    PROVIDER_ID,
    RIGHTS_RECORD_ID,
    SEASONAL_ADJUSTMENT_LABEL,
    SERIES_KEY,
    SOURCE_DATASET,
    SOURCE_ID,
    TITLE,
    UNIT_HEADER,
    UNIT_TEXT,
    VINTAGE_CLASS,
)
from aqil_research.adapters.ons_cpi.stability import observation_id
from aqil_research.contracts.observation import (
    AvailabilityPrecision,
    EconomicObservation,
    Frequency,
    QualityStatus,
    SeasonalAdjustment,
    SeriesProvenance,
)

OBSERVATION_ADAPTER_VERSION = f"{ADAPTER_ID}:{ADAPTER_VERSION}"
MONTHLY = re.compile(r"^(\d{4}) ([A-Z]{3})$")
QUARTERLY = re.compile(r"^(\d{4}) Q([1-4])$")
ANNUAL = re.compile(r"^(\d{4})$")
MONTHS = {
    "JAN": 1,
    "FEB": 2,
    "MAR": 3,
    "APR": 4,
    "MAY": 5,
    "JUN": 6,
    "JUL": 7,
    "AUG": 8,
    "SEP": 9,
    "OCT": 10,
    "NOV": 11,
    "DEC": 12,
}


@dataclass(frozen=True, slots=True)
class OnsCpiParseResult:
    observations: tuple[EconomicObservation, ...]
    omitted_periods: tuple[str, ...]
    series_key: str
    compiler_sentence: str
    unit: str
    seasonal_adjustment: str
    frequency: str
    vintage_class: str


def parse_ons_cpi_csv(text: str, *, retrieved_at: datetime) -> OnsCpiParseResult:
    """Store monthly index rows. Annual and quarterly rows are a different frequency."""
    rows = list(csv.reader(io.StringIO(text)))
    if not rows:
        raise ValueError("ONS CSV has no rows")
    meta: dict[str, str] = {}
    data: list[tuple[str, str]] = []
    for row in rows:
        if not row or not any(cell.strip() for cell in row):
            continue
        token = row[0].strip()
        second = row[1].strip() if len(row) > 1 else ""
        if MONTHLY.match(token) or QUARTERLY.match(token) or ANNUAL.match(token):
            data.append((token, second))
        else:
            meta[token] = second
    _require_identity(meta)
    observations: list[EconomicObservation] = []
    omitted: list[str] = []
    seen_values: dict[date, str] = {}
    monthly_rows = 0
    for token, value_raw in data:
        if QUARTERLY.match(token) or ANNUAL.match(token):
            continue
        month_start = _month_start(token)
        if month_start is None:
            raise ValueError(f"unparseable monthly period {token}")
        monthly_rows += 1
        if value_raw == "":
            omitted.append(token)
            continue
        parsed = _finite_decimal(token, value_raw)
        previous = seen_values.get(month_start)
        if previous is not None:
            if Decimal(previous) != parsed:
                raise ValueError(
                    f"{token}: more than one value; this file is not classified as a vintage panel",
                )
            continue
        seen_values[month_start] = value_raw
        vintage = retrieved_at.date()
        observations.append(_observation(month_start, value_raw, vintage, retrieved_at))
    if monthly_rows == 0:
        raise ValueError("ONS CSV has no monthly rows")
    observations.sort(key=lambda item: item.period_start)
    return OnsCpiParseResult(
        observations=tuple(observations),
        omitted_periods=tuple(omitted),
        series_key=SERIES_KEY,
        compiler_sentence=TITLE,
        unit=UNIT_TEXT,
        seasonal_adjustment=SEASONAL_ADJUSTMENT_LABEL,
        frequency=FREQUENCY_LABEL,
        vintage_class=VINTAGE_CLASS,
    )


def _require_identity(meta: dict[str, str]) -> None:
    expected = {
        "Title": TITLE,
        "CDID": SERIES_KEY,
        "Source dataset ID": SOURCE_DATASET,
        "Unit": UNIT_HEADER,
    }
    for key, value in expected.items():
        actual = meta.get(key, "")
        if actual != value:
            raise ValueError(
                f"{key} is {actual or 'blank'}; refusing a series that is not {SERIES_KEY}",
            )


def _month_start(token: str) -> date | None:
    match = MONTHLY.match(token)
    if match is None:
        return None
    month = MONTHS.get(match.group(2))
    if month is None:
        return None
    return date(int(match.group(1)), month, 1)


def _finite_decimal(period: str, value_raw: str) -> Decimal:
    try:
        parsed = Decimal(value_raw)
    except InvalidOperation as exc:
        raise ValueError(f"{period}: non-numeric value") from exc
    if not parsed.is_finite():
        raise ValueError(f"{period}: non-finite value")
    return parsed


def _observation(
    period_start: date,
    value_raw: str,
    vintage: date,
    retrieved_at: datetime,
) -> EconomicObservation:
    return EconomicObservation(
        observation_id=observation_id(period_start, vintage),
        dataset_id=DATASET_ID,
        provider_id=PROVIDER_ID,
        source_id=SOURCE_ID,
        rights_record_id=RIGHTS_RECORD_ID,
        period_start=period_start,
        frequency=Frequency.MONTHLY,
        geography=GEOGRAPHY,
        unit=UNIT_TEXT,
        seasonal_adjustment=SeasonalAdjustment.NOT_SEASONALLY_ADJUSTED,
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
    )
