"""Append-only atlas writes. Existing hypothesis rows are not rewritten."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import psycopg
from psycopg.types.json import Json

from aqil_research.long_horizon.money import canonical_json
from aqil_research.long_horizon.registry import REVIEWER_NOTE, RegistryError
from aqil_research.long_horizon.state_atlas.specification import (
    PROTECTED_EXECUTIONS,
    PROTECTED_EXPERIMENTS,
    PROTECTED_HYPOTHESES,
)


def _reject_protected(hypothesis_id: str, experiment_id: str, execution_id: str | None) -> None:
    if hypothesis_id in PROTECTED_HYPOTHESES or experiment_id in PROTECTED_EXPERIMENTS:
        raise RegistryError("LH-H-001, LH-H-002, and LH-H-003 are not rewritten")
    if execution_id in PROTECTED_EXECUTIONS:
        raise RegistryError("an earlier execution is not rewritten")


def _copy(connection: psycopg.Connection, statement: str, rows: list[tuple[Any, ...]]) -> None:
    if not rows:
        return
    with connection.cursor() as cursor, cursor.copy(statement) as copy:
        for row in rows:
            copy.write_row(row)


def store_specification(
    connection: psycopg.Connection,
    *,
    specification_id: str,
    version: int,
    specification: dict[str, Any],
    specification_hash: str,
    frozen_at: datetime,
) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            select specification_hash
            from research.atlas_specifications
            where specification_id = %s and version = %s
            """,
            (specification_id, version),
        )
        found = cursor.fetchone()
        if found is not None:
            if found[0] != specification_hash:
                raise RegistryError("the atlas specification hash differs and was not overwritten")
            return
        cursor.execute(
            """
            insert into research.atlas_specifications (
              specification_id, version, specification, specification_hash, frozen_at,
              publication_allowed
            ) values (%s, %s, %s, %s, %s, false)
            """,
            (specification_id, version, Json(specification), specification_hash, frozen_at),
        )


def _status(
    cursor: psycopg.Cursor,
    event_id: str,
    kind: str,
    subject_id: str,
    status: str,
    rationale: str,
    recorded_at: datetime,
) -> None:
    cursor.execute(
        "select status from research.scientific_status_events where status_event_id = %s",
        (event_id,),
    )
    found = cursor.fetchone()
    if found is not None:
        if found[0] != status:
            raise RegistryError("a status event with a different status was not overwritten")
        return
    cursor.execute(
        """
        insert into research.scientific_status_events (
          status_event_id, subject_kind, subject_id, subject_version, status,
          rationale, derivation, recorded_at, publication_allowed
        ) values (%s, %s, %s, 1, %s, %s, 'deterministic_criteria', %s, false)
        """,
        (event_id, kind, subject_id, status, rationale, recorded_at),
    )


