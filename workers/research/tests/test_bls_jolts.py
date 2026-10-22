"""JTS000000000000000JOL from a JT flat-file excerpt. Tests never open a database."""

from __future__ import annotations

import shutil
from datetime import UTC, date, datetime
from pathlib import Path

import psycopg
import pytest

from aqil_research.adapters.bls_jolts import adapter as jolts_adapter
from aqil_research.adapters.bls_jolts.adapter import BlsJoltsAdapter, BlsJoltsAdapterConfig
from aqil_research.adapters.bls_jolts.constants import (
    COMPATIBILITY_NOTE,
    DATA_URL,
    DATASET_ID,
    SOURCE_ID,
)
from aqil_research.adapters.bls_jolts.parse import observations_from_payload
from aqil_research.adapters.bls_jolts.stability import StoredJoltsPoint, stabilise_jolts_vintages
from aqil_research.collection.service import collect_registered_adapter
from aqil_research.contracts.observation import (
    AvailabilityPrecision,
    EconomicObservation,
    QualityStatus,
    SeasonalAdjustment,
    SeriesProvenance,
)
from aqil_research.methods.census_adv_orders import CensusAdvOrdersMethod
from aqil_research.methods.macro_conditions import MacroConditionsMethod
from aqil_research.methods.period_change import PeriodChangeMethod
from aqil_research.methods.sahm_registered import SahmAnalyticalMethod
from aqil_research.methods.sloos_cil import SloosCilMethod
from aqil_research.sources.rights import (
    AttributionRequirement,
    M1Role,
    RightsDecision,
    load_source_rights,
)
from aqil_research.vintages.store import InMemoryObservationStore

FIXTURE = Path(__file__).parent / "fixtures" / "bls_jolts"
FRAGMENT = (
    Path(__file__).resolve().parents[3]
    / "docs"
    / "sources"
    / "fragments"
    / "bls_jolts_total_nonfarm_job_openings.csv"
)
RETRIEVED = datetime(2026, 10, 22, 8, 0, tzinfo=UTC)
STORED_VALUES = {
    date(2000, 12, 1): "5088",
    date(2025, 10, 1): "7170",
    date(2026, 8, 1): "7079",
}


