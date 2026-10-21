"""Collect-and-run end-to-end against PostgreSQL."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from aqil_research.persistence.connection import research_connection
from aqil_research.workflow.collect_and_run import collect_and_run_sahm
from db_guard import open_isolated_test_database

FIXTURE = Path(__file__).parent / "fixtures" / "bls" / "api_lns14000000_success.json"
COLLECTED_AT = datetime(2025, 6, 1, 12, 0, tzinfo=UTC)


pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def require_db() -> str:
    return open_isolated_test_database()


def test_postgres_duplicate_collection_unchanged(require_db: None) -> None:
    from aqil_research.collection.service import collect_bls_unemployment

    with research_connection() as conn:
        r1, _ = collect_bls_unemployment(
            store_backend="postgres",
            collected_at=COLLECTED_AT,
            live=False,
            fixture_path=str(FIXTURE),
            start_year=2022,
            end_year=2025,
            conn=conn,
        )
        r2, _ = collect_bls_unemployment(
            store_backend="postgres",
            collected_at=COLLECTED_AT,
            live=False,
            fixture_path=str(FIXTURE),
            start_year=2022,
            end_year=2025,
            conn=conn,
        )
    assert r1.observations_received > 0
    assert r2.outcome == "unchanged"
    assert r2.observations_newly_stored == 0


def test_collect_and_run_fixture_e2e(require_db: None) -> None:
    run_id = f"workflow-e2e-{int(datetime.now(tz=UTC).timestamp())}"
    with research_connection() as conn:
        outcome = collect_and_run_sahm(
            conn,
            live=False,
            fixture_path=FIXTURE,
            start_year=2022,
            end_year=2025,
            run_id=run_id,
            allow_evaluation_fallback=True,
        )
    assert outcome.run_id == run_id
    assert outcome.execution_status == "completed"
    if not outcome.recompute_match:
        with research_connection() as conn:
            from aqil_research.persistence.reproduce import verify_stored_run_replay

            replay = verify_stored_run_replay(conn, run_id)
            db_replay = verify_stored_run_replay(conn, run_id)
            raise AssertionError(
                f"replay mismatch: input_snapshot={replay.input_snapshot_hash_match}, "
                f"calculation={replay.calculation_match}, "
                f"calc_keys={replay.calculation_mismatch_keys()}, "
                f"db_calc={db_replay.calculation_match}, "
                f"db_calc_keys={db_replay.calculation_mismatch_keys()}, "
                f"payload={replay.analytical_payload_hash_match}, "
                f"observation_ids={replay.observation_ids_match}, "
                f"warnings={outcome.warnings}",
            )
    with research_connection() as conn:
        from aqil_research.persistence.reproduce import verify_stored_run_replay

        db_replay = verify_stored_run_replay(conn, run_id)
    assert db_replay.calculation_match
    assert db_replay.input_snapshot_hash_match
    assert outcome.insight is not None
    assert outcome.insight.publication_status in ("internal_preview", "blocked", "not_eligible")
    assert outcome.insight.data_provenance == "latest_revised"
