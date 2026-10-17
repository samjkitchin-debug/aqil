"""Sahm shortcut — delegates to the modular orchestrator."""

from __future__ import annotations

from aqil_research.methods.registry import default_method_registry
from aqil_research.methods.sahm import SAHM_METHOD_ID
from aqil_research.pipeline.models import (
    ResearchExecutionRequest,
    ResearchResult,
    ResearchRunRequest,
)
from aqil_research.pipeline.orchestrate import execute_research_run
from aqil_research.sources.rights import load_source_rights
from aqil_research.vintages.store import InMemoryObservationStore


def run_research(
    store: InMemoryObservationStore,
    request: ResearchRunRequest,
) -> ResearchResult:
    execution = ResearchExecutionRequest(
        source_id=request.source_id,
        dataset_id=request.dataset_id,
        decision_at=request.decision_at,
        analysis_mode=request.analysis_mode,
        evaluation_period=request.evaluation_period,
        method_id=SAHM_METHOD_ID,
        method_config=request.sahm_config.model_dump(mode="json"),
    )
    return execute_research_run(
        execution,
        store=store,
        rights_records=load_source_rights(),
        method_registry=default_method_registry(),
    )
