"""ONS CPI D7BT: monthly rows only, Open Government Licence, idempotent ingest."""

from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

import psycopg
import pytest

import aqil_research.adapters.ons_cpi.adapter as adapter_module
from aqil_research.adapters.ons_cpi.adapter import OnsCpiAdapter, OnsCpiAdapterConfig
from aqil_research.adapters.ons_cpi.client import series_csv_url
from aqil_research.adapters.ons_cpi.constants import (
    DATASET_ID,
    METHOD_COMPATIBILITY_NOTE,
    SERIES_KEY,
    SOURCE_ID,
    UNIT_TEXT,
)
from aqil_research.adapters.ons_cpi.parse import parse_ons_cpi_csv
from aqil_research.adapters.ons_cpi.stability import StoredOnsPoint
from aqil_research.adapters.protocol import ProviderFailureCode
from aqil_research.collection.service import collect_registered_adapter
from aqil_research.contracts.observation import SeasonalAdjustment, SeriesProvenance
from aqil_research.methods.sahm_registered import SahmAnalyticalMethod
from aqil_research.sources.rights import (
    FIRST_LIVE_OPERATIONS,
    AttributionRequirement,
    M1Role,
    RightsDecision,
    load_source_rights,
)
from aqil_research.vintages.store import InMemoryObservationStore

FIXTURE = Path(__file__).parent / "fixtures" / "ons_cpi" / "d7bt_excerpt.csv"
FRAGMENT = (
    Path(__file__).resolve().parents[3] / "docs" / "sources" / "fragments" / "ons_mm23_cpi_d7bt.csv"
)
RETRIEVED = datetime(2026, 10, 24, 9, 0, tzinfo=UTC)
EXCERPT = {
    date(2026, 6, 1): "142.5",
    date(2026, 7, 1): "142.9",
    date(2026, 8, 1): "143.6",
    date(2026, 9, 1): "144.1",
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
    prior: tuple[StoredOnsPoint, ...] = (),
) -> OnsCpiAdapter:
    return OnsCpiAdapter(
        config=OnsCpiAdapterConfig(live=False, fixture_path=path),
        retrieved_at=retrieved_at,
        prior_points=prior,
    )


def _points(store: InMemoryObservationStore) -> tuple[StoredOnsPoint, ...]:
    return tuple(
        StoredOnsPoint(
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
    assert record.series_or_dataset_code == SERIES_KEY
    assert record.m1_role == M1Role.FIRST_LIVE_PROVIDER
    assert record.attribution == AttributionRequirement.REQUIRED
    assert record.terms_url == "https://www.ons.gov.uk/help/terms-conditions"
    for operation in FIRST_LIVE_OPERATIONS:
        assert record.decision_for(operation) == RightsDecision.PERMITTED
    assert "Open Government Licence" in record.evidence_note
    assert _collapsed(METHOD_COMPATIBILITY_NOTE) in _collapsed(record.evidence_note)


def test_request_and_methods() -> None:
    url = series_csv_url()
    assert url.startswith("https://www.ons.gov.uk/generator?format=csv")
    assert "d7bt/mm23" in url
    assert "includeHistory" not in url
    assert _collapsed(METHOD_COMPATIBILITY_NOTE) in _collapsed(adapter_module.__doc__ or "")
    assert DATASET_ID not in SahmAnalyticalMethod().required_dataset_ids()


def test_monthly_identity_and_other_frequencies_are_not_stored() -> None:
    parsed = parse_ons_cpi_csv(FIXTURE.read_text(encoding="utf-8"), retrieved_at=RETRIEVED)
    assert parsed.unit == UNIT_TEXT
    assert parsed.frequency == "Monthly"
    assert parsed.vintage_class == "latest_revised"
    assert parsed.series_key == SERIES_KEY
    assert len(parsed.observations) == 4
    values = {row.period_start: row.raw_value for row in parsed.observations}
    assert values == EXCERPT
    assert "138.4" not in values.values()
    for observation in parsed.observations:
        assert observation.schema_version == "1.0"
        assert observation.series_provenance == SeriesProvenance.LATEST_REVISED
        assert observation.seasonal_adjustment == SeasonalAdjustment.NOT_SEASONALLY_ADJUSTED
        assert observation.frequency.value == "monthly"
        assert observation.geography == "GB"
        assert observation.source_id == SOURCE_ID
        assert observation.provider_id == "ons"


def test_blank_month_is_omitted(tmp_path: Path) -> None:
    path = tmp_path / "gap.csv"
    text = FIXTURE.read_text(encoding="utf-8").replace('"2026 JUL","142.9"', '"2026 JUL",""')
    path.write_text(text, encoding="utf-8")
    parsed = parse_ons_cpi_csv(path.read_text(encoding="utf-8"), retrieved_at=RETRIEVED)
    assert "2026 JUL" in parsed.omitted_periods
    assert all(row.period_start != date(2026, 7, 1) for row in parsed.observations)
    assert all(row.raw_value != "0" for row in parsed.observations)


def test_wrong_cdid_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "other.csv"
    body = FIXTURE.read_text(encoding="utf-8").replace('"D7BT"', '"D7BU"')
    path.write_text(body, encoding="utf-8")
    result = _adapter(path, RETRIEVED).fetch()
    assert result.observations == ()
    assert result.errors[0].code == ProviderFailureCode.PARSE_FAILED


def test_non_numeric_month_fails(tmp_path: Path) -> None:
    path = tmp_path / "bad.csv"
    text = FIXTURE.read_text(encoding="utf-8").replace('"2026 SEP","144.1"', '"2026 SEP",".."')
    path.write_text(text, encoding="utf-8")
    result = _adapter(path, RETRIEVED).fetch()
    assert result.observations == ()
    assert "non-numeric" in result.errors[0].message


def test_missing_fixture_is_a_fetch_failure() -> None:
    result = OnsCpiAdapter(config=OnsCpiAdapterConfig()).fetch()
    assert result.errors[0].code == ProviderFailureCode.FETCH_FAILED


def test_second_ingest_is_unchanged_until_a_value_changes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
    assert first.observations_newly_stored == 4
    assert psycopg.connect is _refuse_database
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
    changed = tmp_path / "changed.csv"
    changed.write_text(
        FIXTURE.read_text(encoding="utf-8").replace('"2026 SEP","144.1"', '"2026 SEP","144.4"'),
        encoding="utf-8",
    )
    follow_up = _adapter(changed, later, _points(store))
    third, _bound_again = collect_registered_adapter(
        store_backend="memory",
        adapter=follow_up,
        source_id=SOURCE_ID,
        collected_at=later,
        live=False,
    )
    assert third.observations_newly_stored == 1
    september = [row for row in store.all_observations() if row.period_start == date(2026, 9, 1)]
    assert {row.raw_value for row in september} == {"144.1", "144.4"}
