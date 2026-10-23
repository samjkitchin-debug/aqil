"""Persistence tests for research.prospective_assessments on aqil_research_test."""

from __future__ import annotations

import os
import re
import subprocess
import uuid
from datetime import UTC, datetime
from pathlib import Path

import psycopg
import pytest
from psycopg.types.json import Json

from aqil_research.persistence.connection import research_connection
from aqil_research.persistence.prospective_assessments import (
    INPUT_HASH_FIELDS,
    OUTPUT_HASH_FIELDS,
    ProspectiveAssessmentDraft,
    ProspectiveAssessmentPersistenceError,
    insert_prospective_assessment,
    load_prospective_assessment,
    payload_document_hash,
    stored_payload,
)
from aqil_research.persistence.test_database import (
    REQUIRED_DATABASE_NAME,
    TestDatabaseError,
    assert_connected_test_database,
    assert_test_database_url,
)
from db_guard import open_isolated_test_database

pytestmark = pytest.mark.integration

_TEST_DATABASE = "aqil_research_test"
_CONTAINER = "supabase_db_ojvswermsbbaltjohqph"
_MIGRATION = (
    Path(__file__).resolve().parents[3]
    / "supabase"
    / "migrations"
    / "20261023120000_prospective_assessments.sql"
)
_CAPTURE_PHRASE = "not a reconstruction of dates before captured_at"
_SAFE_ASSESSMENT_ID = r"^pa-[0-9a-f-]{36}$"


def _test_database_url_or_skip() -> str:
    configured = os.environ.get("AQIL_RESEARCH_TEST_DATABASE_URL", "")
    if not configured.strip():
        pytest.skip(
            "AQIL_RESEARCH_TEST_DATABASE_URL is unset. Skipping the database test. "
            "The database named postgres was not opened."
        )
    assert_test_database_url(configured)
    return open_isolated_test_database()


@pytest.fixture(scope="module")
def require_db() -> str:
    if os.environ.get("RESEARCH_DATABASE_URL", "").strip():
        raise RuntimeError("RESEARCH_DATABASE_URL must be unset for this test")
    url = _test_database_url_or_skip()
    _ensure_prospective_assessments_table(url)
    return url


def test_not_qualified_row_recomputes_hashes_from_stored_payload(require_db: str) -> None:
    assessment_id = _assessment_id()
    with research_connection() as conn:
        _assert_database(conn)
        before_scenarios = _count(conn, "forward.forward_scenarios")
        before_outcomes = _count(conn, "forward.event_outcomes")
        stored = insert_prospective_assessment(conn, _draft(assessment_id))
        loaded = load_prospective_assessment(conn, assessment_id)
        after_scenarios = _count(conn, "forward.forward_scenarios")
        after_outcomes = _count(conn, "forward.event_outcomes")

    assert loaded == stored
    assert loaded.lifecycle_status == "not_qualified"
    assert loaded.publication_allowed is False
    assert loaded.revision_class == "latest_revised"
    assert loaded.horizon_months is None
    assert _CAPTURE_PHRASE in loaded.capture_note
    payload = stored_payload(loaded)
    assert loaded.input_hash == payload_document_hash(payload["input"])
    assert loaded.output_hash == payload_document_hash(payload["output"])
    assert set(payload["input"]) == set(INPUT_HASH_FIELDS)
    assert set(payload["output"]) == set(OUTPUT_HASH_FIELDS)
    assert loaded.captured_values == {"fixture-observation": "4.3"}
    assert loaded.observation_ids == ("fixture-observation",)
    assert "forecast" not in payload["input"]
    assert "forecast" not in payload["output"]
    assert after_scenarios == before_scenarios
    assert after_outcomes == before_outcomes


def test_update_and_delete_are_rejected_by_the_trigger(require_db: str) -> None:
    assessment_id = _assessment_id()
    with research_connection() as conn:
        original = insert_prospective_assessment(conn, _draft(assessment_id))

    update_result = _owner_psql(
        "update research.prospective_assessments "
        f"set support_text = 'rewritten' where assessment_id = '{assessment_id}';"
    )
    _assert_trigger_rejection(update_result, "UPDATE")

    delete_result = _owner_psql(
        f"delete from research.prospective_assessments where assessment_id = '{assessment_id}';"
    )
    _assert_trigger_rejection(delete_result, "DELETE")

    with research_connection() as conn:
        loaded = load_prospective_assessment(conn, assessment_id)
    assert loaded == original
    assert loaded.support_text == original.support_text