@pytest.fixture(autouse=True)
def refuse_postgres(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(*args: object, **kwargs: object) -> None:
        raise AssertionError("this test must not connect to a database")

    monkeypatch.setattr(psycopg, "connect", fail)


def test_rights_fragment_loads_as_first_live_provider() -> None:
    records = load_source_rights(FRAGMENT)
    assert len(records) == 1
    record = records[0]
    assert record.source_id == SOURCE_ID
    assert record.dataset_id == DATASET_ID
    assert record.m1_role == M1Role.FIRST_LIVE_PROVIDER
    assert record.attribution == AttributionRequirement.REQUIRED
    assert record.ai_processing == RightsDecision.UNKNOWN
    assert record.ai_model_training == RightsDecision.UNKNOWN
    assert record.assessed_on == date(2026, 10, 22)
    assert record.terms_url in record.evidence_urls
    assert "preliminary" in record.revision_behaviour.casefold()
    assert "not an earlier vintage" in record.revision_behaviour.casefold()
    assert COMPATIBILITY_NOTE in record.evidence_note


def test_current_methods_do_not_consume_job_openings() -> None:
    consumed: set[str] = set()
    for method in (
        SahmAnalyticalMethod(),
        SloosCilMethod(),
        CensusAdvOrdersMethod(),
        MacroConditionsMethod(),
        PeriodChangeMethod(),
    ):
        consumed.update(method.required_dataset_ids())
    assert DATASET_ID not in consumed
    assert "fed.sloos.SUBLPDCILS_N.Q" in SloosCilMethod().required_dataset_ids()
    note = jolts_adapter.__doc__ or ""
    assert "PERIOD_LEVEL_CHANGE" in note
    assert DATASET_ID in note


def test_fixture_filters_one_series_and_omits_blanks() -> None:
    adapter = _adapter(RETRIEVED)
    fetched = adapter.fetch()
    assert fetched.errors == ()
    by_period = {row.period_start: row for row in fetched.observations}
    assert set(by_period) == set(STORED_VALUES)
    assert by_period[date(2025, 10, 1)].raw_value == "7170"
    preliminary = by_period[date(2026, 8, 1)]
    assert preliminary.raw_value == "7079"
    assert preliminary.quality_status == QualityStatus.OBSERVED
    assert preliminary.series_provenance == SeriesProvenance.LATEST_REVISED
    assert preliminary.availability_precision == AvailabilityPrecision.UNKNOWN
    assert preliminary.earliest_model_available_at is None
    assert preliminary.schema_version == "1.0"
    assert preliminary.unit == "thousands"
    assert preliminary.seasonal_adjustment == SeasonalAdjustment.SEASONALLY_ADJUSTED
    assert preliminary.period_end == date(2026, 8, 31)
    assert preliminary.source_locator == f"{DATA_URL}#JTS000000000000000JOL"
    values = {row.raw_value for row in fetched.observations}
    assert "0" not in values
    assert "22222" not in values
    assert "3.5" not in values
    assert "31000" not in values
    assert date(2001, 1, 1) not in by_period
    assert date(2001, 2, 1) not in by_period
    omitted = adapter.omitted_periods
    assert "2001-01-01: blank value omitted" in omitted
    assert "2001-M13: non-monthly period omitted" in omitted
    assert "2001-02-01: absent from file" in omitted
    assert adapter._last_diagnostics is not None
    assert adapter._last_diagnostics.bls_status == "fixture"
    assert adapter._last_diagnostics.endpoint == DATA_URL


def test_second_fixture_ingest_inserts_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    records = load_source_rights(FRAGMENT)
    monkeypatch.setattr(
        "aqil_research.collection.service.load_source_rights",
        lambda path=None: records,
    )
    shared = InMemoryObservationStore()
    monkeypatch.setattr(
        "aqil_research.collection.service.InMemoryObservationStore",
        lambda: shared,
    )
    first, store = collect_registered_adapter(
        store_backend="memory",
        adapter=_adapter(RETRIEVED),
        source_id=SOURCE_ID,
        collected_at=RETRIEVED,
        live=False,
    )
    assert first.outcome == "success"
    assert first.observations_newly_stored == len(STORED_VALUES)
    assert first.data_provenance == "latest_revised"
    assert first.provider_status == "fixture"
    assert store is shared
    priors = tuple(_prior(row) for row in shared.all_observations())
    later = datetime(2026, 10, 23, 8, 0, tzinfo=UTC)
    second, again = collect_registered_adapter(
        store_backend="memory",
        adapter=_adapter(later, priors),
        source_id=SOURCE_ID,
        collected_at=later,
        live=False,
    )
    assert again is shared
    assert second.observations_newly_stored == 0
    assert second.observations_unchanged == len(STORED_VALUES)
    assert second.outcome == "unchanged"
    assert len(shared.all_observations()) == len(STORED_VALUES)


def test_unchanged_value_reuses_the_first_observation_id() -> None:
    payload = {
        "observations": [{"period": "2026-08-01", "value": "7079", "footnote": "P"}],
    }
    first = stabilise_jolts_vintages(payload, (), RETRIEVED)
    parsed = observations_from_payload(first, retrieved_at=RETRIEVED, adapter_version="test")
    stored = parsed[0]
    assert stored.series_provenance == SeriesProvenance.LATEST_REVISED
    assert stored.quality_status == QualityStatus.OBSERVED
    prior = _prior(stored)
    later = datetime(2026, 10, 23, 8, 0, tzinfo=UTC)
    repeat = stabilise_jolts_vintages(payload, (prior,), later)
    assert repeat["observations"][0]["observation_id"] == stored.observation_id
    changed = stabilise_jolts_vintages(
        {"observations": [{"period": "2026-08-01", "value": "7100", "footnote": "P"}]},
        (prior,),
        later,
    )
    assert changed["observations"][0]["observation_id"] != stored.observation_id
    store = InMemoryObservationStore()
    assert store.append(stored).inserted == 1
    repeat_row = observations_from_payload(repeat, retrieved_at=later, adapter_version="test")
    second = store.append(repeat_row[0])
    assert second.inserted == 0
    assert second.unchanged == 1
    changed_row = observations_from_payload(changed, retrieved_at=later, adapter_version="test")
    assert store.append(changed_row[0]).inserted == 1
    assert len(store.all_observations()) == 2


def test_unconfirmed_level_code_stores_nothing(tmp_path: Path) -> None:
    shutil.copytree(FIXTURE, tmp_path / "bad")
    series_path = tmp_path / "bad" / "jt.series"
    series_path.write_text(
        series_path.read_text(encoding="utf-8").replace("\tL\t", "\tR\t", 1),
        encoding="utf-8",
    )
    fetched = _adapter(RETRIEVED, fixture_dir=tmp_path / "bad").fetch()
    assert fetched.observations == ()
    assert fetched.errors


def test_client_reads_only_the_job_openings_file() -> None:
    from aqil_research.adapters.bls_jolts import client

    text = Path(client.__file__).read_text(encoding="utf-8")
    assert "AQIL_RETRIEVAL_USER_AGENT" in text
    assert "api.bls.gov" not in text
    assert "adapters.bls.client" not in text
    assert DATA_URL.endswith("/jt.data.2.JobOpenings")


def _adapter(
    retrieved_at: datetime,
    prior_points: tuple[StoredJoltsPoint, ...] = (),
    fixture_dir: Path = FIXTURE,
) -> BlsJoltsAdapter:
    return BlsJoltsAdapter(
        config=BlsJoltsAdapterConfig(live=False, fixture_dir=fixture_dir),
        retrieved_at=retrieved_at,
        prior_points=prior_points,
    )


def _prior(row: EconomicObservation) -> StoredJoltsPoint:
    assert row.source_release_at is not None
    return StoredJoltsPoint(
        period_start=row.period_start,
        observation_id=row.observation_id,
        raw_value=row.raw_value,
        provider_vintage_date=row.provider_vintage_date,
        source_release_at=row.source_release_at,
        retrieved_at=row.retrieved_at,
        first_seen_at=row.first_seen_at,
    )
