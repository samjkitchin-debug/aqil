"""CPI-U all-items flat file: confirm the series, omit gaps, and keep identities."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

from aqil_research.adapters.bls_cpi_series.adapter import (
    BlsCpiSeriesAdapter,
    BlsCpiSeriesAdapterConfig,
)
from aqil_research.adapters.bls_cpi_series.client import (
    AQIL_RETRIEVAL_USER_AGENT,
    CpiClientError,
    assert_cpi_download_url,
    fetch_cpi_flat_files,
)
from aqil_research.adapters.bls_cpi_series.parse import (
    DATASET_ID,
    UNIT,
    confirm_cpi_series,
    parse_cpi_data,
)
from aqil_research.adapters.bls_cpi_series.stability import points_from_observations
from aqil_research.contracts.observation import (
    AvailabilityPrecision,
    Frequency,
    QualityStatus,
    SeasonalAdjustment,
    SeriesProvenance,
)
from aqil_research.methods.census_adv_orders import CensusAdvOrdersMethod
from aqil_research.methods.macro_conditions import MacroConditionsMethod
from aqil_research.methods.period_change import PeriodChangeMethod
from aqil_research.methods.sahm_registered import SahmAnalyticalMethod
from aqil_research.methods.sloos_cil import SloosCilMethod
from aqil_research.pipeline.ingestion import ingest_from_adapter
from aqil_research.sources.rights import load_source_rights
from aqil_research.vintages.store import InMemoryObservationStore

FIXTURES = Path(__file__).parent / "fixtures"
SERIES_FIXTURE = FIXTURES / "cu_series_cusr0000sa0.txt"
DATA_FIXTURE = FIXTURES / "cu_data_1_all_items_cusr0000sa0.txt"
RIGHTS_FRAGMENT = (
    Path(__file__).resolve().parents[3]
    / "docs"
    / "sources"
    / "fragments"
    / "bls_cpi_u_all_items.csv"
)
RETRIEVED = datetime(2026, 10, 22, 8, 0, tzinfo=UTC)
ADAPTER_VERSION = "bls_cpi_u_cusr0000sa0:1.0.0"


@pytest.fixture(autouse=True)
def refuse_database_connections(monkeypatch: pytest.MonkeyPatch) -> None:
    """These tests stay in memory. A database named postgres must not be opened."""
    import psycopg

    def refuse(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("tests must not connect to a database")

    monkeypatch.setattr(psycopg, "connect", refuse)


def _adapter(retrieved_at: datetime) -> BlsCpiSeriesAdapter:
    return BlsCpiSeriesAdapter(
        config=BlsCpiSeriesAdapterConfig(
            fixture_path=DATA_FIXTURE,
            series_fixture_path=SERIES_FIXTURE,
        ),
        retrieved_at=retrieved_at,
    )


def test_series_excerpt_confirms_seasonal_code_unit_and_period() -> None:
    binding = confirm_cpi_series(SERIES_FIXTURE.read_text(encoding="utf-8"))
    assert binding.series_id == "CUSR0000SA0"
    assert binding.seasonal_code == "S"
    assert binding.periodicity_code == "R"
    assert binding.base_period == "1982-84=100"
    assert binding.item_code == "SA0"
    assert binding.area_code == "0000"


def test_series_excerpt_rejects_a_different_seasonal_code() -> None:
    lines = SERIES_FIXTURE.read_text(encoding="utf-8").splitlines()
    cells = lines[1].split("\t")
    cells[3] = "U"
    rejected = lines[0] + "\n" + "\t".join(cells) + "\n"
    with pytest.raises(ValueError, match="seasonal_code"):
        confirm_cpi_series(rejected)


def test_fixture_excerpt_normalises_monthly_index_and_omits_october_2025() -> None:
    binding = confirm_cpi_series(SERIES_FIXTURE.read_text(encoding="utf-8"))
    parsed = parse_cpi_data(
        DATA_FIXTURE.read_text(encoding="utf-8"),
        binding=binding,
        adapter_version=ADAPTER_VERSION,
        retrieved_at=RETRIEVED,
    )
    periods = [row.period_start.isoformat() for row in parsed.observations]
    assert periods == ["1947-01-01", "1947-02-01", "2025-09-01", "2025-11-01", "2026-09-01"]
    assert [item.period_label for item in parsed.omitted_periods] == ["2025-10"]
    assert parsed.omitted_periods[0].reason == "unavailable value is omitted"
    for row in parsed.observations:
        assert row.schema_version == "1.0"
        assert row.dataset_id == DATASET_ID
        assert row.frequency == Frequency.MONTHLY
        assert row.geography == "US"
        assert row.unit == UNIT
        assert row.seasonal_adjustment == SeasonalAdjustment.SEASONALLY_ADJUSTED
        assert row.quality_status == QualityStatus.OBSERVED
        assert row.series_provenance == SeriesProvenance.LATEST_REVISED
        assert row.availability_precision == AvailabilityPrecision.UNKNOWN
        assert row.earliest_model_available_at is None
        assert row.provider_vintage_date == RETRIEVED.date()
        assert row.raw_value != "0"
    assert parsed.observations[0].raw_value == "21.48"
    assert parsed.observations[-1].raw_value == "336.298"


def test_footnote_with_a_number_stays_the_current_observed_value() -> None:
    binding = confirm_cpi_series(SERIES_FIXTURE.read_text(encoding="utf-8"))
    text = "series_id\tyear\tperiod\tvalue\tfootnote_codes\nCUSR0000SA0\t2024\tM12\t310.326\tR\n"
    parsed = parse_cpi_data(
        text,
        binding=binding,
        adapter_version=ADAPTER_VERSION,
        retrieved_at=RETRIEVED,
    )
    assert len(parsed.observations) == 1
    assert parsed.observations[0].raw_value == "310.326"
    assert parsed.observations[0].quality_status == QualityStatus.OBSERVED
    assert parsed.observations[0].series_provenance == SeriesProvenance.LATEST_REVISED
    assert parsed.omitted_periods == ()


def test_zero_annual_average_and_blank_are_omitted_without_filling_months() -> None:
    binding = confirm_cpi_series(SERIES_FIXTURE.read_text(encoding="utf-8"))
    text = (
        "series_id\tyear\tperiod\tvalue\tfootnote_codes\n"
        "CUSR0000SA0\t2024\tM01\t300.100\t\n"
        "CUSR0000SA0\t2024\tM02\t0\t\n"
        "CUSR0000SA0\t2024\tM03\t\t\n"
        "CUSR0000SA0\t2024\tM13\t301.000\t\n"
        "CUUR0000SA0\t2024\tM01\t299.000\t\n"
        "CUSR0000SA0\t2024\tM05\t302.000\t\n"
    )
    parsed = parse_cpi_data(
        text,
        binding=binding,
        adapter_version=ADAPTER_VERSION,
        retrieved_at=RETRIEVED,
    )
    assert [row.period_start.isoformat() for row in parsed.observations] == [
        "2024-01-01",
        "2024-05-01",
    ]
    omitted = {item.period_label: item.reason for item in parsed.omitted_periods}
    assert omitted["2024-02"] == "zero is not stored"
    assert omitted["2024-03"] == "missing value is omitted"
    assert omitted["2024-M13"] == "non-monthly period is omitted"
    assert "2024-04" not in omitted


def test_unchanged_value_keeps_the_first_observation_and_a_change_is_a_new_row() -> None:
    binding = confirm_cpi_series(SERIES_FIXTURE.read_text(encoding="utf-8"))
    original = DATA_FIXTURE.read_text(encoding="utf-8")
    first = parse_cpi_data(
        original,
        binding=binding,
        adapter_version=ADAPTER_VERSION,
        retrieved_at=RETRIEVED,
    )
    stored = points_from_observations(first.observations)
    later = datetime(2026, 10, 23, 8, 0, tzinfo=UTC)
    repeat = parse_cpi_data(
        original,
        binding=binding,
        adapter_version=ADAPTER_VERSION,
        retrieved_at=later,
        prior_points=stored,
    )
    assert [row.observation_id for row in repeat.observations] == [
        row.observation_id for row in first.observations
    ]
    assert repeat.observations[0].provider_vintage_date == RETRIEVED.date()
    changed_text = original.replace("336.298", "337.100")
    changed = parse_cpi_data(
        changed_text,
        binding=binding,
        adapter_version=ADAPTER_VERSION,
        retrieved_at=later,
        prior_points=stored,
    )
    assert changed.observations[-1].observation_id != first.observations[-1].observation_id
    assert changed.observations[-1].raw_value == "337.100"
    assert changed.observations[0].observation_id == first.observations[0].observation_id
    store = InMemoryObservationStore()
    assert store.append_many(first.observations).inserted == 5
    appended = store.append_many(changed.observations)
    assert appended.inserted == 1
    assert appended.unchanged == 4
    assert len(store.all_observations()) == 6


def test_second_fixture_ingest_inserts_nothing() -> None:
    rights = load_source_rights(RIGHTS_FRAGMENT)[0]
    store = InMemoryObservationStore()
    adapter = _adapter(RETRIEVED)
    first = ingest_from_adapter(store, adapter, rights)
    assert first.append is not None
    assert first.append.inserted == 5
    assert first.conflicts == ()
    adapter.prior_points = points_from_observations(adapter.fetch().observations)
    adapter.retrieved_at = datetime(2026, 10, 23, 9, 30, tzinfo=UTC)
    second = ingest_from_adapter(store, adapter, rights)
    assert second.append is not None
    assert second.append.inserted == 0
    assert second.append.unchanged == 5
    assert second.conflicts == ()
    assert len(store.all_observations()) == 5
    assert adapter.fetch().partial is False
    assert [item.period_label for item in adapter.omitted_periods] == ["2025-10"]


def test_rights_fragment_clears_first_live_use() -> None:
    record = load_source_rights(RIGHTS_FRAGMENT)[0]
    assert record.source_id == "bls_cpi_u_all_items"
    assert record.dataset_id == DATASET_ID
    assert record.m1_role.value == "first_live_provider"
    assert record.attribution.value == "required"
    assert record.operational_status.value == "enabled"
    assert record.ai_processing.value == "unknown"
    assert record.ai_model_training.value == "unknown"
    assert record.assessed_on.isoformat() == "2026-10-22"
    assert record.terms_url in record.evidence_urls
    assert "footnote" in record.revision_behaviour
    assert "MACRO_CONDITIONS_PANEL" in record.evidence_note
    assert "PERIOD_LEVEL_CHANGE" in record.evidence_note
    assert "bls.cu.CUSR0000SA0" in record.evidence_note
    assert record.series_or_dataset_code == "CUSR0000SA0"


def test_current_methods_do_not_consume_this_dataset() -> None:
    required = (
        SahmAnalyticalMethod().required_dataset_ids()
        + SloosCilMethod().required_dataset_ids()
        + CensusAdvOrdersMethod().required_dataset_ids()
        + MacroConditionsMethod().required_dataset_ids()
        + PeriodChangeMethod().required_dataset_ids()
    )
    assert DATASET_ID not in required


def test_download_urls_stay_on_the_bls_cu_directory() -> None:
    assert_cpi_download_url("https://download.bls.gov/pub/time.series/cu/cu.series")
    with pytest.raises(CpiClientError):
        assert_cpi_download_url("https://example.com/pub/time.series/cu/cu.series")
    with pytest.raises(CpiClientError):
        assert_cpi_download_url("http://download.bls.gov/pub/time.series/cu/cu.data.1.AllItems")


def test_client_sends_the_existing_user_agent(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if request.url.path.endswith("/cu.series"):
            body = SERIES_FIXTURE.read_bytes()
        elif request.url.path.endswith("/cu.data.1.AllItems"):
            body = DATA_FIXTURE.read_bytes()
        else:
            return httpx.Response(404)
        return httpx.Response(200, content=body)

    transport = httpx.MockTransport(handler)
    real_client = httpx.Client

    def factory(*args: object, **kwargs: object) -> httpx.Client:
        kwargs["transport"] = transport
        return real_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "Client", factory)
    files = fetch_cpi_flat_files()
    assert files.series_status == 200
    assert files.data_status == 200
    assert confirm_cpi_series(files.series_text).series_id == "CUSR0000SA0"
    assert [request.headers["user-agent"] for request in seen] == [
        AQIL_RETRIEVAL_USER_AGENT,
        AQIL_RETRIEVAL_USER_AGENT,
    ]


def test_unconfirmed_series_file_does_not_invent_observations(tmp_path: Path) -> None:
    series_text = SERIES_FIXTURE.read_text(encoding="utf-8").replace(
        "1982-84=100",
        "1999=100",
        1,
    )
    rejected = tmp_path / "cu.series"
    rejected.write_text(series_text, encoding="utf-8")
    adapter = BlsCpiSeriesAdapter(
        config=BlsCpiSeriesAdapterConfig(
            fixture_path=DATA_FIXTURE,
            series_fixture_path=rejected,
        ),
        retrieved_at=RETRIEVED,
    )
    result = adapter.fetch()
    assert result.observations == ()
    assert result.errors[0].code.value == "parse_failed"
