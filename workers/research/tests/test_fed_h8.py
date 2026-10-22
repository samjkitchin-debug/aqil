"""Board H.8 bank credit: one weekly series, latest-revised, no development database."""

from __future__ import annotations

import csv
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

import aqil_research.adapters.fed_h8 as h8_package
from aqil_research.adapters.fed_h8 import adapter as h8_adapter
from aqil_research.adapters.fed_h8.adapter import FedH8Adapter, FedH8AdapterConfig
from aqil_research.adapters.fed_h8.client import PACKAGE_URL
from aqil_research.adapters.fed_h8.package import H8PackageError, series_from_h8_bytes
from aqil_research.adapters.fed_h8.parse import DATASET_ID, SOURCE_ID, parse_h8_payload
from aqil_research.adapters.fed_h8.stability import StoredH8Point, stabilise_h8_vintages
from aqil_research.collection import service as collection_service
from aqil_research.collection.service import collect_registered_adapter
from aqil_research.contracts.observation import (
    AvailabilityPrecision,
    EconomicObservation,
    Frequency,
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
    REGISTER_COLUMNS,
    AttributionRequirement,
    M1Role,
    RightsDecision,
    load_source_rights,
)
from aqil_research.vintages.store import InMemoryObservationStore

FIXTURE = Path(__file__).parent / "fixtures" / "fed_h8" / "b1001ncba_excerpt.xml"
FRAGMENT = (
    Path(__file__).resolve().parents[3]
    / "docs"
    / "sources"
    / "fragments"
    / "federal_reserve_h8_bank_credit.csv"
)
DESCRIPTION = "Bank credit, all commercial banks, seasonally adjusted"
RETRIEVED = datetime(2026, 10, 22, 8, 0, tzinfo=UTC)
SERIES_ATTRIBUTES = (
    'FREQ="19" SA="SA" UNIT_MULT="1000000" CURRENCY="USD" UNIT="Currency" '
    'H8_UNITS="LEVEL" BG="CB" ITEM="1001"'
)


