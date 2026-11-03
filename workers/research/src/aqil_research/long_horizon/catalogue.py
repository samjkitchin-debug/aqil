"""Founding long-horizon catalogue. Rows are design candidates, not results."""

from __future__ import annotations

import csv
import hashlib
import json
import zipfile
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree

from aqil_research.long_horizon.families import FAMILY_GATES, gates_by_name

NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
ORIGINAL_SHA256 = {
    "aqil_long_horizon_scenarios_v1.json": (
        "4c741b4ce40d5ab5ecee5f856653beb2d814f327c1fb7fea0d65cc9f9d62edc0",
        829998,
    ),
    "aqil_long_horizon_strategy_research_matrix_v1.xlsx": (
        "c6abbe20bd15cbd23198a811dc54abe55d40925caf1cf0ea419e5de66a883ee1",
        131542,
    ),
    "aqil_long_horizon_scenarios_v1.csv": (
        "e4a38f60f2178ddef84ea93f0472852abc6af1e05fa4ef18f7c935aca1b3ee4e",
        492482,
    ),
}


@dataclass(frozen=True)
class CatalogueFile:
    filename: str
    sha256: str
    byte_count: int


@dataclass(frozen=True)
class CatalogueReport:
    files: tuple[CatalogueFile, ...]
    json_scenario_count: int
    csv_scenario_count: int
    xlsx_scenario_count: int
    unique_scenario_ids: int
    unique_signal_ids: int
    family_count: int
    declared_signal_count: int
    declared_scenario_count: int
    declared_family_count: int
    json_csv_field_mismatches: int
    xlsx_scenario_cell_mismatches: int
    xlsx_mechanism_mismatches: int
    scenario_ids_only_in_json_versus_csv: tuple[str, ...]
    scenario_ids_only_in_csv_versus_json: tuple[str, ...]
    scenario_ids_only_in_json_versus_xlsx: tuple[str, ...]
    scenario_ids_only_in_xlsx_versus_json: tuple[str, ...]
    signal_ids_only_in_json: tuple[str, ...]
    signal_ids_only_in_xlsx: tuple[str, ...]
    families: tuple[str, ...]
    supported_values: tuple[str, ...]
    execution_status_values: tuple[str, ...]
    sheet_rows: tuple[tuple[str, int], ...]
    scenarios_by_source: dict[str, list[dict[str, str]]]
    signals_by_source: dict[str, list[dict[str, str]]]


def file_sha256(path: Path) -> tuple[str, int]:
    payload = path.read_bytes()
    return hashlib.sha256(payload).hexdigest(), len(payload)


def _column_index(cell_ref: str) -> int:
    letters = "".join(character for character in cell_ref if character.isalpha())
    number = 0
    for character in letters:
        number = number * 26 + ord(character.upper()) - 64
    return number - 1


def _cell_text(cell: ElementTree.Element, shared: list[str]) -> str:
    kind = cell.attrib.get("t")
    if kind == "inlineStr":
        return "".join(node.text or "" for node in cell.findall(".//m:t", NS))
    value = cell.find("m:v", NS)
    if value is None or value.text is None:
        return ""
    if kind == "s":
        return shared[int(value.text)]
    return value.text


