"""Append the CNDX comparison. Earlier executions are not rewritten."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import psycopg
from psycopg.types.json import Json

from aqil_research.long_horizon.registry import REVIEWER_NOTE
from aqil_research.long_horizon.vwra_discovery.battery import ScoredTrial
from aqil_research.long_horizon.vwra_discovery.cndx_comparison import (
    DEPENDENCIES,
    HYPOTHESES,
    PROTECTED_THROUGH,
    REPRODUCTION_COMMAND,
    SPECIFICATION_ID,
    SPECIFICATION_VERSION,
    assert_not_promoted_status,
    specification_document,
    specification_hash,
)
from aqil_research.long_horizon.vwra_discovery.dossier import CaseRow, Finding
from aqil_research.long_horizon.vwra_discovery.store import DiscoveryStoreError

CASE_EXPERIMENT = "LH-E-024"
PAIR = "CNDX-VWRA"


def artifact_bodies(
    trials: list[ScoredTrial],
    cases: list[CaseRow],
    findings: list[Finding],
    coverage: dict[str, Any],
    portfolio: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {str(row["experiment_id"]): [] for row in HYPOTHESES}
    for row in trials:
        grouped[row.trial.experiment_id].append({**row.trial.canonical(), "symbol": row.symbol})
    shared = {
        "specification_hash": specification_hash(),
        "coverage": coverage,
        "publication_allowed": False,
        "point_in_time_results": 0,
        "portfolio": portfolio,
    }
    built: dict[str, dict[str, Any]] = {}
    for hypothesis in HYPOTHESES:
        experiment_id = str(hypothesis["experiment_id"])
        execution_id = str(hypothesis["execution_id"])
        finding = next(item for item in findings if item.experiment_id == experiment_id)
        built[execution_id] = {
            **shared,
            "experiment_id": experiment_id,
            "finding_class": finding.finding_class,
            "statement": finding.statement,
            "trials": grouped[experiment_id],
            "cases": [_case(row) for row in cases] if experiment_id == CASE_EXPERIMENT else None,
            "simulation_start": None,
            "simulation_end": None,
        }
    return built


def store_comparison(
    connection: psycopg.Connection,
    *,
    trials: list[ScoredTrial],
    cases: list[CaseRow],
    findings: list[Finding],
    features: list[tuple[Any, ...]],
    bodies: dict[str, dict[str, Any]],
    hashes: dict[str, str],
    recorded_at: datetime,
    git_commit: str,
    code_hash: str,
    input_manifest: dict[str, Any],
    price_series_versions: list[dict[str, str]],
    library_versions: dict[str, str],
) -> int:
    """Insert the new chain once. A matching artifact inserts nothing."""
    execution_ids = [str(row["execution_id"]) for row in HYPOTHESES]
    _refuse_protected(execution_ids)
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
                "a CNDX comparison execution already exists with a different artifact "
                "and was not overwritten"
            )
        return 0
    with connection.cursor() as cursor:
        cursor.execute(
            """
            select count(*)::int
            from research.discovery_v2_anchor_features f
            join research.decision_anchors a on a.anchor_id = f.anchor_id
            where a.symbol = 'CNDX'
            """
        )
        if int(cursor.fetchone()[0]) > 0:
            raise DiscoveryStoreError("CNDX anchor features already exist and were not overwritten")
        _specification(cursor, recorded_at)
        _features(cursor, features, recorded_at)
        _trials(cursor, trials, recorded_at)
        _cases(cursor, cases, recorded_at)
        _findings(cursor, findings, recorded_at)
        for hypothesis in HYPOTHESES:
            execution_id = str(hypothesis["execution_id"])
            _chain(
                cursor,
                hypothesis,
                bodies[execution_id],
                hashes[execution_id],
                recorded_at=recorded_at,
                git_commit=git_commit,
                code_hash=code_hash,
                input_manifest=input_manifest,
                price_series_versions=price_series_versions,
                library_versions=library_versions,
            )
        for row in DEPENDENCIES:
            _dependency(cursor, row, recorded_at)
    return len(execution_ids)


def _refuse_protected(execution_ids: list[str]) -> None:
    for item in execution_ids:
        number = int(item.removeprefix("LH-X-"))
        if number <= PROTECTED_THROUGH:
            raise DiscoveryStoreError("an earlier execution is not rewritten")


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
            raise DiscoveryStoreError("the CNDX specification hash differs and was not overwritten")
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


def _features(
    cursor: psycopg.Cursor[Any], rows: list[tuple[Any, ...]], recorded_at: datetime
) -> None:
    if not rows:
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
        [(*row, recorded_at) for row in rows],
    )


def _trials(cursor: psycopg.Cursor[Any], trials: list[ScoredTrial], recorded_at: datetime) -> None:
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
          %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
          false, %s
        )
        """,
        [
            (
                row.trial.trial_id,
                SPECIFICATION_ID,
                SPECIFICATION_VERSION,
                digest,
                row.trial.experiment_id,
                row.symbol,
                row.trial.feature,
                row.trial.paired_feature,
                row.trial.statistic,
                row.trial.outcome,
                row.trial.sample_count,
                row.trial.non_overlapping_count,
                row.trial.result_text,
                row.trial.refusal_reason,
                row.trial.p_value_text,
                row.trial.finding_class,
                row.trial.bh_diagnostic,
                row.trial.detail,
                recorded_at,
            )
            for row in trials
        ],
    )


