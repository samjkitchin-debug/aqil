"""Collect confirmed future dates from the official BLS release calendar."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import psycopg

from aqil_research.forward.adapters.bls_ics_schedule import SOURCE_ID, parse_bls_ics
from aqil_research.forward.ics_client import BlsCalendarClientError, fetch_bls_ics
from aqil_research.forward.verified_schedule_store import (
    insert_calendar_retrieval,
    upsert_verified_release,
)
from aqil_research.sources.rights import (
    RightsOperation,
    find_source_rights,
    load_source_rights,
    source_usable,
)


@dataclass(frozen=True, slots=True)
class CalendarCollectResult:
    outcome: str
    received: int
    stored_new: int
    unchanged: int
    revised: int
    omitted_unconfirmed: int
    omitted_past: int


def collect_bls_release_calendar(
    conn: psycopg.Connection,
    *,
    live: bool,
    retrieved_at: datetime,
    fixture_path: Path | None = None,
) -> CalendarCollectResult:
    rights = find_source_rights(load_source_rights(), source_id=SOURCE_ID)
    if rights is None or not source_usable(rights, RightsOperation.AUTOMATED_ACCESS):
        return CalendarCollectResult("failed_rights", 0, 0, 0, 0, 0, 0)

    try:
        text, http_status = fetch_bls_ics(live=live, fixture_path=fixture_path)
    except (BlsCalendarClientError, OSError):
        return CalendarCollectResult("failed_fetch", 0, 0, 0, 0, 0, 0)

    releases = parse_bls_ics(text)
    omitted_unconfirmed = 0
    omitted_past = 0
    stored_new = 0
    unchanged = 0
    revised = 0
    notes: list[str] = []
    for release in releases:
        confirmed = (
            release.stamp_basis in {"utc", "us-eastern"} and release.status.upper() == "CONFIRMED"
        )
        if not confirmed:
            omitted_unconfirmed += 1
            continue
        if release.starts_at <= retrieved_at:
            omitted_past += 1
            continue
        kind = upsert_verified_release(conn, release, retrieved_at=retrieved_at)
        if kind == "new":
            stored_new += 1
        elif kind == "revised":
            revised += 1
        else:
            unchanged += 1

    if omitted_unconfirmed:
        notes.append(
            f"{omitted_unconfirmed} calendar entries had no stated clock time or were not confirmed"
        )
    insert_calendar_retrieval(
        conn,
        rights=rights,
        retrieved_at=retrieved_at,
        collection_mode="live" if live else "fixture",
        http_status=http_status,
        response_byte_count=len(text.encode("utf-8")),
        ingest_notes=notes,
    )
    return CalendarCollectResult(
        outcome="completed",
        received=len(releases),
        stored_new=stored_new,
        unchanged=unchanged,
        revised=revised,
        omitted_unconfirmed=omitted_unconfirmed,
        omitted_past=omitted_past,
    )
