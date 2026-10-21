"""PostgreSQL connections for the research worker role."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

import psycopg

from aqil_research.persistence.test_database import (
    assert_connected_test_database,
    resolve_connection_url,
    running_under_pytest,
)


@contextmanager
def research_connection(url: str | None = None) -> Iterator[psycopg.Connection]:
    """Open a connection as research_worker (must not use service_role)."""
    conn = psycopg.connect(resolve_connection_url(url))
    try:
        with conn.cursor() as cur:
            cur.execute("select current_user")
            user = cur.fetchone()[0]
            if user == "service_role":
                raise RuntimeError("service_role must not be used for research persistence")
        if running_under_pytest():
            assert_connected_test_database(conn)
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
