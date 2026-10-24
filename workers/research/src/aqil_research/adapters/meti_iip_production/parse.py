"""Parse the bound METI production sheet into EconomicObservation 1.0 rows."""

from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from io import BytesIO
from xml.etree import ElementTree

from aqil_research.adapters.meti_iip_production.constants import (
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
    SERIES_NAME,
    SHEET_NAME,
    SOURCE_ID,
    TITLE,
    UNIT_TEXT,
    VINTAGE_CLASS,
    WEIGHT_TEXT,
)
from aqil_research.adapters.meti_iip_production.stability import observation_id
from aqil_research.contracts.observation import (
    AvailabilityPrecision,
    EconomicObservation,
    Frequency,
    QualityStatus,
    SeasonalAdjustment,
    SeriesProvenance,
)

NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
REL_NS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
PKG_REL = "{http://schemas.openxmlformats.org/package/2006/relationships}"
OBSERVATION_ADAPTER_VERSION = f"{ADAPTER_ID}:{ADAPTER_VERSION}"
MONTH_HEADER = re.compile(r"^(?:P)?(\d{4})(0[1-9]|1[0-2])$")
OMITTED_TOKENS = frozenset({"", "***", "X", "x", "-", "－"})

_Grid = dict[tuple[int, int], str]


@dataclass(frozen=True, slots=True)
class MetiIipParseResult:
    observations: tuple[EconomicObservation, ...]
    omitted_periods: tuple[str, ...]
    series_key: str
    compiler_sentence: str
    unit: str
    seasonal_adjustment: str
    frequency: str
    vintage_class: str


def parse_meti_iip_workbook(
    payload: bytes,
    *,
    retrieved_at: datetime,
) -> MetiIipParseResult:
    """Map the production sheet to observations. Blank and suppressed months are omitted."""
    grid = _production_grid(payload)
    title = grid.get((1, 1), "")
    if title != TITLE:
        raise ValueError(
            f"production sheet title is {title or 'blank'}; refusing a workbook that is not "
            f"the seasonally adjusted monthly value-added production index",
        )
    header_row = _header_row(grid)
    code_row = header_row - 1
    if grid.get((code_row, 3), "") != "時系列コード":
        raise ValueError("production sheet is missing the monthly series-code row")
    item_row = _item_row(grid, header_row)
    observations: list[EconomicObservation] = []
    omitted: list[str] = []
    seen_values: dict[date, str] = {}
    month_columns = sorted(col for (row, col) in grid if row == header_row and col >= 4)
    if not month_columns:
        raise ValueError("production sheet has no monthly columns")
    for column in month_columns:
        period_token = grid.get((header_row, column), "").strip()
        period_start = _month_start(period_token)
        if period_start is None:
            raise ValueError(
                f"unparseable monthly period {period_token or 'blank'}; "
                "fiscal-year and quarterly columns are not this series",
            )
        expected_code = _month_code(period_start)
        actual_code = grid.get((code_row, column), "").strip()
        if actual_code != expected_code:
            raise ValueError(
                f"{period_token}: series code is {actual_code or 'blank'}; "
                f"refusing a column that is not {expected_code}",
            )
        value_raw = grid.get((item_row, column), "").strip()
        if value_raw in OMITTED_TOKENS:
            omitted.append(period_start.isoformat())
            continue
        stored = _one_decimal(value_raw, period_start)
        previous = seen_values.get(period_start)
        if previous is not None:
            if Decimal(previous) != Decimal(stored):
                raise ValueError(
                    f"{period_token}: more than one value; this file is not classified "
                    "as a vintage panel",
                )
            continue
        seen_values[period_start] = stored
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
                seasonal_adjustment=SeasonalAdjustment.SEASONALLY_ADJUSTED,
                raw_value=stored,
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
    if not observations:
        raise ValueError("production sheet has no 鉱工業 values")
    observations.sort(key=lambda item: item.period_start)
    return MetiIipParseResult(
        observations=tuple(observations),
        omitted_periods=tuple(omitted),
        series_key=SERIES_KEY,
        compiler_sentence=TITLE,
        unit=UNIT_TEXT,
        seasonal_adjustment=SEASONAL_ADJUSTMENT_LABEL,
        frequency=FREQUENCY_LABEL,
        vintage_class=VINTAGE_CLASS,
    )


def _production_grid(payload: bytes) -> _Grid:
    try:
        archive = zipfile.ZipFile(BytesIO(payload))
    except zipfile.BadZipFile as exc:
        raise ValueError("METI workbook is not an xlsx file") from exc
    sheet_path = _sheet_path(archive, SHEET_NAME)
    shared = _shared_strings(archive)
    root = ElementTree.fromstring(archive.read(sheet_path))
    grid: _Grid = {}
    for cell in root.iter(f"{NS}c"):
        ref = cell.attrib.get("r")
        if not ref:
            continue
        column, row = _column_row(ref)
        grid[(row, column)] = _cell_text(cell, shared)
    return grid


