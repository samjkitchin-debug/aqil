"""Parse the bound machinery-orders workbook into EconomicObservation 1.0 rows.

Only the sheet 季調・月次 is read. The fiscal-year and calendar-year sheet is ignored.
"""

from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from xml.etree import ElementTree

from aqil_research.adapters.cao_mo_private_ex_volatile.constants import (
    ADAPTER_ID,
    ADAPTER_VERSION,
    CALENDAR_BASIS,
    CATALOGUE_URL,
    COLUMN,
    DATASET_ID,
    FIRST_DATA_ROW,
    FREQUENCY_LABEL,
    GEOGRAPHY,
    HEADER_EN_MARK,
    HEADER_JA_MARK,
    PROVIDER_ID,
    RIGHTS_RECORD_ID,
    SEASONAL_ADJUSTMENT_LABEL,
    SERIES_KEY,
    SHEET_NAME,
    SOURCE_ID,
    TITLE_EN_MARK,
    TITLE_JA,
    UNIT_MARK,
    UNIT_TEXT,
    VINTAGE_CLASS,
)
from aqil_research.adapters.cao_mo_private_ex_volatile.stability import observation_id
from aqil_research.contracts.observation import (
    AvailabilityPrecision,
    EconomicObservation,
    Frequency,
    QualityStatus,
    SeasonalAdjustment,
    SeriesProvenance,
)

OBSERVATION_ADAPTER_VERSION = f"{ADAPTER_ID}:{ADAPTER_VERSION}"
MAIN_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
REL_NS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
PACKAGE_REL = "{http://schemas.openxmlformats.org/package/2006/relationships}"
CELL_REF = re.compile(r"^([A-Z]+)(\d+)$")


@dataclass(frozen=True, slots=True)
class CaoMoParseResult:
    observations: tuple[EconomicObservation, ...]
    omitted_periods: tuple[str, ...]
    series_key: str
    unit: str
    seasonal_adjustment: str
    frequency: str
    calendar_basis: str
    vintage_class: str


def parse_cao_mo_workbook(
    payload: bytes,
    *,
    retrieved_at: datetime,
    source_locator: str = CATALOGUE_URL,
) -> CaoMoParseResult:
    """Map column J on the seasonally adjusted monthly sheet. Blank months are omitted."""
    cells = _bound_sheet_cells(payload)
    _require_identity(cells)
    observations: list[EconomicObservation] = []
    omitted: list[str] = []
    seen_values: dict[date, str] = {}
    seen_period = False
    for row_number in sorted(_row_numbers(cells)):
        if row_number < FIRST_DATA_ROW:
            continue
        year_token = _text(cells, "B", row_number)
        month_token = _text(cells, "C", row_number)
        value_token = _text(cells, COLUMN, row_number)
        if year_token == "" and month_token == "" and value_token == "":
            continue
        if value_token == "" and not re.fullmatch(r"\d{4}", year_token):
            continue
        period_start = _calendar_month(year_token, month_token, row_number)
        seen_period = True
        period_label = period_start.strftime("%Y-%m")
        if value_token == "":
            omitted.append(period_label)
            continue
        token = _decimal_token(period_label, value_token)
        previous = seen_values.get(period_start)
        if previous is not None:
            if Decimal(previous) != Decimal(token):
                raise ValueError(
                    f"{period_label}: more than one value; this file is not classified "
                    "as a vintage panel",
                )
            continue
        seen_values[period_start] = token
        vintage = retrieved_at.date()
        observations.append(
            _observation(period_start, token, vintage, retrieved_at, source_locator),
        )
    if not seen_period:
        raise ValueError("machinery-orders sheet has no monthly rows")
    if not observations:
        raise ValueError("machinery-orders sheet has no observed months")
    observations.sort(key=lambda item: item.period_start)
    return CaoMoParseResult(
        observations=tuple(observations),
        omitted_periods=tuple(omitted),
        series_key=SERIES_KEY,
        unit=UNIT_TEXT,
        seasonal_adjustment=SEASONAL_ADJUSTMENT_LABEL,
        frequency=FREQUENCY_LABEL,
        calendar_basis=CALENDAR_BASIS,
        vintage_class=VINTAGE_CLASS,
    )


def _bound_sheet_cells(payload: bytes) -> dict[tuple[str, int], str]:
    try:
        with zipfile.ZipFile(io_bytes(payload)) as book:
            sheet_path = _sheet_path(book, SHEET_NAME)
            shared = _shared_strings(book)
            sheet = ElementTree.fromstring(book.read(sheet_path))
    except (zipfile.BadZipFile, KeyError, ElementTree.ParseError) as exc:
        raise ValueError("machinery-orders workbook could not be read") from exc
    return _cells(sheet, shared)


def io_bytes(payload: bytes):
    import io

    return io.BytesIO(payload)


