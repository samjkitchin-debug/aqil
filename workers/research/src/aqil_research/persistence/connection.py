"""PostgreSQL connections for the research worker role."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

import psycopg

from aqil_research.persistence.config import research_database_url_or_local_default


@contextmanager
def research_connection(url: str | None = None) -> Iterator[psycopg.Connection]:
    """Open a connection as research_worker (must not use service_role)."""
    conn = psycopg.connect(url or research_database_url_or_local_default())
    try:
        with conn.cursor() as cur:
            cur.execute("select current_user")
            user = cur.fetchone()[0]
            if user == "service_role":
                raise RuntimeError("service_role must not be used for research persistence")
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
