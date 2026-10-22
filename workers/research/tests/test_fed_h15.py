"""Board H.15 monthly series: rights, omitted ND, and an in-memory second ingest."""

from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

import psycopg
import pytest

from aqil_research.adapters.fed_h15.adapter import (
    ADAPTER_VERSION,
    FedH15Adapter,
    FedH15AdapterConfig,
)
from aqil_research.adapters.fed_h15.client import H15ClientError, download_h15_package
from aqil_research.adapters.fed_h15.package import H15PackageError, read_h15_series
from aqil_research.adapters.fed_h15.parse import parse_h15_payload
from aqil_research.adapters.fed_h15.series import (
    FEDERAL_FUNDS,
    METHOD_COMPATIBILITY_NOTE,
    PACKAGE_URL,
    TREASURY_10Y,
    H15Series,
)
from aqil_research.adapters.fed_h15.stability import StoredH15Point, stabilise_h15_vintages
from aqil_research.collection.service import collect_registered_adapter
from aqil_research.contracts.observation import (
    AvailabilityPrecision,
    Frequency,
    SeasonalAdjustment,
    SeriesProvenance,
)
from aqil_research.sources.rights import (
    FIRST_LIVE_OPERATIONS,
    AttributionRequirement,
    M1Role,
    RightsDecision,
    load_source_rights,
    operation_allowed,
)
from aqil_research.vintages.store import InMemoryObservationStore

REPO = Path(__file__).resolve().parents[3]
FIXTURE = Path(__file__).parent / "fixtures" / "fed_h15" / "h15_excerpt.xml"
RETRIEVED = datetime(2026, 10, 22, 12, 0, tzinfo=UTC)
TERMS_URL = "https://www.federalreserve.gov/disclaimer.htm"


