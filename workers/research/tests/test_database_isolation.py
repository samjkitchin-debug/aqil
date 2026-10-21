"""Negative tests: research tests must not select the development database."""

from __future__ import annotations

import psycopg
import pytest

from aqil_research.persistence.config import DEFAULT_LOCAL_URL
from aqil_research.persistence.connection import research_connection
from aqil_research.persistence.test_database import (
    REQUIRED_DATABASE_NAME,
    TestDatabaseError,
    assert_test_database_url,
    require_test_database_url,
)

_DEV_COUNTS = """
select
  (select count(*) from research.economic_observations o
    join research.source_retrievals r on r.retrieval_id = o.retrieval_id
    where r.collection_mode = 'live' and r.source_id = 'bls_cps_unemployment_rate') as live_obs,
  (select count(*) from research.sourced_updates
    where source_id = 'bls_employment_situation_archive') as bls_pubs,
  (select count(*) from research.sourced_updates
    where source_id = 'federal_reserve_monetary_press') as fed_pubs,
  (select count(*) from forward.catalyst_events
    where source_id = 'bls_ics_schedule' and scheduled_at > now()) as calendar
"""


def _read_dev_counts() -> tuple[int, int, int, int]:
    with psycopg.connect(DEFAULT_LOCAL_URL, connect_timeout=2) as conn:
        conn.execute("set default_transaction_read_only = on")
        row = conn.execute(_DEV_COUNTS).fetchone()
    assert row is not None
    return tuple(int(value) for value in row)


def test_missing_test_url_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AQIL_RESEARCH_TEST_DATABASE_URL", raising=False)
    with pytest.raises(TestDatabaseError, match="required"):
        require_test_database_url()


def test_blank_test_url_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AQIL_RESEARCH_TEST_DATABASE_URL", "   ")
    with pytest.raises(TestDatabaseError, match="required"):
        require_test_database_url()


def test_development_url_is_rejected() -> None:
    with pytest.raises(TestDatabaseError, match="development database"):
        assert_test_database_url(DEFAULT_LOCAL_URL)


def test_hosted_database_is_rejected() -> None:
    hosted = f"postgresql://worker:secret@db.example.supabase.co:5432/{REQUIRED_DATABASE_NAME}"
    with pytest.raises(TestDatabaseError, match="loopback"):
        assert_test_database_url(hosted)


def test_wrong_database_name_is_rejected() -> None:
    wrong = "postgresql://research_worker:research_worker@127.0.0.1:55432/postgres?sslmode=disable"
    with pytest.raises(TestDatabaseError, match=REQUIRED_DATABASE_NAME):
        assert_test_database_url(wrong)


def test_development_connection_is_refused_before_write() -> None:
    before = _read_dev_counts()
    with pytest.raises(TestDatabaseError):
        with research_connection(DEFAULT_LOCAL_URL):
            raise AssertionError("the development database must not be entered")
    assert _read_dev_counts() == before