def test_superseding_insert_leaves_the_first_row_unchanged(require_db: str) -> None:
    first_id = _assessment_id()
    second_id = _assessment_id()
    with research_connection() as conn:
        first = insert_prospective_assessment(conn, _draft(first_id))
        before = load_prospective_assessment(conn, first_id)
        second = insert_prospective_assessment(
            conn,
            _draft(
                second_id,
                supersedes_assessment_id=first_id,
                uncertainty_text="A later row does not rewrite the earlier capture.",
            ),
        )
        during = load_prospective_assessment(conn, first_id)

    with research_connection() as conn:
        after = load_prospective_assessment(conn, first_id)
        reloaded_second = load_prospective_assessment(conn, second_id)

    assert before == first
    assert during == before
    assert after == before
    assert after.supersedes_assessment_id is None
    assert after.publication_allowed is False
    assert after.revision_class == "latest_revised"
    assert reloaded_second == second
    assert reloaded_second.supersedes_assessment_id == first_id
    assert reloaded_second.lifecycle_status == "not_qualified"
    assert reloaded_second.publication_allowed is False
    assert reloaded_second.revision_class == "latest_revised"
    assert _CAPTURE_PHRASE in reloaded_second.capture_note
    second_payload = stored_payload(reloaded_second)
    assert reloaded_second.input_hash == payload_document_hash(second_payload["input"])
    assert reloaded_second.output_hash == payload_document_hash(second_payload["output"])


class _RefuseWrite:
    def cursor(self) -> None:
        raise AssertionError("a refused assessment must not open a write")


def test_database_named_postgres_is_refused() -> None:
    prohibited = (
        "postgresql://research_worker:research_worker@127.0.0.1:55432/postgres?sslmode=disable"
    )
    with pytest.raises(TestDatabaseError, match=REQUIRED_DATABASE_NAME):
        assert_test_database_url(prohibited)


def test_unset_test_database_url_skips_without_opening_postgres(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("AQIL_RESEARCH_TEST_DATABASE_URL", raising=False)
    with pytest.raises(pytest.skip.Exception, match="was not opened"):
        _test_database_url_or_skip()


def test_capture_note_without_the_required_phrase_is_refused() -> None:
    draft = _draft("pa-00000000-0000-4000-8000-000000000001")
    draft.capture_note = "stored at capture only"
    with pytest.raises(ProspectiveAssessmentPersistenceError, match=_CAPTURE_PHRASE):
        insert_prospective_assessment(_RefuseWrite(), draft)  # type: ignore[arg-type]


def test_insert_without_the_required_capture_note_phrase_fails(require_db: str) -> None:
    database_name = require_db.rstrip("/").rsplit("/", 1)[-1].split("?", 1)[0]
    assert database_name == _TEST_DATABASE
    assert database_name != "postgres"
    assessment_id = _assessment_id()
    bad_note = "stored at capture only"
    assert _CAPTURE_PHRASE not in bad_note
    captured = datetime(2026, 10, 23, 1, 0, tzinfo=UTC)
    with research_connection() as conn:
        _assert_database(conn)
        with pytest.raises(psycopg.Error) as rejected:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    insert into research.prospective_assessments (
                      assessment_id, created_at, captured_at, lifecycle_status,
                      publication_allowed, revision_class, completeness, horizon_months,
                      evaluation_due, run_ids, observation_ids, captured_values,
                      retrieval_timestamps, publication_timestamps, method_versions,
                      parameter_hashes, support_text, contradiction_text, uncertainty_text,
                      unavailable_inputs, input_hash, output_hash, supersedes_assessment_id,
                      capture_note
                    ) values (
                      %s, %s, %s, 'not_qualified', false, 'latest_revised', 'incomplete',
                      null, null, %s, %s, %s, %s, '[]'::jsonb, %s, %s, %s, %s, %s, %s,
                      %s, %s, null, %s
                    )
                    """,
                    (
                        assessment_id,
                        captured,
                        captured,
                        Json(["fixture-run"]),
                        Json(["fixture-observation"]),
                        Json({"fixture-observation": "4.3"}),
                        Json(["2026-10-23T01:00:00+00:00"]),
                        Json({"fixture": "1.0.0"}),
                        Json({"fixture": "a" * 64}),
                        "No 6- or 12-month hypothesis qualifies.",
                        "No qualifying hypothesis is stored.",
                        "This row is the stored capture only.",
                        Json(["qualified_hypothesis"]),
                        "a" * 64,
                        "b" * 64,
                        bad_note,
                    ),
                )
        assert rejected.value.sqlstate == "23514"
        assert "prospective_assessments_capture_note" in str(rejected.value)
        conn.rollback()
    with research_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select count(*)
                from research.prospective_assessments
                where assessment_id = %s
                """,
                (assessment_id,),
            )
            remaining = cur.fetchone()
    assert remaining is not None
    assert remaining[0] == 0


