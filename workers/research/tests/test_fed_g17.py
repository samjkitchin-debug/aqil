"""G.17 total industrial production index: fixture, gaps, and idempotent ingest."""

from __future__ import annotations

import csv
import io
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

import aqil_research.adapters.fed_g17.adapter as g17_adapter
from aqil_research.adapters.fed_g17.client import PACKAGE_URL
from aqil_research.adapters.fed_g17.package import G17PackageError, extract_total_index
from aqil_research.adapters.fed_g17.parse import (
    BOARD_DESCRIPTION,
    BOARD_UNIT_LABEL,
    DATASET_ID,
    SERIES_ID,
    SOURCE_ID,
    UNIT,
    parse_g17_payload,
)
from aqil_research.adapters.fed_g17.stability import StoredG17Point, stabilise_g17_vintages
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
    RightsDecision,
    blocked_operations,
    load_source_rights,
)
from aqil_research.vintages.store import InMemoryObservationStore

FIXTURE = Path(__file__).parent / "fixtures" / "fed_g17" / "table4_total_index_excerpt.csv"
FRAGMENT = (
    Path(__file__).resolve().parents[3]
    / "docs"
    / "sources"
    / "fragments"
    / "federal_reserve_g17_total_ip.csv"
)
RETRIEVED = datetime(2026, 10, 22, 9, 0, tzinfo=UTC)
TERMS_URL = "https://www.federalreserve.gov/disclaimer.htm"

EXPECTED_VALUES = {
    date(1919, 1, 1): "4.8739",
    date(1919, 2, 1): "4.6585",
    date(1919, 3, 1): "4.5238",
    date(2026, 7, 1): "103.2006",
    date(2026, 8, 1): "103.2664",
    date(2026, 9, 1): "103.9506",
}


