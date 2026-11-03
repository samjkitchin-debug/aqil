"""Append-only writes for the outcome-first layer. Existing pilot rows are not rewritten."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import psycopg
from psycopg.types.json import Json

from aqil_research.long_horizon.events.definition import (
    PROTECTED_EXECUTIONS,
    PROTECTED_EXPERIMENTS,
    PROTECTED_HYPOTHESES,
)
from aqil_research.long_horizon.registry import REVIEWER_NOTE, RegistryError


def _reject_protected(hypothesis_id: str, experiment_id: str, execution_id: str | None) -> None:
    if hypothesis_id in PROTECTED_HYPOTHESES or experiment_id in PROTECTED_EXPERIMENTS:
        raise RegistryError("LH-H-001 and LH-E-001 are not rewritten")
    if execution_id in PROTECTED_EXECUTIONS:
        raise RegistryError("LH-X-001 is not rewritten")


def _existing(cursor: psycopg.Cursor, statement: str, params: tuple[Any, ...]) -> Any:
    cursor.execute(statement, params)
    return cursor.fetchone()


def store_definition(
    connection: psycopg.Connection,
    *,
    definition_id: str,
    version: int,
    specification: dict[str, Any],
    specification_hash: str,
    frozen_at: datetime,
) -> str:
    with connection.cursor() as cursor:
        found = _existing(
            cursor,
            """
            select specification_hash
            from research.event_definitions
            where definition_id = %s and version = %s
            """,
            (definition_id, version),
        )
        if found is not None:
            if found[0] != specification_hash:
                raise RegistryError("the event definition hash differs and was not overwritten")
            return "unchanged"
        cursor.execute(
            """
            insert into research.event_definitions (
              definition_id, version, specification, specification_hash, frozen_at,
              publication_allowed
            ) values (%s, %s, %s, %s, %s, false)
            """,
            (definition_id, version, Json(specification), specification_hash, frozen_at),
        )
    return "inserted"


def store_hypothesis_and_specification(
    connection: psycopg.Connection,
    *,
    hypothesis: dict[str, Any],
    specification: dict[str, Any],
    specification_hash: str,
    category: str,
    category_label: str,
    frozen_at: datetime,
    hypothesis_status_id: str,
    experiment_status_id: str,
    status: str,
    rationale: str,
) -> str:
    hypothesis_id = str(hypothesis["hypothesis_id"])
    experiment_id = str(specification["experiment_id"])
    _reject_protected(hypothesis_id, experiment_id, None)
    with connection.cursor() as cursor:
        found = _existing(
            cursor,
            """
            select specification_hash
            from research.experiment_specifications
            where experiment_id = %s and version = 1
            """,
            (experiment_id,),
        )
        if found is not None:
            if found[0] != specification_hash:
                raise RegistryError("the experiment hash differs and was not overwritten")
            stored_proposition = _existing(
                cursor,
                """
                select proposition from research.hypotheses
                where hypothesis_id = %s and version = 1
                """,
                (hypothesis_id,),
            )
            if stored_proposition is None or stored_proposition[0] != hypothesis["proposition"]:
                raise RegistryError("the hypothesis proposition differs and was not overwritten")
            return "unchanged"
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
              'outcome-first-programme', null, false
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
                frozen_at,
            ),
        )
        cursor.execute(
            """
            insert into research.experiment_specifications (
              experiment_id, version, category, category_label, specification,
              specification_hash, frozen_at, publication_allowed
            ) values (%s, 1, %s, %s, %s, %s, %s, false)
            """,
            (
                experiment_id,
                category,
                category_label,
                Json(specification),
                specification_hash,
                frozen_at,
            ),
        )
        cursor.execute(
            """
            insert into research.hypothesis_experiment_links (
              hypothesis_id, hypothesis_version, experiment_id, experiment_version,
              recorded_at
            ) values (%s, 1, %s, 1, %s)
            """,
            (hypothesis_id, experiment_id, frozen_at),
        )
        _status(
            cursor, hypothesis_status_id, "hypothesis", hypothesis_id, status, rationale, frozen_at
        )
        _status(
            cursor, experiment_status_id, "experiment", experiment_id, status, rationale, frozen_at
        )
    return "inserted"


def _status(
    cursor: psycopg.Cursor,
    event_id: str,
    kind: str,
    subject_id: str,
    status: str,
    rationale: str,
    recorded_at: datetime,
) -> None:
    found = _existing(
        cursor,
        "select status from research.scientific_status_events where status_event_id = %s",
        (event_id,),
    )
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


def store_events(
    connection: psycopg.Connection,
    rows: list[tuple[Any, ...]],
) -> str:
    if not rows:
        raise RegistryError("refusing to store an empty event list without an explicit block")
    with connection.cursor() as cursor:
        found = _existing(
            cursor,
            "select count(*) from research.market_events where definition_id = %s",
            (rows[0][1],),
        )
        if found is not None and found[0]:
            return "present"
        cursor.executemany(
            """
            insert into research.market_events (
              event_id, definition_id, definition_version, symbol, listing_currency,
              family, horizon_label, start_date, end_date, label_confirmed_on,
              price_return, session_steps, max_intervening_drawdown, up_session_fraction,
              label_uses_later_prices, usable_as_investment_signal,
              historically_observable_at_event_date, price_series_sha256, detail,
              publication_allowed, recorded_at
            ) values (
              %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, false,
              %s, %s, %s, false, %s
            )
            """,
            rows,
        )
    return "inserted"


def store_family_counts(connection: psycopg.Connection, rows: list[tuple[Any, ...]]) -> str:
    with connection.cursor() as cursor:
        found = _existing(
            cursor,
            "select count(*) from research.event_family_counts where definition_id = %s",
            (rows[0][0],),
        )
        if found is not None and found[0]:
            return "present"
        cursor.executemany(
            """
            insert into research.event_family_counts (
              definition_id, definition_version, symbol, family, horizon_label, status,
              reason, event_count, windows_examined, qualifier_window_count,
              censored_count, price_series_sha256, publication_allowed, recorded_at
            ) values (
              %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, false, %s
            )
            """,
            rows,
        )
    return "inserted"


def store_availability(connection: psycopg.Connection, rows: list[tuple[Any, ...]]) -> str:
    with connection.cursor() as cursor:
        found = _existing(
            cursor,
            """
            select count(*) from research.feature_availability_rows
            where definition_id = %s
            """,
            (rows[0][0],),
        )
        if found is not None and found[0]:
            return "present"
        cursor.executemany(
            """
            insert into research.feature_availability_rows (
              definition_id, definition_version, symbol, feature_id, lookback_label,
              clock, availability, covered_event_count, catalogued_event_count,
              seasonal_adjustment, detail, publication_allowed, recorded_at
            ) values (
              %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, false, %s
            )
            """,
            rows,
        )
    return "inserted"


def store_comparisons(connection: psycopg.Connection, rows: list[tuple[Any, ...]]) -> str:
    with connection.cursor() as cursor:
        found = _existing(
            cursor,
            "select count(*) from research.comparison_periods where experiment_id = %s",
            (rows[0][1],),
        )
        if found is not None and found[0]:
            return "present"
        cursor.executemany(
            """
            insert into research.comparison_periods (
              period_id, experiment_id, experiment_version, symbol, decision_date,
              condition_met, outcome_advance, forward_price_return,
              selected_on_future_return, publication_allowed, recorded_at
            ) values (%s, %s, 1, %s, %s, %s, %s, %s, false, false, %s)
            """,
            rows,
        )
    return "inserted"


def store_execution(
    connection: psycopg.Connection,
    *,
    execution_id: str,
    experiment_id: str,
    hypothesis_id: str,
    state: str,
    validation_status: str,
    artifact: dict[str, Any],
    artifact_sha256: str,
    evidence_id: str,
    evidence_kind: str,
    claim_id: str,
    claim_proposition: str,
    claim_status: str,
    eligibility_class: str,
    statistical_validity: str,
    economic_usefulness: str,
    independent_validation: str,
    remaining_uncertainty: str,
    evidence_relation: str,
    recorded_at: datetime,
    availability_cutoff: datetime,
    git_commit: str,
    code_hash: str,
    input_manifest: dict[str, Any],
    price_series_versions: list[dict[str, Any]],
    library_versions: dict[str, str],
    configuration: dict[str, Any],
    simulation_start: object,
    simulation_end: object,
    reproduction_command: str,
    claim_status_id: str,
    hypothesis_status_id: str,
    experiment_status_id: str,
) -> str:
    _reject_protected(hypothesis_id, experiment_id, execution_id)
    with connection.cursor() as cursor:
        found = _existing(
            cursor,
            "select artifact_sha256 from research.experiment_executions where execution_id = %s",
            (execution_id,),
        )
        if found is not None:
            if found[0] != artifact_sha256:
                raise RegistryError("an execution with a different artifact was not overwritten")
            return "unchanged"
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
              %s, %s, 1, %s, %s, %s, null, %s, '[]'::jsonb, %s, %s,
              'not_applicable_no_randomness', %s, %s, %s, %s, %s,
              %s, %s, %s, null, null, false
            )
            """,
            (
                execution_id,
                experiment_id,
                state,
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
                validation_status,
                Json(configuration),
            ),
        )
        cursor.execute(
            """
            insert into research.evidence_records (
              evidence_id, execution_id, evidence_kind, content_sha256, body,
              recorded_at, publication_allowed
            ) values (%s, %s, %s, %s, %s, %s, false)
            """,
            (
                evidence_id,
                execution_id,
                evidence_kind,
                artifact_sha256,
                Json(artifact),
                recorded_at,
            ),
        )
        cursor.execute(
            """
            insert into research.scientific_claims (
              claim_id, version, proposition, status_at_claim, eligibility_class,
              statistical_validity, economic_usefulness, independent_validation,
              remaining_uncertainty, publication_eligible, publication_allowed,
              derivation, reviewer_note, recorded_at
            ) values (
              %s, 1, %s, %s, %s, %s, %s, %s, %s, false, false,
              'deterministic_criteria', %s, %s
            )
            """,
            (
                claim_id,
                claim_proposition,
                claim_status,
                eligibility_class,
                statistical_validity,
                economic_usefulness,
                independent_validation,
                remaining_uncertainty,
                REVIEWER_NOTE,
                recorded_at,
            ),
        )
        cursor.execute(
            """
            insert into research.claim_evidence_links (
              claim_id, claim_version, evidence_id, relation, recorded_at
            ) values (%s, 1, %s, %s, %s)
            """,
            (claim_id, evidence_id, evidence_relation, recorded_at),
        )
        cursor.execute(
            """
            insert into research.claim_execution_links (
              claim_id, claim_version, execution_id, relation, recorded_at
            ) values (%s, 1, %s, %s, %s)
            """,
            (claim_id, execution_id, evidence_relation, recorded_at),
        )
        _status(
            cursor,
            hypothesis_status_id,
            "hypothesis",
            hypothesis_id,
            claim_status,
            "Current status after the frozen rule. Version 1 of the proposition is unchanged.",
            recorded_at,
        )
        _status(
            cursor,
            experiment_status_id,
            "experiment",
            experiment_id,
            claim_status,
            "The execution followed the frozen specification.",
            recorded_at,
        )
        _status(
            cursor,
            claim_status_id,
            "claim",
            claim_id,
            claim_status,
            "Claim version 1 records the deterministic status.",
            recorded_at,
        )
    return "inserted"