def _shared_strings(book: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in book.namelist():
        return []
    root = ElementTree.fromstring(book.read("xl/sharedStrings.xml"))
    strings: list[str] = []
    for item in root.findall("m:si", NS):
        strings.append("".join(node.text or "" for node in item.findall(".//m:t", NS)))
    return strings


def _sheet_rows(root: ElementTree.Element, shared: list[str]) -> list[list[str]]:
    rows = root.findall("m:sheetData/m:row", NS)
    if not rows:
        return []
    width = 0
    parsed: list[list[tuple[int, str]]] = []
    for row in rows:
        pairs: list[tuple[int, str]] = []
        for cell in row.findall("m:c", NS):
            index = _column_index(cell.attrib.get("r", "A1"))
            pairs.append((index, _cell_text(cell, shared)))
            width = max(width, index + 1)
        parsed.append(pairs)
    table: list[list[str]] = []
    for pairs in parsed:
        values = [""] * width
        for index, text in pairs:
            if index < width:
                values[index] = text
        table.append(values)
    return table


def _records(table: list[list[str]]) -> list[dict[str, str]]:
    if not table:
        return []
    header = table[0]
    records: list[dict[str, str]] = []
    for values in table[1:]:
        if not any(values):
            continue
        record = {
            header[index]: values[index] if index < len(values) else ""
            for index in range(len(header))
            if header[index]
        }
        records.append(record)
    return records


def _workbook_sheets(
    path: Path,
) -> tuple[list[tuple[str, list[dict[str, str]]]], list[tuple[str, int]]]:
    with zipfile.ZipFile(path) as book:
        shared = _shared_strings(book)
        workbook = ElementTree.fromstring(book.read("xl/workbook.xml"))
        relationships = ElementTree.fromstring(book.read("xl/_rels/workbook.xml.rels"))
        targets = {item.attrib["Id"]: item.attrib["Target"].lstrip("/") for item in relationships}
        sheets: list[tuple[str, list[dict[str, str]]]] = []
        counts: list[tuple[str, int]] = []
        for sheet in workbook.findall("m:sheets/m:sheet", NS):
            name = sheet.attrib["name"]
            relation = sheet.attrib[
                "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
            ]
            root = ElementTree.fromstring(book.read(targets[relation]))
            table = _sheet_rows(root, shared)
            counts.append((name, len(table)))
            sheets.append((name, _records(table)))
    return sheets, counts


def _mismatch_count(
    left: dict[str, dict[str, str]],
    right: dict[str, dict[str, str]],
    keys: list[str],
) -> int:
    mismatches = 0
    for scenario_id in sorted(set(left) & set(right)):
        for key in keys:
            if str(left[scenario_id].get(key, "")) != str(right[scenario_id].get(key, "")):
                mismatches += 1
    return mismatches


def load_catalogue(directory: Path) -> CatalogueReport:
    """Read the three founding files. Do not drop a file because another agrees."""
    present = {path.name: path for path in directory.iterdir() if path.is_file()}
    files: list[CatalogueFile] = []
    for filename, (expected_hash, expected_bytes) in ORIGINAL_SHA256.items():
        path = present.get(filename)
        if path is None:
            raise FileNotFoundError(filename)
        digest, size = file_sha256(path)
        if digest != expected_hash or size != expected_bytes:
            raise ValueError(f"{filename} does not match the Downloads checksum")
        files.append(CatalogueFile(filename, digest, size))

    json_payload = json.loads(
        (directory / "aqil_long_horizon_scenarios_v1.json").read_text(encoding="utf-8")
    )
    json_scenarios = [
        {key: str(value) for key, value in scenario.items()}
        for scenario in json_payload["scenarios"]
    ]
    with (directory / "aqil_long_horizon_scenarios_v1.csv").open(
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        csv_scenarios = [
            {key: value for key, value in row.items() if key is not None}
            for row in csv.DictReader(handle)
        ]
    sheets, sheet_rows = _workbook_sheets(
        directory / "aqil_long_horizon_strategy_research_matrix_v1.xlsx"
    )
    by_sheet = dict(sheets)
    xlsx_scenarios = by_sheet["Scenario Matrix"]
    xlsx_signals = by_sheet["Signal Dictionary"]
    keys = list(json_scenarios[0])
    json_by = {row["Scenario ID"]: row for row in json_scenarios}
    csv_by = {row["Scenario ID"]: row for row in csv_scenarios}
    xlsx_by = {row["Scenario ID"]: row for row in xlsx_scenarios}
    signal_ids = {row["Signal ID"] for row in json_scenarios}
    xlsx_signal_ids = {row["Signal ID"] for row in xlsx_signals}
    families = tuple(sorted({row["Research family"] for row in json_scenarios}))
    mechanism_mismatches = 0
    hypothesis_by_signal: dict[str, str] = {}
    for row in json_scenarios:
        hypothesis_by_signal[row["Signal ID"]] = row["Falsifiable hypothesis"]
    for row in xlsx_signals:
        if hypothesis_by_signal.get(row["Signal ID"]) != row.get("Falsifiable mechanism", ""):
            mechanism_mismatches += 1
    json_signal_rows: list[dict[str, str]] = []
    scenarios_for_signal: dict[str, list[str]] = defaultdict(list)
    for row in json_scenarios:
        scenarios_for_signal[row["Signal ID"]].append(row["Scenario ID"])
    for signal_id in sorted(scenarios_for_signal):
        json_signal_rows.append(
            {
                "Signal ID": signal_id,
                "Falsifiable hypothesis": hypothesis_by_signal[signal_id],
                "scenario_ids": ",".join(scenarios_for_signal[signal_id]),
            }
        )
    return CatalogueReport(
        files=tuple(files),
        json_scenario_count=len(json_scenarios),
        csv_scenario_count=len(csv_scenarios),
        xlsx_scenario_count=len(xlsx_scenarios),
        unique_scenario_ids=len(set(json_by)),
        unique_signal_ids=len(signal_ids),
        family_count=len(families),
        declared_signal_count=int(json_payload["signal_count"]),
        declared_scenario_count=int(json_payload["scenario_count"]),
        declared_family_count=int(json_payload["family_count"]),
        json_csv_field_mismatches=_mismatch_count(json_by, csv_by, keys),
        xlsx_scenario_cell_mismatches=_mismatch_count(json_by, xlsx_by, keys),
        xlsx_mechanism_mismatches=mechanism_mismatches,
        scenario_ids_only_in_json_versus_csv=tuple(sorted(set(json_by) - set(csv_by))),
        scenario_ids_only_in_csv_versus_json=tuple(sorted(set(csv_by) - set(json_by))),
        scenario_ids_only_in_json_versus_xlsx=tuple(sorted(set(json_by) - set(xlsx_by))),
        scenario_ids_only_in_xlsx_versus_json=tuple(sorted(set(xlsx_by) - set(json_by))),
        signal_ids_only_in_json=tuple(sorted(signal_ids - xlsx_signal_ids)),
        signal_ids_only_in_xlsx=tuple(sorted(xlsx_signal_ids - signal_ids)),
        families=families,
        supported_values=tuple(sorted({row.get("Supported?", "") for row in xlsx_signals})),
        execution_status_values=tuple(
            sorted({row.get("Execution status", "") for row in xlsx_signals})
        ),
        sheet_rows=tuple(sheet_rows),
        scenarios_by_source={
            "aqil_long_horizon_scenarios_v1.json": json_scenarios,
            "aqil_long_horizon_scenarios_v1.csv": csv_scenarios,
            "aqil_long_horizon_strategy_research_matrix_v1.xlsx": xlsx_scenarios,
        },
        signals_by_source={
            "aqil_long_horizon_scenarios_v1.json": json_signal_rows,
            "aqil_long_horizon_strategy_research_matrix_v1.xlsx": xlsx_signals,
        },
    )


def assert_family_gates(report: CatalogueReport) -> None:
    known = gates_by_name()
    missing = [name for name in report.families if name not in known]
    extra = [gate.family_name for gate in FAMILY_GATES if gate.family_name not in report.families]
    if missing or extra or len(FAMILY_GATES) != len(known):
        raise ValueError(f"family gate mismatch missing={missing} extra={extra}")
