"""Rights-checked forward calendar collection."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path

import httpx
import psycopg

from aqil_research.forward.adapters.bls_release_schedule import (
    DATASET_ID as BLS_DATASET_ID,
)
from aqil_research.forward.adapters.bls_release_schedule import (
    SOURCE_ID as BLS_SOURCE_ID,
)
from aqil_research.forward.adapters.bls_release_schedule import (
    SOURCE_LOCATOR as BLS_LOCATOR,
)
from aqil_research.forward.adapters.bls_release_schedule import (
    parse_empsit_schedule_html,
    release_event_id,
    release_to_catalyst_payload,
)
from aqil_research.forward.adapters.fed_fomc_calendar import (
    DATASET_ID as FED_DATASET_ID,
)
from aqil_research.forward.adapters.fed_fomc_calendar import (
    SOURCE_ID as FED_SOURCE_ID,
)
from aqil_research.forward.adapters.fed_fomc_calendar import (
    SOURCE_LOCATOR as FED_LOCATOR,
)
from aqil_research.forward.adapters.fed_fomc_calendar import (
    meeting_event_id,
    meeting_to_catalyst_payload,
    parse_fomc_calendar_html,
)
from aqil_research.forward.catalyst_store import upsert_catalyst_event
from aqil_research.forward.schedule_rights import assert_schedule_ingest
from aqil_research.sources.rights import find_source_rights, load_source_rights
from aqil_research.sources.rights_gate import RightsGateError


@dataclass(frozen=True, slots=True)
class ForwardCollectionResult:
    source_id: str
    dataset_id: str
    outcome: str
    collection_mode: str
    records_received: int
    records_new: int
    records_updated: int
    records_unchanged: int
    error_summary: str | None = None


def _record_run(
    conn: psycopg.Connection,
    result: ForwardCollectionResult,
    *,
    started_at: datetime,
    finished_at: datetime,
    rights_record_id: str,
    source_locator: str | None,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            insert into forward.collection_runs (
              source_id, dataset_id, collection_mode, started_at, finished_at, outcome,
              records_received, records_new, records_updated, records_unchanged,
              rights_record_id, source_locator, error_summary
            )
            values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                result.source_id,
                result.dataset_id,
                result.collection_mode,
                started_at,
                finished_at,
                result.outcome,
                result.records_received,
                result.records_new,
                result.records_updated,
                result.records_unchanged,
                rights_record_id,
                source_locator,
                result.error_summary,
            ),
        )


def _fetch_html(url: str, *, fixture_path: Path | None) -> str:
    if fixture_path is not None:
        return fixture_path.read_text(encoding="utf-8")
    response = httpx.get(url, timeout=30.0, follow_redirects=True)
    response.raise_for_status()
    return response.text


def collect_fed_fomc_calendar(
    conn: psycopg.Connection,
    *,
    live: bool,
    fixture_path: Path | None,
    horizon_start: date | None = None,
    horizon_end: date | None = None,
) -> ForwardCollectionResult:
    started = datetime.now(tz=UTC)
    mode = "live" if live else "fixture"
    rights_records = load_source_rights()
    rights = find_source_rights(rights_records, source_id=FED_SOURCE_ID)
    if rights is None:
        finished = datetime.now(tz=UTC)
        result = ForwardCollectionResult(
            source_id=FED_SOURCE_ID,
            dataset_id=FED_DATASET_ID,
            outcome="failed_rights",
            collection_mode=mode,
            records_received=0,
            records_new=0,
            records_updated=0,
            records_unchanged=0,
            error_summary="source not in register",
        )
        _record_run(
            conn,
            result,
            started_at=started,
            finished_at=finished,
            rights_record_id=FED_SOURCE_ID,
            source_locator=FED_LOCATOR,
        )
        return result

    try:
        assert_schedule_ingest(
            rights,
            source_id=FED_SOURCE_ID,
            dataset_id=FED_DATASET_ID,
        )
    except RightsGateError as exc:
        finished = datetime.now(tz=UTC)
        result = ForwardCollectionResult(
            source_id=FED_SOURCE_ID,
            dataset_id=FED_DATASET_ID,
            outcome="failed_rights",
            collection_mode=mode,
            records_received=0,
            records_new=0,
            records_updated=0,
            records_unchanged=0,
            error_summary=str(exc),
        )
        _record_run(
            conn,
            result,
            started_at=started,
            finished_at=finished,
            rights_record_id=rights.source_id,
            source_locator=FED_LOCATOR,
        )
        return result

    try:
        html = _fetch_html(FED_LOCATOR, fixture_path=fixture_path if not live else None)
    except Exception as exc:
        finished = datetime.now(tz=UTC)
        result = ForwardCollectionResult(
            source_id=FED_SOURCE_ID,
            dataset_id=FED_DATASET_ID,
            outcome="failed_fetch",
            collection_mode=mode,
            records_received=0,
            records_new=0,
            records_updated=0,
            records_unchanged=0,
            error_summary=str(exc),
        )
        _record_run(
            conn,
            result,
            started_at=started,
            finished_at=finished,
            rights_record_id=rights.source_id,
            source_locator=FED_LOCATOR,
        )
        return result

    today = horizon_start or date.today()
    end = horizon_end or date(today.year + 1, 12, 31)
    meetings = parse_fomc_calendar_html(html, min_year=today.year, max_year=end.year)
    meetings = [m for m in meetings if today <= _meeting_end(m) <= end]

    retrieved_at = datetime.now(tz=UTC)
    new = updated = unchanged = 0
    for meeting in meetings:
        payload = meeting_to_catalyst_payload(meeting, retrieved_at=retrieved_at)
        status = upsert_catalyst_event(
            conn, meeting_event_id(meeting), payload, observed_at=retrieved_at
        )
        if status == "new":
            new += 1
        elif status == "updated":
            updated += 1
        else:
            unchanged += 1

    finished = datetime.now(tz=UTC)
    result = ForwardCollectionResult(
        source_id=FED_SOURCE_ID,
        dataset_id=FED_DATASET_ID,
        outcome="completed",
        collection_mode=mode,
        records_received=len(meetings),
        records_new=new,
        records_updated=updated,
        records_unchanged=unchanged,
    )
    _record_run(
        conn,
        result,
        started_at=started,
        finished_at=finished,
        rights_record_id=rights.source_id,
        source_locator=FED_LOCATOR,
    )
    return result


def _meeting_end(meeting: object) -> date:
    from aqil_research.forward.adapters.fed_fomc_calendar import FomcMeeting

    if not isinstance(meeting, FomcMeeting):
        raise TypeError("expected FomcMeeting")
    return date(meeting.year, meeting.month, meeting.end_day)


def collect_bls_empsit_schedule(
    conn: psycopg.Connection,
    *,
    live: bool,
    fixture_path: Path | None,
    horizon_start: date | None = None,
    horizon_end: date | None = None,
) -> ForwardCollectionResult:
    started = datetime.now(tz=UTC)
    mode = "live" if live else "fixture"
    rights_records = load_source_rights()
    rights = find_source_rights(rights_records, source_id=BLS_SOURCE_ID)
    if rights is None:
        finished = datetime.now(tz=UTC)
        result = ForwardCollectionResult(
            source_id=BLS_SOURCE_ID,
            dataset_id=BLS_DATASET_ID,
            outcome="failed_rights",
            collection_mode=mode,
            records_received=0,
            records_new=0,
            records_updated=0,
            records_unchanged=0,
            error_summary="source not in register",
        )
        _record_run(
            conn,
            result,
            started_at=started,
            finished_at=finished,
            rights_record_id=BLS_SOURCE_ID,
            source_locator=BLS_LOCATOR,
        )
        return result

    try:
        assert_schedule_ingest(
            rights,
            source_id=BLS_SOURCE_ID,
            dataset_id=BLS_DATASET_ID,
        )
    except RightsGateError as exc:
        finished = datetime.now(tz=UTC)
        result = ForwardCollectionResult(
            source_id=BLS_SOURCE_ID,
            dataset_id=BLS_DATASET_ID,
            outcome="failed_rights",
            collection_mode=mode,
            records_received=0,
            records_new=0,
            records_updated=0,
            records_unchanged=0,
            error_summary=str(exc),
        )
        _record_run(
            conn,
            result,
            started_at=started,
            finished_at=finished,
            rights_record_id=rights.source_id,
            source_locator=BLS_LOCATOR,
        )
        return result

    try:
        html = _fetch_html(BLS_LOCATOR, fixture_path=fixture_path if not live else None)
    except Exception as exc:
        finished = datetime.now(tz=UTC)
        result = ForwardCollectionResult(
            source_id=BLS_SOURCE_ID,
            dataset_id=BLS_DATASET_ID,
            outcome="failed_fetch",
            collection_mode=mode,
            records_received=0,
            records_new=0,
            records_updated=0,
            records_unchanged=0,
            error_summary=str(exc),
        )
        _record_run(
            conn,
            result,
            started_at=started,
            finished_at=finished,
            rights_record_id=rights.source_id,
            source_locator=BLS_LOCATOR,
        )
        return result

    today = horizon_start or date.today()
    end = horizon_end or date(today.year + 1, 12, 31)
    releases = parse_empsit_schedule_html(html)
    releases = [r for r in releases if today <= r.release_date <= end]

    retrieved_at = datetime.now(tz=UTC)
    new = updated = unchanged = 0
    for release in releases:
        payload = release_to_catalyst_payload(release, retrieved_at=retrieved_at)
        status = upsert_catalyst_event(
            conn, release_event_id(release), payload, observed_at=retrieved_at
        )
        if status == "new":
            new += 1
        elif status == "updated":
            updated += 1
        else:
            unchanged += 1

    finished = datetime.now(tz=UTC)
    result = ForwardCollectionResult(
        source_id=BLS_SOURCE_ID,
        dataset_id=BLS_DATASET_ID,
        outcome="completed",
        collection_mode=mode,
        records_received=len(releases),
        records_new=new,
        records_updated=updated,
        records_unchanged=unchanged,
    )
    _record_run(
        conn,
        result,
        started_at=started,
        finished_at=finished,
        rights_record_id=rights.source_id,
        source_locator=BLS_LOCATOR,
    )
    return result
