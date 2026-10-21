"""Open the disposable research database or fail before a test writes."""

from __future__ import annotations

import psycopg

from aqil_research.persistence.test_database import (
    assert_connected_test_database,
    require_test_database_url,
)


def open_isolated_test_database() -> str:
    url = require_test_database_url()
    with psycopg.connect(url, connect_timeout=2) as conn:
        assert_connected_test_database(conn)
    return url
