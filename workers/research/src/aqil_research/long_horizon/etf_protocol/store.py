"""Append-only ETF protocol writes. Earlier hypotheses are not rewritten."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import psycopg
from psycopg.types.json import Json

from aqil_research.long_horizon.etf_protocol.specification import (
    PROTECTED_EXECUTIONS,
    PROTECTED_EXPERIMENTS,
    PROTECTED_HYPOTHESES,
    ProtocolError,
)
from aqil_research.long_horizon.registry import REVIEWER_NOTE


def _copy(connection: psycopg.Connection, statement: str, rows: list[tuple[Any, ...]]) -> None:
    if not rows:
        return
    with connection.cursor() as cursor, cursor.copy(statement) as copy:
        for row in rows:
            copy.write_row(row)


def _status(
    cursor: psycopg.Cursor[Any],
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
            raise ProtocolError("a status event with a different status was not overwritten")
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


def store_definition(
    connection: psycopg.Connection,
    *,
    definition: dict[str, Any],
    definition_hash: str,
    frozen_at: datetime,
) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            select specification_hash
            from research.event_definitions
            where definition_id = 'EVT-DEF-002' and version = 1
            """
        )
        found = cursor.fetchone()
        if found is not None:
            if found[0] != definition_hash:
                raise ProtocolError("EVT-DEF-002 hash differs and was not overwritten")
            return
        cursor.execute(
            """
            insert into research.event_definitions (
              definition_id, version, specification, specification_hash, frozen_at,
              publication_allowed
            ) values ('EVT-DEF-002', 1, %s, %s, %s, false)
            """,
            (Json(definition), definition_hash, frozen_at),
        )


def store_events(
    connection: psycopg.Connection,
    events: list[tuple[Any, ...]],
    families: list[tuple[Any, ...]],
) -> None:
    _copy(
        connection,
        """
        copy research.market_events (
          event_id, definition_id, definition_version, symbol, listing_currency, family,
          horizon_label, start_date, end_date, label_confirmed_on, price_return,
          session_steps, max_intervening_drawdown, up_session_fraction,
          label_uses_later_prices, usable_as_investment_signal,
          historically_observable_at_event_date, price_series_sha256, detail,
          publication_allowed, recorded_at
        ) from stdin
        """,
        events,
    )
    _copy(
        connection,
        """
        copy research.event_family_counts (
          definition_id, definition_version, symbol, family, horizon_label, status, reason,
          event_count, windows_examined, qualifier_window_count, censored_count,
          price_series_sha256, publication_allowed, recorded_at
        ) from stdin
        """,
        families,
    )


