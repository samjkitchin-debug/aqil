"""Fail closed before a test writes to the development or hosted database.

Pytest used to call ``research_database_url_or_local_default()``. When
``RESEARCH_DATABASE_URL`` was unset, that opened the development database on
port 55432 and the integration tests committed fixtures there.
"""

from __future__ import annotations

import os
from urllib.parse import urlparse

import psycopg

from aqil_research.persistence.config import DEFAULT_LOCAL_URL

TEST_DATABASE_ENV = "AQIL_RESEARCH_TEST_DATABASE_URL"
REQUIRED_DATABASE_NAME = "aqil_research_test"
ISOLATION_MARKER = "disposable-research-test"

_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})
_HOSTED_MARKERS = (
    "supabase.co",
    "supabase.com",
    "amazonaws.com",
    "azure.com",
    "neon.tech",
    "vercel.app",
)


class TestDatabaseError(RuntimeError):
    """The process must not write. No fallback database is selected."""

    __test__ = False


def running_under_pytest() -> bool:
    return bool(os.environ.get("PYTEST_CURRENT_TEST"))


def assert_test_database_url(url: str) -> str:
    """Reject a missing, development, or hosted target before connecting."""
    candidate = url.strip()
    if not candidate:
        raise TestDatabaseError(f"{TEST_DATABASE_ENV} is required for research tests")
    if candidate == DEFAULT_LOCAL_URL:
        raise TestDatabaseError("research tests must not use the development database")
    parsed = urlparse(candidate)
    host = (parsed.hostname or "").lower()
    database_name = parsed.path.lstrip("/").split("/", 1)[0]
    if not host or host not in _LOOPBACK_HOSTS:
        raise TestDatabaseError("research tests only connect to a loopback database")
    if any(marker in host for marker in _HOSTED_MARKERS):
        raise TestDatabaseError("hosted and production databases are prohibited as test targets")
    if database_name != REQUIRED_DATABASE_NAME:
        raise TestDatabaseError(
            f"research tests only write to database {REQUIRED_DATABASE_NAME}",
        )
    if parsed.port == 5432 or parsed.port == 6543:
        raise TestDatabaseError("research tests must not use the default Postgres or pooler port")
    return candidate


def require_test_database_url() -> str:
    """Read the explicit test URL. A missing value is an error, not a fallback."""
    configured = os.environ.get(TEST_DATABASE_ENV, "")
    if not configured.strip():
        raise TestDatabaseError(f"{TEST_DATABASE_ENV} is required for research tests")
    return assert_test_database_url(configured)


def assert_connected_test_database(conn: psycopg.Connection) -> None:
    """Confirm the open session is the disposable database before any write."""
    with conn.cursor() as cur:
        cur.execute("select current_database()")
        row = cur.fetchone()
        database_name = row[0] if row else ""
        if database_name != REQUIRED_DATABASE_NAME:
            raise TestDatabaseError(
                f"connected database is {database_name or 'unknown'}; refusing to write",
            )
        try:
            cur.execute("select marker from research.test_isolation_marker")
            marker = cur.fetchone()
        except psycopg.Error as exc:
            raise TestDatabaseError(
                "test isolation marker is missing; refusing to write",
            ) from exc
    if marker is None or marker[0] != ISOLATION_MARKER:
        raise TestDatabaseError("test isolation marker does not match; refusing to write")


def resolve_connection_url(explicit: str | None) -> str:
    """During pytest, never fall back to the development database."""
    if running_under_pytest():
        if explicit is not None:
            return assert_test_database_url(explicit)
        return require_test_database_url()
    if explicit is not None:
        return explicit
    from aqil_research.persistence.config import research_database_url_or_local_default

    return research_database_url_or_local_default()