@pytest.fixture(autouse=True)
def refuse_database_connections(monkeypatch: pytest.MonkeyPatch) -> None:
    """These tests count in memory. They must not open a database named postgres."""

    def refuse(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("H.15 tests must not open a database")

    monkeypatch.setattr(psycopg, "connect", refuse)


def test_rights_fragments_clear_first_live_use() -> None:
    for series in (FEDERAL_FUNDS, TREASURY_10Y):
        path = REPO / "docs" / "sources" / "fragments" / f"{series.source_id}.csv"
        record = load_source_rights(path)[0]
        assert record.source_id == series.source_id
        assert record.source_id != "board_h15_selected_interest_rates"
        assert record.dataset_id == series.dataset_id
        assert record.series_or_dataset_code == series.preview_code
        assert record.terms_url == TERMS_URL
        assert record.terms_url in record.evidence_urls
        assert record.access_url == PACKAGE_URL
        assert record.attribution == AttributionRequirement.REQUIRED
        assert record.m1_role == M1Role.FIRST_LIVE_PROVIDER
        assert record.ai_processing == RightsDecision.UNKNOWN
        assert record.ai_model_training == RightsDecision.UNKNOWN
        assert record.assessed_on == date(2026, 10, 22)
        assert all(operation_allowed(record, operation) for operation in FIRST_LIVE_OPERATIONS)
        note = record.evidence_note
        assert METHOD_COMPATIBILITY_NOTE in note
        assert "latest-revised" in note
        assert "not a vintage panel" in note
        assert "not a near-term forward spread" in note
        assert series.dataset_id in note


def test_adapter_docstring_states_method_compatibility() -> None:
    import aqil_research.adapters.fed_h15.adapter as adapter_module

    docstring = " ".join((adapter_module.__doc__ or "").split())
    assert " ".join(METHOD_COMPATIBILITY_NOTE.split()) in docstring
    assert "not a vintage panel" in docstring
    assert "not a near-term forward spread" in docstring


def test_excerpt_omits_nd_and_ignores_the_daily_series() -> None:
    package = FIXTURE.read_bytes()
    assert b"H.15 Selected Interest Rates" in package
    assert b'OBS_STATUS="ND" OBS_VALUE="-9999"' in package
    funds = read_h15_series(package, FEDERAL_FUNDS)
    yields = read_h15_series(package, TREASURY_10Y)
    assert funds.omitted_periods == ("1954-08-31",)
    assert yields.omitted_periods == ("1953-06-30",)
    assert [row.value for row in funds.rows] == ["0.80", "1.07", "0.85"]
    assert [row.value for row in yields.rows] == ["2.83", "3.05", "2.93"]
    assert funds.description_lines[1] == "Long Description: Federal funds effective rate"
    assert "10-year  constant maturity" in yields.long_description
    stored = {row.value for row in funds.rows + yields.rows}
    assert "-9999" not in stored
    assert "0" not in stored
    assert "0.75" not in stored
    assert date(1954, 7, 16) not in {row.period_end for row in funds.rows}


def test_description_or_frequency_mismatch_does_not_bind() -> None:
    wrong_description = _series_xml(
        'CURRENCY="NA" FREQ="129" SERIES_NAME="RIFSPFF_N.M" UNIT="Percent:_Per_Year" UNIT_MULT="1"',
        "Some other rate",
        '<frb:Obs OBS_STATUS="A" OBS_VALUE="9.99" TIME_PERIOD="2020-01-31" />',
    )
    with pytest.raises(H15PackageError, match="description was not repeated"):
        read_h15_series(wrong_description, FEDERAL_FUNDS)
    daily_frequency = _series_xml(
        'CURRENCY="NA" FREQ="9" SERIES_NAME="RIFSPFF_N.M" UNIT="Percent:_Per_Year" UNIT_MULT="1"',
        FEDERAL_FUNDS.long_description,
        '<frb:Obs OBS_STATUS="A" OBS_VALUE="1.00" TIME_PERIOD="2020-01-31" />',
    )
    with pytest.raises(H15PackageError, match="not the monthly frequency"):
        read_h15_series(daily_frequency, FEDERAL_FUNDS)


def test_mid_month_date_is_omitted_and_not_stored_as_zero() -> None:
    package = _series_xml(
        'CURRENCY="NA" FREQ="129" SERIES_NAME="RIFSPFF_N.M" UNIT="Percent:_Per_Year" UNIT_MULT="1"',
        FEDERAL_FUNDS.long_description,
        '<frb:Obs OBS_STATUS="A" OBS_VALUE="1.50" TIME_PERIOD="2020-01-31" />'
        '<frb:Obs OBS_STATUS="A" OBS_VALUE="1.25" TIME_PERIOD="2020-02-15" />'
        '<frb:Obs OBS_STATUS="ND" OBS_VALUE="-9999" TIME_PERIOD="2020-03-31" />',
    )
    extract = read_h15_series(package, FEDERAL_FUNDS)
    assert [row.period_start for row in extract.rows] == [date(2020, 1, 1)]
    assert extract.rows[0].value == "1.50"
    assert extract.omitted_periods == ("2020-02-15", "2020-03-31")


def test_fixture_observations_are_latest_revised() -> None:
    result = _fixture_adapter(FEDERAL_FUNDS, RETRIEVED).fetch()
    assert result.errors == ()
    assert result.partial is False
    observation = result.observations[0]
    assert observation.schema_version == "1.0"
    assert observation.series_provenance == SeriesProvenance.LATEST_REVISED
    assert observation.availability_precision == AvailabilityPrecision.UNKNOWN
    assert observation.earliest_model_available_at is None
    assert observation.frequency == Frequency.MONTHLY
    assert observation.unit == "percent_per_year"
    assert observation.seasonal_adjustment == SeasonalAdjustment.UNKNOWN
    assert observation.geography == "US"
    assert observation.dataset_id == FEDERAL_FUNDS.dataset_id
    assert observation.source_id == FEDERAL_FUNDS.source_id
    assert observation.period_start == date(1954, 7, 1)
    assert observation.period_end == date(1954, 7, 31)
    assert observation.raw_value == "0.80"
    assert observation.source_locator == PACKAGE_URL
    assert observation.adapter_version == f"{FEDERAL_FUNDS.adapter_id}:{ADAPTER_VERSION}"
    assert [row.period_start for row in result.observations] == [
        date(1954, 7, 1),
        date(1954, 9, 1),
        date(1954, 10, 1),
    ]


def test_unchanged_value_keeps_the_first_observation_id() -> None:
    payload = {
        "series_name": FEDERAL_FUNDS.series_name,
        "observations": [
            {"period": "1954-07-01", "period_end": "1954-07-31", "value": "0.80"},
        ],
    }
    first = _parse_stable(payload, ())
    stored = first.observations[0]
    prior = _point(stored)
    later = datetime(2026, 10, 23, 12, 0, tzinfo=UTC)
    repeat = stabilise_h15_vintages(payload, FEDERAL_FUNDS, (prior,), later)
    assert repeat["observations"][0]["observation_id"] == stored.observation_id
    changed = stabilise_h15_vintages(
        {
            "series_name": FEDERAL_FUNDS.series_name,
            "observations": [
                {"period": "1954-07-01", "period_end": "1954-07-31", "value": "0.91"},
            ],
        },
        FEDERAL_FUNDS,
        (prior,),
        later,
    )
    assert changed["observations"][0]["observation_id"] != stored.observation_id


def test_second_fixture_ingest_inserts_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    from aqil_research.collection import service as collection_service

    fragments = load_source_rights(_fragment(FEDERAL_FUNDS)) + load_source_rights(
        _fragment(TREASURY_10Y),
    )
    combined = load_source_rights() + fragments
    monkeypatch.setattr(collection_service, "load_source_rights", lambda path=None: combined)
    for series, expected in ((FEDERAL_FUNDS, 3), (TREASURY_10Y, 3)):
        shared = InMemoryObservationStore()
        monkeypatch.setattr(
            collection_service, "InMemoryObservationStore", lambda store=shared: store
        )
        first_result, first_store = _collect(series, prior=())
        assert first_result.outcome == "success"
        assert first_result.observations_newly_stored == expected
        assert first_store is shared
        priors = tuple(
            _point(row) for row in shared.all_observations() if row.dataset_id == series.dataset_id
        )
        second_result, second_store = _collect(series, prior=priors)
        assert second_store is shared
        assert second_result.outcome == "unchanged"
        assert second_result.observations_newly_stored == 0
        assert second_result.observations_unchanged == expected
        assert len(shared.all_observations()) == expected


def test_non_200_stops(monkeypatch: pytest.MonkeyPatch) -> None:
    class Response:
        status_code = 404
        content = b"missing"

    def fake_get(*_args: object, **_kwargs: object) -> Response:
        return Response()

    monkeypatch.setattr("aqil_research.adapters.fed_h15.client.httpx.get", fake_get)
    with pytest.raises(H15ClientError, match="HTTP 404"):
        download_h15_package()


def test_client_does_not_name_a_blocked_provider() -> None:
    root = Path(__file__).resolve().parents[2] / "src" / "aqil_research" / "adapters" / "fed_h15"
    source = "\n".join(path.read_text(encoding="utf-8") for path in root.glob("*.py"))
    lowered = source.lower()
    assert "fred.stlouisfed.org" not in lowered
    assert "fiscaldata.treasury.gov" not in lowered
    assert "home.treasury.gov" not in lowered


def test_live_board_file_is_counted_in_memory(monkeypatch: pytest.MonkeyPatch) -> None:
    download = download_h15_package()
    assert download.status_code == 200
    assert download.url == PACKAGE_URL
    monkeypatch.setattr(
        "aqil_research.adapters.fed_h15.adapter.download_h15_package",
        lambda: download,
    )
    expected = {
        FEDERAL_FUNDS: (867, date(1954, 7, 1), date(2026, 9, 30), "0.80"),
        TREASURY_10Y: (882, date(1953, 4, 1), date(2026, 9, 30), "2.83"),
    }
    for series, (count, start, end, first_value) in expected.items():
        extract = read_h15_series(download.content, series)
        assert extract.omitted_periods == ()
        assert len(extract.rows) == count
        assert extract.rows[0].period_start == start
        assert extract.rows[0].value == first_value
        assert extract.rows[-1].period_end == end
        assert " ".join(extract.long_description.split()) == series.long_description
        result = FedH15Adapter(
            series=series,
            config=FedH15AdapterConfig(live=True),
            retrieved_at=RETRIEVED,
        ).fetch()
        assert result.errors == ()
        assert len(result.observations) == count
        store = InMemoryObservationStore()
        appended = store.append_many(result.observations)
        assert appended.inserted == count
        assert appended.unchanged == 0
        again = store.append_many(result.observations)
        assert again.inserted == 0
        assert again.unchanged == count


def _collect(series: H15Series, *, prior: tuple[StoredH15Point, ...]):
    return collect_registered_adapter(
        store_backend="memory",
        adapter=FedH15Adapter(
            series=series,
            config=FedH15AdapterConfig(live=False, fixture_path=FIXTURE),
            retrieved_at=RETRIEVED,
            prior_points=prior,
        ),
        source_id=series.source_id,
        collected_at=RETRIEVED,
        live=False,
    )


def _fixture_adapter(series: H15Series, retrieved: datetime) -> FedH15Adapter:
    return FedH15Adapter(
        series=series,
        config=FedH15AdapterConfig(live=False, fixture_path=FIXTURE),
        retrieved_at=retrieved,
    )


def _parse_stable(payload: dict[str, object], prior: tuple[StoredH15Point, ...]):
    stable = stabilise_h15_vintages(payload, FEDERAL_FUNDS, prior, RETRIEVED)
    return parse_h15_payload(
        stable,
        series=FEDERAL_FUNDS,
        adapter_version="test",
        retrieved_at=RETRIEVED,
        collection_vintage_date=RETRIEVED.date(),
    )


def _point(observation) -> StoredH15Point:
    return StoredH15Point(
        period_start=observation.period_start,
        observation_id=observation.observation_id,
        raw_value=observation.raw_value,
        provider_vintage_date=observation.provider_vintage_date,
        source_release_at=observation.source_release_at,
        retrieved_at=observation.retrieved_at,
    )


def _fragment(series: H15Series) -> Path:
    return REPO / "docs" / "sources" / "fragments" / f"{series.source_id}.csv"


def _series_xml(attributes: str, description: str, observations: str) -> bytes:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<frb:DataSet id="H15"
  xmlns:frb="http://www.federalreserve.gov/structure/compact/common"
  xmlns:kf="http://www.federalreserve.gov/structure/compact/H15_H15"
  xmlns:common="http://www.SDMX.org/resources/SDMXML/schemas/v1_0/common">
  <kf:Series {attributes}>
    <frb:Annotations>
      <common:Annotation>
        <common:AnnotationType>Long Description</common:AnnotationType>
        <common:AnnotationText>{description}</common:AnnotationText>
      </common:Annotation>
    </frb:Annotations>
    {observations}
  </kf:Series>
</frb:DataSet>
""".encode()
