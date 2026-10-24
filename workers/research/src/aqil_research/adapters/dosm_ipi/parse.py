"""Parse the DOSM industrial production CSV. Growth rows and the adjusted index are not stored."""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from aqil_research.adapters.dosm_ipi.constants import (
    ACCESS_URL,
    ADAPTER_ID,
    ADAPTER_VERSION,
    DATASET_ID,
    FREQUENCY_LABEL,
    GEOGRAPHY,
    GROWTH_SERIES,
    LEVEL_COLUMN,
    PROVIDER_ID,
    RIGHTS_RECORD_ID,
    SA_COLUMN,
    SEASONAL_ADJUSTMENT_LABEL,
    SERIES_KEY,
    SOURCE_ID,
    UNIT_TEXT,
    VINTAGE_CLASS,
)
from aqil_research.adapters.dosm_ipi.stability import observation_id
from aqil_research.contracts.observation import (
    AvailabilityPrecision,
    EconomicObservation,
    Frequency,
    QualityStatus,
    SeasonalAdjustment,
    SeriesProvenance,
)

OBSERVATION_ADAPTER_VERSION = f"{ADAPTER_ID}:{ADAPTER_VERSION}"
MONTH_START = re.compile(r"^(\d{4})-(\d{2})-01$")
REQUIRED_COLUMNS = ("series", "date", LEVEL_COLUMN, SA_COLUMN)


@dataclass(frozen=True, slots=True)
class DosmIpiParseResult:
    observations: tuple[EconomicObservation, ...]
    omitted_periods: tuple[str, ...]
    series_key: str
    compiler_sentence: str
    unit: str
    seasonal_adjustment: str
    frequency: str
    vintage_class: str


def parse_dosm_ipi_csv(text: str, *, retrieved_at: datetime) -> DosmIpiParseResult:
    """Store the absolute index. Growth rates and the seasonally adjusted column are ignored."""
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        raise ValueError("DOSM CSV has no header")
    reader.fieldnames = [name.strip() if name else "" for name in reader.fieldnames]
    missing = [column for column in REQUIRED_COLUMNS if column not in reader.fieldnames]
    if missing:
        raise ValueError(f"DOSM CSV is missing columns: {', '.join(missing)}")

    observations: list[EconomicObservation] = []
    omitted: list[str] = []
    seen_values: dict[date, str] = {}
    level_rows = 0
    for row in reader:
        if not any((value or "").strip() for value in row.values()):
            continue
        series = (row.get("series") or "").strip()
        if series in GROWTH_SERIES:
            continue
        if series != SERIES_KEY:
            raise ValueError(
                f"series is {series or 'blank'}; refusing a row that is not the absolute index",
            )
        period_token = (row.get("date") or "").strip()
        period_start = _month_start(period_token)
        if period_start is None:
            raise ValueError(f"unparseable monthly period {period_token}")
        level_rows += 1
        value_raw = (row.get(LEVEL_COLUMN) or "").strip()
        if value_raw == "":
            omitted.append(period_token)
            continue
        parsed = _finite_decimal(period_token, value_raw)
        previous = seen_values.get(period_start)
        if previous is not None:
            if Decimal(previous) != parsed:
                raise ValueError(
                    f"{period_token}: more than one value; this file is not classified "
                    "as a vintage panel",
                )
            continue
        seen_values[period_start] = value_raw
        vintage = retrieved_at.date()
        observations.append(
            EconomicObservation(
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
            ),
        )
    if level_rows == 0:
        raise ValueError("DOSM CSV has no absolute-index rows")
    observations.sort(key=lambda item: item.period_start)
    return DosmIpiParseResult(
        observations=tuple(observations),
        omitted_periods=tuple(omitted),
        series_key=SERIES_KEY,
        compiler_sentence="Department of Statistics Malaysia industrial production index",
        unit=UNIT_TEXT,
        seasonal_adjustment=SEASONAL_ADJUSTMENT_LABEL,
        frequency=FREQUENCY_LABEL,
        vintage_class=VINTAGE_CLASS,
    )


def _month_start(period: str) -> date | None:
    match = MONTH_START.match(period)
    if match is None:
        return None
    month = int(match.group(2))
    if month < 1 or month > 12:
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
