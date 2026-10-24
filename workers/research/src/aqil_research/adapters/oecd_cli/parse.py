"""Parse the bound OECD G20 CLI CSV into EconomicObservation 1.0 rows."""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from aqil_research.adapters.oecd_cli.constants import (
    ACCESS_URL,
    ACTIVITY,
    ADAPTER_ID,
    ADAPTER_VERSION,
    ADJUSTMENT,
    ADJUSTMENT_LABEL,
    DATASET_ID,
    FREQ_CODE,
    FREQUENCY_LABEL,
    GEOGRAPHY,
    MEASURE,
    MEASURE_LABEL,
    METHODOLOGY,
    METHODOLOGY_LABEL,
    OBS_STATUS_OBSERVED,
    PROVIDER_ID,
    REF_AREA,
    RIGHTS_RECORD_ID,
    SERIES_KEY,
    SOURCE_ID,
    STRUCTURE_ID,
    STRUCTURE_NAME,
    TIME_HORIZON,
    TRANSFORMATION,
    UNIT_LABEL,
    UNIT_MEASURE,
    UNIT_MULT,
    UNIT_TEXT,
    VINTAGE_CLASS,
)
from aqil_research.adapters.oecd_cli.stability import observation_id
from aqil_research.contracts.observation import (
    AvailabilityPrecision,
    EconomicObservation,
    Frequency,
    QualityStatus,
    SeasonalAdjustment,
    SeriesProvenance,
)

OBSERVATION_ADAPTER_VERSION = f"{ADAPTER_ID}:{ADAPTER_VERSION}"
OMIT_STATUSES = frozenset({"M", ""})
MONTH_PERIOD = re.compile(r"^(\d{4})-(\d{2})$")
_IDENTITY = (
    ("STRUCTURE_ID", STRUCTURE_ID),
    ("STRUCTURE_NAME", STRUCTURE_NAME),
    ("REF_AREA", REF_AREA),
    ("Reference area", GEOGRAPHY),
    ("FREQ", FREQ_CODE),
    ("MEASURE", MEASURE),
    ("Measure", MEASURE_LABEL),
    ("UNIT_MEASURE", UNIT_MEASURE),
    ("Unit of measure", UNIT_LABEL),
    ("ACTIVITY", ACTIVITY),
    ("ADJUSTMENT", ADJUSTMENT),
    ("Adjustment", ADJUSTMENT_LABEL),
    ("TRANSFORMATION", TRANSFORMATION),
    ("TIME_HORIZ", TIME_HORIZON),
    ("METHODOLOGY", METHODOLOGY),
    ("Calculation methodology", METHODOLOGY_LABEL),
    ("UNIT_MULT", UNIT_MULT),
)
REQUIRED = tuple(column for column, _expected in _IDENTITY) + (
    "TIME_PERIOD",
    "OBS_VALUE",
    "OBS_STATUS",
)


@dataclass(frozen=True, slots=True)
class OecdCliParseResult:
    observations: tuple[EconomicObservation, ...]
    omitted_periods: tuple[str, ...]
    series_key: str
    compiler_sentence: str
    unit: str
    seasonal_adjustment: str
    frequency: str
    vintage_class: str


def parse_oecd_cli_csv(text: str, *, retrieved_at: datetime) -> OecdCliParseResult:
    """Map the current CSV to observations. Blank months are omitted, not filled."""
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        raise ValueError("OECD CSV has no header")
    reader.fieldnames = [name.strip() if name else "" for name in reader.fieldnames]
    missing = [column for column in REQUIRED if column not in reader.fieldnames]
    if missing:
        raise ValueError("OECD CSV is missing columns: " + ", ".join(missing))
    observations: list[EconomicObservation] = []
    omitted: list[str] = []
    seen: dict[date, str] = {}
    data_rows = 0
    for row in reader:
        if not any((value or "").strip() for value in row.values()):
            continue
        data_rows += 1
        for column, expected in _IDENTITY:
            actual = (row.get(column) or "").strip()
            if actual != expected:
                raise ValueError(
                    f"{column} is {actual or 'blank'}; refusing a series that is not "
                    f"the OECD G20 CLI {SERIES_KEY}",
                )
        period_token = (row.get("TIME_PERIOD") or "").strip()
        match = MONTH_PERIOD.match(period_token)
        if match is None:
            raise ValueError(f"unparseable monthly period {period_token}")
        month = int(match.group(2))
        if month < 1 or month > 12:
            raise ValueError(f"unparseable monthly period {period_token}")
        period_start = date(int(match.group(1)), month, 1)
        value_raw = (row.get("OBS_VALUE") or "").strip()
        status = (row.get("OBS_STATUS") or "").strip()
        if value_raw == "" or status in OMIT_STATUSES:
            omitted.append(period_token)
            continue
        if status != OBS_STATUS_OBSERVED:
            raise ValueError(f"{period_token}: observation status {status} is not observed")
        try:
            parsed = Decimal(value_raw)
        except InvalidOperation as exc:
            raise ValueError(f"{period_token}: non-numeric value") from exc
        if not parsed.is_finite():
            raise ValueError(f"{period_token}: non-finite value")
        previous = seen.get(period_start)
        if previous is not None:
            if Decimal(previous) != parsed:
                raise ValueError(
                    f"{period_token}: more than one value; this file is not classified "
                    "as a vintage panel",
                )
            continue
        seen[period_start] = value_raw
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
        raise ValueError("OECD CSV has no data rows")
    observations.sort(key=lambda item: item.period_start)
    return OecdCliParseResult(
        observations=tuple(observations),
        omitted_periods=tuple(omitted),
        series_key=SERIES_KEY,
        compiler_sentence=(
            f"{STRUCTURE_NAME}; {MEASURE_LABEL}; {METHODOLOGY_LABEL}; {ADJUSTMENT_LABEL}"
        ),
        unit=UNIT_TEXT,
        seasonal_adjustment="not stated",
        frequency=FREQUENCY_LABEL,
        vintage_class=VINTAGE_CLASS,
    )
