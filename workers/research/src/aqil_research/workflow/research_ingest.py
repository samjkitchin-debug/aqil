"""Operator ingest: permitted sources into the local research database."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import psycopg

from aqil_research.collection.models import CollectionResult
from aqil_research.collection.service import collect_bls_unemployment
from aqil_research.persistence.connection import research_connection


@dataclass(frozen=True, slots=True)
class ResearchIngestOutcome:
    """Result of one `research:ingest` run (quantitative path always; publications optional)."""

    bls_unemployment: CollectionResult
    publications_attempted: bool
    publications_outcome: str | None = None
    calendar_outcome: str | None = None
    calendar_new: int = 0
    calendar_unchanged: int = 0


def _publication_fixture_for_ingest(live: bool, fixture_path: str | None) -> Path | None:
    """Use the ingest fixture for publications only when it is a feed file."""
    if live:
        return None
    if fixture_path is None:
        return None
    path = Path(fixture_path)
    if path.suffix.lower() not in {".rss", ".xml", ".atom"}:
        return None
    return path


def _invoke_optional_bls_publication_ingest(
    conn: psycopg.Connection,
    *,
    live: bool,
    fixture_path: str | None,
    collected_at: datetime,
) -> tuple[bool, str | None]:
    """Run BLS publication collection when the adapter is present."""
    try:
        from aqil_research.adapters.bls_release import (
            PostgresSourcedUpdateStore,
            collect_bls_releases,
        )
    except ImportError:
        return False, None

    pub_fixture = _publication_fixture_for_ingest(live, fixture_path)
    if not live and pub_fixture is None:
        return False, None

    store = PostgresSourcedUpdateStore(conn)
    result = collect_bls_releases(
        store,
        live=live,
        fixture_path=pub_fixture,
        retrieved_at=collected_at,
    )
    return True, str(result.outcome)


def run_research_ingest(
    *,
    live: bool,
    fixture_path: Path | None = None,
    start_year: int | None = None,
    end_year: int | None = None,
    collected_at: datetime | None = None,
) -> ResearchIngestOutcome:
    """Persist permitted BLS series (live by default for local dev) to PostgreSQL."""
    now = collected_at or datetime.now(tz=UTC)
    fixture_str = str(fixture_path) if fixture_path is not None else None
    pubs_attempted = False
    pubs_outcome: str | None = None

    with research_connection() as conn:
        pubs_attempted, pubs_outcome = _invoke_optional_bls_publication_ingest(
            conn,
            live=live,
            fixture_path=fixture_str,
            collected_at=now,
        )
        calendar = _invoke_bls_calendar(conn, live=live, collected_at=now)
        bls_result, _store = collect_bls_unemployment(
            store_backend="postgres",
            collected_at=now,
            live=live,
            fixture_path=fixture_str,
            start_year=start_year,
            end_year=end_year,
            conn=conn,
        )

    return ResearchIngestOutcome(
        bls_unemployment=bls_result,
        publications_attempted=pubs_attempted,
        publications_outcome=pubs_outcome,
        calendar_outcome=calendar.outcome,
        calendar_new=calendar.stored_new,
        calendar_unchanged=calendar.unchanged,
    )


def _invoke_bls_calendar(
    conn: psycopg.Connection,
    *,
    live: bool,
    collected_at: datetime,
):
    from aqil_research.forward.collect_bls_calendar import (
        CalendarCollectResult,
        collect_bls_release_calendar,
    )

    if not live:
        return CalendarCollectResult("not_attempted", 0, 0, 0, 0, 0, 0)
    return collect_bls_release_calendar(conn, live=True, retrieved_at=collected_at)
