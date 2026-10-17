"""Replay uses frozen observation evidence only."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from aqil_research.adapters.fixture_ln_csv import FixtureLnCsvAdapter
from aqil_research.contracts.observation import AnalysisMode
from aqil_research.methods.configs import SAHM_PUBLISHED
from aqil_research.methods.registry import SAHM_METHOD_ID, default_method_registry
from aqil_research.pipeline.ingestion import ingest_from_adapter
from aqil_research.pipeline.models import ResearchExecutionRequest
from aqil_research.pipeline.orchestrate import (
    cited_observation_snapshot_hash,
    execute_research_run,
)
from aqil_research.sources.rights import load_source_rights
from aqil_research.vintages.store import InMemoryObservationStore, content_snapshot_hash
from fixtures.observation_factory import make_observation, month_start

PROVIDERS = Path(__file__).parent / "fixtures" / "providers"
DECISION_AT = datetime(2025, 2, 1, 12, 0, tzinfo=UTC)


def _run(store: InMemoryObservationStore, run_id: str):
    rights = load_source_rights()
    return execute_research_run(
        ResearchExecutionRequest(
            source_id="bls_cps_unemployment_rate",
            dataset_id="bls.ln.LNS14000000",
            decision_at=DECISION_AT,
            analysis_mode=AnalysisMode.POINT_IN_TIME,
            evaluation_period="2024-12-01",
            method_id=SAHM_METHOD_ID,
            method_config=SAHM_PUBLISHED.model_dump(mode="json"),
            collect=False,
        ),
        store=store,
        rights_records=rights,
        method_registry=default_method_registry(),
        executed_at=DECISION_AT,
        run_id=run_id,
    )


def test_cited_snapshot_ignores_extra_observations_in_store() -> None:
    rights = next(r for r in load_source_rights() if r.source_id == "bls_cps_unemployment_rate")
    adapter = FixtureLnCsvAdapter(PROVIDERS / "unemployment_equivalent.csv")
    store = InMemoryObservationStore()
    ingest_from_adapter(store, adapter, rights)
    first = _run(store, "replay-cited-1")

    store.append(
        make_observation(
            period_start=month_start(2022, 1),
            raw_value="3.5",
            provider_vintage_date=month_start(2022, 2),
        ),
    )

    as_of_rows = store.as_of(
        "bls.ln.LNS14000000",
        DECISION_AT,
        AnalysisMode.POINT_IN_TIME,
    )
    full_hash = content_snapshot_hash(tuple(as_of_rows[p] for p in sorted(as_of_rows)))
    cited_hash = cited_observation_snapshot_hash(store, list(first.observation_ids))

    assert cited_hash == first.input_snapshot_hash
    assert full_hash != cited_hash

    second = _run(store, "replay-cited-2")
    assert second.calculation == first.calculation
    assert second.input_snapshot_hash == first.input_snapshot_hash
    assert second.analytical_payload_hash == first.analytical_payload_hash


def test_same_calculation_different_cited_sets_have_distinct_snapshot_hashes() -> None:
    """Matching Sahm numbers must not collapse distinct provenance snapshots."""
    rights = next(r for r in load_source_rights() if r.source_id == "bls_cps_unemployment_rate")
    adapter = FixtureLnCsvAdapter(PROVIDERS / "unemployment_equivalent.csv")
    store_a = InMemoryObservationStore()
    ingest_from_adapter(store_a, adapter, rights)
    run_a = _run(store_a, "prov-a")

    store_b = InMemoryObservationStore()
    ingest_from_adapter(store_b, adapter, rights)
    run_b = _run(store_b, "prov-b")

    assert run_a.calculation == run_b.calculation
    assert run_a.input_snapshot_hash == run_b.input_snapshot_hash
