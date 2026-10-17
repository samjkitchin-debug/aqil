"""Mandatory architectural proof tests (M1 Phase 3)."""

from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

from aqil_research.adapters.fixture_ln_csv import FixtureLnCsvAdapter
from aqil_research.adapters.fixture_series_json import FixtureSeriesJsonAdapter
from aqil_research.adapters.registry import AdapterRegistry
from aqil_research.contracts.observation import AnalysisMode
from aqil_research.methods.configs import SAHM_PUBLISHED, SAHM_SENSITIVITY
from aqil_research.methods.registry import SAHM_METHOD_ID, default_method_registry
from aqil_research.pipeline.integrity import verify_analytical_payload_hash
from aqil_research.pipeline.models import ResearchExecutionRequest
from aqil_research.pipeline.orchestrate import execute_research_run
from aqil_research.sources.rights import (
    OperationalStatus,
    RightsOperation,
    load_source_rights,
    source_usable,
)
from aqil_research.vintages.store import InMemoryObservationStore
from fixtures.observation_factory import (
    DATASET_ID,
    make_observation,
    month_start,
)

PROVIDERS = Path(__file__).parent / "fixtures" / "providers"
DECISION_AT = datetime(2025, 2, 1, 12, 0, tzinfo=UTC)
EXECUTED_AT = datetime(2025, 2, 1, 12, 1, tzinfo=UTC)
SOURCE_ID = "bls_cps_unemployment_rate"


def _adapter_registry() -> AdapterRegistry:
    registry = AdapterRegistry()
    registry.register(FixtureLnCsvAdapter(PROVIDERS / "unemployment_equivalent.csv"))
    registry.register(FixtureSeriesJsonAdapter(PROVIDERS / "unemployment_equivalent.json"))
    return registry


def _sahm_request() -> ResearchExecutionRequest:
    return ResearchExecutionRequest(
        source_id=SOURCE_ID,
        dataset_id=DATASET_ID,
        decision_at=DECISION_AT,
        analysis_mode=AnalysisMode.POINT_IN_TIME,
        evaluation_period="2024-12-01",
        method_id=SAHM_METHOD_ID,
        method_config=SAHM_PUBLISHED.model_dump(mode="json"),
    )


def test_a_provider_replacement_equivalent_sahm_output() -> None:
    rights = load_source_rights()
    methods = default_method_registry()
    adapters = _adapter_registry()
    request = _sahm_request()

    store_csv = InMemoryObservationStore()
    run_csv = execute_research_run(
        request.model_copy(
            update={"collect": True, "primary_adapter_id": "fixture_bls_ln_csv"},
        ),
        store=store_csv,
        rights_records=rights,
        method_registry=methods,
        adapter_registry=adapters,
        executed_at=EXECUTED_AT,
        run_id="proof-a-csv",
    )

    store_json = InMemoryObservationStore()
    run_json = execute_research_run(
        request.model_copy(
            update={"collect": True, "primary_adapter_id": "fixture_aqil_series_json"},
        ),
        store=store_json,
        rights_records=rights,
        method_registry=methods,
        adapter_registry=adapters,
        executed_at=EXECUTED_AT,
        run_id="proof-a-json",
    )

    assert run_csv.data_sufficiency == "sufficient"
    assert run_json.data_sufficiency == "sufficient"
    assert run_csv.calculation == run_json.calculation
    assert run_csv.config_hash == run_json.config_hash
    assert run_csv.input_snapshot_hash != run_json.input_snapshot_hash
    assert verify_analytical_payload_hash(run_csv.model_dump(mode="json"))
    assert verify_analytical_payload_hash(run_json.model_dump(mode="json"))


def test_b_two_configs_identifiable_without_code_change() -> None:
    rights = load_source_rights()
    store = InMemoryObservationStore()
    adapters = _adapter_registry()
    methods = default_method_registry()
    base = _sahm_request()
    execute_research_run(
        base.model_copy(
            update={"collect": True, "primary_adapter_id": "fixture_bls_ln_csv"},
        ),
        store=store,
        rights_records=rights,
        method_registry=methods,
        adapter_registry=adapters,
        executed_at=EXECUTED_AT,
    )
    published = execute_research_run(
        base,
        store=store,
        rights_records=rights,
        method_registry=methods,
        executed_at=EXECUTED_AT,
        run_id="proof-b-pub",
    )
    sensitivity = execute_research_run(
        base.model_copy(
            update={"method_config": SAHM_SENSITIVITY.model_dump(mode="json")},
        ),
        store=store,
        rights_records=rights,
        method_registry=methods,
        executed_at=EXECUTED_AT,
        run_id="proof-b-sens",
    )
    assert published.implementation_hash == sensitivity.implementation_hash
    assert published.config_hash != sensitivity.config_hash
    assert published.config_id != sensitivity.config_id
    assert sensitivity.config_id == SAHM_SENSITIVITY.config_id
    assert published.calculation is not None and sensitivity.calculation is not None
    assert published.calculation["triggered"] is True
    assert sensitivity.calculation["triggered"] is True


