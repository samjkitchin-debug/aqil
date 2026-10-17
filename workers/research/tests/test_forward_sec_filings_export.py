"""SEC completed filings → horizon company_filings export."""

from __future__ import annotations

from pathlib import Path

import psycopg
import pytest

from aqil_research.forward.collection.service import collect_sec_completed_filings
from aqil_research.forward.horizon_export import build_horizon_from_database
from aqil_research.persistence.config import research_database_url_or_local_default
from aqil_research.persistence.connection import research_connection

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "forward"


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


def test_sec_fixture_populates_company_filings_history(require_db: None) -> None:
    with research_connection() as conn:
        result = collect_sec_completed_filings(
            conn,
            live=False,
            fixture_path=FIXTURES / "sec_submissions_sample.json",
        )
        assert result.outcome == "completed"
        bundle = build_horizon_from_database(conn, include_demonstration=False)
    filings = bundle.get("company_filings") or []
    assert len(filings) >= 1
    assert filings[0].get("form") in {"8-K", "10-Q", "10-K"}