def store_chain(
    connection: psycopg.Connection,
    *,
    hypothesis: dict[str, Any],
    specification: dict[str, Any],
    specification_hash: str,
    status: str,
    rationale: str,
    artifact: dict[str, Any],
    artifact_sha256: str,
    recorded_at: datetime,
    git_commit: str,
    code_hash: str,
    input_manifest: dict[str, Any],
    price_series_versions: list[dict[str, Any]],
    library_versions: dict[str, str],
    configuration: dict[str, Any],
    simulation_start: object,
    simulation_end: object,
    reproduction_command: str,
    availability_cutoff: datetime,
) -> None:
    hypothesis_id = str(hypothesis["hypothesis_id"])
    experiment_id = str(specification["experiment_id"])
    execution_id = "LH-X-004"
    _reject_protected(hypothesis_id, experiment_id, execution_id)
    with connection.cursor() as cursor:
        cursor.execute(
            """
            select artifact_sha256
            from research.experiment_executions
            where execution_id = %s
            """,
            (execution_id,),
        )
        found = cursor.fetchone()
        if found is not None:
            if found[0] != artifact_sha256:
                raise RegistryError("LH-X-004 has a different artifact and was not overwritten")
            return
        cursor.execute(
            """
            insert into research.hypotheses (
              hypothesis_id, version, proposition, economic_rationale,
              expected_mechanism, expected_direction, horizon, falsification_criteria,
              alternative_explanations, relevant_indicators, relevant_methodologies,
              target_instruments, initial_status, amendment_rationale, registered_at,
              registered_by, catalogue_signal_id, publication_allowed
            ) values (
              %s, 1, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, null, %s,
              'historical-state-atlas', null, false
            )
            """,
            (
                hypothesis_id,
                hypothesis["proposition"],
                hypothesis["economic_rationale"],
                hypothesis["expected_mechanism"],
                hypothesis["expected_direction"],
                hypothesis["horizon"],
                hypothesis["falsification_criteria"],
                Json(hypothesis["alternative_explanations"]),
                Json(hypothesis["relevant_indicators"]),
                Json(hypothesis["relevant_methodologies"]),
                Json(hypothesis["target_instruments"]),
                hypothesis["initial_status"],
                recorded_at,
            ),
        )
        cursor.execute(
            """
            insert into research.experiment_specifications (
              experiment_id, version, category, category_label, specification,
              specification_hash, frozen_at, publication_allowed
            ) values (%s, 1, 'C', 'price_only_simulator_research', %s, %s, %s, false)
            """,
            (experiment_id, Json(specification), specification_hash, recorded_at),
        )
        cursor.execute(
            """
            insert into research.hypothesis_experiment_links (
              hypothesis_id, hypothesis_version, experiment_id, experiment_version,
              recorded_at
            ) values (%s, 1, %s, 1, %s)
            """,
            (hypothesis_id, experiment_id, recorded_at),
        )
        _status(
            cursor,
            "LH-S-H-004-proposed",
            "hypothesis",
            hypothesis_id,
            "proposed",
            "Specification frozen in code before the sequence was scored.",
            recorded_at,
        )
        _status(
            cursor,
            "LH-S-E-004-proposed",
            "experiment",
            experiment_id,
            "proposed",
            "Specification frozen in code before the sequence was scored.",
            recorded_at,
        )
        cursor.execute(
            """
            insert into research.experiment_executions (
              execution_id, experiment_id, experiment_version, state, git_commit,
              code_hash, parameter_version_id, input_manifest, macro_vintage_ids,
              price_series_versions, library_versions, random_seed, executed_at,
              availability_cutoff, simulation_start, simulation_end, artifact_sha256,
              reproduction_command, validation_status, configuration,
              supersedes_execution_id, research_run_id, publication_allowed
            ) values (
              %s, %s, 1, 'succeeded', %s, %s, null, %s, '[]'::jsonb, %s, %s,
              'not_applicable_no_randomness', %s, %s, %s, %s, %s,
              %s, %s, %s, null, null, false
            )
            """,
            (
                execution_id,
                experiment_id,
                git_commit,
                code_hash,
                Json(input_manifest),
                Json(price_series_versions),
                Json(library_versions),
                recorded_at,
                availability_cutoff,
                simulation_start,
                simulation_end,
                artifact_sha256,
                reproduction_command,
                status,
                Json(configuration),
            ),
        )
        cursor.execute(
            """
            insert into research.evidence_records (
              evidence_id, execution_id, evidence_kind, content_sha256, body,
              recorded_at, publication_allowed
            ) values ('LH-V-004', %s, 'statistical_note', %s, %s, %s, false)
            """,
            (execution_id, artifact_sha256, Json(artifact), recorded_at),
        )
        cursor.execute(
            """
            insert into research.scientific_claims (
              claim_id, version, proposition, status_at_claim, eligibility_class,
              statistical_validity, economic_usefulness, independent_validation,
              remaining_uncertainty, publication_eligible, publication_allowed,
              derivation, reviewer_note, recorded_at
            ) values (
              'LH-C-004', 1, %s, %s, 'category_c_price_only',
              'not_assessed_overlapping_months', 'not_assessed', 'not_forward_validated',
              %s, false, false, 'deterministic_criteria', %s, %s
            )
            """,
            (
                artifact["proposition"],
                status,
                rationale,
                REVIEWER_NOTE,
                recorded_at,
            ),
        )
        cursor.execute(
            """
            insert into research.claim_evidence_links (
              claim_id, claim_version, evidence_id, relation, recorded_at
            ) values ('LH-C-004', 1, 'LH-V-004', 'qualifies', %s)
            """,
            (recorded_at,),
        )
        cursor.execute(
            """
            insert into research.claim_execution_links (
              claim_id, claim_version, execution_id, relation, recorded_at
            ) values ('LH-C-004', 1, %s, 'qualifies', %s)
            """,
            (execution_id, recorded_at),
        )
        result_rationale = "Current status after the frozen sequence rule. Version 1 is unchanged."
        _status(
            cursor,
            "LH-S-H-004-result",
            "hypothesis",
            hypothesis_id,
            status,
            result_rationale,
            recorded_at,
        )
        _status(
            cursor,
            "LH-S-E-004-result",
            "experiment",
            experiment_id,
            status,
            "The execution followed the frozen specification.",
            recorded_at,
        )
        _status(
            cursor,
            "LH-S-C-004-result",
            "claim",
            "LH-C-004",
            status,
            "Claim version 1 records the deterministic status.",
            recorded_at,
        )


