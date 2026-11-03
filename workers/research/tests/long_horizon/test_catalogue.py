"""The founding files stay design candidates."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from aqil_research.long_horizon.catalogue import (
    ORIGINAL_SHA256,
    assert_family_gates,
    load_catalogue,
)
from aqil_research.long_horizon.families import FAMILY_GATES
from aqil_research.long_horizon.registry import candidate_parameters

ROOT = Path(__file__).resolve().parents[4]
CATALOGUE = ROOT / "docs" / "research" / "long-horizon" / "founding-catalogue"


def test_founding_files_match_the_downloads_checksums() -> None:
    report = load_catalogue(CATALOGUE)
    assert_family_gates(report)
    assert report.declared_signal_count == 309
    assert report.declared_scenario_count == 618
    assert report.declared_family_count == 26
    assert report.unique_signal_ids == 309
    assert report.unique_scenario_ids == 618
    assert report.json_scenario_count == 618
    assert report.csv_scenario_count == 618
    assert report.xlsx_scenario_count == 618
    assert report.family_count == 26
    assert len(FAMILY_GATES) == 26
    assert report.json_csv_field_mismatches == 0
    assert report.xlsx_scenario_cell_mismatches == 0
    assert report.xlsx_mechanism_mismatches == 0
    assert report.scenario_ids_only_in_json_versus_csv == ()
    assert report.scenario_ids_only_in_csv_versus_json == ()
    assert report.scenario_ids_only_in_json_versus_xlsx == ()
    assert report.scenario_ids_only_in_xlsx_versus_json == ()
    assert report.signal_ids_only_in_json == ()
    assert report.signal_ids_only_in_xlsx == ()
    assert report.supported_values == ("No",)
    assert report.execution_status_values == ("Not executed",)
    names = {item.filename: item for item in report.files}
    for filename, (digest, size) in ORIGINAL_SHA256.items():
        assert names[filename].sha256 == digest
        assert names[filename].byte_count == size
    assert len({item.sha256 for item in report.files}) == 3


def test_candidate_rows_are_not_results_and_keep_every_source() -> None:
    report = load_catalogue(CATALOGUE)
    rows = candidate_parameters(report, datetime(2026, 11, 3, tzinfo=None))
    kinds: dict[str, int] = {}
    for row in rows:
        kinds[row[5]] = kinds.get(row[5], 0) + 1
        assert row[8] is False
        assert row[11] is False
    assert kinds["scenario"] == 618 * 3
    assert kinds["signal"] == 309 * 2
    assert kinds["file"] == 3
    assert kinds["comparison"] == 1
    assert kinds["sheet"] == 12


def test_notes_name_every_family_and_every_checksum() -> None:
    readiness = (ROOT / "docs" / "research" / "long-horizon" / "READINESS.md").read_text(
        encoding="utf-8"
    )
    catalogue_note = (ROOT / "docs" / "research" / "long-horizon" / "CATALOGUE.md").read_text(
        encoding="utf-8"
    )
    for gate in FAMILY_GATES:
        assert gate.family_name in readiness
    for digest, _size in ORIGINAL_SHA256.values():
        assert digest in catalogue_note
