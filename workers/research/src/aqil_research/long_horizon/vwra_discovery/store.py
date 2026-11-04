"""Append the VWRA discovery chain. An existing artifact is not overwritten."""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any

import psycopg
from psycopg.types.json import Json

from aqil_research.long_horizon.registry import REVIEWER_NOTE
from aqil_research.long_horizon.vwra_discovery.dossier import Dossier
from aqil_research.long_horizon.vwra_discovery.specification import (
    DEPENDENCIES,
    HYPOTHESES,
    PROTECTED_EXECUTIONS,
    PROTECTED_EXPERIMENTS,
    PROTECTED_HYPOTHESES,
    SPECIFICATION_ID,
    SPECIFICATION_VERSION,
    specification_document,
    specification_hash,
)


class DiscoveryStoreError(RuntimeError):
    """The store refused to overwrite a registry row."""


def point_checksum(dossier: Dossier) -> str:
    lines: list[str] = []
    for run in dossier.runs:
        for point in run.points:
            lines.append(
                "|".join(
                    (
                        run.method_id,
                        point.series_key,
                        point.period_start.isoformat(),
                        point.period_end.isoformat(),
                        point.value_text or "",
                        point.change_text or "",
                        point.direction or "",
                        point.unit,
                    )
                )
            )
    payload = "\n".join(sorted(lines)).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def feature_checksum(dossier: Dossier) -> str:
    lines = [
        "|".join(
            (
                row.anchor_id,
                row.feature_id,
                row.period_end.isoformat(),
                row.value_text or "",
                row.reconstruction,
            )
        )
        for row in dossier.features
    ]
    return hashlib.sha256("\n".join(sorted(lines)).encode("utf-8")).hexdigest()


def case_checksum(dossier: Dossier) -> str:
    lines = [
        "|".join(
            (
                row.case_id,
                row.episode_group,
                row.family,
                row.event_id or "",
                row.value_text or "",
                row.detail,
            )
        )
        for row in dossier.cases
    ]
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


def artifacts(dossier: Dossier) -> dict[str, dict[str, Any]]:
    """One artifact per execution. The git commit is not part of the hash."""
    by_experiment = {
        "LH-E-008": [],
        "LH-E-009": [],
        "LH-E-010": [],
        "LH-E-011": [],
    }
    for trial in dossier.trials:
        by_experiment[trial.experiment_id].append(trial.canonical())
    shared = {
        "specification_hash": specification_hash(),
        "coverage": dossier.coverage,
        "point_sha256": point_checksum(dossier),
        "feature_sha256": feature_checksum(dossier),
        "case_sha256": case_checksum(dossier),
        "publication_allowed": False,
        "portfolio_simulation": "not_called",
        "point_in_time_results": 0,
    }
    built: dict[str, dict[str, Any]] = {}
    for hypothesis in HYPOTHESES:
        experiment_id = str(hypothesis["experiment_id"])
        execution_id = str(hypothesis["execution_id"])
        finding = next(item for item in dossier.findings if item.experiment_id == experiment_id)
        built[execution_id] = {
            **shared,
            "experiment_id": experiment_id,
            "finding_class": finding.finding_class,
            "statement": finding.statement,
            "trials": by_experiment[experiment_id],
            "sequence": dossier.sequence if experiment_id == "LH-E-011" else None,
            "methods": [
                {
                    "method_id": run.method_id,
                    "status": run.status,
                    "method_class": run.method_class,
                    "reconstruction": run.reconstruction,
                    "numeric_count": run.numeric_count,
                    "reason": run.reason,
                    "method_version": run.method_version,
                    "implementation_hash": run.implementation_hash,
                    "config_hash": run.config_hash,
                    "parameter_policy": run.parameter_policy,
                }
                for run in dossier.runs
            ]
            if experiment_id == "LH-E-008"
            else None,
        }
    return built


