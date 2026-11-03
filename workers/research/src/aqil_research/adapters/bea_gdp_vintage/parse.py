"""Parse the official BEA GDP and GDI vintage-history workbook.

The stored column is Real GDP under "Percent change from preceding period".
It is not Table 1.1.6 account A191RX and it is not a chained-dollar level.
A cell of dots is an unpublished estimate, not a zero.
"""

from __future__ import annotations

import calendar
import hashlib
import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from io import BytesIO
from xml.etree import ElementTree as ET
from zipfile import ZipFile

NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
REL = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
PKG = "{http://schemas.openxmlformats.org/package/2006/relationships}"

DATASET_ID = "bea.vintage.real_gdp.pct_preceding"
SOURCE_ID = "bea_gdp_gdi_vintage_history"
WORKBOOK_URL = "https://apps.bea.gov/national/xls/gdp-gdi-vintage-history.xlsx"
UNIT = "percent_change_from_preceding_period"
ADAPTER_VERSION = "bea-gdp-vintage-0.1.0"

_QUARTER = re.compile(r"^(\d{4})Q([1-4])$")
_RELEASE_DATE = re.compile(r"^([A-Za-z]+ \d{1,2}, \d{4})\b")
_HEADER_LABELS = frozenset(
    {
        "vintage",
        "gdp",
        "gdi",
        "real gdp",
        "real gdi",
        "release date",
        "percent change",
        "from preceding period",
        "billions of current dollars",
    }
)


class VintageWorkbookError(ValueError):
    """The workbook is not the expected vintage history layout."""


@dataclass(frozen=True, slots=True)
class RealGdpVintagePoint:
    quarter_label: str
    period_start: date
    period_end: date
    vintage_label: str
    release_date: date
    raw_value: str


@dataclass(frozen=True, slots=True)
class RealGdpVintageWorkbook:
    updated_on: date | None
    description: str
    points: tuple[RealGdpVintagePoint, ...]
    skipped_unpublished: int

    @property
    def distinct_quarters(self) -> int:
        return len({point.period_start for point in self.points})

    @property
    def distinct_release_dates(self) -> int:
        return len({point.release_date for point in self.points})


def series_checksum(points: tuple[RealGdpVintagePoint, ...]) -> str:
    """Hash the printed quarter, release date, vintage label, and value."""
    lines = [
        "|".join(
            (
                point.quarter_label,
                point.release_date.isoformat(),
                point.vintage_label,
                point.raw_value,
            )
        )
        for point in sorted(
            points,
            key=lambda item: (item.period_start, item.release_date, item.vintage_label),
        )
    ]
    payload = ("\n".join(lines) + "\n").encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def release_date_boundary(release_date: date) -> datetime:
    """UTC midnight on the printed date.

    The workbook prints a calendar date and no clock time. This value is the
    identity anchor for that date. It is not an observed publication time.
    Availability stays date precision, so the as-of rule uses the next UTC day.
    """
    from datetime import UTC

    return datetime(release_date.year, release_date.month, release_date.day, tzinfo=UTC)


def parse_real_gdp_vintage_workbook(payload: bytes) -> RealGdpVintageWorkbook:
    if not payload.startswith(b"PK"):
        raise VintageWorkbookError("response was not a workbook")
    try:
        with ZipFile(BytesIO(payload)) as book:
            shared = _shared_strings(book)
            sheet_name = _sheet_name(book, "Vintage History")
            rows = _sheet_cells(book, sheet_name, shared)
    except VintageWorkbookError:
        raise
    except Exception as exc:
        raise VintageWorkbookError("vintage workbook could not be read") from exc
    return _interpret(rows)


