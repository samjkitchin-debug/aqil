"""PostgreSQL persistence vertical slice (requires local Supabase)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path

import psycopg
import pytest

from aqil_research.adapters.fixture_ln_csv import FixtureLnCsvAdapter
from aqil_research.adapters.registry import AdapterRegistry
from aqil_research.contracts.observation import AnalysisMode
from aqil_research.methods.configs import SAHM_PUBLISHED
from aqil_research.methods.registry import SAHM_METHOD_ID, default_method_registry
from aqil_research.persistence.config import research_database_url_or_local_default
from aqil_research.persistence.connection import research_connection
from aqil_research.persistence.ingest import ingest_adapter_to_postgres
from aqil_research.persistence.reproduce import recompute_stored_run
from aqil_research.persistence.runs import load_research_run, save_research_run
from aqil_research.pipeline.ingestion import ingest_from_adapter
from aqil_research.pipeline.models import ResearchExecutionRequest
from aqil_research.pipeline.orchestrate import execute_research_run
from aqil_research.sources.rights import load_source_rights
from aqil_research.vintages.store import InMemoryObservationStore

PROVIDERS = Path(__file__).parent / "fixtures" / "providers"
SOURCE_ID = "bls_cps_unemployment_rate"
DATASET_ID = "bls.ln.LNS14000000"
DECISION_AT = datetime(2025, 2, 1, 12, 0, tzinfo=UTC)
EVALUATION = "2024-12-01"


def _db_available() -> bool:
    try:
        with psycopg.connect(research_database_url_or_local_default(), connect_timeout=2) as conn:
            with conn.cursor() as cur:
                cur.execute("select 1")
        return True
    except Exception:
        return False


pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def require_db() -> None:
    if not _db_available():
        pytest.skip("RESEARCH_DATABASE_URL / local Supabase not available")


def _sahm_request() -> ResearchExecutionRequest:
    return ResearchExecutionRequest(
        source_id=SOURCE_ID,
        dataset_id=DATASET_ID,
        decision_at=DECISION_AT,
        analysis_mode=AnalysisMode.POINT_IN_TIME,
        evaluation_period=EVALUATION,
        method_id=SAHM_METHOD_ID,
        method_config=SAHM_PUBLISHED.model_dump(mode="json"),
        collect=False,
    )


def test_memory_and_postgres_equivalent_sahm(require_db: None) -> None:
    rights = load_source_rights()
    adapter = FixtureLnCsvAdapter(PROVIDERS / "unemployment_equivalent.csv")
    registry = AdapterRegistry()
    registry.register(adapter)

    memory_store = InMemoryObservationStore()
    ingest_from_adapter(memory_store, adapter, next(r for r in rights if r.source_id == SOURCE_ID))
    memory_run = execute_research_run(
        _sahm_request(),
        store=memory_store,
        rights_records=rights,
        method_registry=default_method_registry(),
        executed_at=DECISION_AT,
        run_id="equiv-memory",
    )

    with research_connection() as conn:
        pg_store, _ingest = ingest_adapter_to_postgres(
            conn,
            adapter,
            next(r for r in rights if r.source_id == SOURCE_ID),
            retrieved_at=DECISION_AT,
            collection_mode="fixture",
        )
        pg_run = execute_research_run(
            _sahm_request(),
            store=pg_store,
            rights_records=rights,
            method_registry=default_method_registry(),
            executed_at=DECISION_AT,
            run_id="equiv-postgres",
        )

    assert memory_run.data_sufficiency == pg_run.data_sufficiency
    assert memory_run.calculation == pg_run.calculation


def test_persisted_run_immutable_after_new_observations(require_db: None) -> None:
    rights = load_source_rights()
    record = next(r for r in rights if r.source_id == SOURCE_ID)
    adapter = FixtureLnCsvAdapter(PROVIDERS / "unemployment_equivalent.csv")
    run_id = f"immutability-run-{uuid.uuid4().hex[:12]}"

    with research_connection() as conn:
        store, _ = ingest_adapter_to_postgres(
            conn,
            adapter,
            record,
            retrieved_at=DECISION_AT,
            collection_mode="fixture",
        )
        run = execute_research_run(
            _sahm_request(),
            store=store,
            rights_records=rights,
            method_registry=default_method_registry(),
            executed_at=DECISION_AT,
            run_id=run_id,
        )
        save_research_run(conn, run)
        stored_hash = run.analytical_payload_hash

        # Second ingest adds rows but must not mutate the saved run record.
        ingest_adapter_to_postgres(
            conn,
            adapter,
            record,
            retrieved_at=datetime(2025, 3, 1, 12, 0, tzinfo=UTC),
            collection_mode="fixture",
        )
        reloaded = load_research_run(conn, run_id)
        assert reloaded.analytical_payload_hash == stored_hash
        assert reloaded.calculation == run.calculation

        recompute = recompute_stored_run(conn, run_id)
        assert recompute.calculation == run.calculation