def _sheet_path(book: zipfile.ZipFile, sheet_name: str) -> str:
    workbook = ElementTree.fromstring(book.read("xl/workbook.xml"))
    rels = ElementTree.fromstring(book.read("xl/_rels/workbook.xml.rels"))
    targets = {
        node.attrib.get("Id", ""): node.attrib.get("Target", "")
        for node in rels.findall(f"{PACKAGE_REL}Relationship")
    }
    for sheet in workbook.findall(f"{MAIN_NS}sheets/{MAIN_NS}sheet"):
        if sheet.attrib.get("name") != sheet_name:
            continue
        relation_id = sheet.attrib.get(f"{REL_NS}id", "")
        target = targets.get(relation_id, "")
        if not target:
            break
        normalised = target.lstrip("/")
        if not normalised.startswith("xl/"):
            normalised = f"xl/{normalised}"
        return normalised
    raise ValueError(f"refusing a workbook without the sheet {SHEET_NAME}")


def _shared_strings(book: zipfile.ZipFile) -> tuple[str, ...]:
    if "xl/sharedStrings.xml" not in book.namelist():
        return ()
    root = ElementTree.fromstring(book.read("xl/sharedStrings.xml"))
    strings: list[str] = []
    for item in root.findall(f"{MAIN_NS}si"):
        parts = [node.text or "" for node in item.iter(f"{MAIN_NS}t")]
        strings.append("".join(parts))
    return tuple(strings)


def _cells(
    sheet: ElementTree.Element,
    shared: tuple[str, ...],
) -> dict[tuple[str, int], str]:
    found: dict[tuple[str, int], str] = {}
    for cell in sheet.iter(f"{MAIN_NS}c"):
        ref = cell.attrib.get("r", "")
        match = CELL_REF.match(ref)
        if match is None:
            continue
        column, row_text = match.groups()
        found[(column, int(row_text))] = _cell_text(cell, shared)
    return found


def _cell_text(cell: ElementTree.Element, shared: tuple[str, ...]) -> str:
    kind = cell.attrib.get("t")
    value = cell.find(f"{MAIN_NS}v")
    if kind == "s" and value is not None and value.text:
        index = int(value.text)
        if index < 0 or index >= len(shared):
            raise ValueError("machinery-orders shared string is out of range")
        return shared[index].strip()
    if kind == "inlineStr":
        inline = cell.find(f"{MAIN_NS}is")
        if inline is None:
            return ""
        return "".join(node.text or "" for node in inline.iter(f"{MAIN_NS}t")).strip()
    if value is None or value.text is None:
        return ""
    return value.text.strip()


def _require_identity(cells: dict[tuple[str, int], str]) -> None:
    if _text(cells, "D", 2) != TITLE_JA:
        raise ValueError(
            "refusing a sheet whose title is not the seasonally adjusted monthly orders series",
        )
    if TITLE_EN_MARK not in _text(cells, "D", 3):
        raise ValueError("refusing a sheet that is not marked seasonally adjusted and monthly")
    if UNIT_MARK not in _row_text(cells, 2):
        raise ValueError("refusing a sheet that is not marked in million yen")
    japanese = _text(cells, COLUMN, 5) + _text(cells, COLUMN, 6)
    english = _text(cells, COLUMN, 8) + _text(cells, COLUMN, 9)
    if HEADER_JA_MARK not in japanese or HEADER_EN_MARK not in english:
        raise ValueError(
            "refusing a sheet whose column J is not private demand excluding volatile orders",
        )


def _row_text(cells: dict[tuple[str, int], str], row_number: int) -> str:
    return " ".join(value for (column, row), value in cells.items() if row == row_number)


def _text(cells: dict[tuple[str, int], str], column: str, row_number: int) -> str:
    return cells.get((column, row_number), "").strip()


def _row_numbers(cells: dict[tuple[str, int], str]) -> set[int]:
    return {row for _column, row in cells}


def _calendar_month(year_token: str, month_token: str, row_number: int) -> date:
    if not re.fullmatch(r"\d{4}", year_token) or not re.fullmatch(r"\d{1,2}", month_token):
        raise ValueError(
            f"row {row_number}: expected a calendar year and month, not a fiscal-year label",
        )
    year = int(year_token)
    month = int(month_token)
    if month < 1 or month > 12:
        raise ValueError(f"row {row_number}: month {month_token} is not a calendar month")
    return date(year, month, 1)


def _decimal_token(period: str, value_raw: str) -> str:
    try:
        parsed = Decimal(value_raw)
    except InvalidOperation as exc:
        raise ValueError(f"{period}: non-numeric value") from exc
    if not parsed.is_finite():
        raise ValueError(f"{period}: non-finite value")
    rendered = format(parsed, "f")
    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")
    return rendered


def _observation(
    period_start: date,
    token: str,
    vintage: date,
    retrieved_at: datetime,
    source_locator: str,
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
        seasonal_adjustment=SeasonalAdjustment.SEASONALLY_ADJUSTED,
        raw_value=token,
        quality_status=QualityStatus.OBSERVED,
        series_provenance=SeriesProvenance.LATEST_REVISED,
        provider_vintage_date=vintage,
        source_release_at=retrieved_at,
        earliest_model_available_at=None,
        availability_precision=AvailabilityPrecision.UNKNOWN,
        retrieved_at=retrieved_at,
        first_seen_at=retrieved_at,
        source_locator=source_locator,
        adapter_version=OBSERVATION_ADAPTER_VERSION,
    )