def store_dependency(
    connection: psycopg.Connection,
    *,
    dependency_id: str,
    left_kind: str,
    left_id: str,
    right_kind: str,
    right_id: str,
    relation: str,
    methodology_id: str | None,
    instrument_id: str | None,
    detail: str,
    recorded_at: datetime,
) -> None:
    protected = {f"LH-D-{index:03d}" for index in range(1, 11)}
    if dependency_id in protected or not dependency_id.startswith("LH-D-"):
        raise RegistryError("an earlier dependency row is not rewritten")
    with connection.cursor() as cursor:
        cursor.execute(
            """
            select detail from research.research_dependencies where dependency_id = %s
            """,
            (dependency_id,),
        )
        found = cursor.fetchone()
        if found is not None:
            if found[0] != detail:
                raise RegistryError("a dependency detail differs and was not overwritten")
            return
        cursor.execute(
            """
            insert into research.research_dependencies (
              dependency_id, left_kind, left_id, right_kind, right_id, relation,
              dataset_id, indicator_id, instrument_id, methodology_id,
              period_start, period_end, independent_confirmation, detail, recorded_at
            ) values (
              %s, %s, %s, %s, %s, %s, null, null, %s, %s, null, null, false, %s, %s
            )
            """,
            (
                dependency_id,
                left_kind,
                left_id,
                right_kind,
                right_id,
                relation,
                instrument_id,
                methodology_id,
                detail,
                recorded_at,
            ),
        )


def copy_atlas(connection: psycopg.Connection, batch: Any) -> None:
    _copy(
        connection,
        """
        copy research.decision_anchors (
          anchor_id, specification_id, specification_version, specification_hash,
          symbol, anchor_kind, session_date, lookback_sufficient, listing_currency,
          publication_allowed, recorded_at
        ) from stdin
        """,
        batch.anchors,
    )
    _copy(
        connection,
        """
        copy research.state_observations (
          state_id, anchor_id, feature_id, feature_family, availability, clock,
          usable_as_decision_input, value_text, detail, publication_allowed, recorded_at
        ) from stdin
        """,
        batch.states,
    )
    _copy(
        connection,
        """
        copy research.outcome_measures (
          outcome_id, anchor_id, horizon_label, session_steps, status, value_text,
          labelled_advance, readable_as_state_input, known_at_anchor,
          publication_allowed, recorded_at
        ) from stdin
        """,
        batch.outcomes,
    )
    inventory_rows = [
        (row[0], row[1], row[2], row[3], canonical_json(row[4]), row[5], row[6])
        for row in batch.inventory
    ]
    _copy(
        connection,
        """
        copy research.scientific_inventory_rows (
          specification_id, specification_version, row_kind, row_key, payload,
          publication_allowed, recorded_at
        ) from stdin
        """,
        inventory_rows,
    )
    _copy(
        connection,
        """
        copy research.anchor_event_links (
          anchor_id, event_id, relation, publication_allowed, recorded_at
        ) from stdin
        """,
        batch.links,
    )
    _copy(
        connection,
        """
        copy research.market_episodes (
          episode_id, specification_id, specification_version, symbol, start_date,
          end_date, event_count, publication_allowed, recorded_at
        ) from stdin
        """,
        batch.episodes,
    )
    _copy(
        connection,
        """
        copy research.market_episode_events (
          episode_id, event_id, publication_allowed, recorded_at
        ) from stdin
        """,
        batch.episode_events,
    )


def store_claim_anchors(
    connection: psycopg.Connection,
    rows: list[tuple[Any, ...]],
) -> None:
    _copy(
        connection,
        """
        copy research.atlas_claim_anchors (
          anchor_id, claim_id, claim_version, role, publication_allowed, recorded_at
        ) from stdin
        """,
        rows,
    )


def store_coverage(
    connection: psycopg.Connection,
    rows: list[tuple[Any, ...]],
) -> None:
    _copy(
        connection,
        """
        copy research.atlas_coverage_counts (
          specification_id, specification_version, metric, metric_count, detail,
          publication_allowed, recorded_at
        ) from stdin
        """,
        rows,
    )
