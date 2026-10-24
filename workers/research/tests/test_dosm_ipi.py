"""DOSM industrial production: absolute index only, not growth and not the adjusted column."""

from __future__ import annotations

import csv
from datetime import UTC, date, datetime
from pathlib import Path

import psycopg
import pytest

import aqil_research.adapters.dosm_ipi.adapter as adapter_module
from aqil_research.adapters.dosm_ipi.adapter import DosmIpiAdapter, DosmIpiAdapterConfig
from aqil_research.adapters.dosm_ipi.client import series_csv_url
from aqil_research.adapters.dosm_ipi.constants import (
    DATASET_ID,
    METHOD_COMPATIBILITY_NOTE,
    SOURCE_ID,
    UNIT_TEXT,
)
from aqil_research.adapters.dosm_ipi.parse import parse_dosm_ipi_csv
from aqil_research.adapters.dosm_ipi.stability import StoredDosmPoint
from aqil_research.adapters.protocol import ProviderFailureCode
from aqil_research.collection.service import collect_registered_adapter
from aqil_research.contracts.observation import SeasonalAdjustment, SeriesProvenance
from aqil_research.methods.macro_conditions import MacroConditionsMethod
from aqil_research.sources.rights import (
    FIRST_LIVE_OPERATIONS,
    AttributionRequirement,
    M1Role,
    RightsDecision,
    load_source_rights,
)
from aqil_research.vintages.store import InMemoryObservationStore

FIXTURE = Path(__file__).parent / "fixtures" / "dosm_ipi" / "ipi_abs_excerpt.csv"
FRAGMENT = (
    Path(__file__).resolve().parents[3] / "docs" / "sources" / "fragments" / "dosm_ipi_abs.csv"
)
RETRIEVED = datetime(2026, 10, 24, 9, 0, tzinfo=UTC)
EXCERPT = {
    date(2026, 5, 1): "139.382",
    date(2026, 6, 1): "147.11",
    date(2026, 7, 1): "144.209",
    date(2026, 8, 1): "147.996",
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
    prior: tuple[StoredDosmPoint, ...] = (),
) -> DosmIpiAdapter:
    return DosmIpiAdapter(
        config=DosmIpiAdapterConfig(live=False, fixture_path=path),
        retrieved_at=retrieved_at,
        prior_points=prior,
    )


def _points(store: InMemoryObservationStore) -> tuple[StoredDosmPoint, ...]:
    return tuple(
        StoredDosmPoint(
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
        change = edits.get(f"{row['series']}|{row['date']}")
        if change:
            row.update(change)
    with dest.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def test_rights_fragment_clears_first_live_use() -> None:
    record = load_source_rights(FRAGMENT)[0]
    assert record.source_id == SOURCE_ID
    assert record.dataset_id == DATASET_ID
    assert record.m1_role == M1Role.FIRST_LIVE_PROVIDER
    assert record.attribution == AttributionRequirement.REQUIRED
    assert record.terms_url == "https://www.dosm.gov.my/portal-main/article/term-of-use"
    for operation in FIRST_LIVE_OPERATIONS:
        assert record.decision_for(operation) == RightsDecision.PERMITTED
    assert "CC BY 4.0" in record.evidence_note
    assert "not a growth rate" in record.evidence_note
    assert _collapsed(METHOD_COMPATIBILITY_NOTE) in _collapsed(record.evidence_note)


def test_request_and_methods() -> None:
    url = series_csv_url()
    assert url == "https://storage.dosm.gov.my/ipi/ipi.csv"
    assert "includeHistory" not in url
    assert _collapsed(METHOD_COMPATIBILITY_NOTE) in _collapsed(adapter_module.__doc__ or "")
    assert DATASET_ID not in MacroConditionsMethod().required_dataset_ids()


def test_absolute_index_not_growth_or_adjusted_column() -> None:
    parsed = parse_dosm_ipi_csv(FIXTURE.read_text(encoding="utf-8"), retrieved_at=RETRIEVED)
    assert parsed.unit == UNIT_TEXT
    assert parsed.frequency == "Monthly"
    assert parsed.seasonal_adjustment == "not seasonally adjusted"
    assert parsed.vintage_class == "latest_revised"
    values = {row.period_start: row.raw_value for row in parsed.observations}
    assert values == EXCERPT
    stored = set(values.values())
    assert "145.744" not in stored
    assert "4.954" not in stored
    for observation in parsed.observations:
        assert observation.schema_version == "1.0"
        assert observation.frequency.value == "monthly"
        assert observation.geography == "MY"
        assert observation.source_id == SOURCE_ID
        assert observation.provider_id == "dosm"
        assert observation.series_provenance == SeriesProvenance.LATEST_REVISED
        assert observation.seasonal_adjustment == SeasonalAdjustment.NOT_SEASONALLY_ADJUSTED


def test_blank_index_is_omitted(tmp_path: Path) -> None:
    path = tmp_path / "gap.csv"
    _rewrite(FIXTURE, path, {"abs|2026-06-01": {"index": ""}})
    parsed = parse_dosm_ipi_csv(path.read_text(encoding="utf-8"), retrieved_at=RETRIEVED)
    assert parsed.omitted_periods == ("2026-06-01",)
    assert all(row.raw_value != "0" for row in parsed.observations)
    assert all(row.period_start != date(2026, 6, 1) for row in parsed.observations)


def test_unknown_series_code_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "other.csv"
    _rewrite(FIXTURE, path, {"abs|2026-05-01": {"series": "electronics"}})
    result = _adapter(path, RETRIEVED).fetch()
    assert result.observations == ()
    assert result.errors[0].code == ProviderFailureCode.PARSE_FAILED
    assert "refusing" in result.errors[0].message


def test_missing_fixture_and_idempotent_ingest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    failed = DosmIpiAdapter(config=DosmIpiAdapterConfig()).fetch()
    assert failed.errors[0].code == ProviderFailureCode.FETCH_FAILED
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
    changed = tmp_path / "changed.csv"
    _rewrite(FIXTURE, changed, {"abs|2026-08-01": {"index": "148.1"}})
    third, _bound_again = collect_registered_adapter(
        store_backend="memory",
        adapter=_adapter(changed, later, _points(store)),
        source_id=SOURCE_ID,
        collected_at=later,
        live=False,
    )
    assert third.observations_newly_stored == 1
    august = [row for row in store.all_observations() if row.period_start == date(2026, 8, 1)]
    assert {row.raw_value for row in august} == {"147.996", "148.1"}
