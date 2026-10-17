"""Forward intelligence persistence (local Supabase)."""

from __future__ import annotations

import json
from datetime import UTC, datetime

import psycopg
import pytest

from aqil_research.forward.demo_fixtures import (
    DEMO_ETF_ID,
    DEMO_EVENT_MSFT_EARNINGS,
    DEMO_SCENARIO_ID,
)
from aqil_research.forward.persistence import (
    import_demo_fixture_bundle,
    load_frozen_scenario,
    load_persisted_forward_horizon,
)
from aqil_research.persistence.config import research_database_url_or_local_default
from aqil_research.persistence.connection import research_connection


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


def _counts(conn: psycopg.Connection) -> dict[str, int]:
    tables = (
        "forward.etf_instrument_records",
        "forward.etf_holdings_snapshots",
        "forward.etf_holding_lines",
        "forward.catalyst_events",
        "forward.catalyst_etf_exposure",
        "forward.event_expectations",
        "forward.forward_scenarios",
        "forward.event_outcomes",
    )
    counts: dict[str, int] = {}
    with conn.cursor() as cur:
        for table in tables:
            cur.execute(f"select count(*) from {table}")
            counts[table] = cur.fetchone()[0]
    return counts


def test_repeat_import_keeps_row_counts_and_frozen_identity(require_db: None) -> None:
    first = datetime(2026, 10, 17, 10, 0, tzinfo=UTC)
    second = datetime(2026, 10, 17, 18, 30, tzinfo=UTC)
    with research_connection() as conn:
        import_demo_fixture_bundle(conn, recorded_at=first)
        before = _counts(conn)
        original = load_frozen_scenario(conn, DEMO_SCENARIO_ID)
        import_demo_fixture_bundle(conn, recorded_at=second)
        after = _counts(conn)
        again = load_frozen_scenario(conn, DEMO_SCENARIO_ID)

    assert before == after
    assert before["forward.etf_holdings_snapshots"] >= 1
    assert before["forward.forward_scenarios"] >= 1
    assert again["payload_hash"] == original["payload_hash"]
    assert again["payload"] == original["payload"]
    assert again["frozen_at"] == original["frozen_at"]
    assert again["evidence_class"] == "synthetic_demonstration"


def test_frozen_scenario_survives_later_holdings_and_expectations(require_db: None) -> None:
    with research_connection() as conn:
        import_demo_fixture_bundle(conn, recorded_at=datetime(2026, 10, 17, 10, 0, tzinfo=UTC))
        original = load_frozen_scenario(conn, DEMO_SCENARIO_ID)
        with conn.cursor() as cur:
            cur.execute(
                """
                select snapshot_id::text from forward.catalyst_etf_exposure
                where event_id = %s
                """,
                (DEMO_EVENT_MSFT_EARNINGS,),
            )
            linked_snapshot = cur.fetchone()[0]
            cur.execute(
                """
                insert into forward.etf_holdings_snapshots (
                  etf_id, as_of_date, retrieved_at, completeness, source_id, source_locator,
                  payload, content_hash, evidence_class
                )
                values (
                  %s, '2025-09-30', timestamptz '2026-10-18 00:00:00+00',
                  'top_holdings_partial', 'fixture_vwra_holdings_v1',
                  'synthetic://aqil/demo/vwra-holdings-revised',
                  '{"evidence_class":"synthetic_demonstration","note":"revised snapshot"}'::jsonb,
                  'revised-demonstration-hash', 'synthetic_demonstration'
                )
                on conflict (etf_id, as_of_date, source_id, content_hash) do nothing
                """,
                (DEMO_ETF_ID,),
            )
            cur.execute(
                """
                insert into forward.event_expectations (
                  event_id, recorded_at, payload, content_hash, source_id, evidence_class
                )
                values (
                  %s, timestamptz '2026-10-18 00:00:00+00',
                  '{"evidence_class":"synthetic_demonstration","note":"later expectation"}'::jsonb,
                  'later-expectation-hash', 'fixture_later_expectation', 'synthetic_demonstration'
                )
                on conflict (event_id, source_id, content_hash) do nothing
                """,
                (DEMO_EVENT_MSFT_EARNINGS,),
            )
            cur.execute(
                "select count(*) from forward.etf_holdings_snapshots where etf_id = %s",
                (DEMO_ETF_ID,),
            )
            snapshot_count = cur.fetchone()[0]
        survived = load_frozen_scenario(conn, DEMO_SCENARIO_ID)
        horizon = load_persisted_forward_horizon(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                select scenario_id::text from forward.event_outcomes
                where scenario_id = %s
                """,
                (DEMO_SCENARIO_ID,),
            )
            outcome_scenario = cur.fetchone()[0]
            update_sql = (
                "update forward.forward_scenarios set payload = '{}'::jsonb where scenario_id = %s"
            )
            with pytest.raises(psycopg.Error) as exc_info:
                cur.execute(update_sql, (DEMO_SCENARIO_ID,))
            assert exc_info.value.sqlstate in ("42501", "P0001")
            conn.rollback()

    assert snapshot_count >= 2
    assert survived["payload_hash"] == original["payload_hash"]
    assert survived["payload"] == original["payload"]
    assert horizon["scenarios"][0]["record_source"] == "database"
    assert horizon["scenarios"][0]["scenario_id"] == str(DEMO_SCENARIO_ID)
    assert horizon["scenarios"][0]["headline"] == original["payload"]["headline"]
    assert horizon["outcomes"][0]["scenario_id"] == str(DEMO_SCENARIO_ID)
    assert outcome_scenario == str(DEMO_SCENARIO_ID)
    assert linked_snapshot
    assert "synthetic demonstration" in horizon["etfs"][0]["holdings_caveat"].lower()
    assert json.dumps(survived["payload"]) == json.dumps(original["payload"])
