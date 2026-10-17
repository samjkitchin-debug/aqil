"""Verified macro calendar → frozen assessment → horizon export (integration)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import psycopg
import pytest

from aqil_research.forward.collection.service import collect_fed_fomc_calendar
from aqil_research.forward.horizon_export import build_horizon_from_database
from aqil_research.forward.intelligence.macro_assessment import freeze_macro_pre_event_assessments
from aqil_research.persistence.config import research_database_url_or_local_default
from aqil_research.persistence.connection import research_connection

FIXTURES = Path(__file__).parent / "fixtures" / "forward"
FED_FIXTURE = FIXTURES / "fed_fomc_calendar_snippet.html"


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


def test_macro_vertical_slice_collect_freeze_export(require_db: None) -> None:
    horizon_start = date(2026, 1, 1)
    horizon_end = date(2027, 12, 31)
    with research_connection() as conn:
        fed = collect_fed_fomc_calendar(
            conn,
            live=False,
            fixture_path=FED_FIXTURE,
            horizon_start=horizon_start,
            horizon_end=horizon_end,
        )
        assert fed.outcome == "completed"
        new_frozen, existing = freeze_macro_pre_event_assessments(conn)
        assert new_frozen + existing >= 1
        bundle = build_horizon_from_database(
            conn,
            reference_date=horizon_start,
            horizon_days=365,
            include_demonstration=False,
        )

    assert bundle["data_mode"] == "verified_source"
    assert bundle["events"]
    macro_events = [
        event
        for event in bundle["events"]
        if event.get("category") == "central_bank_meeting" and not event.get("is_fixture")
    ]
    assert macro_events
    scenarios = bundle.get("scenarios") or []
    assert scenarios
    assessment = next(
        (row for row in scenarios if row.get("evidence_class") == "research_assessment"),
        None,
    )
    assert assessment is not None
    assert assessment.get("record_source") == "database"
    assert assessment.get("expected_information")
    assert assessment.get("no_action_conclusion")
    event_ids = {event["event_id"] for event in bundle["events"] if not event.get("is_fixture")}
    assert assessment["event_id"] in event_ids
    assert any(
        event["event_id"] == assessment["event_id"] and event.get("category") == "central_bank_meeting"
        for event in bundle["events"]
    ) or any(
        event["event_id"] == assessment["event_id"]
        and event.get("category") == "us_employment_report"
        for event in bundle["events"]
    )
