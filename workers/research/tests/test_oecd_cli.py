"""OECD G20 CLI: the register stays pending, and the parser keeps the published schema."""

from __future__ import annotations

import csv
from datetime import UTC, date, datetime
from pathlib import Path

import psycopg
import pytest

import aqil_research.adapters.oecd_cli.adapter as adapter_module
from aqil_research.adapters.oecd_cli.adapter import OecdCliAdapter, OecdCliAdapterConfig
from aqil_research.adapters.oecd_cli.client import series_csv_url
from aqil_research.adapters.oecd_cli.constants import (
    DATASET_ID,
    METHOD_COMPATIBILITY_NOTE,
    METHODOLOGY_LABEL,
    SERIES_KEY,
    SOURCE_ID,
    UNIT_TEXT,
)
from aqil_research.adapters.oecd_cli.parse import parse_oecd_cli_csv
from aqil_research.adapters.oecd_cli.stability import StoredOecdPoint
from aqil_research.collection.service import collect_registered_adapter
from aqil_research.contracts.observation import (
    AvailabilityPrecision,
    SeasonalAdjustment,
    SeriesProvenance,
)
from aqil_research.methods.macro_conditions import MacroConditionsMethod
from aqil_research.methods.sahm_registered import SahmAnalyticalMethod
from aqil_research.sources.rights import (
    FIRST_LIVE_OPERATIONS,
    AttributionRequirement,
    M1Role,
    OperationalStatus,
    RightsDecision,
    load_source_rights,
)
from aqil_research.vintages.store import InMemoryObservationStore

FIXTURE = Path(__file__).parent / "fixtures" / "oecd_cli" / "g20_cli_excerpt.csv"
FRAGMENT = (
    Path(__file__).resolve().parents[3] / "docs" / "sources" / "fragments" / "oecd_cli_g20.csv"
)
RETRIEVED = datetime(2026, 10, 24, 9, 0, tzinfo=UTC)
EXCERPT_VALUES = {
    date(2026, 6, 1): "100.204",
    date(2026, 7, 1): "100.1805",
    date(2026, 8, 1): "100.1609",
    date(2026, 9, 1): "100.1431",
}


def _collapsed(value: str) -> str:
    return " ".join(value.split())


def _refuse_database(*args: object, **kwargs: object) -> None:
    raise AssertionError(f"database connection is not allowed: {args!r} {kwargs!r}")