def _draft(
    assessment_id: str,
    *,
    supersedes_assessment_id: str | None = None,
    uncertainty_text: str = "This row is the stored capture only.",
) -> ProspectiveAssessmentDraft:
    captured = datetime(2026, 10, 23, 1, 0, tzinfo=UTC)
    return ProspectiveAssessmentDraft(
        assessment_id=assessment_id,
        created_at=captured,
        captured_at=captured,
        lifecycle_status="not_qualified",
        completeness="incomplete",
        run_ids=("fixture-run",),
        observation_ids=("fixture-observation",),
        captured_values={"fixture-observation": "4.3"},
        retrieval_timestamps=("2026-10-23T01:00:00+00:00",),
        publication_timestamps=(),
        method_versions={"fixture": "1.0.0"},
        parameter_hashes={"fixture": "a" * 64},
        support_text="No 6- or 12-month hypothesis qualifies.",
        contradiction_text="No qualifying hypothesis is stored.",
        uncertainty_text=uncertainty_text,
        unavailable_inputs=("qualified_hypothesis",),
        capture_note=f"Stored at capture; {_CAPTURE_PHRASE}",
        horizon_months=None,
        evaluation_due=None,
        supersedes_assessment_id=supersedes_assessment_id,
    )


def _assessment_id() -> str:
    assessment_id = f"pa-{uuid.uuid4()}"
    if re.fullmatch(_SAFE_ASSESSMENT_ID, assessment_id) is None:
        raise RuntimeError("assessment id is not safe to interpolate")
    return assessment_id


def _count(conn: psycopg.Connection, table: str) -> int:
    if table not in {"forward.forward_scenarios", "forward.event_outcomes"}:
        raise RuntimeError("unexpected count target")
    with conn.cursor() as cur:
        cur.execute(f"select count(*) from {table}")
        row = cur.fetchone()
    if row is None:
        raise RuntimeError("count returned no row")
    return int(row[0])


def _assert_database(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute("select current_database()")
        row = cur.fetchone()
    database_name = row[0] if row else ""
    if database_name == "postgres":
        raise RuntimeError("refusing to connect to the database named postgres")
    assert_connected_test_database(conn)


def _ensure_prospective_assessments_table(url: str) -> None:
    with psycopg.connect(url, connect_timeout=2) as conn:
        _assert_database(conn)
        if _table_present(conn):
            return
    migration = _MIGRATION.read_text(encoding="utf-8")
    applied = _owner_psql(migration)
    if applied.returncode != 0:
        raise RuntimeError(applied.stderr.strip() or "migration apply failed")
    with psycopg.connect(url, connect_timeout=2) as conn:
        _assert_database(conn)
        if not _table_present(conn):
            raise RuntimeError("research.prospective_assessments is still absent")


def _table_present(conn: psycopg.Connection) -> bool:
    with conn.cursor() as cur:
        cur.execute("select to_regclass('research.prospective_assessments')")
        row = cur.fetchone()
    return row is not None and row[0] is not None


def _owner_psql(sql: str) -> subprocess.CompletedProcess[str]:
    """Run SQL as the table owner on aqil_research_test only."""
    identity = _owner_command(tuples_only=True)
    checked = subprocess.run(
        identity,
        input="select current_database();",
        text=True,
        capture_output=True,
        check=False,
    )
    database_name = checked.stdout.strip()
    if database_name == "postgres":
        raise RuntimeError("refusing to connect to the database named postgres")
    if checked.returncode != 0 or database_name != _TEST_DATABASE:
        detail = checked.stderr.strip() or database_name or "no database name"
        raise RuntimeError(f"owner session is not {_TEST_DATABASE}: {detail}")
    return subprocess.run(
        _owner_command(tuples_only=False),
        input=sql,
        text=True,
        capture_output=True,
        check=False,
    )


def _owner_command(*, tuples_only: bool) -> list[str]:
    database = _TEST_DATABASE
    if database == "postgres":
        raise RuntimeError("refusing to connect to the database named postgres")
    command = [
        "docker",
        "exec",
        "-i",
        _CONTAINER,
        "psql",
        "-U",
        "postgres",
        "-d",
        database,
        "-v",
        "ON_ERROR_STOP=1",
    ]
    if tuples_only:
        command.append("-tA")
    return command


def _assert_trigger_rejection(result: subprocess.CompletedProcess[str], operation: str) -> None:
    detail = f"{result.stdout}\n{result.stderr}"
    assert result.returncode != 0
    assert "append-only" in detail
    assert f"{operation} is not permitted" in detail
    assert "deny_row_mutation" in detail