def _shared_strings(book: ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in book.namelist():
        raise VintageWorkbookError("workbook has no shared strings")
    root = ET.fromstring(book.read("xl/sharedStrings.xml"))
    return [
        "".join((node.text or "") for node in item.iter(f"{NS}t"))
        for item in root.findall(f"{NS}si")
    ]


def _sheet_name(book: ZipFile, title: str) -> str:
    workbook = ET.fromstring(book.read("xl/workbook.xml"))
    rels = ET.fromstring(book.read("xl/_rels/workbook.xml.rels"))
    targets = {
        node.attrib["Id"]: node.attrib["Target"] for node in rels.findall(f"{PKG}Relationship")
    }
    for sheet in workbook.findall(f"{NS}sheets/{NS}sheet"):
        if sheet.attrib.get("name") != title:
            continue
        target = targets.get(sheet.attrib[f"{REL}id"])
        if target is None:
            break
        path = target if target.startswith("xl/") else f"xl/{target}"
        if path not in book.namelist():
            break
        return path
    raise VintageWorkbookError(f"workbook has no sheet named {title}")


def _column_index(letters: str) -> int:
    total = 0
    for letter in letters:
        total = total * 26 + (ord(letter.upper()) - 64)
    return total


def _sheet_cells(book: ZipFile, sheet: str, shared: list[str]) -> dict[int, dict[int, str]]:
    root = ET.fromstring(book.read(sheet))
    rows: dict[int, dict[int, str]] = {}
    for cell in root.iter(f"{NS}c"):
        ref = cell.get("r") or ""
        letters = "".join(ch for ch in ref if ch.isalpha())
        digits = "".join(ch for ch in ref if ch.isdigit())
        if not letters or not digits:
            continue
        node = cell.find(f"{NS}v")
        if node is None or node.text is None:
            inline = cell.find(f"{NS}is")
            if inline is None:
                continue
            value = "".join((item.text or "") for item in inline.iter(f"{NS}t"))
        elif cell.get("t") == "s":
            value = shared[int(node.text)]
        else:
            value = node.text
        rows.setdefault(int(digits), {})[_column_index(letters)] = value.strip()
    if not rows:
        raise VintageWorkbookError("vintage sheet has no cells")
    return rows


def _interpret(rows: dict[int, dict[int, str]]) -> RealGdpVintageWorkbook:
    updated_on: date | None = None
    description = ""
    quarter: tuple[str, date, date] | None = None
    points: list[RealGdpVintagePoint] = []
    seen: dict[tuple[date, date], RealGdpVintagePoint] = {}
    skipped = 0
    for index in sorted(rows):
        cells = rows[index]
        lead = cells.get(1, "")
        if lead.startswith("Last Updated "):
            updated_on = _parse_release_date(lead.removeprefix("Last Updated ").strip(), index)
            continue
        if "by publication" in lead.lower() and not description:
            description = lead
        quarter_match = _QUARTER.fullmatch(lead)
        if quarter_match:
            year = int(quarter_match.group(1))
            quarter_number = int(quarter_match.group(2))
            start_month = (quarter_number - 1) * 3 + 1
            end_month = start_month + 2
            quarter = (
                lead,
                date(year, start_month, 1),
                date(year, end_month, calendar.monthrange(year, end_month)[1]),
            )
            continue
        if quarter is None:
            continue
        label = cells.get(2, "")
        if not label or label.lower() in _HEADER_LABELS:
            continue
        release_text = cells.get(7, "")
        if not release_text:
            raise VintageWorkbookError(f"row {index} has vintage {label} and no release date")
        release_date = _parse_release_date(release_text, index)
        raw = cells.get(5, "")
        if _unpublished(raw):
            skipped += 1
            continue
        value = _decimal_text(raw, index)
        point = RealGdpVintagePoint(
            quarter_label=quarter[0],
            period_start=quarter[1],
            period_end=quarter[2],
            vintage_label=label,
            release_date=release_date,
            raw_value=value,
        )
        key = (point.period_start, point.release_date)
        existing = seen.get(key)
        if existing is None:
            seen[key] = point
            points.append(point)
            continue
        if existing.raw_value != point.raw_value or existing.vintage_label != point.vintage_label:
            raise VintageWorkbookError(
                f"{point.quarter_label} on {point.release_date.isoformat()} "
                "has two different real GDP vintages"
            )
    if not points:
        raise VintageWorkbookError("workbook contains no published real GDP vintages")
    if updated_on is None:
        raise VintageWorkbookError("workbook does not print a last-updated date")
    return RealGdpVintageWorkbook(
        updated_on=updated_on,
        description=description,
        points=tuple(points),
        skipped_unpublished=skipped,
    )


def _unpublished(value: str) -> bool:
    token = value.strip().lower()
    return token == "" or token == "na" or set(token) <= {"."}


def _decimal_text(value: str, row_index: int) -> str:
    token = value.replace(",", "").strip()
    if not re.fullmatch(r"-?\d+(\.\d+)?", token):
        raise VintageWorkbookError(f"row {row_index} real GDP value is not a decimal")
    try:
        parsed = Decimal(token)
    except InvalidOperation as exc:
        raise VintageWorkbookError(f"row {row_index} real GDP value is not a decimal") from exc
    if not parsed.is_finite():
        raise VintageWorkbookError(f"row {row_index} real GDP value is not finite")
    return token


def _parse_release_date(value: str, row_index: int) -> date:
    cleaned = re.sub(r"\s+", " ", value).strip()
    match = _RELEASE_DATE.match(cleaned)
    if match is None:
        raise VintageWorkbookError(f"row {row_index} release cell is not a printed date")
    text = match.group(1)
    for pattern in ("%b %d, %Y", "%B %d, %Y"):
        try:
            return datetime.strptime(text, pattern).date()
        except ValueError:
            continue
    raise VintageWorkbookError(f"row {row_index} release cell is not a printed date")
