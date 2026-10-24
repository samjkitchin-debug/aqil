"""Bank Rate: rights, schema 1.0, omitted gaps, and a second ingest that adds nothing."""

from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

import psycopg
import pytest

import aqil_research.adapters.boe_bank_rate.adapter as adapter_module
from aqil_research.adapters.boe_bank_rate.adapter import (
    BoeBankRateAdapter,
    BoeBankRateAdapterConfig,
)
from aqil_research.adapters.boe_bank_rate.client import series_csv_url
from aqil_research.adapters.boe_bank_rate.constants import (
    DATASET_ID,
    METHOD_COMPATIBILITY_NOTE,
    SERIES_CODE,
    SERIES_DESCRIPTION,
    SOURCE_ID,
    UNIT_TEXT,
)
from aqil_research.adapters.boe_bank_rate.parse import parse_boe_bank_rate_csv
from aqil_research.adapters.boe_bank_rate.stability import StoredBoePoint
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

FIXTURE = Path(__file__).parent / "fixtures" / "boe_bank_rate" / "iudbedr_excerpt.csv"
FRAGMENT = (
    Path(__file__).resolve().parents[3]
    / "docs"
    / "sources"
    / "fragments"
    / "boe_official_bank_rate.csv"
)
RETRIEVED = datetime(2026, 10, 24, 9, 0, tzinfo=UTC)


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
    prior: tuple[StoredBoePoint, ...] = (),
) -> BoeBankRateAdapter:
    return BoeBankRateAdapter(
        config=BoeBankRateAdapterConfig(live=False, fixture_path=path),
        retrieved_at=retrieved_at,
        prior_points=prior,
    )


def _points(store: InMemoryObservationStore) -> tuple[StoredBoePoint, ...]:
    return tuple(
        StoredBoePoint(
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


def test_rights_fragment_clears_first_live_use() -> None:
    record = load_source_rights(FRAGMENT)[0]
    assert record.source_id == SOURCE_ID
    assert record.dataset_id == DATASET_ID
    assert record.series_or_dataset_code == SERIES_CODE
    assert record.m1_role == M1Role.FIRST_LIVE_PROVIDER
    assert record.operational_status == OperationalStatus.ENABLED
    assert record.attribution == AttributionRequirement.REQUIRED
    for operation in FIRST_LIVE_OPERATIONS:
        assert record.decision_for(operation) == RightsDecision.PERMITTED
    assert "Open Government Licence" in record.evidence_note
    assert "exchange rate" in record.evidence_note
    assert "latest-revised" in record.evidence_note
    assert "not a historical vintage panel" in record.evidence_note
    assert _collapsed(METHOD_COMPATIBILITY_NOTE) in _collapsed(record.evidence_note)


def test_adapter_documents_method_compatibility() -> None:
    assert _collapsed(METHOD_COMPATIBILITY_NOTE) in _collapsed(adapter_module.__doc__ or "")
    assert DATASET_ID not in SahmAnalyticalMethod().required_dataset_ids()
    assert DATASET_ID not in MacroConditionsMethod().required_dataset_ids()


def test_request_does_not_ask_for_provisional_data() -> None:
    url = series_csv_url()
    assert url.startswith("https://www.bankofengland.co.uk/boeapps/database/")
    assert "SeriesCodes=IUDBEDR" in url
    assert "VPD=" not in url
    assert "includeHistory" not in url


def test_excerpt_is_latest_revised_schema_v1() -> None:
    parsed = parse_boe_bank_rate_csv(FIXTURE.read_text(encoding="utf-8"), retrieved_at=RETRIEVED)
    assert parsed.series_key == SERIES_CODE
    assert parsed.compiler_sentence == SERIES_DESCRIPTION
    assert parsed.unit == UNIT_TEXT
    assert parsed.vintage_class == "latest_revised"
    assert len(parsed.observations) == 4
    assert [row.period_start for row in parsed.observations] == [
        date(2026, 10, 19),
        date(2026, 10, 20),
        date(2026, 10, 21),
        date(2026, 10, 22),
    ]
    for observation in parsed.observations:
        assert observation.schema_version == "1.0"
        assert observation.series_provenance == SeriesProvenance.LATEST_REVISED
        assert observation.availability_precision == AvailabilityPrecision.UNKNOWN
        assert observation.seasonal_adjustment == SeasonalAdjustment.UNKNOWN
        assert observation.frequency.value == "daily"
        assert observation.geography == "United Kingdom"
        assert observation.raw_value == "3.75"


def test_unavailable_day_is_omitted(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "gap.csv"
    text = FIXTURE.read_text(encoding="utf-8").replace(
        "20 Oct 2026,IUDBEDR,3.75",
        "20 Oct 2026,IUDBEDR,..",
    )
    path.write_text(text, encoding="utf-8")
    parsed = parse_boe_bank_rate_csv(path.read_text(encoding="utf-8"), retrieved_at=RETRIEVED)
    assert parsed.omitted_periods == ("20 Oct 2026",)
    assert all(row.raw_value != "0" for row in parsed.observations)
    _bind_memory(monkeypatch)
    result, _bound = collect_registered_adapter(
        store_backend="memory",
        adapter=_adapter(path, RETRIEVED),
        source_id=SOURCE_ID,
        collected_at=RETRIEVED,
        live=False,
    )
    assert result.observations_newly_stored == 3
    assert psycopg.connect is _refuse_database


def test_exchange_rate_code_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "fx.csv"
    text = (
        FIXTURE.read_text(encoding="utf-8")
        .replace("IUDBEDR", "XUDLERS")
        .replace(
            "Official Bank Rate",
            "Spot exchange rate",
        )
    )
    path.write_text(text, encoding="utf-8")
    result = _adapter(path, RETRIEVED).fetch()
    assert result.observations == ()
    assert result.errors


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
    assert first.observations_newly_stored == 4
    assert first.data_provenance == "latest_revised"
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
