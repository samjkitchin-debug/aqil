"""Research orchestration — rights, ingest, as-of, method, evidence."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from typing import Literal

from aqil_research.adapters.registry import AdapterRegistry
from aqil_research.methods.protocol import MethodContext
from aqil_research.methods.registry import MethodRegistry
from aqil_research.pipeline.evidence import assess_analytical_evidence
from aqil_research.pipeline.ingestion import IngestionBlockedError, ingest_from_adapter
from aqil_research.pipeline.integrity import analytical_payload_hash
from aqil_research.pipeline.models import ResearchExecutionRequest, ResearchRun
from aqil_research.sources.rights import SourceRightsRecord
from aqil_research.sources.rights_gate import (
    RightsGateError,
    assert_rights_for_analysis,
    assert_rights_for_ingest,
    assert_rights_for_replay,
    resolve_research_rights,
)
from aqil_research.vintages.store import ObservationStore, content_snapshot_hash


def cited_observation_snapshot_hash(
    store: ObservationStore,
    observation_ids: list[str],
) -> str:
    """Hash only observations cited on the run (frozen evidence set)."""
    if not observation_ids:
        return content_snapshot_hash(())
    wanted = frozenset(observation_ids)
    cited = tuple(
        sorted(
            (obs for obs in store.all_observations() if obs.observation_id in wanted),
            key=lambda row: row.observation_id,
        )
    )
    if len(cited) != len(wanted):
        missing = wanted - {row.observation_id for row in cited}
        raise ValueError(f"cited observations missing from store: {sorted(missing)}")
    return content_snapshot_hash(cited)


def execute_research_run(
    request: ResearchExecutionRequest,
    *,
    store: ObservationStore,
    rights_records: tuple[SourceRightsRecord, ...],
    method_registry: MethodRegistry,
    adapter_registry: AdapterRegistry | None = None,
    executed_at: datetime | None = None,
    run_id: str | None = None,
) -> ResearchRun:
    """Single entry point with explicit dependency injection."""
    wall_clock = executed_at or datetime.now(tz=UTC)
    try:
        rights = resolve_research_rights(
            rights_records,
            source_id=request.source_id,
            dataset_id=request.dataset_id,
        )
    except RightsGateError as exc:
        return _failed_run(
            request,
            execution_status="failed_rights",
            reason=str(exc),
            wall_clock=wall_clock,
            run_id=run_id,
        )

    ingest_notes: list[str] = []
    adapter_ids: list[str] = []
    if request.collect and adapter_registry is not None:
        if request.primary_adapter_id:
            adapter = adapter_registry.get(request.primary_adapter_id)
            adapter_ids.append(adapter.identity.adapter_id)
            try:
                assert_rights_for_ingest(rights, adapter)
                outcome = ingest_from_adapter(store, adapter, rights, optional=False)
            except (IngestionBlockedError, RightsGateError) as exc:
                return _failed_run(
                    request,
                    execution_status="failed_rights",
                    reason=str(exc),
                    wall_clock=wall_clock,
                    run_id=run_id,
                    rights=rights,
                )
            if outcome.block_reason and outcome.append is None:
                return _failed_run(
                    request,
                    execution_status="failed_ingest",
                    reason=outcome.block_reason,
                    wall_clock=wall_clock,
                    run_id=run_id,
                    rights=rights,
                )
            if outcome.fetch and outcome.fetch.errors and not outcome.fetch.observations:
                return _failed_run(
                    request,
                    execution_status="failed_ingest",
                    reason=outcome.fetch.errors[0].message,
                    wall_clock=wall_clock,
                    run_id=run_id,
                    rights=rights,
                )
            if outcome.conflicts:
                return _failed_run(
                    request,
                    execution_status="failed_ingest",
                    reason=outcome.conflicts[0],
                    wall_clock=wall_clock,
                    run_id=run_id,
                    rights=rights,
                )
            if outcome.fetch and outcome.fetch.errors:
                ingest_notes.extend(error.message for error in outcome.fetch.errors)

        for optional_id in request.optional_adapter_ids:
            adapter = adapter_registry.get(optional_id)
            adapter_ids.append(adapter.identity.adapter_id)
            outcome = ingest_from_adapter(store, adapter, rights, optional=True)
            if outcome.block_reason:
                ingest_notes.append(outcome.block_reason)
            if outcome.fetch and outcome.fetch.errors:
                ingest_notes.extend(error.message for error in outcome.fetch.errors)

    try:
        assert_rights_for_replay(rights)
        assert_rights_for_analysis(rights)
    except RightsGateError as exc:
        return _failed_run(
            request,
            execution_status="failed_rights",
            reason=str(exc),
            wall_clock=wall_clock,
            run_id=run_id,
            rights=rights,
        )

    evaluation_period = date.fromisoformat(request.evaluation_period)
    by_period = store.as_of(request.dataset_id, request.decision_at, request.analysis_mode)
    as_of_snapshot_hash = content_snapshot_hash(
        tuple(by_period[period] for period in sorted(by_period)),
    )

    method = method_registry.get(request.method_id)
    try:
        config = method_registry.parse_config(request.method_id, request.method_config)
    except Exception as exc:
        return _failed_run(
            request,
            execution_status="failed_method",
            reason=f"invalid method configuration: {exc}",
            wall_clock=wall_clock,
            run_id=run_id,
            rights=rights,
            input_snapshot_hash=as_of_snapshot_hash,
            method=method,
        )

    context = MethodContext(
        inputs_by_dataset={request.dataset_id: by_period},
        evaluation_period=evaluation_period,
        analysis_mode=request.analysis_mode,
        primary_dataset_id=request.dataset_id,
    )
    try:
        execution = method.run(context, config)
    except Exception as exc:
        return _failed_run(
            request,
            execution_status="failed_method",
            reason=str(exc),
            wall_clock=wall_clock,
            run_id=run_id,
            rights=rights,
            input_snapshot_hash=as_of_snapshot_hash,
            method=method,
            config_id=getattr(config, "config_id", ""),
            config_hash=method.config_hash(config),
        )

    if execution.observation_ids:
        snapshot_hash = cited_observation_snapshot_hash(store, list(execution.observation_ids))
    else:
        snapshot_hash = content_snapshot_hash(())

    execution_status: Literal["completed", "completed_insufficient"] = (
        "completed" if execution.sufficiency == "sufficient" else "completed_insufficient"
    )

    evidence = assess_analytical_evidence(
        execution_status=execution_status,
        data_sufficiency=execution.sufficiency,
        publication_allowed=False,
    )

    run_body = ResearchRun(
        run_id=run_id or str(uuid.uuid4()),
        executed_at=wall_clock,
        execution_status=execution_status,
        dataset_id=request.dataset_id,
        input_dataset_ids=[request.dataset_id],
        source_id=rights.source_id,
        rights_record_id=rights.source_id,
        analysis_mode=request.analysis_mode,
        analysis_type=request.method_id,
        decision_at=request.decision_at,
        evaluation_period=request.evaluation_period,
        method_id=method.method_id,
        method_version=method.method_version,
        implementation_hash=method.implementation_hash(),
        config_id=getattr(config, "config_id", ""),
        config_hash=method.config_hash(config),
        input_snapshot_hash=snapshot_hash,
        data_sufficiency=execution.sufficiency,
        missing_data_reason=execution.missing_reason,
        calculation=execution.calculation,
        statistical_interpretation=execution.statistical_interpretation,
        causal_hypothesis=execution.causal_hypothesis,
        market_pricing="unknown",
        investment_implication=execution.investment_implication,
        assumptions=list(execution.assumptions),
        limitations=list(execution.limitations),
        observation_ids=list(execution.observation_ids),
        adapter_ids=adapter_ids,
        ingest_notes=ingest_notes,
        reproduction={
            "method_id": method.method_id,
            "method_version": method.method_version,
            "implementation_hash": method.implementation_hash(),
            "config_hash": method.config_hash(config),
            "input_snapshot_hash": snapshot_hash,
        },
        narrative=execution.narrative,
        publication_allowed=False,
        verification_status=evidence.verification_status,
        evidence_reasons=list(evidence.reasons),
    )
    return _with_payload_hash(run_body)


def _failed_run(
    request: ResearchExecutionRequest,
    *,
    execution_status: Literal[
        "failed_rights",
        "failed_ingest",
        "failed_method",
    ],
    reason: str,
    wall_clock: datetime,
    run_id: str | None,
    rights: SourceRightsRecord | None = None,
    input_snapshot_hash: str = "",
    method: object | None = None,
    config_id: str = "",
    config_hash: str = "",
) -> ResearchRun:
    evidence = assess_analytical_evidence(
        execution_status=execution_status,
        data_sufficiency="insufficient",
        publication_allowed=False,
    )
    method_id = getattr(method, "method_id", request.method_id)
    method_version = getattr(method, "method_version", "")
    implementation_hash = method.implementation_hash() if method is not None else ""
    run_body = ResearchRun(
        run_id=run_id or str(uuid.uuid4()),
        executed_at=wall_clock,
        execution_status=execution_status,
        dataset_id=request.dataset_id,
        input_dataset_ids=[request.dataset_id],
        source_id=rights.source_id if rights else request.source_id,
        rights_record_id=rights.source_id if rights else request.source_id,
        analysis_mode=request.analysis_mode,
        analysis_type=request.method_id,
        decision_at=request.decision_at,
        evaluation_period=request.evaluation_period,
        method_id=method_id,
        method_version=method_version,
        implementation_hash=implementation_hash,
        config_id=config_id,
        config_hash=config_hash,
        input_snapshot_hash=input_snapshot_hash,
        data_sufficiency="insufficient",
        missing_data_reason=reason,
        calculation=None,
        statistical_interpretation="Run did not complete.",
        causal_hypothesis="Unresolved.",
        market_pricing="unknown",
        investment_implication="insufficient_evidence",
        assumptions=[],
        limitations=[],
        observation_ids=[],
        adapter_ids=[],
        ingest_notes=[reason],
        reproduction={
            "method_id": method_id,
            "method_version": method_version,
            "implementation_hash": implementation_hash,
            "config_hash": config_hash,
            "input_snapshot_hash": input_snapshot_hash,
        },
        narrative=reason,
        publication_allowed=False,
        verification_status=evidence.verification_status,
        evidence_reasons=list(evidence.reasons),
    )
    return _with_payload_hash(run_body)


def _with_payload_hash(run: ResearchRun) -> ResearchRun:
    payload_hash = analytical_payload_hash(run.model_dump(mode="json"))
    return run.model_copy(update={"analytical_payload_hash": payload_hash})
