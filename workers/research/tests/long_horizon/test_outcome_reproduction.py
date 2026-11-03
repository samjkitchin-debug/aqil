"""Recompute the stored outcome-first inventory. Skips when the local databases are down."""

from __future__ import annotations

import psycopg
import pytest

from aqil_research.long_horizon.events.reproduce import reproduce_outcome
from aqil_research.long_horizon.pilot import LOCAL_RESEARCH_URL


def test_stored_outcome_inventory_reproduces_without_promotion() -> None:
    try:
        connection = psycopg.connect(LOCAL_RESEARCH_URL, connect_timeout=3)
    except psycopg.OperationalError:
        pytest.skip("local research database is unavailable")
    connection.close()
    reproduced = reproduce_outcome()
    assert reproduced["execution_id"] == "LH-X-002"
    assert reproduced["status"] == "inconclusive"
    assert reproduced["event_count"] == "1749"
    assert reproduced["comparison_count"] == "1700"
    assert reproduced["macro_execution_id"] == "LH-X-003"
    assert reproduced["macro_state"] == "blocked"
    assert reproduced["original_execution_id"] == "LH-X-001"
    assert reproduced["original_status"] == "inconclusive"
