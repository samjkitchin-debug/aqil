"""Statistics Bureau CPI reference series: rights, schema 1.0, and stable ids."""

from __future__ import annotations

import csv
from datetime import UTC, date, datetime
from pathlib import Path

import psycopg
import pytest

import aqil_research.adapters.stat_cpi_all_items.adapter as adapter_module
from aqil_research.adapters.protocol import ProviderFailureCode
from aqil_research.adapters.stat_cpi_all_items.adapter import (
    StatCpiAdapter,
    StatCpiAdapterConfig,
)
from aqil_research.adapters.stat_cpi_all_items.client import (
    MAX_ATTEMPTS,
    StatCpiClientError,
    cpi_csv_url,
    cpi_request_headers,
)
from aqil_research.adapters.stat_cpi_all_items.constants import (
    DATASET_ID,
    ITEM_CODE,
    METHOD_COMPATIBILITY_NOTE,
    SOURCE_ID,
    UNIT_TEXT,
)
from aqil_research.adapters.stat_cpi_all_items.parse import parse_stat_cpi_csv
from aqil_research.adapters.stat_cpi_all_items.stability import StoredStatCpiPoint
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

FIXTURE = Path(__file__).parent / "fixtures" / "stat_cpi_all_items" / "zmi2025aa_excerpt.csv"
FRAGMENT = (
    Path(__file__).resolve().parents[3]
    / "docs"
    / "sources"
    / "fragments"
    / "stat_cpi_2025_all_items_reference.csv"
)
RETRIEVED = datetime(2026, 10, 24, 4, 0, tzinfo=UTC)
EXCERPT_VALUES = {
    date(2025, 6, 1): "101.560",
    date(2025, 8, 1): "102.179",
    date(2026, 9, 1): "102.228",
}


def _collapsed(value: str) -> str:
    return " ".join(value.split())


def _refuse_database(*args: object, **kwargs: object) -> None:
    raise AssertionError(f"database connection is not allowed: {args!r} {kwargs!r}")


def _bind_memory(monkeypatch: pytest.MonkeyPatch) -> InMemoryObservationStore:
    monkeypatch.setattr("psycopg.connect", _refuse_database)
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
    prior: tuple[StoredStatCpiPoint, ...] = (),
) -> StatCpiAdapter:
    return StatCpiAdapter(
        config=StatCpiAdapterConfig(live=False, fixture_path=path),
        retrieved_at=retrieved_at,
        prior_points=prior,
    )


def _points(store: InMemoryObservationStore) -> tuple[StoredStatCpiPoint, ...]:
    return tuple(
        StoredStatCpiPoint(
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


def _rewrite(source: Path, dest: Path, edits: dict[str, dict[int, str]]) -> None:
    with source.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle))
    for row in rows:
        change = edits.get(row[0] if row else "")
        if not change:
            continue
        for index, value in change.items():
            while len(row) <= index:
                row.append("")
            row[index] = value
    with dest.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerows(rows)


def test_rights_fragment_clears_first_live_use() -> None:
    records = load_source_rights(FRAGMENT)
    assert len(records) == 1
    record = records[0]
    assert record.source_id == SOURCE_ID
    assert record.dataset_id == DATASET_ID
    assert record.m1_role == M1Role.FIRST_LIVE_PROVIDER
    assert record.operational_status == OperationalStatus.ENABLED
    assert record.attribution == AttributionRequirement.REQUIRED
    assert record.ai_processing == RightsDecision.UNKNOWN
    assert record.ai_model_training == RightsDecision.UNKNOWN
    assert record.assessed_on.isoformat() == "2026-10-24"
    assert record.terms_url in record.evidence_urls
    assert "商用利用も可能です" in record.evidence_note
    assert "latest-revised" in record.evidence_note
    assert "three-decimal" in record.evidence_note
    assert "calendar month" in record.evidence_note
    assert _collapsed(METHOD_COMPATIBILITY_NOTE) in _collapsed(record.evidence_note)
    for operation in FIRST_LIVE_OPERATIONS:
        assert record.decision_for(operation) == RightsDecision.PERMITTED


def test_adapter_documents_method_compatibility() -> None:
    assert _collapsed(METHOD_COMPATIBILITY_NOTE) in _collapsed(adapter_module.__doc__ or "")
    assert SahmAnalyticalMethod().required_dataset_ids() == ("bls.ln.LNS14000000",)
    assert SloosCilMethod().required_dataset_ids() == ("fed.sloos.SUBLPDCILS_N.Q",)
    assert CensusAdvOrdersMethod().required_dataset_ids() == ("census.m3.adv.MDM.NO",)
    assert PeriodChangeMethod().required_dataset_ids() == ("bls.ln.LNS14000000",)
    assert DATASET_ID not in MacroConditionsMethod().required_dataset_ids()


def test_request_does_not_ask_for_history() -> None:
    url = cpi_csv_url()
    assert url == "https://www.stat.go.jp/data/cpi/2025/csv/zmi2025aa.csv"
    assert "includeHistory" not in url
    assert MAX_ATTEMPTS == 1
    assert cpi_request_headers()["Accept"] == "text/csv"


