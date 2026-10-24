"""Parse the bound BIS global-liquidity CSV into EconomicObservation 1.0 rows."""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from aqil_research.adapters.bis_gli.constants import (
    ACCESS_URL,
    ADAPTER_ID,
    ADAPTER_VERSION,
    BORROWERS_CTY,
    BORROWERS_SECTOR,
    CURR_DENOM,
    DATAFLOW,
    DATASET_ID,
    FREQ_CODE,
    FREQUENCY_LABEL,
    GEOGRAPHY,
    INSTRUMENT,
    LENDERS_SECTOR,
    OBS_CONF_FREE,
    OBS_STATUS_OBSERVED,
    POSITION_TYPE,
    PROVIDER_ID,
    RIGHTS_RECORD_ID,
    SERIES_KEY,
    SOURCE_ID,
    TITLE,
    UNIT_MEASURE,
    UNIT_MULT,
    UNIT_TEXT,
    VINTAGE_CLASS,
)
from aqil_research.adapters.bis_gli.stability import observation_id
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
QUARTER_PERIOD = re.compile(r"^(\d{4})-Q([1-4])$")
QUARTER_ENDS = {1: (3, 31), 2: (6, 30), 3: (9, 30), 4: (12, 31)}

_IDENTITY_COLUMNS: tuple[tuple[str, str], ...] = (
    ("DATAFLOW", DATAFLOW),
    ("FREQ", FREQ_CODE),
    ("CURR_DENOM", CURR_DENOM),
    ("BORROWERS_CTY", BORROWERS_CTY),
    ("BORROWERS_SECTOR", BORROWERS_SECTOR),
    ("LENDERS_SECTOR", LENDERS_SECTOR),
    ("L_POS_TYPE", POSITION_TYPE),
    ("L_INSTR", INSTRUMENT),
    ("UNIT_MEASURE", UNIT_MEASURE),
    ("TITLE", TITLE),
    ("UNIT_MULT", UNIT_MULT),
)
REQUIRED_COLUMNS = tuple(column for column, _expected in _IDENTITY_COLUMNS) + (
    "TIME_PERIOD",
    "OBS_VALUE",
    "OBS_STATUS",
    "OBS_CONF",
)


@dataclass(frozen=True, slots=True)
class BisGliParseResult:
    observations: tuple[EconomicObservation, ...]
    omitted_periods: tuple[str, ...]
    series_key: str
    compiler_sentence: str
    unit: str
    seasonal_adjustment: str
    frequency: str
    vintage_class: str


def parse_bis_gli_csv(text: str, *, retrieved_at: datetime) -> BisGliParseResult:
    """Map the current CSV to observations. Blank quarters are omitted, not filled."""
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        raise ValueError("BIS CSV has no header")
    reader.fieldnames = [name.strip() if name else "" for name in reader.fieldnames]
    missing = [column for column in REQUIRED_COLUMNS if column not in reader.fieldnames]
    if missing:
        joined = ", ".join(missing)
        raise ValueError(f"BIS CSV is missing columns: {joined}")

    observations: list[EconomicObservation] = []
    omitted: list[str] = []
    seen_values: dict[date, str] = {}
    data_rows = 0
    for row in reader:
        if not any((value or "").strip() for value in row.values()):
            continue
        data_rows += 1
        _require_bound_series(row)
        period_token = (row.get("TIME_PERIOD") or "").strip()
        period_start, period_end = _quarter_bounds(period_token)
        if period_start is None or period_end is None:
            raise ValueError(f"unparseable quarterly period {period_token}")
        value_raw = (row.get("OBS_VALUE") or "").strip()
        status = (row.get("OBS_STATUS") or "").strip()
        if value_raw == "" or status in OMIT_STATUSES:
            omitted.append(period_token)
            continue
        if status != OBS_STATUS_OBSERVED:
            raise ValueError(f"{period_token}: observation status {status} is not observed")
        confidential = (row.get("OBS_CONF") or "").strip()
        if confidential != OBS_CONF_FREE:
            raise ValueError(f"{period_token}: observation is not marked free")
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
                period_end=period_end,
                frequency=Frequency.QUARTERLY,
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
        raise ValueError("BIS CSV has no data rows")
    observations.sort(key=lambda item: item.period_start)
    return BisGliParseResult(
        observations=tuple(observations),
        omitted_periods=tuple(omitted),
        series_key=SERIES_KEY,
        compiler_sentence=TITLE,
        unit=UNIT_TEXT,
        seasonal_adjustment="not stated",
        frequency=FREQUENCY_LABEL,
        vintage_class=VINTAGE_CLASS,
    )


def _require_bound_series(row: dict[str, str | None]) -> None:
    for column, expected in _IDENTITY_COLUMNS:
        actual = (row.get(column) or "").strip()
        if actual != expected:
            raise ValueError(
                f"{column} is {actual or 'blank'}; refusing a series that is not "
                f"the BIS credit series {SERIES_KEY}",
            )


def _finite_decimal(period: str, value_raw: str) -> Decimal:
    try:
        parsed = Decimal(value_raw)
    except InvalidOperation as exc:
        raise ValueError(f"{period}: non-numeric value") from exc
    if not parsed.is_finite():
        raise ValueError(f"{period}: non-finite value")
    return parsed


def _quarter_bounds(period: str) -> tuple[date | None, date | None]:
    match = QUARTER_PERIOD.match(period)
    if match is None:
        return None, None
    year = int(match.group(1))
    quarter = int(match.group(2))
    end_month, end_day = QUARTER_ENDS[quarter]
    start_month = (quarter - 1) * 3 + 1
    return date(year, start_month, 1), date(year, end_month, end_day)