def store_dossier(
    connection: psycopg.Connection,
    dossier: Dossier,
    bodies: dict[str, dict[str, Any]],
    hashes: dict[str, str],
    *,
    recorded_at: datetime,
    git_commit: str,
    code_hash: str,
    input_manifest: dict[str, Any],
    price_series_versions: list[dict[str, str]],
    library_versions: dict[str, str],
    simulation_start: object,
    simulation_end: object,
) -> int:
    """Insert the chain once. A matching artifact inserts nothing."""
    execution_ids = [str(row["execution_id"]) for row in HYPOTHESES]
    if any(item in PROTECTED_EXECUTIONS for item in execution_ids):
        raise DiscoveryStoreError("an earlier execution is not rewritten")
    with connection.cursor() as cursor:
        cursor.execute(
            """
            select execution_id, artifact_sha256
            from research.experiment_executions
            where execution_id = any(%s)
            """,
            (execution_ids,),
        )
        found = {str(row[0]): str(row[1]) for row in cursor.fetchall()}
    if found:
        if set(found) != set(execution_ids) or any(found[item] != hashes[item] for item in found):
            raise DiscoveryStoreError(
                "a discovery execution already exists with a different artifact "
                "and was not overwritten"
            )
        return 0
    with connection.cursor() as cursor:
        _specification(cursor, recorded_at)
        _methods(cursor, dossier, recorded_at)
        _features(cursor, dossier, recorded_at)
        _trials(cursor, dossier, recorded_at)
        _cases(cursor, dossier, recorded_at)
        _findings(cursor, dossier, recorded_at)
        for hypothesis in HYPOTHESES:
            _chain(
                cursor,
                hypothesis,
                bodies[str(hypothesis["execution_id"])],
                hashes[str(hypothesis["execution_id"])],
                recorded_at=recorded_at,
                git_commit=git_commit,
                code_hash=code_hash,
                input_manifest=input_manifest,
                price_series_versions=price_series_versions,
                library_versions=library_versions,
                simulation_start=simulation_start,
                simulation_end=simulation_end,
            )
        for row in DEPENDENCIES:
            _dependency(cursor, row, recorded_at)
    return len(execution_ids)


def _specification(cursor: psycopg.Cursor[Any], recorded_at: datetime) -> None:
    digest = specification_hash()
    cursor.execute(
        """
        select specification_hash
        from research.discovery_v2_specifications
        where specification_id = %s and version = %s
        """,
        (SPECIFICATION_ID, SPECIFICATION_VERSION),
    )
    found = cursor.fetchone()
    if found is not None:
        if found[0] != digest:
            raise DiscoveryStoreError(
                "the discovery specification hash differs and was not overwritten"
            )
        return
    cursor.execute(
        """
        insert into research.discovery_v2_specifications (
          specification_id, version, specification, specification_hash, frozen_at,
          publication_allowed
        ) values (%s, %s, %s, %s, %s, false)
        """,
        (
            SPECIFICATION_ID,
            SPECIFICATION_VERSION,
            Json(specification_document()),
            digest,
            recorded_at,
        ),
    )


def _methods(cursor: psycopg.Cursor[Any], dossier: Dossier, recorded_at: datetime) -> None:
    for run in dossier.runs:
        cursor.execute(
            """
            insert into research.discovery_v2_method_runs (
              specification_id, specification_version, method_id, method_version,
              implementation_hash, config_hash, parameter_policy, method_class,
              reconstruction, status, reason, point_count, numeric_count,
              publication_allowed, recorded_at
            ) values (
              %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, false, %s
            )
            """,
            (
                SPECIFICATION_ID,
                SPECIFICATION_VERSION,
                run.method_id,
                run.method_version,
                run.implementation_hash,
                run.config_hash,
                run.parameter_policy,
                run.method_class,
                run.reconstruction,
                run.status,
                run.reason,
                len(run.points),
                run.numeric_count,
                recorded_at,
            ),
        )
        if not run.points:
            continue
        cursor.executemany(
            """
            insert into research.discovery_v2_method_points (
              specification_id, specification_version, method_id, series_key,
              period_start, period_end, value_text, direction, change_text,
              state_label, unit, reconstruction, publication_allowed, recorded_at
            ) values (
              %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, false, %s
            )
            """,
            [
                (
                    SPECIFICATION_ID,
                    SPECIFICATION_VERSION,
                    run.method_id,
                    point.series_key,
                    point.period_start,
                    point.period_end,
                    point.value_text,
                    point.direction,
                    point.change_text,
                    point.state_label,
                    point.unit,
                    run.reconstruction,
                    recorded_at,
                )
                for point in run.points
            ],
        )


def _features(cursor: psycopg.Cursor[Any], dossier: Dossier, recorded_at: datetime) -> None:
    if not dossier.features:
        return
    cursor.executemany(
        """
        insert into research.discovery_v2_anchor_features (
          anchor_id, feature_id, anchor_session, period_end, value_text, state_label,
          unit, source, method_id, reconstruction, usable_as_decision_input,
          publication_allowed, recorded_at
        ) values (
          %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, false, false, %s
        )
        """,
        [
            (
                row.anchor_id,
                row.feature_id,
                row.anchor_session,
                row.period_end,
                row.value_text,
                row.state_label,
                row.unit,
                row.source,
                row.method_id,
                row.reconstruction,
                recorded_at,
            )
            for row in dossier.features
        ],
    )


