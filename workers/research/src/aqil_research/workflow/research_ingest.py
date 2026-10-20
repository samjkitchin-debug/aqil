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


def _invoke_optional_bls_publication_ingest(
    conn: psycopg.Connection,
    *,
    live: bool,
    fixture_path: str | None,
    collected_at: datetime,
) -> tuple[bool, str | None]:
    """Hook for `collect_bls_releases` when the publication adapter branch merges.

    If `aqil_research.collection.publications` is absent, this is a no-op and series
    ingest still succeeds.
    """
    try:
        from aqil_research.collection.publications import collect_bls_releases
    except ImportError:
        return False, None
    result = collect_bls_releases(
        conn=conn,
        live=live,
        fixture_path=fixture_path,
        collected_at=collected_at,
    )
    outcome = getattr(result, "outcome", None)
    return True, str(outcome) if outcome is not None else "completed"


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
    )
