"""BIS global liquidity: rights, schema 1.0, omitted gaps, and a second ingest that adds nothing."""

from __future__ import annotations

import csv
from datetime import UTC, date, datetime
from pathlib import Path

import psycopg
import pytest

import aqil_research.adapters.bis_gli.adapter as adapter_module
from aqil_research.adapters.bis_gli.adapter import BisGliAdapter, BisGliAdapterConfig
from aqil_research.adapters.bis_gli.client import series_csv_url, series_request_headers
from aqil_research.adapters.bis_gli.constants import (
    DATASET_ID,
    METHOD_COMPATIBILITY_NOTE,
    SERIES_KEY,
    SOURCE_ID,
    TITLE,
    UNIT_TEXT,
)
from aqil_research.adapters.bis_gli.parse import parse_bis_gli_csv
from aqil_research.adapters.bis_gli.stability import StoredBisPoint
from aqil_research.collection.service import collect_registered_adapter
from aqil_research.contracts.observation import (
    AvailabilityPrecision,
    SeasonalAdjustment,
    SeriesProvenance,
)
from aqil_research.methods.census_adv_orders import CensusAdvOrdersMethod
from aqil_research.methods.macro_conditions import MacroConditionsMethod
from aqil_research.methods.period_change import PeriodChangeMethod
from aqil_research.methods.sahm_registered import SahmAnalyticalMethod
from aqil_research.methods.sloos_cil import SloosCilMethod
from aqil_research.sources.rights import (
    FIRST_LIVE_OPERATIONS,
    AttributionRequirement,
    M1Role,
    OperationalStatus,
    RightsDecision,
    load_source_rights,
)
from aqil_research.vintages.store import InMemoryObservationStore

FIXTURE = Path(__file__).parent / "fixtures" / "bis_gli" / "gli_excerpt.csv"
FRAGMENT = (
    Path(__file__).resolve().parents[3]
    / "docs"
    / "sources"
    / "fragments"
    / "bis_gli_usd_credit_nonbanks.csv"
)
RETRIEVED = datetime(2026, 10, 24, 9, 0, tzinfo=UTC)
EXCERPT_VALUES = {
    date(2025, 4, 1): "13979225.357",
    date(2025, 7, 1): "14226387.541",
    date(2025, 10, 1): "14253874.857",
    date(2026, 1, 1): "14747653.746",
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
    prior: tuple[StoredBisPoint, ...] = (),
) -> BisGliAdapter:
    return BisGliAdapter(
        config=BisGliAdapterConfig(live=False, fixture_path=path),
        retrieved_at=retrieved_at,
        prior_points=prior,
    )