def _package_csv(periods: list[str], row: list[str]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(
        [
            "Description:",
            "Unit:",
            "Multiplier:",
            "Currency:",
            "Unique Identifier:",
            "Series Name:",
            *periods,
        ],
    )
    writer.writerow(row)
    return buffer.getvalue()


def test_fixture_parses_total_index_units_and_seasonal_adjustment() -> None:
    extracted = extract_total_index(FIXTURE.read_text(encoding="utf-8"))
    assert extracted["description"] == BOARD_DESCRIPTION
    assert extracted["unit_label"] == BOARD_UNIT_LABEL
    assert extracted["series_id"] == SERIES_ID
    assert extracted["omitted_periods"] == []

    fetch = _adapter(FIXTURE).fetch()
    assert fetch.errors == ()
    observations = fetch.observations
    assert len(observations) == len(EXPECTED_VALUES)
    for observation in observations:
        assert observation.schema_version == "1.0"
        assert observation.dataset_id == DATASET_ID
        assert observation.unit == UNIT
        assert observation.seasonal_adjustment == SeasonalAdjustment.SEASONALLY_ADJUSTED
        assert observation.frequency.value == "monthly"
        assert observation.geography == "US"
        assert observation.series_provenance == SeriesProvenance.LATEST_REVISED
        assert observation.availability_precision == AvailabilityPrecision.UNKNOWN
        assert observation.earliest_model_available_at is None
        assert observation.source_locator == PACKAGE_URL
        assert observation.raw_value == EXPECTED_VALUES[observation.period_start]
    assert {observation.raw_value for observation in observations} == set(EXPECTED_VALUES.values())
    assert "99.8772" not in {observation.raw_value for observation in observations}
    assert all(observation.raw_value not in {"", "0", "ND", "NA"} for observation in observations)


def test_nd_blank_and_na_are_omitted(tmp_path: Path) -> None:
    path = tmp_path / "gap.csv"
    path.write_text(
        _package_csv(
            ["1919-01", "1919-02", "1919-03", "2026-09"],
            [
                BOARD_DESCRIPTION,
                BOARD_UNIT_LABEL,
                "1",
                "NA",
                SERIES_ID,
                "IP.B50001.S",
                "4.8739",
                "ND",
                "",
                "NA",
            ],
        ),
        encoding="utf-8",
    )
    extracted = extract_total_index(path.read_text(encoding="utf-8"))
    omitted = {item["period"]: item["token"] for item in extracted["omitted_periods"]}
    assert omitted == {"1919-02": "ND", "1919-03": "", "2026-09": "NA"}

    fetch = _adapter(path).fetch()
    assert [observation.period_start for observation in fetch.observations] == [date(1919, 1, 1)]
    assert fetch.observations[0].raw_value == "4.8739"
    assert fetch.observations[0].unit == UNIT
    assert fetch.observations[0].seasonal_adjustment == SeasonalAdjustment.SEASONALLY_ADJUSTED


def test_parser_does_not_store_nd_blank_or_na_as_zero() -> None:
    parsed = parse_g17_payload(
        {
            "series_id": SERIES_ID,
            "observations": [
                {"period": "1919-01", "value": "4.8739"},
                {"period": "1919-02", "value": "ND"},
                {"period": "1919-03", "value": " "},
                {"period": "2026-09", "value": "NA"},
            ],
        },
        adapter_version="test",
        retrieved_at=RETRIEVED,
        collection_vintage_date=RETRIEVED.date(),
    )
    assert [observation.period_start for observation in parsed.observations] == [date(1919, 1, 1)]
    assert parsed.observations[0].raw_value == "4.8739"
    assert "1919-02" in parsed.warnings[0]


def test_series_code_with_a_different_description_is_rejected() -> None:
    text = _package_csv(
        ["1919-01"],
        [
            "Manufacturing (SIC); s.a. IP",
            BOARD_UNIT_LABEL,
            "1",
            "NA",
            SERIES_ID,
            "IP.B50001.S",
            "4.8739",
        ],
    )
    with pytest.raises(G17PackageError, match="did not confirm"):
        extract_total_index(text)


def test_a_different_series_code_is_not_bound() -> None:
    text = _package_csv(
        ["1919-01"],
        [
            BOARD_DESCRIPTION,
            BOARD_UNIT_LABEL,
            "1",
            "NA",
            "G17/IP_MARKET_GROUPS/IP.OTHER",
            "IP.OTHER",
            "4.8739",
        ],
    )
    with pytest.raises(G17PackageError, match="was not in the G.17 package"):
        extract_total_index(text)


def test_unchanged_value_keeps_the_first_observation_id() -> None:
    payload = {
        "series_id": SERIES_ID,
        "observations": [{"period": "2026-09", "value": "103.9506"}],
    }
    first = stabilise_g17_vintages(payload, (), RETRIEVED)
    parsed = parse_g17_payload(
        first,
        adapter_version="test",
        retrieved_at=RETRIEVED,
        collection_vintage_date=RETRIEVED.date(),
    )
    stored = parsed.observations[0]
    assert stored.series_provenance == SeriesProvenance.LATEST_REVISED
    assert stored.availability_precision == AvailabilityPrecision.UNKNOWN
    prior = StoredG17Point(
        period_start=stored.period_start,
        observation_id=stored.observation_id,
        raw_value=stored.raw_value,
        provider_vintage_date=stored.provider_vintage_date,
        source_release_at=stored.source_release_at,
        retrieved_at=stored.retrieved_at,
    )
    later = datetime(2026, 10, 23, 9, 0, tzinfo=UTC)
    repeat = stabilise_g17_vintages(payload, (prior,), later)
    assert repeat["observations"][0]["observation_id"] == stored.observation_id
    assert repeat["observations"][0]["vintage"] == stored.provider_vintage_date.isoformat()
    assert repeat["observations"][0]["source_release_at"] == RETRIEVED.isoformat()


def test_changed_value_is_a_new_row() -> None:
    payload = {
        "series_id": SERIES_ID,
        "observations": [{"period": "2026-09", "value": "103.9506"}],
    }
    first = stabilise_g17_vintages(payload, (), RETRIEVED)
    parsed = parse_g17_payload(
        first,
        adapter_version="test",
        retrieved_at=RETRIEVED,
        collection_vintage_date=RETRIEVED.date(),
    )
    stored = parsed.observations[0]
    prior = StoredG17Point(
        period_start=stored.period_start,
        observation_id=stored.observation_id,
        raw_value=stored.raw_value,
        provider_vintage_date=stored.provider_vintage_date,
        source_release_at=stored.source_release_at,
        retrieved_at=stored.retrieved_at,
    )
    changed = stabilise_g17_vintages(
        {
            "series_id": SERIES_ID,
            "observations": [{"period": "2026-09", "value": "104.1000"}],
        },
        (prior,),
        datetime(2026, 10, 23, 9, 0, tzinfo=UTC),
    )
    assert changed["observations"][0]["observation_id"] != stored.observation_id


def test_second_fixture_ingest_inserts_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    shared: dict[str, InMemoryObservationStore] = {}

    class SharedStore(InMemoryObservationStore):
        def __new__(cls) -> InMemoryObservationStore:
            if "store" not in shared:
                shared["store"] = InMemoryObservationStore()
            return shared["store"]

    monkeypatch.setattr(
        "aqil_research.collection.service.InMemoryObservationStore",
        SharedStore,
    )
    monkeypatch.setattr(
        "aqil_research.collection.service.load_source_rights",
        lambda path=None: load_source_rights(FRAGMENT),
    )

    def refuse_connect(*args: object, **kwargs: object) -> None:
        raise AssertionError(f"refusing database connection {args!r} {kwargs!r}")

    monkeypatch.setattr("aqil_research.collection.service.psycopg.connect", refuse_connect)
    adapter = _adapter(FIXTURE)
    first, store = collect_registered_adapter(
        store_backend="memory",
        adapter=adapter,
        source_id=SOURCE_ID,
        collected_at=RETRIEVED,
        live=False,
    )
    second, again = collect_registered_adapter(
        store_backend="memory",
        adapter=adapter,
        source_id=SOURCE_ID,
        collected_at=RETRIEVED,
        live=False,
    )
    assert first.outcome == "success"
    assert first.observations_newly_stored == len(EXPECTED_VALUES)
    assert second.outcome == "unchanged"
    assert second.observations_newly_stored == 0
    assert second.observations_unchanged == len(EXPECTED_VALUES)
    assert len(store.all_observations()) == len(EXPECTED_VALUES)
    assert again is store


def test_rights_fragment_loads() -> None:
    records = load_source_rights(FRAGMENT)
    assert len(records) == 1
    record = records[0]
    assert record.source_id == SOURCE_ID
    assert record.dataset_id == DATASET_ID
    assert record.series_or_dataset_code == SERIES_ID
    assert record.access_url == PACKAGE_URL
    assert record.terms_url == TERMS_URL
    assert TERMS_URL in record.evidence_urls
    assert PACKAGE_URL in record.evidence_urls
    assert record.m1_role == M1Role.FIRST_LIVE_PROVIDER
    assert record.operational_status.value == "enabled"
    assert record.attribution == AttributionRequirement.REQUIRED
    assert record.ai_processing == RightsDecision.UNKNOWN
    assert record.ai_model_training == RightsDecision.UNKNOWN
    assert record.assessed_on == date(2026, 10, 22)
    assert blocked_operations(record, FIRST_LIVE_OPERATIONS) == ()
    note = record.evidence_note.casefold()
    assert "latest revised" in note
    assert "not a historical vintage panel" in note
    assert "macro_conditions_panel" in note
    assert "period_level_change" in note
    assert g17_adapter.__doc__ is not None
    assert "MACRO_CONDITIONS_PANEL" in g17_adapter.__doc__
    assert "PERIOD_LEVEL_CHANGE" in g17_adapter.__doc__
    assert DATASET_ID in g17_adapter.__doc__
    assert g17_adapter.ADAPTER_VERSION == "1.0.0"


def test_current_methods_do_not_consume_this_dataset() -> None:
    required = (
        SahmAnalyticalMethod().required_dataset_ids()
        + SloosCilMethod().required_dataset_ids()
        + CensusAdvOrdersMethod().required_dataset_ids()
        + MacroConditionsMethod().required_dataset_ids()
        + PeriodChangeMethod().required_dataset_ids()
    )
    assert DATASET_ID not in required


def _adapter(path: Path) -> g17_adapter.FedG17Adapter:
    return g17_adapter.FedG17Adapter(
        config=g17_adapter.FedG17AdapterConfig(live=False, fixture_path=path),
        retrieved_at=RETRIEVED,
    )