def store_dependency(
    connection: psycopg.Connection,
    *,
    dependency_id: str,
    left_kind: str,
    left_id: str,
    right_kind: str,
    right_id: str,
    relation: str,
    dataset_id: str | None,
    instrument_id: str | None,
    period_start: object,
    period_end: object,
    detail: str,
    recorded_at: datetime,
) -> None:
    if not dependency_id.startswith("LH-D-") or dependency_id in {
        "LH-D-001",
        "LH-D-002",
        "LH-D-003",
        "LH-D-004",
        "LH-D-005",
        "LH-D-006",
    }:
        raise RegistryError("the original dependency rows are not rewritten")
    with connection.cursor() as cursor:
        found = _existing(
            cursor,
            """
            select independent_confirmation
            from research.research_dependencies
            where dependency_id = %s
            """,
            (dependency_id,),
        )
        if found is not None:
            if found[0] is not False:
                raise RegistryError("a dependency was marked independent and was not overwritten")
            return
        cursor.execute(
            """
            insert into research.research_dependencies (
              dependency_id, left_kind, left_id, right_kind, right_id, relation,
              dataset_id, indicator_id, instrument_id, methodology_id,
              period_start, period_end, independent_confirmation, detail, recorded_at
            ) values (
              %s, %s, %s, %s, %s, %s, %s, null, %s, null, %s, %s, false, %s, %s
            )
            """,
            (
                dependency_id,
                left_kind,
                left_id,
                right_kind,
                right_id,
                relation,
                dataset_id,
                instrument_id,
                period_start,
                period_end,
                detail,
                recorded_at,
            ),
        )
