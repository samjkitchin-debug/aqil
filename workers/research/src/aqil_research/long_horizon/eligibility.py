"""Conservative next-eligible-session rule.

A source_release_at value at midnight UTC is an identity anchor. It is not an
observed publication time. The category C pilot does not apply this rule,
because that pilot does not use a macroeconomic vintage. The stored
observation-availability selector is unchanged.
"""

from __future__ import annotations

from datetime import date, datetime


def printed_release_date(source_release_at: datetime) -> date:
    """Calendar date of an identity anchor. The clock time is not observed."""
    return source_release_at.date()


def next_eligible_session(
    printed_release: date,
    sessions: list[date] | tuple[date, ...],
) -> date | None:
    """First stored session strictly after the printed release date.

    The printed date itself is not eligible, even when that date is a stored
    session. A later session that is not in the stored list is not invented.
    None means the decision is blocked.
    """
    later = [session for session in sessions if session > printed_release]
    if not later:
        return None
    return min(later)
