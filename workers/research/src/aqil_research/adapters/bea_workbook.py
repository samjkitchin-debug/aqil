"""Parse the two official BEA workbook lines used by the 1988 refit."""

from __future__ import annotations

import zipfile
from dataclasses import dataclass
from datetime import date
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