def test_c_second_method_via_same_orchestrator() -> None:
    rights = load_source_rights()
    store = InMemoryObservationStore()
    adapters = _adapter_registry()
    methods = default_method_registry()
    execute_research_run(
        _sahm_request().model_copy(
            update={"collect": True, "primary_adapter_id": "fixture_bls_ln_csv"},
        ),
        store=store,
        rights_records=rights,
        method_registry=methods,
        adapter_registry=adapters,
        executed_at=EXECUTED_AT,
    )
    run = execute_research_run(
        ResearchExecutionRequest(
            source_id=SOURCE_ID,
            dataset_id=DATASET_ID,
            decision_at=DECISION_AT,
            analysis_mode=AnalysisMode.POINT_IN_TIME,
            evaluation_period="2024-12-01",
            method_id="PERIOD_LEVEL_CHANGE",
            method_config={
                "config_id": "pchange_demo_v1",
                "months_back": 3,
                "label": "Three-month level change demo",
            },
        ),
        store=store,
        rights_records=rights,
        method_registry=methods,
        executed_at=EXECUTED_AT,
        run_id="proof-c",
    )
    assert run.execution_status == "completed"
    assert run.method_id == "PERIOD_LEVEL_CHANGE"
    assert run.calculation is not None
    assert "level_change" in run.calculation


def test_d_disabled_source_blocks_collection_preserves_history() -> None:
    rights = load_source_rights()
    record = next(row for row in rights if row.source_id == SOURCE_ID)
    assert source_usable(record, RightsOperation.AUTOMATED_ACCESS)

    store = InMemoryObservationStore()
    store.append(
        make_observation(
            period_start=month_start(2024, 1),
            raw_value="3.7",
            provider_vintage_date=date(2024, 2, 5),
        ),
    )
    before = len(store.all_observations())

    disabled = record.model_copy(update={"operational_status": OperationalStatus.DISABLED})
    adapters = _adapter_registry()
    run = execute_research_run(
        _sahm_request().model_copy(
            update={"collect": True, "primary_adapter_id": "fixture_bls_ln_csv"},
        ),
        store=store,
        rights_records=tuple(disabled if row.source_id == SOURCE_ID else row for row in rights),
        method_registry=default_method_registry(),
        adapter_registry=adapters,
        executed_at=EXECUTED_AT,
    )
    assert run.execution_status == "failed_rights"
    assert len(store.all_observations()) == before


def test_e_later_revision_does_not_alter_original_run_payload() -> None:
    rights = load_source_rights()
    store = InMemoryObservationStore()
    adapters = _adapter_registry()
    methods = default_method_registry()
    execute_research_run(
        _sahm_request().model_copy(
            update={"collect": True, "primary_adapter_id": "fixture_bls_ln_csv"},
        ),
        store=store,
        rights_records=rights,
        method_registry=methods,
        adapter_registry=adapters,
        executed_at=EXECUTED_AT,
    )
    original = execute_research_run(
        _sahm_request(),
        store=store,
        rights_records=rights,
        method_registry=methods,
        executed_at=EXECUTED_AT,
        run_id="proof-e-original",
    )
    frozen_hash = original.analytical_payload_hash

    store.append(
        make_observation(
            period_start=month_start(2024, 12),
            raw_value="9.9",
            provider_vintage_date=date(2025, 6, 1),
            observation_id="future-revision",
        ),
    )
    replay = execute_research_run(
        _sahm_request(),
        store=store,
        rights_records=rights,
        method_registry=methods,
        executed_at=EXECUTED_AT,
        run_id="proof-e-replay",
    )
    assert replay.analytical_payload_hash == frozen_hash
    assert original.analytical_payload_hash == frozen_hash


def test_h_identical_inputs_reproduce_analytical_payload() -> None:
    rights = load_source_rights()
    store = InMemoryObservationStore()
    adapters = _adapter_registry()
    methods = default_method_registry()
    execute_research_run(
        _sahm_request().model_copy(
            update={"collect": True, "primary_adapter_id": "fixture_bls_ln_csv"},
        ),
        store=store,
        rights_records=rights,
        method_registry=methods,
        adapter_registry=adapters,
        executed_at=EXECUTED_AT,
    )
    first = execute_research_run(
        _sahm_request(),
        store=store,
        rights_records=rights,
        method_registry=methods,
        executed_at=EXECUTED_AT,
        run_id="proof-h-1",
    )
    second = execute_research_run(
        _sahm_request(),
        store=store,
        rights_records=rights,
        method_registry=methods,
        executed_at=EXECUTED_AT,
        run_id="proof-h-2",
    )
    assert first.analytical_payload_hash == second.analytical_payload_hash
    assert first.run_id != second.run_id
