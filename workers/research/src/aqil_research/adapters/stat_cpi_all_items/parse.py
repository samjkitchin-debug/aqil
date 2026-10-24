"""Parse the bound Statistics Bureau CPI CSV into EconomicObservation 1.0 rows."""

from __future__ import annotations

import csv
import io
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from aqil_research.adapters.stat_cpi_all_items.constants import (
    ACCESS_URL,
    ADAPTER_ID,
    ADAPTER_VERSION,
    CALENDAR_BASIS,
    CODE_HEADER_MARK,
    DATASET_ID,
    ENGLISH_HEADER,
    FREQUENCY_LABEL,
    GEOGRAPHY,
    ITEM_CODE,
    ITEM_EN,
    ITEM_JA,
    JAPANESE_HEADER,
    PROVIDER_ID,
    RIGHTS_RECORD_ID,
    SEASONAL_ADJUSTMENT_LABEL,
    SOURCE_ID,
    UNIT_TEXT,
    VINTAGE_CLASS,
)
from aqil_research.adapters.stat_cpi_all_items.stability import observation_id
from aqil_research.contracts.observation import (
    AvailabilityPrecision,
    EconomicObservation,
    Frequency,
    QualityStatus,
    SeasonalAdjustment,
    SeriesProvenance,
)

OBSERVATION_ADAPTER_VERSION = f"{ADAPTER_ID}:{ADAPTER_VERSION}"
MONTH_PERIOD = re.compile(r"^(\d{4})(\d{2})$")
SEASONAL_MARKERS = ("季節調整", "seasonally adjusted")


@dataclass(frozen=True, slots=True)
class StatCpiParseResult:
    observations: tuple[EconomicObservation, ...]
    omitted_periods: tuple[str, ...]
    series_key: str
    unit: str
    seasonal_adjustment: str
    frequency: str
    calendar_basis: str
    vintage_class: str


def parse_stat_cpi_csv(
    payload: bytes | str,
    *,
    retrieved_at: datetime,
) -> StatCpiParseResult:
    """Map group code 0001 to observations. Blank months are omitted, not filled."""
    text = _decode(payload)
    rows = list(csv.reader(io.StringIO(text)))
    if not rows:
        raise ValueError("CPI CSV has no rows")
    japanese_index = _one_row(rows, lambda label: label == JAPANESE_HEADER, "Japanese header")
    english_index = _one_row(rows, lambda label: label == ENGLISH_HEADER, "English header")
    code_index = _one_row(rows, lambda label: CODE_HEADER_MARK in label, "code header")
    _refuse_seasonal_marker(rows[japanese_index], rows[english_index], rows[code_index])
    column = _bound_column(rows[japanese_index], rows[english_index], rows[code_index])

    observations: list[EconomicObservation] = []
    omitted: list[str] = []
    seen_values: dict[date, str] = {}
    seen_period = False
    for row in rows[code_index + 1 :]:
        label = row[0].strip() if row else ""
        if label == "":
            continue
        period_start = _month_start(label)
        if period_start is None:
            if seen_period:
                raise ValueError(f"unexpected row after monthly observations: {label}")
            continue
        seen_period = True
        value_raw = row[column].strip() if column < len(row) else ""
        if value_raw == "":
            omitted.append(label)
            continue
        token = _decimal_token(label, value_raw)
        previous = seen_values.get(period_start)
        if previous is not None:
            if Decimal(previous) != Decimal(token):
                raise ValueError(
                    f"{label}: more than one value; this file is not classified as a vintage panel",
                )
            continue
        seen_values[period_start] = token
        vintage = retrieved_at.date()
        observations.append(_observation(period_start, token, vintage, retrieved_at))
    if not seen_period:
        raise ValueError("CPI CSV has no monthly rows")
    if not observations:
        raise ValueError("CPI CSV has no observed months")
    observations.sort(key=lambda item: item.period_start)
    return StatCpiParseResult(
        observations=tuple(observations),
        omitted_periods=tuple(omitted),
        series_key=ITEM_CODE,
        unit=UNIT_TEXT,
        seasonal_adjustment=SEASONAL_ADJUSTMENT_LABEL,
        frequency=FREQUENCY_LABEL,
        calendar_basis=CALENDAR_BASIS,
        vintage_class=VINTAGE_CLASS,
    )


def _decode(payload: bytes | str) -> str:
    if isinstance(payload, str):
        return payload
    try:
        return payload.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            return payload.decode("cp932")
        except UnicodeDecodeError as exc:
            raise ValueError("CPI CSV is not UTF-8 or CP932") from exc


def _one_row(
    rows: list[list[str]],
    predicate: Callable[[str], bool],
    label: str,
) -> int:
    matches = [index for index, row in enumerate(rows) if row and predicate((row[0] or "").strip())]
    if len(matches) != 1:
        raise ValueError(f"CPI CSV {label} count is {len(matches)}")
    return matches[0]


def _refuse_seasonal_marker(*header_rows: list[str]) -> None:
    for row in header_rows:
        for cell in row:
            lowered = cell.lower()
            if any(marker in cell or marker in lowered for marker in SEASONAL_MARKERS):
                raise ValueError(
                    "refusing a CPI file marked as seasonally adjusted; "
                    "this package is bound to the unadjusted item price index",
                )


def _bound_column(japanese: list[str], english: list[str], codes: list[str]) -> int:
    width = max(len(japanese), len(english), len(codes))
    bound: list[int] = []
    for index in range(width):
        item_ja = _cell(japanese, index)
        item_en = _cell(english, index)
        code = _cell(codes, index)
        if code == ITEM_CODE and item_ja == ITEM_JA and item_en == ITEM_EN:
            bound.append(index)
    if len(bound) != 1:
        raise ValueError(
            f"refusing a CPI file that does not contain exactly one {ITEM_EN} "
            f"column with code {ITEM_CODE}",
        )
    return bound[0]


def _cell(row: list[str], index: int) -> str:
    if index >= len(row):
        return ""
    return row[index].strip()


def _month_start(period: str) -> date | None:
    match = MONTH_PERIOD.match(period)
    if match is None:
        return None
    year = int(match.group(1))
    month = int(match.group(2))
    if month < 1 or month > 12:
        return None
    return date(year, month, 1)


def _decimal_token(period: str, value_raw: str) -> str:
    try:
        parsed = Decimal(value_raw)
    except InvalidOperation as exc:
        raise ValueError(f"{period}: non-numeric value") from exc
    if not parsed.is_finite():
        raise ValueError(f"{period}: non-finite value")
    return value_raw


def _observation(
    period_start: date,
    token: str,
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
        raw_value=token,
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
