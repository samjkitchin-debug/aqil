"""Sahm insight wording: threshold met vs crossed."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from aqil_research.adapters.fixture_ln_csv import FixtureLnCsvAdapter
from aqil_research.contracts.observation import AnalysisMode
from aqil_research.insight.build_sahm import build_sahm_insight
from aqil_research.methods.configs import SAHM_PUBLISHED
from aqil_research.methods.registry import SAHM_METHOD_ID, default_method_registry
from aqil_research.pipeline.ingestion import ingest_from_adapter
from aqil_research.pipeline.models import ResearchExecutionRequest
from aqil_research.pipeline.orchestrate import execute_research_run
from aqil_research.sources.rights import load_source_rights
from aqil_research.vintages.store import InMemoryObservationStore

PROVIDERS = Path(__file__).parent / "fixtures" / "providers"


def _insight_for_fixture(csv_name: str, evaluation: str):
    rights = next(r for r in load_source_rights() if r.source_id == "bls_cps_unemployment_rate")
    store = InMemoryObservationStore()
    ingest_from_adapter(store, FixtureLnCsvAdapter(PROVIDERS / csv_name), rights)
    run = execute_research_run(
        ResearchExecutionRequest(
            source_id=rights.source_id,
            dataset_id=rights.dataset_id,
            decision_at=datetime(2025, 2, 1, 12, 0, tzinfo=UTC),
            analysis_mode=AnalysisMode.LATEST_REVISED,
            evaluation_period=evaluation,
            method_id=SAHM_METHOD_ID,
            method_config=SAHM_PUBLISHED.model_dump(mode="json"),
        ),
        store=store,
        rights_records=load_source_rights(),
        method_registry=default_method_registry(),
        run_id=f"lang-{csv_name}-{evaluation}",
    )
    return build_sahm_insight(run), run.calculation or {}


def test_threshold_met_without_crossing_does_not_claim_crossed() -> None:
    insight, calc = _insight_for_fixture("unemployment_equivalent.csv", "2024-12-01")
    assert calc.get("threshold_met") is True
    assert calc.get("threshold_crossed") is False
    assert "meets its conventional threshold" in insight.headline
    assert "crossed" not in insight.headline.lower()


def test_threshold_not_met_headline() -> None:
    from aqil_research.pipeline.models import ResearchRun

    run = ResearchRun(
        run_id="lang-not-met",
        executed_at=datetime(2025, 2, 1, 12, 0, tzinfo=UTC),
        execution_status="completed",
        dataset_id="bls.ln.LNS14000000",
        input_dataset_ids=["bls.ln.LNS14000000"],
        source_id="bls_cps_unemployment_rate",
        rights_record_id="bls_cps_unemployment_rate",
        analysis_mode=AnalysisMode.LATEST_REVISED,
        analysis_type="SAHM_UNEMPLOYMENT_GAP",
        decision_at=datetime(2025, 2, 1, 12, 0, tzinfo=UTC),
        evaluation_period="2024-12-01",
        method_id="SAHM_UNEMPLOYMENT_GAP",
        method_version="1.0.1",
        implementation_hash="x",
        config_id="sahm_published_v1",
        config_hash="y",
        input_snapshot_hash="z",
        data_sufficiency="sufficient",
        missing_data_reason=None,
        calculation={
            "evaluation_period": "2024-12-01",
            "gap_percentage_points": "0.40",
            "triggered": False,
            "threshold_met": False,
            "threshold_crossed": False,
        },
        statistical_interpretation="",
        causal_hypothesis="",
        market_pricing="unknown",
        investment_implication="no_action",
        assumptions=[],
        limitations=[],
        observation_ids=[],
        adapter_ids=[],
        ingest_notes=[],
        reproduction={},
        narrative="",
        publication_allowed=False,
        verification_status="unverified",
        evidence_reasons=[],
    )
    insight = build_sahm_insight(run)
    assert "crossed" not in insight.headline.lower()
    assert "meets its conventional threshold" not in insight.headline