def store_specification(
    connection: psycopg.Connection,
    *,
    specification: dict[str, Any],
    specification_hash: str,
    frozen_at: datetime,
) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            select specification_hash
            from research.etf_protocol_specifications
            where specification_id = 'ETF-PROT-001' and version = 1
            """
        )
        found = cursor.fetchone()
        if found is not None:
            if found[0] != specification_hash:
                raise ProtocolError("ETF-PROT-001 hash differs and was not overwritten")
            return
        cursor.execute(
            """
            insert into research.etf_protocol_specifications (
              specification_id, version, specification, specification_hash, frozen_at,
              publication_allowed
            ) values ('ETF-PROT-001', 1, %s, %s, %s, false)
            """,
            (Json(specification), specification_hash, frozen_at),
        )


def store_trials(connection: psycopg.Connection, rows: list[tuple[Any, ...]]) -> None:
    _copy(
        connection,
        """
        copy research.etf_protocol_trials (
          trial_id, specification_id, specification_version, specification_hash, dossier_id,
          symbol, feature, transform, horizon_label, outcome, statistic, eligibility,
          result_text, refusal_reason, effect_text, p_value_text, result_status, detail,
          publication_allowed, recorded_at
        ) from stdin
        """,
        rows,
    )


def store_chain(
    connection: psycopg.Connection,
    *,
    dossier: dict[str, object],
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
    price_series_versions: list[dict[str, str]],
    library_versions: dict[str, str],
    configuration: dict[str, Any],
    simulation_start: object,
    simulation_end: object,
    reproduction_command: str,
    availability_cutoff: datetime,
) -> None:
    hypothesis_id = str(dossier["hypothesis_id"])
    experiment_id = str(dossier["experiment_id"])
    execution_id = str(dossier["execution_id"])
    evidence_id = str(dossier["evidence_id"])
    claim_id = str(dossier["claim_id"])
    if (
        hypothesis_id in PROTECTED_HYPOTHESES
        or experiment_id in PROTECTED_EXPERIMENTS
        or execution_id in PROTECTED_EXECUTIONS
    ):
        raise ProtocolError("an earlier registry row is not rewritten")
    with connection.cursor() as cursor:
        cursor.execute(
            "select artifact_sha256 from research.experiment_executions where execution_id = %s",
            (execution_id,),
        )
        found = cursor.fetchone()
        if found is not None:
            if found[0] != artifact_sha256:
                raise ProtocolError(
                    f"{execution_id} has a different artifact and was not overwritten"
                )
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
              'etf-protocol', null, false
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
            ) values (
              %s, 1, 'B', 'retrospective_economic_research', %s, %s, %s, false
            )
            """,
            (experiment_id, Json(specification), specification_hash, recorded_at),
        )
        cursor.execute(
            """
            insert into research.hypothesis_experiment_links (
              hypothesis_id, hypothesis_version, experiment_id, experiment_version, recorded_at
            ) values (%s, 1, %s, 1, %s)
            """,
            (hypothesis_id, experiment_id, recorded_at),
        )
        _status(
            cursor,
            f"LH-S-H-{hypothesis_id[-3:]}-proposed",
            "hypothesis",
            hypothesis_id,
            "proposed",
            "Specification frozen in code before this dossier was scored.",
            recorded_at,
        )
        _status(
            cursor,
            f"LH-S-E-{experiment_id[-3:]}-proposed",
            "experiment",
            experiment_id,
            "proposed",
            "Specification frozen in code before this dossier was scored.",
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
            ) values (%s, %s, 'statistical_note', %s, %s, %s, false)
            """,
            (evidence_id, execution_id, artifact_sha256, Json(artifact), recorded_at),
        )
        cursor.execute(
            """
            insert into research.scientific_claims (
              claim_id, version, proposition, status_at_claim, eligibility_class,
              statistical_validity, economic_usefulness, independent_validation,
              remaining_uncertainty, publication_eligible, publication_allowed,
              derivation, reviewer_note, recorded_at
            ) values (
              %s, 1, %s, %s, 'category_b_retrospective',
              'not_assessed_overlapping_months', 'not_assessed', 'not_forward_validated',
              %s, false, false, 'deterministic_criteria', %s, %s
            )
            """,
            (
                claim_id,
                hypothesis["proposition"],
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
            ) values (%s, 1, %s, 'qualifies', %s)
            """,
            (claim_id, evidence_id, recorded_at),
        )
        cursor.execute(
            """
            insert into research.claim_execution_links (
              claim_id, claim_version, execution_id, relation, recorded_at
            ) values (%s, 1, %s, 'qualifies', %s)
            """,
            (claim_id, execution_id, recorded_at),
        )
        result = "Current status after the frozen protocol. Version 1 is unchanged."
        _status(
            cursor,
            f"LH-S-H-{hypothesis_id[-3:]}-result",
            "hypothesis",
            hypothesis_id,
            status,
            result,
            recorded_at,
        )
        _status(
            cursor,
            f"LH-S-E-{experiment_id[-3:]}-result",
            "experiment",
            experiment_id,
            status,
            result,
            recorded_at,
        )
        _status(
            cursor, f"LH-S-C-{claim_id[-3:]}-result", "claim", claim_id, status, result, recorded_at
        )


def store_dependency(
    connection: psycopg.Connection,
    *,
    dependency_id: str,
    experiment_id: str,
    right_id: str,
    detail: str,
    recorded_at: datetime,
) -> None:
    if not dependency_id.startswith("LH-D-"):
        raise ProtocolError("the dependency id is not in the registry sequence")
    number = int(dependency_id.removeprefix("LH-D-"))
    if number < 15:
        raise ProtocolError("an earlier dependency row is not rewritten")
    with connection.cursor() as cursor:
        cursor.execute(
            "select detail from research.research_dependencies where dependency_id = %s",
            (dependency_id,),
        )
        found = cursor.fetchone()
        if found is not None:
            if found[0] != detail:
                raise ProtocolError("a dependency detail differs and was not overwritten")
            return
        cursor.execute(
            """
            insert into research.research_dependencies (
              dependency_id, left_kind, left_id, right_kind, right_id, relation,
              dataset_id, indicator_id, instrument_id, methodology_id,
              period_start, period_end, independent_confirmation, detail, recorded_at
            ) values (
              %s, 'experiment', %s, 'methodology', %s, 'shares_methodology',
              null, null, null, %s, null, null, false, %s, %s
            )
            """,
            (dependency_id, experiment_id, right_id, right_id, detail, recorded_at),
        )
