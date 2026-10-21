"""M6 collect → run → replay integration (PostgreSQL)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import psycopg
import pytest

from aqil_research.persistence.config import research_database_url_or_local_default
from aqil_research.persistence.reproduce import verify_stored_run_replay
from aqil_research.workflow.collect_and_run_macro import collect_and_run_macro_conditions

FIXTURES = Path(__file__).parent / "fixtures"
BLS = FIXTURES / "bls" / "api_lns14000000_success.json"
SLOOS = FIXTURES / "fed_sloos" / "sublpdcils_n_q_bundle.json"
CENSUS = FIXTURES / "census" / "mdm_no_adv_vintages.json"


def _db_available() -> bool:
    try:
        with psycopg.connect(research_database_url_or_local_default(), connect_timeout=2) as conn:
            with conn.cursor() as cur:
                cur.execute("select 1")
        return True
    except Exception:
        return False


pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def require_db() -> None:
    if not _db_available():
        pytest.skip("local Supabase not available")


def test_macro_conditions_fixture_e2e(require_db: None) -> None:
    """Replay inside one transaction, then roll back.

    The local database already holds the accepted live BLS retrieval.
    This fixture run must not commit observations or a research run beside it.
    """
    run_id = f"m6-macro-{int(datetime.now(tz=UTC).timestamp())}"
    conn = psycopg.connect(research_database_url_or_local_default())
    try:
        with conn.cursor() as cur:
            cur.execute("select current_user")
            user = cur.fetchone()
            assert user is not None
            assert user[0] != "service_role"
        outcome = collect_and_run_macro_conditions(
            conn,
            bls_fixture_path=BLS,
            sloos_fixture_path=SLOOS,
            census_fixture_path=CENSUS,
            run_id=run_id,
            start_year=2022,
            end_year=2025,
        )
        assert outcome.run_id == run_id
        assert outcome.execution_status == "completed"
        assert outcome.insight is not None
        assert outcome.recompute_match is True
        replay = verify_stored_run_replay(conn, run_id)
        assert replay.full_match
        conn.rollback()
    finally:
        conn.close()
