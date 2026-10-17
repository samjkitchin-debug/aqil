"""Collect labour, SLOOS and Census advance orders → macro conditions run → insight."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import psycopg

from aqil_research.adapters.census_adv_orders.adapter import (
    CensusAdvOrdersAdapter,
    CensusAdvOrdersAdapterConfig,
)
from aqil_research.adapters.fed_sloos.adapter import FedSloosAdapter, FedSloosAdapterConfig
from aqil_research.adapters.registry import AdapterRegistry
from aqil_research.collection.service import (
    CENSUS_SOURCE_ID,
    SLOOS_SOURCE_ID,
    collect_bls_unemployment,
    collect_registered_adapter,
)
from aqil_research.contracts.observation import AnalysisMode
from aqil_research.insight.build_macro_conditions import build_macro_conditions_insight
from aqil_research.insight.models import ResearchInsight
from aqil_research.methods.configs import MACRO_CONDITIONS_PUBLISHED
from aqil_research.methods.registry import MACRO_CONDITIONS_METHOD_ID, default_method_registry
from aqil_research.persistence.observation_store import PostgresResearchObservationStore
from aqil_research.persistence.reproduce import verify_stored_run_replay
from aqil_research.persistence.runs import save_research_run
from aqil_research.pipeline.models import ResearchExecutionRequest
from aqil_research.pipeline.orchestrate import execute_research_run
from aqil_research.sources.rights import load_source_rights

BLS_DATASET_ID = "bls.ln.LNS14000000"
BLS_SOURCE_ID = "bls_cps_unemployment_rate"


@dataclass(frozen=True, slots=True)
class CollectAndRunMacroResult:
    collection_outcomes: tuple[str, ...]
    run_id: str | None
    execution_status: str | None
    analytical_payload_hash: str | None
    recompute_match: bool | None
    insight: ResearchInsight | None
    warnings: tuple[str, ...]


def collect_and_run_macro_conditions(
    conn: psycopg.Connection,
    *,
    bls_fixture_path: Path,
    sloos_fixture_path: Path,
    census_fixture_path: Path,
    run_id: str,
    live: bool = False,
    start_year: int | None = None,
    end_year: int | None = None,
) -> CollectAndRunMacroResult:
    now = datetime.now(tz=UTC)
    rights = load_source_rights()
    warnings: list[str] = []
    outcomes: list[str] = []

    bls_result, store = collect_bls_unemployment(
        store_backend="postgres",
        collected_at=now,
        live=live,
        fixture_path=str(bls_fixture_path) if not live else None,
        start_year=start_year,
        end_year=end_year,
        conn=conn,
    )
    outcomes.append(bls_result.outcome)
    warnings.extend(bls_result.warnings)
    if bls_result.outcome in ("failed_rights", "failed_fetch", "failed_validation"):
        return _failed(outcomes, warnings)

    sloos_adapter = FedSloosAdapter(
        config=FedSloosAdapterConfig(
            live=live,
            fixture_path=sloos_fixture_path if not live else None,
        ),
        retrieved_at=now,
    )
    census_adapter = CensusAdvOrdersAdapter(
        config=CensusAdvOrdersAdapterConfig(
            live=live,
            fixture_path=census_fixture_path if not live else None,
        ),
        retrieved_at=now,
    )

    for adapter, source_id in (
        (sloos_adapter, SLOOS_SOURCE_ID),
        (census_adapter, CENSUS_SOURCE_ID),
    ):
        result, _store = collect_registered_adapter(
            store_backend="postgres",
            adapter=adapter,
            source_id=source_id,
            collected_at=now,
            live=live,
            conn=conn,
        )
        outcomes.append(result.outcome)
        warnings.extend(result.warnings)
        if result.outcome in ("failed_rights", "failed_fetch", "conflicts"):
            return _failed(outcomes, warnings)

    research_store = PostgresResearchObservationStore(conn)

    adapter_registry = AdapterRegistry()
    adapter_registry.register(sloos_adapter)
    adapter_registry.register(census_adapter)

    request = ResearchExecutionRequest(
        source_id=BLS_SOURCE_ID,
        dataset_id=BLS_DATASET_ID,
        decision_at=now,
        analysis_mode=AnalysisMode.LATEST_REVISED,
        evaluation_period=MACRO_CONDITIONS_PUBLISHED["labour_evaluation_period"],
        method_id=MACRO_CONDITIONS_METHOD_ID,
        method_config=MACRO_CONDITIONS_PUBLISHED,
        collect=False,
        primary_adapter_id=None,
        optional_adapter_ids=(),
    )
    run = execute_research_run(
        request,
        store=research_store,
        rights_records=rights,
        method_registry=default_method_registry(),
        adapter_registry=adapter_registry,
        executed_at=now,
        run_id=run_id,
    )
    save_research_run(conn, run)
    replay = verify_stored_run_replay(conn, run_id)
    recompute_match = replay.full_match
    if not recompute_match:
        warnings.append("Replay mismatch on macro conditions run")

    insight = build_macro_conditions_insight(run)
    return CollectAndRunMacroResult(
        collection_outcomes=tuple(outcomes),
        run_id=run.run_id,
        execution_status=run.execution_status,
        analytical_payload_hash=run.analytical_payload_hash,
        recompute_match=recompute_match,
        insight=insight,
        warnings=tuple(warnings),
    )


def _failed(outcomes: list[str], warnings: list[str]) -> CollectAndRunMacroResult:
    return CollectAndRunMacroResult(
        collection_outcomes=tuple(outcomes),
        run_id=None,
        execution_status=None,
        analytical_payload_hash=None,
        recompute_match=None,
        insight=None,
        warnings=tuple(warnings),
    )
