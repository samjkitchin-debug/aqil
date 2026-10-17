"""Evidence and failure-path tests for the research orchestrator."""

from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from aqil_research.adapters.fixture_ln_csv import FixtureLnCsvAdapter
from aqil_research.adapters.registry import AdapterRegistry
from aqil_research.contracts.observation import AnalysisMode
from aqil_research.editorial.claim_verifier import ClaimVerificationError
from aqil_research.editorial.research_verification import (
    verify_calculated_claim_for_publication,
    verify_research_run_for_publication,
)
from aqil_research.methods.configs import SAHM_PUBLISHED
from aqil_research.methods.registry import SAHM_METHOD_ID, default_method_registry
from aqil_research.pipeline.ingestion import ingest_from_adapter
from aqil_research.pipeline.models import ResearchExecutionRequest
from aqil_research.pipeline.orchestrate import execute_research_run
from aqil_research.sources.rights import load_source_rights
from aqil_research.vintages.store import InMemoryObservationStore
from fixtures.observation_factory import DATASET_ID, make_observation, month_start

SOURCE_ID = "bls_cps_unemployment_rate"
DECISION_AT = datetime(2025, 2, 1, tzinfo=UTC)


def test_f_missing_essential_observations_insufficient() -> None:
    run = execute_research_run(
        ResearchExecutionRequest(
            source_id=SOURCE_ID,
            dataset_id=DATASET_ID,
            decision_at=DECISION_AT,
            analysis_mode=AnalysisMode.POINT_IN_TIME,
            evaluation_period="2024-12-01",
            method_id=SAHM_METHOD_ID,
            method_config=SAHM_PUBLISHED.model_dump(mode="json"),
        ),
        store=InMemoryObservationStore(),
        rights_records=load_source_rights(),
        method_registry=default_method_registry(),
    )
    assert run.data_sufficiency == "insufficient"
    assert run.execution_status == "completed_insufficient"


def test_unknown_source_identity_fails_rights() -> None:
    run = execute_research_run(
        ResearchExecutionRequest(
            source_id="unknown_source",
            dataset_id=DATASET_ID,
            decision_at=DECISION_AT,
            analysis_mode=AnalysisMode.POINT_IN_TIME,
            evaluation_period="2024-12-01",
            method_id=SAHM_METHOD_ID,
            method_config=SAHM_PUBLISHED.model_dump(mode="json"),
        ),
        store=InMemoryObservationStore(),
        rights_records=load_source_rights(),
        method_registry=default_method_registry(),
    )
    assert run.execution_status == "failed_rights"


def test_invalid_method_config_fails_method() -> None:
    run = execute_research_run(
        ResearchExecutionRequest(
            source_id=SOURCE_ID,
            dataset_id=DATASET_ID,
            decision_at=DECISION_AT,
            analysis_mode=AnalysisMode.POINT_IN_TIME,
            evaluation_period="2024-12-01",
            method_id=SAHM_METHOD_ID,
            method_config={"config_id": "bad", "threshold_percentage_points": "-1", "label": "x"},
        ),
        store=InMemoryObservationStore(),
        rights_records=load_source_rights(),
        method_registry=default_method_registry(),
    )
    assert run.execution_status == "failed_method"


def test_contradictory_provider_records_retained_as_conflict(tmp_path: Path) -> None:
    rights = load_source_rights()
    record = next(row for row in rights if row.source_id == SOURCE_ID)
    store = InMemoryObservationStore()
    store.append(
        make_observation(
            period_start=month_start(2024, 1),
            raw_value="3.7",
            provider_vintage_date=date(2024, 2, 5),
            observation_id="seed-jan",
        ),
    )
    fixture = tmp_path / "conflict_row.csv"
    fixture.write_text(
        "observation_id,period_start,raw_value,provider_vintage_date\n"
        "seed-jan,2024-01-01,3.9,2024-02-05\n",
        encoding="utf-8",
    )
    adapter = FixtureLnCsvAdapter(fixture)
    outcome = ingest_from_adapter(store, adapter, record)
    assert outcome.conflicts
    assert store.all_observations()[0].raw_value == "3.7"


def test_g_unverified_research_and_calculated_claims_blocked() -> None:
    store = InMemoryObservationStore()
    rights = load_source_rights()
    adapters = AdapterRegistry()
    providers = Path(__file__).parent / "fixtures" / "providers"
    adapters.register(FixtureLnCsvAdapter(providers / "unemployment_equivalent.csv"))
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
        store=store,
        rights_records=rights,
        method_registry=default_method_registry(),
        adapter_registry=adapters,
    )
    with pytest.raises(ClaimVerificationError):
        verify_research_run_for_publication(run)
    with pytest.raises(ClaimVerificationError):
        verify_calculated_claim_for_publication(
            {
                "claim_type": "calculated",
                "verification_status": "unverified",
            },
        )
