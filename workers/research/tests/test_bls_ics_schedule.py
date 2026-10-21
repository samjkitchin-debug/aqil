"""BLS release calendar parsing. Stated times only."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from aqil_research.forward.adapters.bls_ics_schedule import parse_bls_ics

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "forward" / "bls_ics_sample.ics"


def test_zulu_fixture_stays_an_absolute_instant() -> None:
    releases = parse_bls_ics(FIXTURE.read_text(encoding="utf-8"))
    assert len(releases) == 2
    assert releases[0].starts_at == datetime(2008, 4, 4, 12, 30, tzinfo=UTC)
    assert releases[0].stamp_basis == "utc"
    assert releases[0].status == "CONFIRMED"


def test_us_eastern_clock_time_converts_without_guessing_a_date() -> None:
    text = """
BEGIN:VCALENDAR
BEGIN:VEVENT
UID:employment-2025-01
DTSTART;TZID=US-Eastern:20250110T083000
SUMMARY:Employment Situation
END:VEVENT
BEGIN:VEVENT
UID:date-only
DTSTART:20250110
SUMMARY:No clock time
END:VEVENT
BEGIN:VEVENT
UID:unknown-zone
DTSTART;TZID=Mars/Standard:20250110T083000
SUMMARY:Unknown zone
END:VEVENT
END:VCALENDAR
"""
    releases = parse_bls_ics(text)
    assert len(releases) == 1
    assert releases[0].uid == "employment-2025-01"
    assert releases[0].starts_at == datetime(2025, 1, 10, 13, 30, tzinfo=UTC)
    assert releases[0].stamp_basis == "us-eastern"
    assert releases[0].status == "CONFIRMED"
