"""Research ingest command (fixture path, offline)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import psycopg
import pytest

from aqil_research.persistence.config import research_database_url_or_local_default
from aqil_research.persistence.connection import research_connection
from aqil_research.workflow.research_ingest import run_research_ingest

FIXTURE = Path(__file__).parent / "fixtures" / "bls" / "api_lns14000000_success.json"
BAD_FIXTURE = Path(__file__).parent / "fixtures" / "bls" / "api_empty_series.json"
COLLECTED_AT = datetime(2025, 6, 1, 12, 0, tzinfo=UTC)
DATASET_ID = "bls.ln.LNS14000000"


def _db_available() -> bool:
    try:
        with psycopg.connect(research_database_url_or_local_default(), connect_timeout=2) as conn:
            with conn.cursor() as cur:
                cur.execute("select 1")
        return True
    except Exception:
        return False


def _observation_count(conn: psycopg.Connection) -> int:
    with conn.cursor() as cur:
        cur.execute(
            "select count(*) from research.economic_observations where dataset_id = %s",
            (DATASET_ID,),
        )
        row = cur.fetchone()
    return int(row[0]) if row else 0


pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def require_db() -> None:
    if not _db_available():
        pytest.skip("local Supabase not available")


def test_fixture_ingest_is_idempotent(require_db: None) -> None:
    first = run_research_ingest(
        live=False,
        fixture_path=FIXTURE,
        start_year=2022,
        end_year=2025,
        collected_at=COLLECTED_AT,
    )
    second = run_research_ingest(
        live=False,
        fixture_path=FIXTURE,
        start_year=2022,
        end_year=2025,
        collected_at=COLLECTED_AT,
    )
    assert first.bls_unemployment.observations_received > 0
    assert second.bls_unemployment.outcome == "unchanged"
    assert second.bls_unemployment.observations_newly_stored == 0
    assert first.bls_unemployment.data_provenance == "latest_revised"


def test_failed_fetch_does_not_write_observations(require_db: None) -> None:
    if not BAD_FIXTURE.exists():
        pytest.skip("empty-series fixture not present")
    with research_connection() as conn:
        before = _observation_count(conn)
    outcome = run_research_ingest(
        live=False,
        fixture_path=BAD_FIXTURE,
        start_year=2022,
        end_year=2025,
        collected_at=datetime(2025, 7, 1, 12, 0, tzinfo=UTC),
    )
    assert outcome.bls_unemployment.outcome in ("failed_fetch", "partial")
    assert outcome.bls_unemployment.observations_newly_stored == 0
    with research_connection() as conn:
        after = _observation_count(conn)
    assert after == before