def _sheet_path(archive: zipfile.ZipFile, sheet_name: str) -> str:
    workbook = ElementTree.fromstring(archive.read("xl/workbook.xml"))
    relation_id = ""
    for sheet in workbook.findall(f"{NS}sheets/{NS}sheet"):
        if sheet.attrib.get("name") == sheet_name:
            relation_id = sheet.attrib.get(f"{REL_NS}id", "")
            break
    if not relation_id:
        raise ValueError(
            f"workbook has no {sheet_name} sheet; refusing shipments, inventories, "
            "and other indices",
        )
    rels = ElementTree.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    target = ""
    for rel in rels.findall(f"{PKG_REL}Relationship"):
        if rel.attrib.get("Id") == relation_id:
            target = rel.attrib.get("Target", "")
            break
    if not target or target.startswith(".."):
        raise ValueError("production sheet target is not inside the workbook")
    path = target if target.startswith("xl/") else f"xl/{target.lstrip('/')}"
    if path not in archive.namelist():
        raise ValueError("production sheet is missing from the workbook")
    return path


def _shared_strings(archive: zipfile.ZipFile) -> tuple[str, ...]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return ()
    root = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
    values: list[str] = []
    for item in root.findall(f"{NS}si"):
        values.append("".join(text.text or "" for text in item.iter(f"{NS}t")))
    return tuple(values)


def _cell_text(cell: ElementTree.Element, shared: tuple[str, ...]) -> str:
    kind = cell.attrib.get("t")
    if kind == "inlineStr":
        return "".join(text.text or "" for text in cell.iter(f"{NS}t")).strip()
    value = cell.find(f"{NS}v")
    if value is None or value.text is None:
        return ""
    if kind == "s":
        return shared[int(value.text)].strip()
    return value.text.strip()


def _column_row(ref: str) -> tuple[int, int]:
    letters = ""
    digits = ""
    for char in ref:
        if char.isalpha():
            letters += char
        elif char.isdigit():
            digits += char
    if not letters or not digits:
        raise ValueError(f"unparseable cell reference {ref}")
    column = 0
    for char in letters.upper():
        column = column * 26 + (ord(char) - 64)
    return column, int(digits)


def _header_row(grid: _Grid) -> int:
    rows = {row for (row, column) in grid if column == 1 and grid[(row, column)] == "品目番号"}
    if len(rows) != 1:
        raise ValueError("production sheet does not have one item-number header")
    row = next(iter(rows))
    if grid.get((row, 2), "") != "品目名称" or grid.get((row, 3), "") != "付加生産ウエイト":
        raise ValueError("production sheet header is not the value-added production layout")
    return row


def _item_row(grid: _Grid, header_row: int) -> int:
    matches = [
        row
        for (row, column) in grid
        if column == 1 and row > header_row and grid[(row, column)] == SERIES_KEY
    ]
    if len(matches) != 1:
        raise ValueError(
            f"refusing a sheet that does not contain exactly one {SERIES_NAME} row {SERIES_KEY}",
        )
    row = matches[0]
    name = grid.get((row, 2), "")
    weight = grid.get((row, 3), "")
    if name != SERIES_NAME or not _same_weight(weight):
        raise ValueError(
            f"item {SERIES_KEY} is {name or 'blank'} with weight {weight or 'blank'}; "
            f"refusing a series that is not {SERIES_NAME}",
        )
    return row


def _same_weight(value: str) -> bool:
    try:
        return Decimal(value) == Decimal(WEIGHT_TEXT)
    except InvalidOperation:
        return False


def _month_start(period: str) -> date | None:
    if any(token in period for token in ("FY", "CY", "Q")):
        return None
    match = MONTH_HEADER.match(period)
    if match is None:
        return None
    return date(int(match.group(1)), int(match.group(2)), 1)


def _month_code(period_start: date) -> str:
    month = f"{period_start.month:02d}"
    return f"{period_start.year}00{month}{month}"


def _one_decimal(value: str, period_start: date) -> str:
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError(f"{period_start.isoformat()}: non-numeric value") from exc
    if not parsed.is_finite():
        raise ValueError(f"{period_start.isoformat()}: non-finite value")
    published = parsed.quantize(Decimal("0.1"))
    if published != parsed:
        raise ValueError(
            f"{period_start.isoformat()}: value has more than one decimal place; "
            "this sheet publishes the index to one decimal place",
        )
    return f"{published:.1f}"