def _cases(cursor: psycopg.Cursor[Any], cases: list[CaseRow], recorded_at: datetime) -> None:
    if not cases:
        return
    cursor.executemany(
        """
        insert into research.discovery_v2_casebook (
          case_id, specification_id, specification_version, symbol, episode_group,
          family, event_id, anchor_session, window_steps, value_text, sample_count,
          detail, publication_allowed, recorded_at
        ) values (
          %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, false, %s
        )
        """,
        [
            (
                row.case_id,
                SPECIFICATION_ID,
                SPECIFICATION_VERSION,
                PAIR,
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
            for row in cases
        ],
    )


def _findings(cursor: psycopg.Cursor[Any], findings: list[Finding], recorded_at: datetime) -> None:
    for finding in findings:
        assert_not_promoted_status(finding.finding_class)
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
) -> None:
    hypothesis_id = str(hypothesis["hypothesis_id"])
    experiment_id = str(hypothesis["experiment_id"])
    execution_id = str(hypothesis["execution_id"])
    evidence_id = str(hypothesis["evidence_id"])
    claim_id = str(hypothesis["claim_id"])
    category = str(hypothesis["category"])
    status = str(body["finding_class"])
    if category == "C":
        status = str(body["portfolio"]["claim_status"])
        state = str(body["portfolio"]["execution_state"])
        configuration = body["portfolio"]["configuration"]
        eligibility = "category_c_price_only"
    else:
        state = "succeeded"
        configuration = {
            "portfolio_simulation": "not_called",
            "portfolio_path": "not_called",
            "portfolio_simulator": "not_called",
            "portfolio_comparison": "not_called",
            "point_in_time": False,
            "executable_strategy": False,
            "specification_id": SPECIFICATION_ID,
        }
        eligibility = "category_b_retrospective"
    assert_not_promoted_status(status)
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
          'cndx-vwra-comparison', null, false
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
        ) values (%s, 1, %s, %s, %s, %s, %s, false)
        """,
        (
            experiment_id,
            category,
            hypothesis["category_label"],
            Json(specification_document()),
            specification_hash(),
            recorded_at,
        ),
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
    cursor.execute(
        """
        insert into research.experiment_executions (
          execution_id, experiment_id, experiment_version, state, git_commit, code_hash,
          parameter_version_id, input_manifest, macro_vintage_ids, price_series_versions,
          library_versions, random_seed, executed_at, availability_cutoff, simulation_start,
          simulation_end, artifact_sha256, reproduction_command, validation_status,
          configuration, supersedes_execution_id, research_run_id, publication_allowed
        ) values (
          %s, %s, 1, %s, %s, %s, null, %s, '[]'::jsonb, %s, %s,
          'not_applicable_no_randomness', %s, %s, %s, %s, %s, %s, %s, %s,
          null, null, false
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
            recorded_at,
            body.get("simulation_start"),
            body.get("simulation_end"),
            digest,
            REPRODUCTION_COMMAND,
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
    uncertainty = (
        "Price-return accounting only. Not a total return, not an SGD investor return, "
        "and not independently validated."
        if category == "C"
        else "Retrospective and overlapping. Not point-in-time and not independently validated."
    )
    cursor.execute(
        """
        insert into research.scientific_claims (
          claim_id, version, proposition, status_at_claim, eligibility_class,
          statistical_validity, economic_usefulness, independent_validation,
          remaining_uncertainty, publication_eligible, publication_allowed,
          derivation, reviewer_note, recorded_at
        ) values (
          %s, 1, %s, %s, %s,
          'not_assessed_overlapping_months', 'not_assessed', 'not_forward_validated',
          %s, false, false, 'deterministic_criteria', %s, %s
        )
        """,
        (
            claim_id,
            body["statement"],
            status,
            eligibility,
            uncertainty,
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
    note = "Current status after the frozen comparison rules. Version 1 is unchanged."
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
    rationale: str = "Specification frozen in code before this comparison was scored.",
) -> None:
    assert_not_promoted_status(status)
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
    if number <= 43:
        raise DiscoveryStoreError("an earlier dependency row is not rewritten")
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
            row["period_start"],
            row["detail"],
            recorded_at,
        ),
    )


def _case(row: CaseRow) -> dict[str, Any]:
    return {
        "case_id": row.case_id,
        "episode_group": row.episode_group,
        "family": row.family,
        "window_steps": row.window_steps,
        "value_text": row.value_text,
        "sample_count": row.sample_count,
        "detail": row.detail,
    }