@pytest.fixture(autouse=True)
def _block_database_connections(monkeypatch: pytest.MonkeyPatch) -> None:
    def _blocked(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("H.8 tests must not open a database")

    monkeypatch.setattr("psycopg.connect", _blocked)


def test_fixture_excerpt_has_the_board_header_and_description() -> None:
    text = FIXTURE.read_text(encoding="utf-8")
    assert "H.8 Assets and Liabilities of Commercial Banks in the United States" in text
    assert DESCRIPTION in text
    assert 'SERIES_NAME="B1001NCBA"' in text
    assert "fred.stlouisfed.org" not in text


def test_package_binds_the_weekly_series_from_the_fixture() -> None:
    payload = series_from_h8_bytes(FIXTURE.read_bytes())
    assert payload["series_id"] == "B1001NCBA"
    assert payload["description"] == DESCRIPTION
    assert payload["omitted_periods"] == []
    assert payload["observations"] == [
        {"period": "1973-01-03", "value": "567255.3"},
        {"period": "1973-01-10", "value": "565505.4"},
        {"period": "1973-01-17", "value": "565347.7"},
    ]


def test_nd_and_blank_are_omitted_and_weeks_are_not_filled() -> None:
    payload = series_from_h8_bytes(_gap_excerpt().encode("utf-8"))
    assert payload["observations"] == [
        {"period": "2024-01-03", "value": "1.5"},
        {"period": "2024-01-24", "value": "0"},
        {"period": "2024-02-07", "value": "2.0"},
    ]
    assert payload["omitted_periods"] == ["2024-01-10", "2024-01-17", "2024-01-31"]
    parsed = parse_h8_payload(
        payload,
        adapter_version="fed_h8_b1001ncba:1.0.0",
        retrieved_at=RETRIEVED,
        collection_vintage_date=RETRIEVED.date(),
    )
    periods = [row.period_start for row in parsed.observations]
    assert periods == [date(2024, 1, 3), date(2024, 1, 24), date(2024, 2, 7)]
    assert [row.raw_value for row in parsed.observations] == ["1.5", "0", "2.0"]
    assert "2024-01-31" not in {item.isoformat() for item in periods}
    assert parsed.omitted_periods == ("2024-01-10", "2024-01-17", "2024-01-31")
    stored = parsed.observations[0]
    assert stored.schema_version == "1.0"
    assert stored.frequency == Frequency.WEEKLY
    assert stored.seasonal_adjustment == SeasonalAdjustment.SEASONALLY_ADJUSTED
    assert stored.series_provenance == SeriesProvenance.LATEST_REVISED
    assert stored.availability_precision == AvailabilityPrecision.UNKNOWN
    assert stored.earliest_model_available_at is None
    assert stored.unit == "usd_millions"
    assert stored.dataset_id == DATASET_ID


def test_unchanged_value_keeps_the_first_identity() -> None:
    payload = {
        "series_id": "B1001NCBA",
        "description": DESCRIPTION,
        "observations": [{"period": "1973-01-03", "value": "567255.3"}],
        "omitted_periods": [],
    }
    first = stabilise_h8_vintages(payload, (), RETRIEVED)
    parsed = parse_h8_payload(
        first,
        adapter_version="test",
        retrieved_at=RETRIEVED,
        collection_vintage_date=RETRIEVED.date(),
    )
    stored = parsed.observations[0]
    prior = _point(stored)
    later = datetime(2026, 10, 23, 8, 0, tzinfo=UTC)
    repeat = stabilise_h8_vintages(
        {
            **payload,
            "observations": [{"period": "1973-01-03", "value": "567255.30"}],
        },
        (prior,),
        later,
    )
    assert repeat["observations"][0]["observation_id"] == stored.observation_id
    assert repeat["observations"][0]["value"] == "567255.3"
    assert repeat["observations"][0]["vintage"] == stored.provider_vintage_date.isoformat()
    changed = stabilise_h8_vintages(
        {
            **payload,
            "observations": [{"period": "1973-01-03", "value": "570000.0"}],
        },
        (prior,),
        later,
    )
    assert changed["observations"][0]["observation_id"] != stored.observation_id
    assert changed["observations"][0]["revision_basis"] == "latest_revised"


def test_second_fixture_ingest_inserts_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    shared = _share_memory_store(monkeypatch)
    _patch_rights(monkeypatch)
    first_result, _store = collect_registered_adapter(
        store_backend="memory",
        adapter=FedH8Adapter(
            config=FedH8AdapterConfig(live=False, fixture_path=FIXTURE),
            retrieved_at=RETRIEVED,
        ),
        source_id=SOURCE_ID,
        collected_at=RETRIEVED,
        live=False,
    )
    assert first_result.outcome == "success"
    assert first_result.observations_newly_stored == 3
    assert first_result.dataset_id == DATASET_ID
    held = shared.instance
    assert held is not None
    prior = tuple(_point(row) for row in held.all_observations())
    first_ids = [row.observation_id for row in held.all_observations()]

    later = datetime(2026, 10, 23, 9, 0, tzinfo=UTC)
    second_result, _second_store = collect_registered_adapter(
        store_backend="memory",
        adapter=FedH8Adapter(
            config=FedH8AdapterConfig(live=False, fixture_path=FIXTURE),
            retrieved_at=later,
            prior_points=prior,
        ),
        source_id=SOURCE_ID,
        collected_at=later,
        live=False,
    )
    assert second_result.outcome == "unchanged"
    assert second_result.observations_newly_stored == 0
    assert second_result.observations_unchanged == 3
    assert [row.observation_id for row in held.all_observations()] == first_ids
    assert len(held.all_observations()) == 3


def test_rights_fragment_clears_first_live_use() -> None:
    with FRAGMENT.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        assert tuple(reader.fieldnames or ()) == REGISTER_COLUMNS
    record = load_source_rights(FRAGMENT)[0]
    assert record.source_id == SOURCE_ID
    assert record.dataset_id == DATASET_ID
    assert record.series_or_dataset_code == "B1001NCBA"
    assert record.m1_role == M1Role.FIRST_LIVE_PROVIDER
    assert record.attribution == AttributionRequirement.REQUIRED
    assert record.terms_url == "https://www.federalreserve.gov/disclaimer.htm"
    assert record.terms_url in record.evidence_urls
    assert record.assessed_on == date(2026, 10, 22)
    assert record.ai_processing == RightsDecision.UNKNOWN
    assert record.ai_model_training == RightsDecision.UNKNOWN
    for operation in FIRST_LIVE_OPERATIONS:
        assert record.decision_for(operation) == RightsDecision.PERMITTED
    note = record.evidence_note
    assert "latest-revised, not a vintage panel" in note
    assert DATASET_ID in note
    assert "MACRO_CONDITIONS_PANEL" in note
    assert "PERIOD_LEVEL_CHANGE" in note
    assert "bls.ln.LNS14000000" in note
    assert "fed.sloos.SUBLPDCILS_N.Q" in note
    assert "census.m3.adv.MDM.NO" in note


def test_current_methods_do_not_consume_this_dataset() -> None:
    methods = (
        SahmAnalyticalMethod(),
        SloosCilMethod(),
        CensusAdvOrdersMethod(),
        MacroConditionsMethod(),
        PeriodChangeMethod(),
    )
    for method in methods:
        assert DATASET_ID not in method.required_dataset_ids()
    text = " ".join(
        part for part in (h8_package.__doc__, h8_adapter.__doc__, FedH8Adapter.__doc__) if part
    )
    assert "latest-revised, not a vintage panel" in text
    for name in (
        "Sahm",
        "SLOOS",
        "Census",
        "MACRO_CONDITIONS_PANEL",
        "PERIOD_LEVEL_CHANGE",
        DATASET_ID,
    ):
        assert name in text


def test_client_stays_on_the_board_package() -> None:
    assert PACKAGE_URL == (
        "https://www.federalreserve.gov/datadownload/Output.aspx?rel=H8&filetype=zip"
    )


def test_wrong_description_is_rejected() -> None:
    body = (
        '<?xml version="1.0"?>\n<Root xmlns:common="urn:t" '
        'xmlns:frb="urn:t" xmlns:kf="urn:t">\n'
        + _series_xml(
            "B1001NCBA",
            "Some other bank series",
            ('<frb:Obs OBS_STATUS="A" OBS_VALUE="1" TIME_PERIOD="2024-01-03" />',),
        )
        + "</Root>\n"
    )
    with pytest.raises(H8PackageError):
        series_from_h8_bytes(body.encode("utf-8"))


def _point(row: EconomicObservation) -> StoredH8Point:
    return StoredH8Point(
        period_start=row.period_start,
        observation_id=row.observation_id,
        raw_value=row.raw_value,
        provider_vintage_date=row.provider_vintage_date,
        source_release_at=row.source_release_at,
        retrieved_at=row.retrieved_at,
        first_seen_at=row.first_seen_at,
    )


def _share_memory_store(monkeypatch: pytest.MonkeyPatch) -> type[InMemoryObservationStore]:
    class Shared(InMemoryObservationStore):
        instance: InMemoryObservationStore | None = None

        def __new__(cls) -> Shared:
            if cls.instance is None:
                cls.instance = super().__new__(cls)
            assert isinstance(cls.instance, Shared)
            return cls.instance

        def __init__(self) -> None:
            if getattr(self, "_ready", False):
                return
            super().__init__()
            self._ready = True

    monkeypatch.setattr(collection_service, "InMemoryObservationStore", Shared)
    return Shared


def _patch_rights(monkeypatch: pytest.MonkeyPatch) -> None:
    def _load() -> tuple[object, ...]:
        return load_source_rights() + load_source_rights(FRAGMENT)

    monkeypatch.setattr(collection_service, "load_source_rights", _load)


def _gap_excerpt() -> str:
    weekly = "\n".join(
        (
            '<frb:Obs OBS_STATUS="A" OBS_VALUE="1.5" TIME_PERIOD="2024-01-03" />',
            '<frb:Obs OBS_STATUS="ND" OBS_VALUE="ND" TIME_PERIOD="2024-01-10" />',
            '<frb:Obs OBS_STATUS="A" TIME_PERIOD="2024-01-17" />',
            '<frb:Obs OBS_STATUS="ND" OBS_VALUE="123" TIME_PERIOD="2024-01-31" />',
            '<frb:Obs OBS_STATUS="A" OBS_VALUE="0" TIME_PERIOD="2024-01-24" />',
            '<frb:Obs OBS_STATUS="A" OBS_VALUE="2.0" TIME_PERIOD="2024-02-07" />',
        ),
    )
    monthly = '<frb:Obs OBS_STATUS="A" OBS_VALUE="9" TIME_PERIOD="2024-01-31" />'
    return (
        '<?xml version="1.0"?>\n<Root xmlns:common="urn:t" xmlns:frb="urn:t" '
        'xmlns:kf="urn:t">\n'
        + _series_xml("B1001NCBAM", DESCRIPTION, (monthly,), frequency="129")
        + _series_xml("B1001NCBA", DESCRIPTION, (weekly,))
        + "\n</Root>\n"
    )


def _series_xml(
    series_id: str,
    description: str,
    rows: tuple[str, ...],
    frequency: str = "19",
) -> str:
    attributes = SERIES_ATTRIBUTES.replace('FREQ="19"', f'FREQ="{frequency}"')
    body = "\n".join(rows)
    return (
        f'<kf:Series SERIES_NAME="{series_id}" {attributes}>\n'
        "<frb:Annotations><common:Annotation>"
        "<common:AnnotationType>Short Description</common:AnnotationType>"
        f"<common:AnnotationText>{description}</common:AnnotationText>"
        "</common:Annotation></frb:Annotations>\n"
        f"{body}\n</kf:Series>\n"
    )
