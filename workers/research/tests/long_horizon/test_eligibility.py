"""Next-eligible-session rule. The pilot does not apply it to a BEA decision."""

from __future__ import annotations

from datetime import UTC, date, datetime

from aqil_research.long_horizon.eligibility import (
    next_eligible_session,
    printed_release_date,
)

FRIDAY = date(2024, 1, 5)
MONDAY = date(2024, 1, 8)
SESSIONS = (FRIDAY, MONDAY)


def test_printed_date_is_not_eligible_even_when_it_is_a_session() -> None:
    assert next_eligible_session(FRIDAY, SESSIONS) == MONDAY


def test_a_weekend_release_uses_the_next_stored_session() -> None:
    assert next_eligible_session(date(2024, 1, 6), SESSIONS) == MONDAY


def test_no_later_session_blocks_instead_of_inventing_one() -> None:
    assert next_eligible_session(MONDAY, SESSIONS) is None


def test_midnight_utc_is_only_the_printed_calendar_date() -> None:
    anchor = datetime(2024, 1, 5, 0, 0, tzinfo=UTC)
    assert printed_release_date(anchor) == FRIDAY
    assert next_eligible_session(printed_release_date(anchor), SESSIONS) == MONDAY
