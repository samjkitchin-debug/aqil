"""Recompute research from a persisted run's frozen observation evidence."""

from __future__ import annotations

import psycopg

from aqil_research.methods.configs import SAHM_PUBLISHED, SAHM_SENSITIVITY
from aqil_research.methods.registry import default_method_registry
from aqil_research.persistence.observation_store import load_observations_by_ids
from aqil_research.persistence.runs import load_research_run, load_run_observation_ids
from aqil_research.pipeline.models import ResearchExecutionRequest, ResearchRun
from aqil_research.pipeline.orchestrate import execute_research_run
from aqil_research.sources.rights import load_source_rights
from aqil_research.vintages.store import InMemoryObservationStore


def recompute_stored_run(conn: psycopg.Connection, run_id: str) -> ResearchRun:
    """Re-run analysis using observation IDs recorded on the immutable run."""
    stored = load_research_run(conn, run_id)
    observation_ids = load_run_observation_ids(conn, run_id)
    observations = load_observations_by_ids(conn, observation_ids)
    store = InMemoryObservationStore()
    for row in observations:
        store.append(row)

    method_config = _config_for_id(stored.config_id)
    request = ResearchExecutionRequest(
        source_id=stored.source_id,
        dataset_id=stored.dataset_id,
        decision_at=stored.decision_at,
        analysis_mode=stored.analysis_mode,
        evaluation_period=stored.evaluation_period,
        method_id=stored.method_id,
        method_config=method_config,
        collect=False,
    )
    return execute_research_run(
        request,
        store=store,
        rights_records=load_source_rights(),
        method_registry=default_method_registry(),
        executed_at=stored.executed_at,
        run_id=stored.run_id,
    )


def _config_for_id(config_id: str) -> dict[str, object]:
    if config_id == SAHM_PUBLISHED.config_id:
        return SAHM_PUBLISHED.model_dump(mode="json")
    if config_id == SAHM_SENSITIVITY.config_id:
        return SAHM_SENSITIVITY.model_dump(mode="json")
    raise ValueError(f"unknown config_id for reproduction: {config_id}")
