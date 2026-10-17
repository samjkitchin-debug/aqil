"""Forward calendar collection against local Supabase."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import psycopg
import pytest

from aqil_research.forward.collection.service import (
    collect_bls_empsit_schedule,
    collect_fed_fomc_calendar,
)
from aqil_research.persistence.config import research_database_url_or_local_default
from aqil_research.persistence.connection import research_connection

FIXTURES = Path(__file__).parent / "fixtures" / "forward"


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


def test_collect_fed_and_bls_fixture_idempotent(require_db: None) -> None:
    horizon_start = date(2026, 1, 1)
    horizon_end = date(2027, 12, 31)
    with research_connection() as conn:
        first_fed = collect_fed_fomc_calendar(
            conn,
            live=False,
            fixture_path=FIXTURES / "fed_fomc_calendar_snippet.html",
            horizon_start=horizon_start,
            horizon_end=horizon_end,
        )
        assert first_fed.outcome == "completed"
        assert first_fed.records_received >= 3
        second_fed = collect_fed_fomc_calendar(
            conn,
            live=False,
            fixture_path=FIXTURES / "fed_fomc_calendar_snippet.html",
            horizon_start=horizon_start,
            horizon_end=horizon_end,
        )
        assert second_fed.records_unchanged >= first_fed.records_received

        bls = collect_bls_empsit_schedule(
            conn,
            live=False,
            fixture_path=FIXTURES / "bls_empsit_schedule_snippet.html",
            horizon_start=horizon_start,
            horizon_end=horizon_end,
        )
        assert bls.outcome == "completed"
        assert bls.records_new + bls.records_unchanged >= 2

        with conn.cursor() as cur:
            cur.execute(
                """
                select evidence_class, source_locator
                from forward.catalyst_events
                where event_id = 'event:verified:fed:fomc:2026-10-28'
                """,
            )
            row = cur.fetchone()
        assert row is not None
        assert row[0] == "verified_schedule"
        assert str(row[1]).startswith("https://")
