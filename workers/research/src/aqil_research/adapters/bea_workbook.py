"""Parse the two official BEA workbook lines used by the 1988 refit."""

from __future__ import annotations

import zipfile
from dataclasses import dataclass
from datetime import date, datetime
from xml.etree import ElementTree as ET

NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


@dataclass(frozen=True, slots=True)
class BeaMonth:
    period_start: date
    value: str


def _shared_strings(book: zipfile.ZipFile) -> list[str]:
    root = ET.fromstring(book.read("xl/sharedStrings.xml"))
    values: list[str] = []
    for item in root.findall(f"{NS}si"):
        values.append("".join((node.text or "") for node in item.iter(f"{NS}t")))
    return values


def _column_index(letters: str) -> int:
    total = 0
    for letter in letters:
        total = total * 26 + (ord(letter) - 64)
    return total


def _sheet_cells(book: zipfile.ZipFile, sheet: str, shared: list[str]) -> dict[int, dict[int, str]]:
    root = ET.fromstring(book.read(sheet))
    rows: dict[int, dict[int, str]] = {}
    for cell in root.iter(f"{NS}c"):
        ref = cell.get("r") or ""
        letters = "".join(ch for ch in ref if ch.isalpha())
        row = int("".join(ch for ch in ref if ch.isdigit()))
        node = cell.find(f"{NS}v")
        if node is None or node.text is None:
            continue
        value = shared[int(node.text)] if cell.get("t") == "s" else node.text
        rows.setdefault(row, {})[_column_index(letters)] = value
    return rows


def _months(
    rows: dict[int, dict[int, str]], header_row: int, value_row: int, code: str
) -> tuple[BeaMonth, ...]:
    if rows[value_row].get(3) != code:
        raise ValueError(f"expected account {code}")
    series: list[BeaMonth] = []
    for index, label in rows[header_row].items():
        if index < 4 or "M" not in label:
            continue
        raw = rows[value_row].get(index)
        if raw in (None, "", "NA"):
            continue
        year, month = label.split("M")
        series.append(BeaMonth(date(int(year), int(month), 1), raw))
    if not series:
        raise ValueError(f"no months for {code}")
    return tuple(series)


def personal_income_ex_transfers(payload: bytes) -> tuple[BeaMonth, ...]:
    with zipfile.ZipFile(__import__("io").BytesIO(payload)) as book:
        shared = _shared_strings(book)
        rows = _sheet_cells(book, "xl/worksheets/sheet43.xml", shared)
    return _months(rows, 8, 45, "W875RX")


def manufacturing_trade_sales(payload: bytes) -> tuple[BeaMonth, ...]:
    with zipfile.ZipFile(__import__("io").BytesIO(payload)) as book:
        shared = _shared_strings(book)
        rows = _sheet_cells(book, "xl/worksheets/sheet18.xml", shared)
    return _months(rows, 8, 9, "KPMT")


@dataclass(frozen=True, slots=True)
class BeaRealGdp:
    """Table 1.1.6 line 1 as printed in the downloaded workbook."""

    sheet_name: str
    line_number: str
    account_code: str
    line_label: str
    unit_text: str
    published_on: date
    quarters: tuple[BeaMonth, ...]


def real_gross_domestic_product(payload: bytes) -> BeaRealGdp:
    """Bind sheet T10106-Q line 1 account A191RX, or refuse the workbook."""
    with zipfile.ZipFile(__import__("io").BytesIO(payload)) as book:
        shared = _shared_strings(book)
        sheet_path = _sheet_path(book, "T10106-Q")
        rows = _sheet_cells(book, sheet_path, shared)
    title = rows.get(1, {}).get(1, "")
    units = rows.get(2, {}).get(1, "")
    if title != "Table 1.1.6. Real Gross Domestic Product, Chained Dollars":
        raise ValueError("workbook is not Table 1.1.6 real gross domestic product")
    if units != "[Millions of chained (2017) dollars] Seasonally adjusted at annual rates":
        raise ValueError("Table 1.1.6 units or seasonal adjustment were not repeated")
    published = _published_on(rows)
    value_row = _gdp_line(rows)
    quarters = _quarters(rows, 8, value_row)
    if not quarters:
        raise ValueError("Table 1.1.6 line 1 had no quarters")
    return BeaRealGdp(
        sheet_name="T10106-Q",
        line_number="1",
        account_code="A191RX",
        line_label="Gross domestic product",
        unit_text=units,
        published_on=published,
        quarters=quarters,
    )


def _sheet_path(book: zipfile.ZipFile, sheet_name: str) -> str:
    rel_id = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
    workbook = ET.fromstring(book.read("xl/workbook.xml"))
    relationships = ET.fromstring(book.read("xl/_rels/workbook.xml.rels"))
    targets = {item.attrib.get("Id"): item.attrib.get("Target", "") for item in relationships}
    for sheet in workbook.iter(f"{NS}sheet"):
        if sheet.attrib.get("name") != sheet_name:
            continue
        target = targets.get(sheet.attrib.get(rel_id), "")
        if not target:
            raise ValueError(f"{sheet_name} has no worksheet")
        return target if target.startswith("xl/") else f"xl/{target}"
    raise ValueError(f"workbook has no sheet {sheet_name}")


def _published_on(rows: dict[int, dict[int, str]]) -> date:
    for cells in rows.values():
        text = cells.get(1, "")
        if not text.startswith("Data published "):
            continue
        try:
            return datetime.strptime(
                text.removeprefix("Data published ").strip(), "%B %d, %Y"
            ).date()
        except ValueError as exc:
            raise ValueError(f"unreadable publication line {text}") from exc
    raise ValueError("workbook does not state a publication date")


def _gdp_line(rows: dict[int, dict[int, str]]) -> int:
    matches = [
        row
        for row, cells in rows.items()
        if cells.get(1) == "1"
        and cells.get(3) == "A191RX"
        and cells.get(2, "").strip() == "Gross domestic product"
    ]
    if len(matches) != 1:
        raise ValueError("Table 1.1.6 line 1 account A191RX was not identified")
    return matches[0]


def _quarters(
    rows: dict[int, dict[int, str]], header_row: int, value_row: int
) -> tuple[BeaMonth, ...]:
    if rows[value_row].get(3) != "A191RX":
        raise ValueError("expected account A191RX")
    series: list[BeaMonth] = []
    for index, label in rows[header_row].items():
        if index < 4 or "Q" not in label:
            continue
        year_text, _, quarter_text = label.partition("Q")
        if not year_text.isdigit() or quarter_text not in {"1", "2", "3", "4"}:
            continue
        raw = rows[value_row].get(index)
        if raw in (None, "", "NA", "....."):
            continue
        month = (int(quarter_text) - 1) * 3 + 1
        series.append(BeaMonth(date(int(year_text), month, 1), raw))
    return tuple(series)
