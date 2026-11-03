"""Append-only registry constraints on the disposable research database."""

from __future__ import annotations

import os
import re
import subprocess
import uuid

import psycopg
import pytest

from aqil_research.persistence.connection import research_connection

HASH = "a" * 64
GDP = "bea.vintage.real_gdp.pct_preceding"


def _skip_without_disposable_database() -> None:
    url = os.environ.get("AQIL_RESEARCH_TEST_DATABASE_URL", "").strip()
    if not url:
        pytest.skip("disposable research database is not configured")
    if url.endswith("/postgres"):
        raise AssertionError("refusing the development database")


def _owner_mutation_is_refused(hypothesis_id: str, verb: str) -> None:
    if re.fullmatch(r"lh-probe-h-[0-9a-f]{12}", hypothesis_id) is None:
        raise AssertionError("unexpected hypothesis id")
    if verb == "update":
        statement = (
            "update research.hypotheses set proposition = 'rewritten' "
            f"where hypothesis_id = '{hypothesis_id}'"
        )
    elif verb == "delete":
        statement = f"delete from research.hypotheses where hypothesis_id = '{hypothesis_id}'"
    else:
        raise AssertionError(verb)
    identity = subprocess.run(
        [
            "docker",
            "exec",
            "supabase_db_ojvswermsbbaltjohqph",
            "psql",
            "-U",
            "postgres",
            "-d",
            "aqil_research_test",
            "-tA",
            "-c",
            "select current_database()",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    if identity.stdout.strip() != "aqil_research_test":
        raise AssertionError("refusing a database that is not disposable")
    result = subprocess.run(
        [
            "docker",
            "exec",
            "supabase_db_ojvswermsbbaltjohqph",
            "psql",
            "-U",
            "postgres",
            "-d",
            "aqil_research_test",
            "-v",
            "ON_ERROR_STOP=1",
            "-c",
            statement,
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "append-only" in result.stderr


def test_registry_is_append_only_and_does_not_grant_publication() -> None:
    _skip_without_disposable_database()
    token = uuid.uuid4().hex[:12]
    hypothesis_id = f"lh-probe-h-{token}"
    experiment_id = f"lh-probe-e-{token}"
    with research_connection() as connection:
        connection.execute(
            """
            insert into research.hypotheses (
              hypothesis_id, version, proposition, economic_rationale,
              expected_mechanism, expected_direction, horizon, falsification_criteria,
              alternative_explanations, relevant_indicators, relevant_methodologies,
              target_instruments, initial_status, registered_at, registered_by
            ) values (
              %s, 1, 'probe', 'none', 'none', 'none', 'one window', 'none',
              '[]'::jsonb, '[]'::jsonb, '[]'::jsonb, '[]'::jsonb,
              'proposed', now(), 'contract-probe'
            )
            """,
            (hypothesis_id,),
        )
    with research_connection() as connection, pytest.raises(psycopg.Error) as update_error:
        connection.execute(
            "update research.hypotheses set proposition = 'rewritten' where hypothesis_id = %s",
            (hypothesis_id,),
        )
    assert "permission denied" in str(update_error.value)
    _owner_mutation_is_refused(hypothesis_id, "update")
    with research_connection() as connection, pytest.raises(psycopg.Error) as delete_error:
        connection.execute(
            "delete from research.hypotheses where hypothesis_id = %s",
            (hypothesis_id,),
        )
    assert "permission denied" in str(delete_error.value)
    _owner_mutation_is_refused(hypothesis_id, "delete")
    with research_connection() as connection, pytest.raises(psycopg.Error):
        connection.execute(
            """
            insert into research.hypotheses (
              hypothesis_id, version, proposition, economic_rationale,
              expected_mechanism, expected_direction, horizon, falsification_criteria,
              alternative_explanations, relevant_indicators, relevant_methodologies,
              target_instruments, initial_status, registered_at, registered_by,
              publication_allowed
            ) values (
              %s, 1, 'probe', 'none', 'none', 'none', 'one window', 'none',
              '[]'::jsonb, '[]'::jsonb, '[]'::jsonb, '[]'::jsonb,
              'proposed', now(), 'contract-probe', true
            )
            """,
            (hypothesis_id + "-pub",),
        )
    with research_connection() as connection, pytest.raises(psycopg.Error):
        connection.execute(
            """
            insert into research.experiment_specifications (
              experiment_id, version, category, category_label, specification,
              specification_hash, frozen_at
            ) values (
              %s, 1, 'C', 'price_only_simulator_research', '{}'::jsonb, %s, now()
            )
            """,
            (experiment_id, HASH),
        )
    with research_connection() as connection:
        connection.execute(
            """
            insert into research.experiment_specifications (
              experiment_id, version, category, category_label, specification,
              specification_hash, frozen_at
            ) values (
              %s, 1, 'C', 'price_only_simulator_research',
              '{"not_macroeconomic_investment_intelligence": true}'::jsonb, %s, now()
            )
            """,
            (experiment_id, HASH),
        )
    with research_connection() as connection, pytest.raises(psycopg.Error):
        connection.execute(
            """
            insert into research.scientific_claims (
              claim_id, version, proposition, status_at_claim, eligibility_class,
              statistical_validity, economic_usefulness, independent_validation,
              remaining_uncertainty, derivation, reviewer_note, recorded_at
            ) values (
              %s, 1, 'probe', 'economically_useful', 'category_c_price_only',
              'not assessed', 'not claimed', 'not forward-validated',
              'one window', 'deterministic_criteria', 'probe', now()
            )
            """,
            (f"lh-probe-c-{token}",),
        )
    with research_connection() as connection, pytest.raises(psycopg.Error) as gdp_error:
        connection.execute(
            """
            insert into research.experiment_executions (
              execution_id, experiment_id, experiment_version, state, git_commit,
              code_hash, input_manifest, macro_vintage_ids, price_series_versions,
              library_versions, executed_at, availability_cutoff, artifact_sha256,
              reproduction_command, validation_status, configuration
            ) values (
              %s, %s, 1, 'blocked', 'probe', %s, '{}'::jsonb,
              jsonb_build_array(%s::text), '{}'::jsonb, '{}'::jsonb, now(), now(), %s,
              'not run', 'rejected', '{}'::jsonb
            )
            """,
            (f"lh-probe-x-{token}", experiment_id, HASH, GDP, HASH),
        )
    assert GDP in str(gdp_error.value)
    with research_connection() as connection, pytest.raises(psycopg.Error):
        connection.execute(
            """
            insert into research.candidate_design_rows (
              register_id, register_version, source_filename, source_sha256,
              source_bytes, row_kind, original_id, payload, empirical_result,
              imported_at
            ) values (
              'probe', 1, 'probe.json', %s, 1, 'file', %s, '{}'::jsonb, true, now()
            )
            """,
            (HASH, f"probe-{token}"),
        )
    with research_connection() as connection:
        connection.execute(
            """
            insert into research.hypotheses (
              hypothesis_id, version, proposition, economic_rationale,
              expected_mechanism, expected_direction, horizon, falsification_criteria,
              alternative_explanations, relevant_indicators, relevant_methodologies,
              target_instruments, initial_status, amendment_rationale, registered_at,
              registered_by
            ) values (
              %s, 2, 'probe', 'none', 'none', 'none', 'one window', 'none',
              '[]'::jsonb, '[]'::jsonb, '[]'::jsonb, '[]'::jsonb,
              'proposed', 'version append probe', now(), 'contract-probe'
            )
            """,
            (hypothesis_id,),
        )
        connection.execute(
            """
            insert into research.scientific_status_events (
              status_event_id, subject_kind, subject_id, subject_version, status,
              rationale, derivation, recorded_at
            ) values (%s, 'hypothesis', %s, 1, 'proposed', 'probe', 'deterministic_criteria', now())
            """,
            (f"lh-probe-s-{token}", hypothesis_id),
        )
        versions = connection.execute(
            "select count(*) from research.hypotheses where hypothesis_id = %s",
            (hypothesis_id,),
        ).fetchone()
        original = connection.execute(
            """
            select proposition from research.hypotheses
            where hypothesis_id = %s and version = 1
            """,
            (hypothesis_id,),
        ).fetchone()
        current = connection.execute(
            """
            select status from research.current_scientific_status
            where subject_kind = 'hypothesis' and subject_id = %s
            """,
            (hypothesis_id,),
        ).fetchone()
        published = connection.execute(
            """
            select executions_published, candidate_rows_marked_as_results
            from research.long_horizon_progress
            """
        ).fetchone()
    assert versions is not None and versions[0] == 2
    assert original is not None and original[0] == "probe"
    assert current is not None and current[0] == "proposed"
    assert published is not None
    assert published[0] == 0
    assert published[1] == 0