def _points(store: InMemoryObservationStore) -> tuple[StoredBisPoint, ...]:
    return tuple(
        StoredBisPoint(
            period_start=row.period_start,
            observation_id=row.observation_id,
            raw_value=row.raw_value,
            provider_vintage_date=row.provider_vintage_date,
            source_release_at=row.source_release_at,
            retrieved_at=row.retrieved_at,
            first_seen_at=row.first_seen_at,
        )
        for row in store.all_observations()
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
    records = load_source_rights(FRAGMENT)
    assert len(records) == 1
    record = records[0]
    assert record.source_id == SOURCE_ID
    assert record.dataset_id == DATASET_ID
    assert record.series_or_dataset_code == SERIES_KEY
    assert record.m1_role == M1Role.FIRST_LIVE_PROVIDER
    assert record.operational_status == OperationalStatus.ENABLED
    assert record.attribution == AttributionRequirement.REQUIRED
    assert record.ai_processing == RightsDecision.UNKNOWN
    assert record.ai_model_training == RightsDecision.UNKNOWN
    for operation in FIRST_LIVE_OPERATIONS:
        assert record.decision_for(operation) == RightsDecision.PERMITTED
    assert TITLE in record.evidence_note
    assert "latest-revised" in record.evidence_note
    assert "not a historical vintage panel" in record.evidence_note
    assert "additional charge" in record.conditions
    assert _collapsed(METHOD_COMPATIBILITY_NOTE) in _collapsed(record.evidence_note)


def test_adapter_documents_method_compatibility() -> None:
    assert _collapsed(METHOD_COMPATIBILITY_NOTE) in _collapsed(adapter_module.__doc__ or "")
    assert DATASET_ID not in SahmAnalyticalMethod().required_dataset_ids()
    assert DATASET_ID not in SloosCilMethod().required_dataset_ids()
    assert DATASET_ID not in CensusAdvOrdersMethod().required_dataset_ids()
    assert DATASET_ID not in PeriodChangeMethod().required_dataset_ids()
    assert DATASET_ID not in MacroConditionsMethod().required_dataset_ids()


def test_request_does_not_ask_for_history() -> None:
    url = series_csv_url()
    assert url.startswith("https://stats.bis.org/api/v1/data/WS_GLI/")
    assert SERIES_KEY in url
    assert "includeHistory" not in url
    assert "csv" in series_request_headers()["Accept"]


def test_excerpt_is_latest_revised_schema_v1() -> None:
    parsed = parse_bis_gli_csv(FIXTURE.read_text(encoding="utf-8"), retrieved_at=RETRIEVED)
    assert parsed.series_key == SERIES_KEY
    assert parsed.compiler_sentence == TITLE
    assert parsed.unit == UNIT_TEXT
    assert parsed.vintage_class == "latest_revised"
    assert len(parsed.observations) == 4
    for observation in parsed.observations:
        assert observation.schema_version == "1.0"
        assert observation.series_provenance == SeriesProvenance.LATEST_REVISED
        assert observation.availability_precision == AvailabilityPrecision.UNKNOWN
        assert observation.earliest_model_available_at is None
        assert observation.seasonal_adjustment == SeasonalAdjustment.UNKNOWN
        assert observation.unit == UNIT_TEXT
        assert observation.frequency.value == "quarterly"
        assert observation.geography == "Outside the United States"
        assert observation.raw_value == EXCERPT_VALUES[observation.period_start]
    assert parsed.observations[-1].period_end == date(2026, 3, 31)


def test_blank_quarter_is_omitted_and_not_stored_as_zero(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "gap.csv"
    _rewrite(FIXTURE, path, {"2025-Q3": {"OBS_VALUE": "", "OBS_STATUS": "M"}})
    parsed = parse_bis_gli_csv(path.read_text(encoding="utf-8"), retrieved_at=RETRIEVED)
    assert parsed.omitted_periods == ("2025-Q3",)
    assert all(row.raw_value != "0" for row in parsed.observations)
    store = _bind_memory(monkeypatch)
    result, bound = collect_registered_adapter(
        store_backend="memory",
        adapter=_adapter(path, RETRIEVED),
        source_id=SOURCE_ID,
        collected_at=RETRIEVED,
        live=False,
    )
    assert bound is store
    assert result.outcome == "success"
    assert result.observations_newly_stored == 3
    assert result.retrieval_id is None
    assert psycopg.connect is _refuse_database


def test_other_series_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "other.csv"
    _rewrite(FIXTURE, path, {"2025-Q2": {"BORROWERS_CTY": "US", "TITLE": "Some other series"}})
    result = _adapter(path, RETRIEVED).fetch()
    assert result.observations == ()
    assert result.errors
    assert "refusing" in result.errors[0].message


def test_contradictory_values_are_not_treated_as_vintages(tmp_path: Path) -> None:
    path = tmp_path / "two.csv"
    text = FIXTURE.read_text(encoding="utf-8")
    extra = text.strip().splitlines()[-1].replace("14747653.746", "1")
    body = text if text.endswith("\n") else f"{text}\n"
    path.write_text(f"{body}{extra}\n", encoding="utf-8")
    result = _adapter(path, RETRIEVED).fetch()
    assert result.observations == ()
    assert "vintage panel" in result.errors[0].message


def test_second_fixture_ingest_inserts_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    store = _bind_memory(monkeypatch)
    adapter = _adapter(FIXTURE, RETRIEVED)
    first, _bound = collect_registered_adapter(
        store_backend="memory",
        adapter=adapter,
        source_id=SOURCE_ID,
        collected_at=RETRIEVED,
        live=False,
    )
    assert first.outcome == "success"
    assert first.data_provenance == "latest_revised"
    assert first.observations_newly_stored == 4
    first_ids = {row.period_start: row.observation_id for row in store.all_observations()}
    later = datetime(2026, 10, 25, 9, 0, tzinfo=UTC)
    adapter.prior_points = _points(store)
    adapter.retrieved_at = later
    second, _again = collect_registered_adapter(
        store_backend="memory",
        adapter=adapter,
        source_id=SOURCE_ID,
        collected_at=later,
        live=False,
    )
    assert second.outcome == "unchanged"
    assert second.observations_newly_stored == 0
    assert {row.period_start: row.observation_id for row in store.all_observations()} == first_ids


def test_changed_value_is_a_new_row(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    store = _bind_memory(monkeypatch)
    adapter = _adapter(FIXTURE, RETRIEVED)
    collect_registered_adapter(
        store_backend="memory",
        adapter=adapter,
        source_id=SOURCE_ID,
        collected_at=RETRIEVED,
        live=False,
    )
    original = next(
        row.observation_id
        for row in store.all_observations()
        if row.period_start == date(2026, 1, 1)
    )
    changed = tmp_path / "changed.csv"
    _rewrite(FIXTURE, changed, {"2026-Q1": {"OBS_VALUE": "15000000"}})
    later = datetime(2026, 10, 25, 9, 0, tzinfo=UTC)
    follow_up = _adapter(changed, later, _points(store))
    second, _bound = collect_registered_adapter(
        store_backend="memory",
        adapter=follow_up,
        source_id=SOURCE_ID,
        collected_at=later,
        live=False,
    )
    assert second.observations_newly_stored == 1
    january = [row for row in store.all_observations() if row.period_start == date(2026, 1, 1)]
    assert len(january) == 2
    revised = next(row for row in january if row.raw_value == "15000000")
    assert revised.observation_id != original
