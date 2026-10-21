"""A revised SLOOS vintage is a new run. The earlier run stays."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import psycopg
import pytest

from aqil_research.adapters.fed_sloos.adapter import FedSloosAdapter, FedSloosAdapterConfig
from aqil_research.adapters.fed_sloos.parse import DATASET_ID, SOURCE_ID
from aqil_research.collection.service import collect_registered_adapter
from aqil_research.methods.sloos_cil import SLOOS_CIL_METHOD_ID
from aqil_research.persistence.runs import load_research_run
from aqil_research.workflow.sloos_reading import record_sloos_reading
from db_guard import open_isolated_test_database

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def require_db() -> str:
    return open_isolated_test_database()


def test_a_revised_value_is_a_new_run(require_db: str, tmp_path: Path) -> None:
    moment = datetime(2026, 10, 22, 13, 0, tzinfo=UTC)
    later = datetime(2026, 10, 23, 13, 0, tzinfo=UTC)
    with psycopg.connect(require_db) as conn:
        period = _next_quarter(conn)
        _collect(conn, tmp_path / "first.json", period, "11.8", "2026-08-03", moment)
        original = record_sloos_reading(conn, decision_at=moment)
        again = record_sloos_reading(conn, decision_at=later)
        _collect(conn, tmp_path / "revised.json", period, "12.4", "2026-10-22", later)
        revised = record_sloos_reading(conn, decision_at=later)
        assert original.run_id is not None
        assert revised.run_id is not None
        first = load_research_run(conn, original.run_id)
        second = load_research_run(conn, revised.run_id)
        stored = conn.execute(
            """
            select count(*)
            from research.research_runs
            where method_id = %s and run_id = %s
            """,
            (SLOOS_CIL_METHOD_ID, original.run_id),
        ).fetchone()
    assert original.status == "completed"
    assert again.status == "unchanged"
    assert again.run_id == original.run_id
    assert revised.status == "completed"
    assert revised.run_id != original.run_id
    assert first.observation_ids != second.observation_ids
    assert first.analytical_payload_hash != second.analytical_payload_hash
    assert first.publication_allowed is False
    assert second.publication_allowed is False
    assert second.investment_implication == "no_action"
    assert stored == (1,)


def _next_quarter(conn: psycopg.Connection) -> str:
    row = conn.execute(
        """
        select max(period_start)
        from research.economic_observations
        where dataset_id = %s
        """,
        (DATASET_ID,),
    ).fetchone()
    start = row[0] if row else None
    if start is None:
        return "2090-Q1"
    month = start.month + 3
    year = start.year
    if month > 12:
        month -= 12
        year += 1
    quarter = ((month - 1) // 3) + 1
    return f"{year}-Q{quarter}"


def _collect(
    conn: psycopg.Connection,
    path: Path,
    period: str,
    value: str,
    vintage: str,
    moment: datetime,
) -> None:
    path.write_text(
        json.dumps(
            {
                "series_id": "SUBLPDCILS_N.Q",
                "observations": [
                    {"period": period, "value": value, "vintage": vintage},
                ],
            },
        ),
        encoding="utf-8",
    )
    result, _store = collect_registered_adapter(
        store_backend="postgres",
        adapter=FedSloosAdapter(
            config=FedSloosAdapterConfig(live=False, fixture_path=path),
            retrieved_at=moment,
        ),
        source_id=SOURCE_ID,
        collected_at=moment,
        live=False,
        conn=conn,
    )
    assert result.outcome in {"success", "unchanged"}