def _trials(cursor: psycopg.Cursor[Any], dossier: Dossier, recorded_at: datetime) -> None:
    digest = specification_hash()
    cursor.executemany(
        """
        insert into research.discovery_v2_trials (
          trial_id, specification_id, specification_version, specification_hash,
          experiment_id, symbol, feature, paired_feature, statistic, outcome,
          sample_count, non_overlapping_count, result_text, refusal_reason,
          p_value_text, finding_class, bh_diagnostic, detail, publication_allowed,
          recorded_at
        ) values (
          %s, %s, %s, %s, %s, 'VWRA', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
          %s, %s, false, %s
        )
        """,
        [
            (
                trial.trial_id,
                SPECIFICATION_ID,
                SPECIFICATION_VERSION,
                digest,
                trial.experiment_id,
                trial.feature,
                trial.paired_feature,
                trial.statistic,
                trial.outcome,
                trial.sample_count,
                trial.non_overlapping_count,
                trial.result_text,
                trial.refusal_reason,
                trial.p_value_text,
                trial.finding_class,
                trial.bh_diagnostic,
                trial.detail,
                recorded_at,
            )
            for trial in dossier.trials
        ],
    )


def _cases(cursor: psycopg.Cursor[Any], dossier: Dossier, recorded_at: datetime) -> None:
    cursor.executemany(
        """
        insert into research.discovery_v2_casebook (
          case_id, specification_id, specification_version, symbol, episode_group,
          family, event_id, anchor_session, window_steps, value_text, sample_count,
          detail, publication_allowed, recorded_at
        ) values (
          %s, %s, %s, 'VWRA', %s, %s, %s, %s, %s, %s, %s, %s, false, %s
        )
        """,
        [
            (
                row.case_id,
                SPECIFICATION_ID,
                SPECIFICATION_VERSION,
                row.episode_group,
                row.family,
                row.event_id,
                row.anchor_session,
                row.window_steps,
                row.value_text,
                row.sample_count,
                row.detail,
                recorded_at,
            )
            for row in dossier.cases
        ],
    )


def _findings(cursor: psycopg.Cursor[Any], dossier: Dossier, recorded_at: datetime) -> None:
    for finding in dossier.findings:
        if finding.finding_class in {
            "statistically_supported",
            "economically_useful",
            "forward_validated",
        }:
            raise DiscoveryStoreError("a retrospective finding cannot be promoted")
        cursor.execute(
            """
            insert into research.discovery_v2_findings (
              finding_id, specification_id, specification_version, hypothesis_id,
              experiment_id, finding_class, point_in_time, independently_validated,
              executable_strategy, statement, publication_allowed, recorded_at
            ) values (
              %s, %s, %s, %s, %s, %s, false, false, false, %s, false, %s
            )
            """,
            (
                finding.finding_id,
                SPECIFICATION_ID,
                SPECIFICATION_VERSION,
                finding.hypothesis_id,
                finding.experiment_id,
                finding.finding_class,
                finding.statement,
                recorded_at,
            ),
        )


