"""Parse the bound ECB deposit-facility CSV into EconomicObservation 1.0 rows."""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from aqil_research.adapters.ecb_fm_dfr.constants import (
    ACCESS_URL,
    ADAPTER_ID,
    ADAPTER_VERSION,
    COMPILER_SENTENCE,
    COMPILING_ORG,
    CURRENCY,
    DATA_TYPE_FM,
    DATASET_ID,
    FREQ_CODE,
    FREQUENCY_LABEL,
    GEOGRAPHY,
    INSTRUMENT_FM,
    PROVIDER_FM,
    PROVIDER_FM_ID,
    PROVIDER_ID,
    REF_AREA,
    RIGHTS_RECORD_ID,
    SERIES_KEY,
    SOURCE_ID,
    TITLE,
    UNIT_CODE,
    UNIT_MULT,
    UNIT_TEXT,
    VINTAGE_CLASS,
)
from aqil_research.adapters.ecb_fm_dfr.stability import observation_id
from aqil_research.contracts.observation import (
    AvailabilityPrecision,
    EconomicObservation,
    Frequency,
    QualityStatus,
    SeasonalAdjustment,
    SeriesProvenance,
)

OBSERVATION_ADAPTER_VERSION = f"{ADAPTER_ID}:{ADAPTER_VERSION}"
MISSING_STATUSES = frozenset({"M"})
DAY_PERIOD = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")

_IDENTITY_COLUMNS: tuple[tuple[str, str], ...] = (
    ("KEY", SERIES_KEY),
    ("FREQ", FREQ_CODE),
    ("REF_AREA", REF_AREA),
    ("CURRENCY", CURRENCY),
    ("PROVIDER_FM", PROVIDER_FM),
    ("INSTRUMENT_FM", INSTRUMENT_FM),
    ("PROVIDER_FM_ID", PROVIDER_FM_ID),
    ("DATA_TYPE_FM", DATA_TYPE_FM),
    ("COMPILING_ORG", COMPILING_ORG),
    ("TITLE", TITLE),
    ("TITLE_COMPL", COMPILER_SENTENCE),
    ("UNIT", UNIT_CODE),
    ("UNIT_MULT", UNIT_MULT),
)
REQUIRED_COLUMNS = tuple(column for column, _expected in _IDENTITY_COLUMNS) + (
    "TIME_PERIOD",
    "OBS_VALUE",
)


@dataclass(frozen=True, slots=True)
class EcbFmDfrParseResult:
    observations: tuple[EconomicObservation, ...]
    omitted_periods: tuple[str, ...]
    series_key: str
    compiler_sentence: str
    unit: str
    seasonal_adjustment: str
    frequency: str
    vintage_class: str


def parse_ecb_fm_dfr_csv(text: str, *, retrieved_at: datetime) -> EcbFmDfrParseResult:
    """Map the current CSV to observations. Missing days are omitted, not filled."""
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        raise ValueError("ECB CSV has no header")
    reader.fieldnames = [name.strip() if name else "" for name in reader.fieldnames]
    missing = [column for column in REQUIRED_COLUMNS if column not in reader.fieldnames]
    if missing:
        raise ValueError(f"ECB CSV is missing columns: {', '.join(missing)}")

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
        period_start = _day(period_token)
        if period_start is None:
            raise ValueError(f"unparseable daily period {period_token}")
        value_raw = (row.get("OBS_VALUE") or "").strip()
        status = (row.get("OBS_STATUS") or "").strip()
        if value_raw == "" or status in MISSING_STATUSES:
            omitted.append(period_token)
            continue
        try:
            parsed = Decimal(value_raw)
        except InvalidOperation as exc:
            raise ValueError(f"{period_token}: non-numeric value") from exc
        if not parsed.is_finite():
            raise ValueError(f"{period_token}: non-finite value")
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
        raise ValueError("ECB CSV has no data rows")
    observations.sort(key=lambda item: item.period_start)
    return EcbFmDfrParseResult(
        observations=tuple(observations),
        omitted_periods=tuple(omitted),
        series_key=SERIES_KEY,
        compiler_sentence=COMPILER_SENTENCE,
        unit=UNIT_TEXT,
        seasonal_adjustment="not stated on the file",
        frequency=FREQUENCY_LABEL,
        vintage_class=VINTAGE_CLASS,
    )


def _require_bound_series(row: dict[str, str | None]) -> None:
    for column, expected in _IDENTITY_COLUMNS:
        actual = (row.get(column) or "").strip()
        if actual != expected:
            raise ValueError(
                f"{column} is {actual or 'blank'}; refusing a series that is not "
                f"the ECB deposit facility {SERIES_KEY}",
            )
    sentence = row.get("TITLE_COMPL") or ""
    if "European Central Bank" not in sentence and "ECB" not in sentence and "ESCB" not in sentence:
        raise ValueError("response metadata does not name the ECB or ESCB as compiler")


def _day(period: str) -> date | None:
    match = DAY_PERIOD.match(period)
    if match is None:
        return None
    year = int(match.group(1))
    month = int(match.group(2))
    day = int(match.group(3))
    try:
        return date(year, month, day)
    except ValueError:
        return None
