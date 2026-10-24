"""Wave 1 euro-area adapters: rights, schema 1.0, and a second ingest that adds nothing."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import psycopg
import pytest

from aqil_research.adapters.ecb_fm_dfr.adapter import EcbFmDfrAdapter, EcbFmDfrAdapterConfig
from aqil_research.adapters.ecb_fm_dfr.client import series_csv_url as dfr_url
from aqil_research.adapters.ecb_fm_dfr.constants import DATASET_ID as DFR_DATASET
from aqil_research.adapters.ecb_fm_dfr.constants import SOURCE_ID as DFR_SOURCE
from aqil_research.adapters.ecb_fm_dfr.stability import StoredEcbPoint as StoredDfrPoint
from aqil_research.adapters.ecb_hicp_core.adapter import (
    EcbHicpCoreAdapter,
    EcbHicpCoreAdapterConfig,
)
from aqil_research.adapters.ecb_hicp_core.client import series_csv_url as core_url
from aqil_research.adapters.ecb_hicp_core.constants import DATASET_ID as CORE_DATASET
from aqil_research.adapters.ecb_hicp_core.constants import SOURCE_ID as CORE_SOURCE
from aqil_research.adapters.ecb_hicp_core.stability import StoredEcbPoint as StoredCorePoint
from aqil_research.adapters.eurostat_gdp.adapter import EurostatSeriesAdapter as GdpAdapter
from aqil_research.adapters.eurostat_gdp.adapter import EurostatSeriesAdapterConfig as GdpConfig
from aqil_research.adapters.eurostat_gdp.client import series_json_url as gdp_url
from aqil_research.adapters.eurostat_gdp.constants import DATASET_ID as GDP_DATASET
from aqil_research.adapters.eurostat_gdp.constants import DIMENSIONS as GDP_DIMENSIONS
from aqil_research.adapters.eurostat_gdp.constants import SOURCE_ID as GDP_SOURCE
from aqil_research.adapters.eurostat_gdp.stability import StoredEurostatPoint
from aqil_research.adapters.eurostat_industry.adapter import (
    EurostatSeriesAdapter as IndustryAdapter,
)
from aqil_research.adapters.eurostat_industry.adapter import (
    EurostatSeriesAdapterConfig as IndustryConfig,
)
from aqil_research.adapters.eurostat_industry.client import series_json_url as industry_url
from aqil_research.adapters.eurostat_industry.constants import DATASET_ID as INDUSTRY_DATASET
from aqil_research.adapters.eurostat_industry.constants import DIMENSIONS as INDUSTRY_DIMENSIONS
from aqil_research.adapters.eurostat_industry.constants import SOURCE_ID as INDUSTRY_SOURCE
from aqil_research.adapters.eurostat_retail.adapter import EurostatSeriesAdapter as RetailAdapter
from aqil_research.adapters.eurostat_retail.adapter import (
    EurostatSeriesAdapterConfig as RetailConfig,
)
from aqil_research.adapters.eurostat_retail.client import series_json_url as retail_url
from aqil_research.adapters.eurostat_retail.constants import DATASET_ID as RETAIL_DATASET
from aqil_research.adapters.eurostat_retail.constants import DIMENSIONS as RETAIL_DIMENSIONS
from aqil_research.adapters.eurostat_retail.constants import SOURCE_ID as RETAIL_SOURCE
from aqil_research.adapters.eurostat_unemployment.adapter import (
    EurostatSeriesAdapter as UnemploymentAdapter,
)
from aqil_research.adapters.eurostat_unemployment.adapter import (
    EurostatSeriesAdapterConfig as UnemploymentConfig,
)
from aqil_research.adapters.eurostat_unemployment.client import series_json_url as unemployment_url
from aqil_research.adapters.eurostat_unemployment.constants import (
    DATASET_ID as UNEMPLOYMENT_DATASET,
)
from aqil_research.adapters.eurostat_unemployment.constants import (
    DIMENSIONS as UNEMPLOYMENT_DIMENSIONS,
)
from aqil_research.adapters.eurostat_unemployment.constants import SOURCE_ID as UNEMPLOYMENT_SOURCE
from aqil_research.collection.service import collect_registered_adapter
from aqil_research.contracts.observation import SeriesProvenance
from aqil_research.methods.census_adv_orders import CensusAdvOrdersMethod
from aqil_research.methods.macro_conditions import MacroConditionsMethod
from aqil_research.methods.period_change import PeriodChangeMethod
from aqil_research.methods.sahm_registered import SahmAnalyticalMethod
from aqil_research.methods.sloos_cil import SloosCilMethod
from aqil_research.sources.rights import FIRST_LIVE_OPERATIONS, RightsDecision, load_source_rights
from aqil_research.vintages.store import InMemoryObservationStore

FIXTURES = Path(__file__).parent / "fixtures"
FRAGMENTS = Path(__file__).resolve().parents[3] / "docs" / "sources" / "fragments"
RETRIEVED = datetime(2026, 10, 24, 4, 0, tzinfo=UTC)
LATER = datetime(2026, 10, 24, 5, 0, tzinfo=UTC)


def _refuse_database(*args: object, **kwargs: object) -> None:
    raise AssertionError(f"database connection is not allowed: {args!r} {kwargs!r}")


def _bind(monkeypatch: pytest.MonkeyPatch, source_id: str) -> InMemoryObservationStore:
    monkeypatch.setattr("psycopg.connect", _refuse_database)
    records = load_source_rights(FRAGMENTS / f"{source_id}.csv")
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


def _eurostat_fixture(
    dimensions: tuple[tuple[str, str, str], ...], periods: list[tuple[str, str | None]]
) -> str:
    dimension: dict[str, object] = {}
    for name, code, label in dimensions:
        dimension[name] = {"category": {"index": {code: 0}, "label": {code: label}}}
    dimension["time"] = {
        "category": {
            "index": {token: index for index, (token, _value) in enumerate(periods)},
            "label": {token: token for token, _value in periods},
        },
    }
    values = {
        str(index): json.loads(value)
        for index, (_token, value) in enumerate(periods)
        if value is not None
    }
    payload = {
        "source": "ESTAT",
        "class": "dataset",
        "extension": {"agencyId": "ESTAT", "id": "FIXTURE"},
        "id": [name for name, _code, _label in dimensions] + ["time"],
        "size": [1 for _item in dimensions] + [len(periods)],
        "dimension": dimension,
        "value": values,
    }
    return json.dumps(payload)


def test_requests_do_not_ask_for_history() -> None:
    for url in (core_url(), dfr_url(), gdp_url(), unemployment_url(), industry_url(), retail_url()):
        assert "includeHistory" not in url
        assert url.startswith("https://")


def test_new_dataset_ids_stay_out_of_existing_methods() -> None:
    required = {
        dataset_id
        for method in (
            SahmAnalyticalMethod(),
            SloosCilMethod(),
            CensusAdvOrdersMethod(),
            PeriodChangeMethod(),
            MacroConditionsMethod(),
        )
        for dataset_id in method.required_dataset_ids()
    }
    for dataset_id in (
        CORE_DATASET,
        DFR_DATASET,
        GDP_DATASET,
        UNEMPLOYMENT_DATASET,
        INDUSTRY_DATASET,
        RETAIL_DATASET,
    ):
        assert dataset_id not in required


def test_rights_fragments_clear_first_live_use() -> None:
    expected = {
        CORE_SOURCE: CORE_DATASET,
        DFR_SOURCE: DFR_DATASET,
        GDP_SOURCE: GDP_DATASET,
        UNEMPLOYMENT_SOURCE: UNEMPLOYMENT_DATASET,
        INDUSTRY_SOURCE: INDUSTRY_DATASET,
        RETAIL_SOURCE: RETAIL_DATASET,
    }
    for source_id, dataset_id in expected.items():
        records = load_source_rights(FRAGMENTS / f"{source_id}.csv")
        assert len(records) == 1
        record = records[0]
        assert record.dataset_id == dataset_id
        assert record.assessed_on.isoformat() == "2026-10-24"
        for operation in FIRST_LIVE_OPERATIONS:
            assert record.decision_for(operation) == RightsDecision.PERMITTED
        assert "latest-revised" in record.evidence_note or "latest revised" in record.evidence_note
        assert "EU27" in record.evidence_note


def test_blocked_credit_fragments_are_not_cleared_for_ingest() -> None:
    for source_id in ("ecb_bls_credit_standards", "ecb_bsi_loans_nfc"):
        record = load_source_rights(FRAGMENTS / f"{source_id}.csv")[0]
        assert record.operational_status.value == "disabled"
        assert record.m1_role.value != "first_live_provider"
        for operation in FIRST_LIVE_OPERATIONS:
            assert record.decision_for(operation) != RightsDecision.PERMITTED


@pytest.mark.parametrize(
    ("source_id", "build"),
    [
        (
            CORE_SOURCE,
            lambda path, prior: EcbHicpCoreAdapter(
                config=EcbHicpCoreAdapterConfig(live=False, fixture_path=path),
                retrieved_at=RETRIEVED,
                prior_points=prior,
            ),
        ),
        (
            DFR_SOURCE,
            lambda path, prior: EcbFmDfrAdapter(
                config=EcbFmDfrAdapterConfig(live=False, fixture_path=path),
                retrieved_at=RETRIEVED,
                prior_points=prior,
            ),
        ),
    ],
)
def test_ecb_fixture_second_ingest_inserts_nothing(
    monkeypatch: pytest.MonkeyPatch, source_id: str, build
) -> None:
    store = _bind(monkeypatch, source_id)
    path = FIXTURES / source_id / "excerpt.csv"
    adapter = build(path, ())
    first, _bound = collect_registered_adapter(
        store_backend="memory",
        adapter=adapter,
        source_id=source_id,
        collected_at=RETRIEVED,
        live=False,
    )
    assert first.outcome == "success"
    assert first.observations_newly_stored > 0
    assert first.data_provenance == "latest_revised"
    assert psycopg.connect is _refuse_database
    assert all(
        row.series_provenance == SeriesProvenance.LATEST_REVISED for row in store.all_observations()
    )
    ids = {row.period_start: row.observation_id for row in store.all_observations()}
    point_type = StoredCorePoint if source_id == CORE_SOURCE else StoredDfrPoint
    priors = tuple(
        point_type(
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
    follow_up = build(path, priors)
    follow_up.retrieved_at = LATER
    second, _again = collect_registered_adapter(
        store_backend="memory",
        adapter=follow_up,
        source_id=source_id,
        collected_at=LATER,
        live=False,
    )
    assert second.outcome == "unchanged"
    assert second.observations_newly_stored == 0
    assert {row.period_start: row.observation_id for row in store.all_observations()} == ids


@pytest.mark.parametrize(
    ("source_id", "adapter_type", "config_type", "dimensions", "periods"),
    [
        (
            GDP_SOURCE,
            GdpAdapter,
            GdpConfig,
            GDP_DIMENSIONS,
            [("2026-Q1", "116.5"), ("2026-Q2", None), ("2026-Q3", "116.9")],
        ),
        (
            UNEMPLOYMENT_SOURCE,
            UnemploymentAdapter,
            UnemploymentConfig,
            UNEMPLOYMENT_DIMENSIONS,
            [("2026-07", "6.3"), ("2026-08", None), ("2026-09", "6.4")],
        ),
        (
            INDUSTRY_SOURCE,
            IndustryAdapter,
            IndustryConfig,
            INDUSTRY_DIMENSIONS,
            [("2026-06", "97.1"), ("2026-07", None), ("2026-08", "97.5")],
        ),
        (
            RETAIL_SOURCE,
            RetailAdapter,
            RetailConfig,
            RETAIL_DIMENSIONS,
            [("2026-06", "103.8"), ("2026-07", None), ("2026-08", "104.3")],
        ),
    ],
)
def test_eurostat_fixture_omits_gaps_and_second_ingest_inserts_nothing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    source_id: str,
    adapter_type,
    config_type,
    dimensions,
    periods,
) -> None:
    store = _bind(monkeypatch, source_id)
    path = tmp_path / "series.json"
    path.write_text(_eurostat_fixture(dimensions, periods), encoding="utf-8")
    adapter = adapter_type(
        config=config_type(live=False, fixture_path=path), retrieved_at=RETRIEVED
    )
    first, _bound = collect_registered_adapter(
        store_backend="memory",
        adapter=adapter,
        source_id=source_id,
        collected_at=RETRIEVED,
        live=False,
    )
    assert first.outcome == "success"
    assert first.observations_newly_stored == 2
    assert adapter.last_parse is not None
    assert adapter.last_parse.omitted_periods == (periods[1][0],)
    assert all(row.geography == "EA21" for row in store.all_observations())
    assert all(
        row.series_provenance == SeriesProvenance.LATEST_REVISED for row in store.all_observations()
    )
    assert psycopg.connect is _refuse_database
    ids = {row.period_start: row.observation_id for row in store.all_observations()}
    priors = tuple(
        StoredEurostatPoint(
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
    follow_up = adapter_type(
        config=config_type(live=False, fixture_path=path),
        retrieved_at=LATER,
        prior_points=priors,
    )
    second, _again = collect_registered_adapter(
        store_backend="memory",
        adapter=follow_up,
        source_id=source_id,
        collected_at=LATER,
        live=False,
    )
    assert second.outcome == "unchanged"
    assert second.observations_newly_stored == 0
    assert {row.period_start: row.observation_id for row in store.all_observations()} == ids


def test_eurostat_refuses_eu27(tmp_path: Path) -> None:
    text = _eurostat_fixture(GDP_DIMENSIONS, [("2026-Q1", "116.5"), ("2026-Q2", "116.9")])
    text = text.replace("EA21", "EU27_2020").replace(
        "Euro area \\u2013 21 countries (from 2026)", "European Union"
    )
    path = tmp_path / "eu27.json"
    path.write_text(text, encoding="utf-8")
    result = GdpAdapter(
        config=GdpConfig(live=False, fixture_path=path), retrieved_at=RETRIEVED
    ).fetch()
    assert result.observations == ()
    assert result.errors


def test_deposit_facility_without_ecb_name_is_refused(tmp_path: Path) -> None:
    source = (FIXTURES / DFR_SOURCE / "excerpt.csv").read_text(encoding="utf-8")
    path = tmp_path / "other.csv"
    path.write_text(
        source.replace("provided by ECB", "provided by another compiler"), encoding="utf-8"
    )
    result = EcbFmDfrAdapter(
        config=EcbFmDfrAdapterConfig(live=False, fixture_path=path),
        retrieved_at=RETRIEVED,
    ).fetch()
    assert result.observations == ()
    assert result.errors
