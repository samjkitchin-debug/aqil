"""Regression tests for Grok M1 audit findings F1–F9."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from aqil_research.adapters.bls.client import BlsClientError, _build_request_body, fetch_timeseries
from aqil_research.adapters.bls.parse import parse_bls_payload
from aqil_research.adapters.fixture_ln_csv import FixtureLnCsvAdapter
from aqil_research.adapters.registry import AdapterRegistry
from aqil_research.contracts.observation import (
    AnalysisMode,
    AvailabilityPrecision,
    SeriesProvenance,
)
from aqil_research.methods.configs import SAHM_PUBLISHED
from aqil_research.methods.registry import SAHM_METHOD_ID, default_method_registry
from aqil_research.methods.sahm import run_sahm
from aqil_research.pipeline.integrity import analytical_payload_hash, verify_analytical_payload_hash
from aqil_research.pipeline.models import ResearchExecutionRequest
from aqil_research.pipeline.orchestrate import execute_research_run
from aqil_research.sources.rights import OperationalStatus, load_source_rights
from aqil_research.vintages.store import InMemoryObservationStore, content_snapshot_hash
from fixtures.observation_factory import (
    DATASET_ID,
    constant_unemployment_series,
    make_observation,
    month_start,
)

PROVIDERS = Path(__file__).parent / "fixtures" / "providers"
SOURCE_ID = "bls_cps_unemployment_rate"
DECISION_AT = datetime(2025, 2, 1, tzinfo=UTC)
BLS_FIXTURE = Path(__file__).parent / "fixtures" / "bls" / "api_lns14000000_success.json"
RETRIEVED = datetime(2026, 10, 17, 8, 0, tzinfo=UTC)


def test_f2_rejects_availability_before_source_release() -> None:
    release = datetime(2024, 7, 5, 12, 30, tzinfo=UTC)
    with pytest.raises(ValueError, match="earliest_model_available_at cannot precede"):
        make_observation(
            period_start=month_start(2024, 5),
            raw_value="3.7",
            provider_vintage_date=date(2024, 7, 6),
            source_release_at=release,
            earliest_model_available_at=datetime(2019, 1, 2, tzinfo=UTC),
        )


def test_f1_disabled_source_blocks_collect_through_pipeline() -> None:
    rights = load_source_rights()
    disabled = tuple(
        row.model_copy(update={"operational_status": OperationalStatus.DISABLED})
        if row.source_id == SOURCE_ID
        else row
        for row in rights
    )
    adapters = AdapterRegistry()
    adapters.register(FixtureLnCsvAdapter(PROVIDERS / "unemployment_equivalent.csv"))
    run = execute_research_run(
        ResearchExecutionRequest(
            source_id=SOURCE_ID,
            dataset_id=DATASET_ID,
            decision_at=DECISION_AT,
            analysis_mode=AnalysisMode.POINT_IN_TIME,
            evaluation_period="2024-12-01",
            method_id=SAHM_METHOD_ID,
            method_config=SAHM_PUBLISHED.model_dump(mode="json"),
            collect=True,
            primary_adapter_id="fixture_bls_ln_csv",
        ),
        store=InMemoryObservationStore(),
        rights_records=disabled,
        method_registry=default_method_registry(),
        adapter_registry=adapters,
    )
    assert run.execution_status == "failed_rights"


def test_f1_dataset_mismatch_blocks_ingest() -> None:
    rights = load_source_rights()
    record = next(row for row in rights if row.source_id == SOURCE_ID)
    mismatched = record.model_copy(update={"dataset_id": "wrong.dataset"})
    adapters = AdapterRegistry()
    adapters.register(FixtureLnCsvAdapter(PROVIDERS / "unemployment_equivalent.csv"))
    run = execute_research_run(
        ResearchExecutionRequest(
            source_id=SOURCE_ID,
            dataset_id="wrong.dataset",
            decision_at=DECISION_AT,
            analysis_mode=AnalysisMode.POINT_IN_TIME,
            evaluation_period="2024-12-01",
            method_id=SAHM_METHOD_ID,
            method_config=SAHM_PUBLISHED.model_dump(mode="json"),
            collect=True,
            primary_adapter_id="fixture_bls_ln_csv",
        ),
        store=InMemoryObservationStore(),
        rights_records=(mismatched,),
        method_registry=default_method_registry(),
        adapter_registry=adapters,
    )
    assert run.execution_status == "failed_rights"


def test_f3_snapshot_hash_changes_with_unit_and_value() -> None:
    base = make_observation(
        period_start=month_start(2024, 1),
        raw_value="3.7",
        provider_vintage_date=date(2024, 2, 5),
    )
    other_unit = base.model_copy(update={"unit": "index"})
    other_value = base.model_copy(update={"raw_value": "3.8"})
    h0 = content_snapshot_hash((base,))
    assert content_snapshot_hash((other_unit,)) != h0
    assert content_snapshot_hash((other_value,)) != h0


def test_f3_payload_hash_excludes_self_and_reverifies() -> None:
    payload = {"calculation": {"x": 1}, "analytical_payload_hash": "deadbeef"}
    digest = analytical_payload_hash(payload)
    payload["analytical_payload_hash"] = digest
    assert verify_analytical_payload_hash(payload)
    payload["calculation"] = {"x": 2}
    assert not verify_analytical_payload_hash(payload)


def test_f6_bls_parse_rejects_contradictory_duplicate_period() -> None:
    payload = json.loads(BLS_FIXTURE.read_text(encoding="utf-8"))
    series = payload["Results"]["series"][0]
    dup = dict(series["data"][0])
    dup["value"] = "5.1"
    series["data"] = [series["data"][0], dup]
    with pytest.raises(ValueError, match="contradictory values"):
        parse_bls_payload(
            payload,
            adapter_version="test:1",
            retrieved_at=RETRIEVED,
            collection_vintage_date=RETRIEVED.date(),
        )


def test_f5_sahm_negative_gap_not_triggered() -> None:
    rows = constant_unemployment_series(month_start(2022, 12), 15, "5.0")
    spike = make_observation(
        period_start=month_start(2024, 2),
        raw_value="4.0",
        provider_vintage_date=date(2024, 3, 5),
    )
    by_period = {row.period_start: row for row in rows + (spike,)}
    out = run_sahm(by_period, month_start(2024, 2), SAHM_PUBLISHED)
    assert out.gap_percentage_points < Decimal("0")
    assert out.triggered is False


def test_f5_sahm_gap_just_below_threshold() -> None:
    base = constant_unemployment_series(month_start(2023, 10), 12, "4.0")
    last_three = (
        make_observation(
            period_start=month_start(2024, 10),
            raw_value="4.4",
            provider_vintage_date=date(2024, 11, 5),
        ),
        make_observation(
            period_start=month_start(2024, 11),
            raw_value="4.4",
            provider_vintage_date=date(2024, 12, 5),
        ),
        make_observation(
            period_start=month_start(2024, 12),
            raw_value="4.4",
            provider_vintage_date=date(2025, 1, 5),
        ),
    )
    by_period = {row.period_start: row for row in base + last_three}
    out = run_sahm(by_period, month_start(2024, 12), SAHM_PUBLISHED)
    assert out.gap_percentage_points == Decimal("0.40")
    assert out.triggered is False


def test_f5_lookback_excludes_evaluation_month() -> None:
    """Prior low must not use a three-month average ending on the evaluation month."""
    months = constant_unemployment_series(month_start(2023, 1), 24, "4.0")
    by_period = {row.period_start: row for row in months}
    eval_month = month_start(2024, 12)
    out = run_sahm(by_period, eval_month, SAHM_PUBLISHED)
    assert eval_month not in out.months_used_for_lookback
    assert out.months_used_for_lookback[-1] == month_start(2024, 11)


def test_f7_year_span_limit_without_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("BLS_API_KEY", raising=False)
    with pytest.raises(BlsClientError, match="10 inclusive years"):
        _build_request_body("LNS14000000", 2010, 2020)


def test_f7_http_4xx_not_retried() -> None:
    response = MagicMock()
    response.status_code = 400
    response.content = b"{}"
    with patch("httpx.Client") as client_cls:
        client_cls.return_value.__enter__.return_value.post.return_value = response
        with pytest.raises(BlsClientError, match="HTTP 400"):
            fetch_timeseries("LNS14000000", 2022, 2023, live=True, fixture_payload=None)


def test_f2_latest_revised_excluded_from_point_in_time() -> None:
    store = InMemoryObservationStore()
    store.append(
        make_observation(
            period_start=month_start(2024, 1),
            raw_value="3.7",
            provider_vintage_date=date(2024, 2, 1),
            series_provenance=SeriesProvenance.LATEST_REVISED,
            availability_precision=AvailabilityPrecision.UNKNOWN,
        ),
    )
    pit = store.as_of(DATASET_ID, DECISION_AT, AnalysisMode.POINT_IN_TIME)
    assert pit == {}
