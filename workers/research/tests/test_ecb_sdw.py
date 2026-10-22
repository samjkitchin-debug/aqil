"""ECB SDW HICP: rights, schema 1.0, omitted gaps, and a second ingest that adds nothing."""

from __future__ import annotations

import csv
from datetime import UTC, date, datetime
from pathlib import Path

import psycopg
import pytest

import aqil_research.adapters.ecb_sdw.adapter as adapter_module
from aqil_research.adapters.ecb_sdw.adapter import EcbSdwAdapter, EcbSdwAdapterConfig
from aqil_research.adapters.ecb_sdw.client import series_csv_url, series_request_headers
from aqil_research.adapters.ecb_sdw.constants import (
    COMPILER_SENTENCE,
    DATASET_ID,
    METHOD_COMPATIBILITY_NOTE,
    SERIES_KEY,
    SOURCE_ID,
    UNIT_TEXT,
)
from aqil_research.adapters.ecb_sdw.parse import parse_ecb_sdw_csv
from aqil_research.adapters.ecb_sdw.stability import StoredEcbPoint
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

FIXTURE = (
    Path(__file__).parent / "fixtures" / "ecb_sdw" / "icp_m_u2_y_000000_3_inx_excerpt.csv"
)
FRAGMENT = (
    Path(__file__).resolve().parents[3]
    / "docs"
    / "sources"
    / "fragments"
    / "ecb_sdw_hicp_sa.csv"
)
RETRIEVED = datetime(2026, 10, 22, 9, 0, tzinfo=UTC)
EXCERPT_VALUES = {
    date(2025, 9, 1): "129.20340945369898",
    date(2025, 10, 1): "129.4138430053961",
    date(2025, 11, 1): "129.67318795084398",
    date(2025, 12, 1): "129.7338491760366",
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
    prior: tuple[StoredEcbPoint, ...] = (),
) -> EcbSdwAdapter:
    return EcbSdwAdapter(
        config=EcbSdwAdapterConfig(live=False, fixture_path=path),
        retrieved_at=retrieved_at,
        prior_points=prior,
    )