def _chain(
    cursor: psycopg.Cursor[Any],
    hypothesis: dict[str, object],
    body: dict[str, Any],
    digest: str,
    *,
    recorded_at: datetime,
    git_commit: str,
    code_hash: str,
    input_manifest: dict[str, Any],
    price_series_versions: list[dict[str, str]],
    library_versions: dict[str, str],
    simulation_start: object,
    simulation_end: object,
) -> None:
    hypothesis_id = str(hypothesis["hypothesis_id"])
    experiment_id = str(hypothesis["experiment_id"])
    execution_id = str(hypothesis["execution_id"])
    evidence_id = str(hypothesis["evidence_id"])
    claim_id = str(hypothesis["claim_id"])
    if (
        hypothesis_id in PROTECTED_HYPOTHESES
        or experiment_id in PROTECTED_EXPERIMENTS
        or execution_id in PROTECTED_EXECUTIONS
    ):
        raise DiscoveryStoreError("an earlier registry row is not rewritten")
    status = str(body["finding_class"])
    cursor.execute(
        """
        insert into research.hypotheses (
          hypothesis_id, version, proposition, economic_rationale, expected_mechanism,
          expected_direction, horizon, falsification_criteria, alternative_explanations,
          relevant_indicators, relevant_methodologies, target_instruments, initial_status,
          amendment_rationale, registered_at, registered_by, catalogue_signal_id,
          publication_allowed
        ) values (
          %s, 1, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'proposed', null, %s,
          'vwra-discovery', null, false
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
            recorded_at,
        ),
    )
    cursor.execute(
        """
        insert into research.experiment_specifications (
          experiment_id, version, category, category_label, specification,
          specification_hash, frozen_at, publication_allowed
        ) values (%s, 1, 'B', 'retrospective_economic_research', %s, %s, %s, false)
        """,
        (experiment_id, Json(specification_document()), specification_hash(), recorded_at),
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
        recorded_at,
    )
    _status(
        cursor,
        f"LH-S-E-{experiment_id[-3:]}-proposed",
        "experiment",
        experiment_id,
        "proposed",
        recorded_at,
    )
    configuration = {
        "portfolio_simulation": "not_called",
        "portfolio_path": "not_called",
        "portfolio_simulator": "not_called",
        "portfolio_comparison": "not_called",
        "point_in_time": False,
        "executable_strategy": False,
        "specification_id": SPECIFICATION_ID,
    }
    cursor.execute(
        """
        insert into research.experiment_executions (
          execution_id, experiment_id, experiment_version, state, git_commit, code_hash,
          parameter_version_id, input_manifest, macro_vintage_ids, price_series_versions,
          library_versions, random_seed, executed_at, availability_cutoff, simulation_start,
          simulation_end, artifact_sha256, reproduction_command, validation_status,
          configuration, supersedes_execution_id, research_run_id, publication_allowed
        ) values (
          %s, %s, 1, 'succeeded', %s, %s, null, %s, '[]'::jsonb, %s, %s,
          'not_applicable_no_randomness', %s, %s, %s, %s, %s, %s, %s, %s,
          null, null, false
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
            recorded_at,
            simulation_start,
            simulation_end,
            digest,
            "uv run python -m aqil_research.long_horizon.vwra_discovery",
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
        (evidence_id, execution_id, digest, Json(body), recorded_at),
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
            "Retrospective and overlapping. Not point-in-time and not independently validated.",
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
    note = "Current status after the frozen discovery rules. Version 1 is unchanged."
    _status(
        cursor,
        f"LH-S-H-{hypothesis_id[-3:]}-result",
        "hypothesis",
        hypothesis_id,
        status,
        recorded_at,
        note,
    )
    _status(
        cursor,
        f"LH-S-E-{experiment_id[-3:]}-result",
        "experiment",
        experiment_id,
        status,
        recorded_at,
        note,
    )
    _status(cursor, f"LH-S-C-{claim_id[-3:]}-result", "claim", claim_id, status, recorded_at, note)


def _status(
    cursor: psycopg.Cursor[Any],
    event_id: str,
    kind: str,
    subject_id: str,
    status: str,
    recorded_at: datetime,
    rationale: str = "Specification frozen in code before this dossier was scored.",
) -> None:
    cursor.execute(
        """
        insert into research.scientific_status_events (
          status_event_id, subject_kind, subject_id, subject_version, status,
          rationale, derivation, recorded_at, publication_allowed
        ) values (%s, %s, %s, 1, %s, %s, 'deterministic_criteria', %s, false)
        """,
        (event_id, kind, subject_id, status, rationale, recorded_at),
    )


def _dependency(cursor: psycopg.Cursor[Any], row: dict[str, object], recorded_at: datetime) -> None:
    dependency_id = str(row["dependency_id"])
    number = int(dependency_id.removeprefix("LH-D-"))
    if number < 27:
        raise DiscoveryStoreError("an earlier dependency row is not rewritten")
    period = row["period_start"]
    cursor.execute(
        """
        insert into research.research_dependencies (
          dependency_id, left_kind, left_id, right_kind, right_id, relation,
          dataset_id, indicator_id, instrument_id, methodology_id,
          period_start, period_end, independent_confirmation, detail, recorded_at
        ) values (
          %s, 'experiment', %s, %s, %s, %s, null, null, %s, %s, %s, null, false, %s, %s
        )
        """,
        (
            dependency_id,
            row["experiment_id"],
            row["right_kind"],
            row["right_id"],
            row["relation"],
            row["instrument_id"],
            row["methodology_id"],
            period,
            row["detail"],
            recorded_at,
        ),
    )