@pytest.fixture(autouse=True)
def _no_database(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("psycopg.connect", _refuse_database)


def _bind_memory(monkeypatch: pytest.MonkeyPatch) -> InMemoryObservationStore:
    records = load_source_rights(FRAGMENT)
    monkeypatch.setattr(
        "aqil_research.collection.service.load_source_rights",
        lambda path=None: records,
    )
    store = InMemoryObservationStore()
    monkeypatch.setattr(
        "aqil_research.collection.service.InMemoryObservationStore",
        lambda: store,
    )
    return store


def _adapter(
    path: Path,
    retrieved_at: datetime,
    prior: tuple[StoredOecdPoint, ...] = (),
) -> OecdCliAdapter:
    return OecdCliAdapter(
        config=OecdCliAdapterConfig(live=False, fixture_path=path),
        retrieved_at=retrieved_at,
        prior_points=prior,
    )


def _rewrite(source: Path, dest: Path, edits: dict[str, dict[str, str]]) -> None:
    with source.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        fieldnames = list(reader.fieldnames or [])
    for row in rows:
        change = edits.get(row["TIME_PERIOD"])
        if change:
            row.update(change)
    with dest.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def test_rights_fragment_clears_first_live_use() -> None:
    record = load_source_rights(FRAGMENT)[0]
    assert record.source_id == SOURCE_ID
    assert record.dataset_id == DATASET_ID
    assert record.m1_role == M1Role.UNRESOLVED
    assert record.operational_status == OperationalStatus.DISABLED
    assert "rights pending" in record.conditions.lower()
    assert record.attribution == AttributionRequirement.REQUIRED
    for operation in FIRST_LIVE_OPERATIONS:
        assert record.decision_for(operation) == RightsDecision.PERMITTED
    assert "even for commercial use" in record.evidence_note
    assert "OECD harmonised" in record.evidence_note
    assert "latest-revised" in record.evidence_note
    assert "not a historical vintage panel" in record.evidence_note
    assert _collapsed(METHOD_COMPATIBILITY_NOTE) in _collapsed(record.evidence_note)


def test_adapter_documents_method_compatibility() -> None:
    assert _collapsed(METHOD_COMPATIBILITY_NOTE) in _collapsed(adapter_module.__doc__ or "")
    assert DATASET_ID not in SahmAnalyticalMethod().required_dataset_ids()
    assert DATASET_ID not in MacroConditionsMethod().required_dataset_ids()


def test_request_does_not_ask_for_history() -> None:
    url = series_csv_url()
    assert url.startswith("https://sdmx.oecd.org/public/rest/data/")
    assert SERIES_KEY in url
    assert "format=csvfilewithlabels" in url
    assert "includeHistory" not in url


def test_excerpt_is_latest_revised_schema_v1() -> None:
    parsed = parse_oecd_cli_csv(FIXTURE.read_text(encoding="utf-8"), retrieved_at=RETRIEVED)
    assert parsed.series_key == SERIES_KEY
    assert METHODOLOGY_LABEL in parsed.compiler_sentence
    assert parsed.unit == UNIT_TEXT
    assert parsed.vintage_class == "latest_revised"
    assert len(parsed.observations) == 4
    for observation in parsed.observations:
        assert observation.schema_version == "1.0"
        assert observation.series_provenance == SeriesProvenance.LATEST_REVISED
        assert observation.availability_precision == AvailabilityPrecision.UNKNOWN
        assert observation.seasonal_adjustment == SeasonalAdjustment.UNKNOWN
        assert observation.geography == "G20"
        assert observation.frequency.value == "monthly"
        assert observation.raw_value == EXCERPT_VALUES[observation.period_start]


def test_blank_month_is_omitted(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "gap.csv"
    _rewrite(FIXTURE, path, {"2026-07": {"OBS_VALUE": "", "OBS_STATUS": "M"}})
    parsed = parse_oecd_cli_csv(path.read_text(encoding="utf-8"), retrieved_at=RETRIEVED)
    assert parsed.omitted_periods == ("2026-07",)
    assert all(row.raw_value != "0" for row in parsed.observations)
    _bind_memory(monkeypatch)
    result, _bound = collect_registered_adapter(
        store_backend="memory",
        adapter=_adapter(path, RETRIEVED),
        source_id=SOURCE_ID,
        collected_at=RETRIEVED,
        live=False,
    )
    assert result.outcome == "failed_rights"
    assert result.observations_newly_stored == 0
    assert psycopg.connect is _refuse_database


def test_other_reference_area_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "usa.csv"
    _rewrite(FIXTURE, path, {"2026-06": {"REF_AREA": "USA", "Reference area": "United States"}})
    result = _adapter(path, RETRIEVED).fetch()
    assert result.observations == ()
    assert "refusing" in result.errors[0].message


def test_register_blocks_fixture_ingest(monkeypatch: pytest.MonkeyPatch) -> None:
    _bind_memory(monkeypatch)
    adapter = _adapter(FIXTURE, RETRIEVED)
    first, _bound = collect_registered_adapter(
        store_backend="memory",
        adapter=adapter,
        source_id=SOURCE_ID,
        collected_at=RETRIEVED,
        live=False,
    )
    assert first.outcome == "failed_rights"
    assert first.observations_newly_stored == 0
    later = datetime(2026, 10, 25, 9, 0, tzinfo=UTC)
    second, _again = collect_registered_adapter(
        store_backend="memory",
        adapter=adapter,
        source_id=SOURCE_ID,
        collected_at=later,
        live=False,
    )
    assert second.outcome == "failed_rights"
    assert second.observations_newly_stored == 0
