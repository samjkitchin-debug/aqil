"""Persist and load immutable research runs."""

from __future__ import annotations

from datetime import date

import psycopg

from aqil_research.persistence.calculation_normalize import normalize_calculation_payload
from aqil_research.pipeline.models import ResearchRun


def save_research_run(conn: psycopg.Connection, run: ResearchRun) -> None:
    evaluation = date.fromisoformat(run.evaluation_period)
    datasets = run.input_dataset_ids or [run.dataset_id]
    with conn.cursor() as cur:
        cur.execute(
            """
            insert into research.research_runs (
              run_id, executed_at, execution_status, primary_dataset_id,
              source_id, rights_record_id, analysis_mode, analysis_type,
              decision_at, evaluation_period, method_id, method_version,
              implementation_hash, config_id, config_hash, input_snapshot_hash,
              analytical_payload_hash, data_sufficiency, missing_data_reason,
              calculation, statistical_interpretation, causal_hypothesis,
              market_pricing, investment_implication, assumptions, limitations,
              observation_ids, adapter_ids, ingest_notes, reproduction, narrative,
              publication_allowed, verification_status, evidence_reasons
            )
            values (
              %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
              %s::jsonb, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb,
              %s::jsonb, %s::jsonb, %s, %s, %s, %s::jsonb
            )
            """,
            (
                run.run_id,
                run.executed_at,
                run.execution_status,
                run.dataset_id,
                run.source_id,
                run.rights_record_id,
                run.analysis_mode.value,
                run.analysis_type,
                run.decision_at,
                evaluation,
                run.method_id,
                run.method_version,
                run.implementation_hash,
                run.config_id,
                run.config_hash,
                run.input_snapshot_hash,
                run.analytical_payload_hash,
                run.data_sufficiency,
                run.missing_data_reason,
                psycopg.types.json.Json(run.calculation) if run.calculation else None,
                run.statistical_interpretation,
                run.causal_hypothesis,
                run.market_pricing,
                run.investment_implication,
                psycopg.types.json.Json(run.assumptions),
                psycopg.types.json.Json(run.limitations),
                psycopg.types.json.Json(run.observation_ids),
                psycopg.types.json.Json(run.adapter_ids),
                psycopg.types.json.Json(run.ingest_notes),
                psycopg.types.json.Json(run.reproduction),
                run.narrative,
                run.publication_allowed,
                run.verification_status,
                psycopg.types.json.Json(run.evidence_reasons),
            ),
        )
        for dataset_id in datasets:
            cur.execute(
                """
                insert into research.research_run_datasets (
                  run_id, dataset_id, source_id, rights_record_id,
                  input_snapshot_hash, is_primary
                )
                values (%s, %s, %s, %s, %s, %s)
                """,
                (
                    run.run_id,
                    dataset_id,
                    run.source_id,
                    run.rights_record_id,
                    run.input_snapshot_hash,
                    dataset_id == run.dataset_id,
                ),
            )
        for observation_id in run.observation_ids:
            cur.execute(
                """
                insert into research.research_run_observations (
                  run_id, observation_id, dataset_id
                )
                values (%s, %s, %s)
                """,
                (run.run_id, observation_id, run.dataset_id),
            )


def load_research_run(conn: psycopg.Connection, run_id: str) -> ResearchRun:
    with conn.cursor() as cur:
        cur.execute(
            """
            select
              run_id, executed_at, execution_status, primary_dataset_id,
              source_id, rights_record_id, analysis_mode, analysis_type,
              decision_at, evaluation_period, method_id, method_version,
              implementation_hash, config_id, config_hash, input_snapshot_hash,
              analytical_payload_hash, data_sufficiency, missing_data_reason,
              calculation, statistical_interpretation, causal_hypothesis,
              market_pricing, investment_implication, assumptions, limitations,
              observation_ids, adapter_ids, ingest_notes, reproduction, narrative,
              publication_allowed, verification_status, evidence_reasons
            from research.research_runs
            where run_id = %s
            """,
            (run_id,),
        )
        row = cur.fetchone()
    if row is None:
        raise LookupError(f"research run not found: {run_id}")
    evaluation_period = row[9]
    if isinstance(evaluation_period, date):
        evaluation_str = evaluation_period.isoformat()
    else:
        evaluation_str = str(evaluation_period)
    from aqil_research.contracts.observation import AnalysisMode

    return ResearchRun(
        run_id=row[0],
        executed_at=row[1],
        execution_status=row[2],
        dataset_id=row[3],
        input_dataset_ids=[row[3]],
        source_id=row[4],
        rights_record_id=row[5],
        analysis_mode=AnalysisMode(row[6]),
        analysis_type=row[7],
        decision_at=row[8],
        evaluation_period=evaluation_str,
        method_id=row[10],
        method_version=row[11],
        implementation_hash=row[12],
        config_id=row[13],
        config_hash=row[14],
        input_snapshot_hash=row[15],
        analytical_payload_hash=row[16] or "",
        data_sufficiency=row[17],
        missing_data_reason=row[18],
        calculation=normalize_calculation_payload(row[19]),
        statistical_interpretation=row[20],
        causal_hypothesis=row[21],
        market_pricing=row[22],
        investment_implication=row[23],
        assumptions=row[24] or [],
        limitations=row[25] or [],
        observation_ids=row[26] or [],
        adapter_ids=row[27] or [],
        ingest_notes=row[28] or [],
        reproduction=row[29] or {},
        narrative=row[30],
        publication_allowed=row[31],
        verification_status=row[32],
        evidence_reasons=row[33] or [],
    )


def load_run_observation_ids(conn: psycopg.Connection, run_id: str) -> tuple[str, ...]:
    with conn.cursor() as cur:
        cur.execute(
            """
            select observation_id
            from research.research_run_observations
            where run_id = %s
            order by observation_id
            """,
            (run_id,),
        )
        return tuple(row[0] for row in cur.fetchall())
