"""Offline tests for BLS adapter parsing and rights."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from aqil_research.adapters.bls.adapter import BlsAdapterConfig, BlsUnemploymentAdapter
from aqil_research.adapters.bls.client import BlsClientError, fetch_timeseries
from aqil_research.adapters.bls.parse import parse_bls_payload
from aqil_research.contracts.observation import (
    AnalysisMode,
    SeriesProvenance,
)
from aqil_research.interpret.research_note import render_bls_sahm_research_note
from aqil_research.methods.configs import SAHM_PUBLISHED
from aqil_research.methods.registry import SAHM_METHOD_ID, default_method_registry
from aqil_research.pipeline.models import ResearchExecutionRequest
from aqil_research.pipeline.orchestrate import execute_research_run
from aqil_research.sources.rights import (
    OperationalStatus,
    RightsOperation,
    find_source_rights,
    load_source_rights,
    source_usable,
)
from aqil_research.vintages.store import InMemoryObservationStore

FIXTURE = Path(__file__).parent / "fixtures" / "bls" / "api_lns14000000_success.json"
RETRIEVED = datetime(2026, 10, 17, 8, 0, tzinfo=UTC)
VINTAGE = RETRIEVED.date()


def test_parse_labels_latest_revised() -> None:
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    parsed = parse_bls_payload(
        payload,
        adapter_version="test:1",
        retrieved_at=RETRIEVED,
        collection_vintage_date=VINTAGE,
    )
    assert parsed.observations
    row = parsed.observations[0]
    assert row.series_provenance == SeriesProvenance.LATEST_REVISED
    assert row.unit == "percent"
    assert row.seasonal_adjustment.value == "seasonally_adjusted"


def test_offline_adapter_ingest_and_sahm() -> None:
    rights = find_source_rights(load_source_rights(), source_id="bls_cps_unemployment_rate")
    assert rights is not None
    adapter = BlsUnemploymentAdapter(
        config=BlsAdapterConfig(
            start_year=2022,
            end_year=2025,
            live=False,
            fixture_path=FIXTURE,
        ),
        retrieved_at=RETRIEVED,
    )
    fetch = adapter.fetch()
    assert fetch.observations
    store = InMemoryObservationStore()
    for row in fetch.observations:
        store.append(row)
    from aqil_research.methods.evaluation import latest_sahm_evaluation_period

    view = store.as_of("bls.ln.LNS14000000", RETRIEVED, AnalysisMode.LATEST_REVISED)
    latest = latest_sahm_evaluation_period(view)
    assert latest is not None
    run = execute_research_run(
        ResearchExecutionRequest(
            source_id="bls_cps_unemployment_rate",
            dataset_id="bls.ln.LNS14000000",
            decision_at=RETRIEVED,
            analysis_mode=AnalysisMode.LATEST_REVISED,
            evaluation_period=latest.isoformat(),
            method_id=SAHM_METHOD_ID,
            method_config=SAHM_PUBLISHED.model_dump(mode="json"),
        ),
        store=store,
        rights_records=load_source_rights(),
        method_registry=default_method_registry(),
        executed_at=RETRIEVED,
        run_id="bls-offline-run",
    )
    assert run.execution_status == "completed"
    assert run.data_sufficiency == "sufficient"
    note = render_bls_sahm_research_note(run)
    assert "Bureau of Labor Statistics" in note
    assert "latest-revised" in note.lower()
    assert "NBER" in note


def test_point_in_time_excludes_latest_revised_bls_rows() -> None:
    adapter = BlsUnemploymentAdapter(
        config=BlsAdapterConfig(2022, 2025, live=False, fixture_path=FIXTURE),
        retrieved_at=RETRIEVED,
    )
    store = InMemoryObservationStore()
    store.append_many(adapter.fetch().observations)
    pit = store.as_of("bls.ln.LNS14000000", RETRIEVED, AnalysisMode.POINT_IN_TIME)
    assert pit == {}


def test_rights_gate_refuses_disabled_source() -> None:
    rights = load_source_rights()
    record = next(row for row in rights if row.source_id == "bls_cps_unemployment_rate")
    disabled = record.model_copy(update={"operational_status": OperationalStatus.DISABLED})
    assert not source_usable(disabled, RightsOperation.AUTOMATED_ACCESS)


def test_malformed_payload_rejected() -> None:
    with pytest.raises(ValueError):
        parse_bls_payload(
            {"status": "REQUEST_SUCCEEDED", "Results": {"series": []}},
            adapter_version="t",
            retrieved_at=RETRIEVED,
            collection_vintage_date=VINTAGE,
        )


def test_offline_client_requires_fixture() -> None:
    with pytest.raises(BlsClientError):
        fetch_timeseries("LNS14000000", 2022, 2024, live=False, fixture_payload=None)


def _series_payload(points: list[dict[str, object]]) -> dict[str, object]:
    return {
        "status": "REQUEST_SUCCEEDED",
        "Results": {"series": [{"seriesID": "LNS14000000", "data": points}]},
    }


def _month(
    year: int, month: int, value: str, footnotes: list[dict[str, str]] | None = None
) -> dict[str, object]:
    point: dict[str, object] = {
        "year": str(year),
        "period": f"M{month:02d}",
        "periodName": "Month",
        "value": value,
    }
    if footnotes is not None:
        point["footnotes"] = footnotes
    return point


def test_official_unavailable_month_is_not_an_interrupted_fetch() -> None:
    points = [_month(2025, month, "4.0") for month in range(1, 13) if month != 10]
    points.append(
        _month(
            2025,
            10,
            "-",
            [{"code": "9", "text": "Data unavailable due to the 2025 lapse in appropriations."}],
        ),
    )
    parsed = parse_bls_payload(
        _series_payload(points),
        adapter_version="test:1",
        retrieved_at=RETRIEVED,
        collection_vintage_date=VINTAGE,
        start_year=2025,
        end_year=2025,
    )
    assert parsed.unavailable_months == ("2025-10-01",)
    assert parsed.missing_months == ()
    assert all(row.period_start.isoformat() != "2025-10-01" for row in parsed.observations)
    assert len(parsed.observations) == 11


def test_dash_without_official_footnote_stays_partial() -> None:
    points = [_month(2025, month, "4.0") for month in range(1, 13)]
    points[9] = _month(2025, 10, "-")
    parsed = parse_bls_payload(
        _series_payload(points),
        adapter_version="test:1",
        retrieved_at=RETRIEVED,
        collection_vintage_date=VINTAGE,
        start_year=2025,
        end_year=2025,
    )
    assert parsed.unavailable_months == ()
    assert "missing value for 2025-10-01" in parsed.missing_months


def test_absent_released_month_stays_partial() -> None:
    points = [_month(2025, month, "4.0") for month in range(1, 13) if month != 10]
    parsed = parse_bls_payload(
        _series_payload(points),
        adapter_version="test:1",
        retrieved_at=RETRIEVED,
        collection_vintage_date=VINTAGE,
        start_year=2025,
        end_year=2025,
    )
    assert "absent period 2025-10-01" in parsed.missing_months


def test_unreleased_current_month_is_not_required() -> None:
    points = [_month(2026, month, "4.0") for month in range(1, 10)]
    parsed = parse_bls_payload(
        _series_payload(points),
        adapter_version="test:1",
        retrieved_at=RETRIEVED,
        collection_vintage_date=VINTAGE,
        start_year=2026,
        end_year=2026,
    )
    assert parsed.missing_months == ()
    assert len(parsed.observations) == 9


def test_conflict_preserves_first_value() -> None:
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    parsed = parse_bls_payload(
        payload,
        adapter_version="test:1",
        retrieved_at=RETRIEVED,
        collection_vintage_date=VINTAGE,
    )
    store = InMemoryObservationStore()
    store.append(parsed.observations[0])
    conflict = parsed.observations[0].model_copy(update={"raw_value": "9.9"})
    from aqil_research.vintages.store import VintageConflictError

    with pytest.raises(VintageConflictError):
        store.append(conflict)
