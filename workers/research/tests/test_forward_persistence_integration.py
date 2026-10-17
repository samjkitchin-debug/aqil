"""Forward intelligence persistence (local Supabase)."""

from __future__ import annotations

from datetime import UTC, datetime

import psycopg
import pytest

from aqil_research.forward.demo_fixtures import DEMO_SCENARIO_ID
from aqil_research.forward.persistence import import_demo_fixture_bundle
from aqil_research.persistence.config import research_database_url_or_local_default
from aqil_research.persistence.connection import research_connection


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


def test_demo_fixture_import_and_scenario_immutable(require_db: None) -> None:
    now = datetime(2026, 10, 17, 10, 0, tzinfo=UTC)
    with research_connection() as conn:
        import_demo_fixture_bundle(conn, recorded_at=now)
        with conn.cursor() as cur:
            cur.execute(
                "select count(*) from forward.forward_scenarios where scenario_id = %s",
                (DEMO_SCENARIO_ID,),
            )
            assert cur.fetchone()[0] == 1
            update_sql = (
                "update forward.forward_scenarios set payload = '{}'::jsonb "
                "where scenario_id = %s"
            )
            with pytest.raises(psycopg.Error) as exc_info:
                cur.execute(update_sql, (DEMO_SCENARIO_ID,))
            assert exc_info.value.sqlstate in ("42501", "P0001")