def test_excerpt_is_latest_revised_schema_v1() -> None:
    parsed = parse_stat_cpi_csv(FIXTURE.read_bytes(), retrieved_at=RETRIEVED)
    assert parsed.series_key == ITEM_CODE
    assert parsed.unit == UNIT_TEXT
    assert parsed.seasonal_adjustment == "not seasonally adjusted"
    assert parsed.frequency == "monthly"
    assert parsed.calendar_basis == "calendar_month"
    assert parsed.vintage_class == "latest_revised"
    assert parsed.omitted_periods == ("202507",)
    assert len(parsed.observations) == 3
    for observation in parsed.observations:
        assert observation.schema_version == "1.0"
        assert observation.series_provenance == SeriesProvenance.LATEST_REVISED
        assert observation.availability_precision == AvailabilityPrecision.UNKNOWN
        assert observation.earliest_model_available_at is None
        assert observation.seasonal_adjustment == SeasonalAdjustment.NOT_SEASONALLY_ADJUSTED
        assert observation.frequency.value == "monthly"
        assert observation.geography == "JP"
        assert observation.unit == UNIT_TEXT
        assert observation.dataset_id == DATASET_ID
        assert observation.source_id == SOURCE_ID
        assert observation.provider_id == "stat"
        assert observation.raw_value == EXCERPT_VALUES[observation.period_start]
    assert [row.period_start for row in parsed.observations] == sorted(EXCERPT_VALUES)
    stored = {row.raw_value for row in parsed.observations}
    assert "99.001" not in stored
    assert "50.000" not in stored


def test_cp932_bytes_parse() -> None:
    encoded = FIXTURE.read_text(encoding="utf-8").encode("cp932")
    parsed = parse_stat_cpi_csv(encoded, retrieved_at=RETRIEVED)
    assert len(parsed.observations) == 3


def test_blank_month_is_omitted_and_not_stored_as_zero() -> None:
    parsed = parse_stat_cpi_csv(FIXTURE.read_bytes(), retrieved_at=RETRIEVED)
    assert all(row.period_start != date(2025, 7, 1) for row in parsed.observations)
    assert all(row.raw_value != "0" for row in parsed.observations)


def test_seasonally_adjusted_header_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "sa.csv"
    _rewrite(FIXTURE, path, {"Group/Item": {1: "All items, seasonally adjusted"}})
    result = _adapter(path, RETRIEVED).fetch()
    assert result.observations == ()
    assert result.errors[0].code == ProviderFailureCode.PARSE_FAILED
    assert "seasonally adjusted" in result.errors[0].message


def test_other_all_items_code_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "other.csv"
    _rewrite(FIXTURE, path, {"類・品目符号(Group/Item code)": {1: "0201"}})
    result = _adapter(path, RETRIEVED).fetch()
    assert result.observations == ()
    assert "0001" in result.errors[0].message


def test_contradictory_values_are_not_treated_as_vintages(tmp_path: Path) -> None:
    path = tmp_path / "two.csv"
    text = FIXTURE.read_text(encoding="utf-8")
    path.write_text(f"{text}202609,102.000,99.300,50.200\n", encoding="utf-8")
    result = _adapter(path, RETRIEVED).fetch()
    assert result.observations == ()
    assert "vintage panel" in result.errors[0].message


def test_non_numeric_value_fails(tmp_path: Path) -> None:
    path = tmp_path / "bad.csv"
    _rewrite(FIXTURE, path, {"202508": {1: "x"}})
    result = _adapter(path, RETRIEVED).fetch()
    assert result.observations == ()
    assert result.errors[0].code == ProviderFailureCode.PARSE_FAILED


def test_missing_fixture_is_a_fetch_failure() -> None:
    result = StatCpiAdapter(
        config=StatCpiAdapterConfig(live=False, fixture_path=None),
        retrieved_at=RETRIEVED,
    ).fetch()
    assert result.errors[0].code == ProviderFailureCode.FETCH_FAILED


def test_client_error_is_a_fetch_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom() -> tuple[bytes, int]:
        raise StatCpiClientError("Statistics Bureau CPI CSV returned HTTP 503")

    monkeypatch.setattr(
        "aqil_research.adapters.stat_cpi_all_items.adapter.fetch_cpi_csv",
        _boom,
    )
    result = StatCpiAdapter(
        config=StatCpiAdapterConfig(live=True),
        retrieved_at=RETRIEVED,
    ).fetch()
    assert result.errors[0].code == ProviderFailureCode.FETCH_FAILED
    assert "503" in result.errors[0].message


def test_second_fixture_ingest_reuses_observation_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    store = _bind_memory(monkeypatch)
    adapter = _adapter(FIXTURE, RETRIEVED)
    first, bound = collect_registered_adapter(
        store_backend="memory",
        adapter=adapter,
        source_id=SOURCE_ID,
        collected_at=RETRIEVED,
        live=False,
    )
    assert bound is store
    assert first.outcome == "success"
    assert first.observations_newly_stored == 3
    assert first.data_provenance == "latest_revised"
    assert psycopg.connect is _refuse_database
    first_ids = {row.period_start: row.observation_id for row in store.all_observations()}
    later = datetime(2026, 10, 25, 4, 0, tzinfo=UTC)
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
        if row.period_start == date(2026, 9, 1)
    )
    changed = tmp_path / "changed.csv"
    _rewrite(FIXTURE, changed, {"202609": {1: "102.300"}})
    later = datetime(2026, 10, 25, 4, 0, tzinfo=UTC)
    follow_up = _adapter(changed, later, _points(store))
    second, _bound = collect_registered_adapter(
        store_backend="memory",
        adapter=follow_up,
        source_id=SOURCE_ID,
        collected_at=later,
        live=False,
    )
    assert second.observations_newly_stored == 1
    september = [row for row in store.all_observations() if row.period_start == date(2026, 9, 1)]
    assert len(september) == 2
    revised = next(row for row in september if row.raw_value == "102.300")
    assert revised.observation_id != original