def _points(store: InMemoryObservationStore) -> tuple[StoredEcbPoint, ...]:
    return tuple(
        StoredEcbPoint(
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
    assert record.assessed_on.isoformat() == "2026-10-22"
    assert record.terms_url in record.evidence_urls
    assert record.terms_url.startswith("https://")
    assert record.access_url.startswith("https://")
    for operation in FIRST_LIVE_OPERATIONS:
        assert record.decision_for(operation) == RightsDecision.PERMITTED
    assert COMPILER_SENTENCE in record.evidence_note
    assert "4F0" in record.evidence_note
    assert "latest-revised" in record.evidence_note
    assert "not a historical vintage panel" in record.evidence_note
    assert _collapsed(METHOD_COMPATIBILITY_NOTE) in _collapsed(record.evidence_note)
    assert "Eurostat" in record.evidence_note


def test_adapter_documents_method_compatibility() -> None:
    text = adapter_module.__doc__ or ""
    assert "ecb_monetary_press" in text
    assert _collapsed(METHOD_COMPATIBILITY_NOTE) in _collapsed(text)
    assert SahmAnalyticalMethod().required_dataset_ids() == ("bls.ln.LNS14000000",)
    assert SloosCilMethod().required_dataset_ids() == ("fed.sloos.SUBLPDCILS_N.Q",)
    assert CensusAdvOrdersMethod().required_dataset_ids() == ("census.m3.adv.MDM.NO",)
    assert PeriodChangeMethod().required_dataset_ids() == ("bls.ln.LNS14000000",)
    assert MacroConditionsMethod().required_dataset_ids() == (
        "bls.ln.LNS14000000",
        "fed.sloos.SUBLPDCILS_N.Q",
        "census.m3.adv.MDM.NO",
    )
    for method in (
        SahmAnalyticalMethod(),
        SloosCilMethod(),
        CensusAdvOrdersMethod(),
        PeriodChangeMethod(),
        MacroConditionsMethod(),
    ):
        assert DATASET_ID not in method.required_dataset_ids()


def test_request_does_not_ask_for_history() -> None:
    url = series_csv_url()
    assert url.startswith("https://data-api.ecb.europa.eu/service/data/ICP/")
    assert SERIES_KEY.split(".", 1)[1] in url
    assert "format=csvdata" in url
    assert "includeHistory" not in url
    assert series_request_headers()["Accept"] == "text/csv"


def test_excerpt_is_latest_revised_schema_v1() -> None:
    parsed = parse_ecb_sdw_csv(FIXTURE.read_text(encoding="utf-8"), retrieved_at=RETRIEVED)
    assert parsed.series_key == SERIES_KEY
    assert parsed.compiler_sentence == COMPILER_SENTENCE
    assert parsed.unit == UNIT_TEXT
    assert parsed.seasonal_adjustment == "Working day and seasonally adjusted"
    assert parsed.frequency == "Monthly"
    assert parsed.vintage_class == "latest_revised"
    assert parsed.omitted_periods == ()
    assert len(parsed.observations) == 4
    for observation in parsed.observations:
        assert observation.schema_version == "1.0"
        assert observation.series_provenance == SeriesProvenance.LATEST_REVISED
        assert observation.availability_precision == AvailabilityPrecision.UNKNOWN
        assert observation.earliest_model_available_at is None
        assert observation.seasonal_adjustment == SeasonalAdjustment.SEASONALLY_ADJUSTED
        assert observation.unit == UNIT_TEXT
        assert observation.frequency.value == "monthly"
        assert observation.geography == "EA"
        assert observation.raw_value == EXCERPT_VALUES[observation.period_start]
        assert observation.dataset_id == DATASET_ID
    periods = [row.period_start for row in parsed.observations]
    assert periods == sorted(EXCERPT_VALUES)


def test_blank_month_is_omitted_and_not_stored_as_zero(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "gap.csv"
    _rewrite(FIXTURE, path, {"2025-10": {"OBS_VALUE": "", "OBS_STATUS": "M"}})
    parsed = parse_ecb_sdw_csv(path.read_text(encoding="utf-8"), retrieved_at=RETRIEVED)
    assert parsed.omitted_periods == ("2025-10",)
    assert all(row.period_start != date(2025, 10, 1) for row in parsed.observations)
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
    assert result.observations_received == 3
    assert result.observations_newly_stored == 3
    assert result.retrieval_id is None
    assert {row.period_start for row in store.all_observations()} == {
        date(2025, 9, 1),
        date(2025, 11, 1),
        date(2025, 12, 1),
    }


def test_eurostat_series_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "eurostat.csv"
    _rewrite(
        FIXTURE,
        path,
        {
            "2025-09": {
                "KEY": "ICP.M.U2.N.000000.4.INX",
                "ADJUSTMENT": "N",
                "STS_INSTITUTION": "4",
                "COMPILING_ORG": "4D0",
                "SOURCE_AGENCY": "4D0",
                "TITLE_COMPL": (
                    "Euro area (changing composition) - HICP - Overall index, "
                    "Index, Eurostat, Neither seasonally nor working day adjusted"
                ),
            },
        },
    )
    result = _adapter(path, RETRIEVED).fetch()
    assert result.observations == ()
    assert result.errors
    assert "refusing" in result.errors[0].message


def test_contradictory_values_are_not_treated_as_vintages(tmp_path: Path) -> None:
    path = tmp_path / "two.csv"
    text = FIXTURE.read_text(encoding="utf-8")
    extra = text.strip().splitlines()[-1].replace("129.7338491760366", "130.0")
    body = text if text.endswith("\n") else f"{text}\n"
    path.write_text(f"{body}{extra}\n", encoding="utf-8")
    result = _adapter(path, RETRIEVED).fetch()
    assert result.observations == ()
    assert result.errors
    assert "vintage panel" in result.errors[0].message


def test_second_fixture_ingest_inserts_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
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
    assert first.source_id == SOURCE_ID
    assert first.dataset_id == DATASET_ID
    assert first.data_provenance == "latest_revised"
    assert first.observations_received == 4
    assert first.observations_newly_stored == 4
    assert first.retrieval_id is None
    assert psycopg.connect is _refuse_database
    metadata = adapter.last_parse
    assert metadata is not None
    assert metadata.compiler_sentence == COMPILER_SENTENCE
    assert metadata.vintage_class == "latest_revised"
    assert metadata.omitted_periods == ()
    first_ids = {row.period_start: row.observation_id for row in store.all_observations()}

    later = datetime(2026, 10, 23, 9, 0, tzinfo=UTC)
    adapter.prior_points = _points(store)
    adapter.retrieved_at = later
    second, again = collect_registered_adapter(
        store_backend="memory",
        adapter=adapter,
        source_id=SOURCE_ID,
        collected_at=later,
        live=False,
    )
    assert again is store
    assert second.outcome == "unchanged"
    assert second.observations_newly_stored == 0
    assert second.observations_unchanged == 4
    assert len(store.all_observations()) == 4
    assert {row.period_start: row.observation_id for row in store.all_observations()} == first_ids


def test_changed_value_is_a_new_row(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _bind_memory(monkeypatch)
    adapter = _adapter(FIXTURE, RETRIEVED)
    collect_registered_adapter(
        store_backend="memory",
        adapter=adapter,
        source_id=SOURCE_ID,
        collected_at=RETRIEVED,
        live=False,
    )
    kept = {
        row.period_start: row.observation_id
        for row in store.all_observations()
        if row.period_start != date(2025, 12, 1)
    }
    original_december = next(
        row.observation_id
        for row in store.all_observations()
        if row.period_start == date(2025, 12, 1)
    )
    changed = tmp_path / "changed.csv"
    _rewrite(FIXTURE, changed, {"2025-12": {"OBS_VALUE": "130.1"}})
    later = datetime(2026, 10, 23, 9, 0, tzinfo=UTC)
    follow_up = _adapter(changed, later, _points(store))
    second, _bound = collect_registered_adapter(
        store_backend="memory",
        adapter=follow_up,
        source_id=SOURCE_ID,
        collected_at=later,
        live=False,
    )
    assert second.observations_newly_stored == 1
    assert second.observations_unchanged == 3
    december = [
        row for row in store.all_observations() if row.period_start == date(2025, 12, 1)
    ]
    assert len(december) == 2
    revised = next(row for row in december if row.raw_value == "130.1")
    assert revised.observation_id != original_december
    assert any(row.observation_id == original_december for row in december)
    for period_start, observation_id in kept.items():
        match = next(row for row in store.all_observations() if row.period_start == period_start)
        assert match.observation_id == observation_id
        assert match.raw_value == EXCERPT_VALUES[period_start]
