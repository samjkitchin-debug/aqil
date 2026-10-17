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


def _fetch_html(
    url: str,
    *,
    fixture_path: Path | None,
    headers: dict[str, str] | None = None,
) -> str:
    if fixture_path is not None:
        return fixture_path.read_text(encoding="utf-8")
    request_headers = {
        "User-Agent": "AqilResearch/1.0 (calendar collector; local operator)",
    }
    if headers:
        request_headers.update(headers)
    response = httpx.get(url, timeout=30.0, follow_redirects=True, headers=request_headers)
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


def collect_bls_ics_schedule(
    conn: psycopg.Connection,
    *,
    live: bool,
    fixture_path: Path | None,
    horizon_start: date | None = None,
    horizon_end: date | None = None,
) -> ForwardCollectionResult:
    from aqil_research.forward.adapters.bls_ics_schedule import (
        DATASET_ID,
        SOURCE_ID,
        SOURCE_LOCATOR,
        parse_bls_ics,
        release_event_id,
        release_to_catalyst_payload,
    )

    def payloads(body: str, retrieved_at: datetime) -> list[tuple[str, dict[str, object]]]:
        today = horizon_start or date.today()
        end = horizon_end or date(today.year + 1, 12, 31)
        releases = [
            release
            for release in parse_bls_ics(body)
            if today <= release.starts_at.date() <= end
        ]
        return [
            (
                release_event_id(release),
                release_to_catalyst_payload(release, retrieved_at=retrieved_at),
            )
            for release in releases
        ]

    return _collect_text_source(
        conn,
        source_id=SOURCE_ID,
        dataset_id=DATASET_ID,
        source_locator=SOURCE_LOCATOR,
        live=live,
        fixture_path=fixture_path,
        build_payloads=payloads,
    )


def collect_bea_schedule(
    conn: psycopg.Connection,
    *,
    live: bool,
    fixture_path: Path | None,
    horizon_start: date | None = None,
    horizon_end: date | None = None,
) -> ForwardCollectionResult:
    from aqil_research.forward.adapters.bea_release_schedule import (
        DATASET_ID,
        SOURCE_ID,
        SOURCE_LOCATOR,
        parse_bea_schedule_html,
        release_event_id,
        release_to_catalyst_payload,
    )

    def payloads(body: str, retrieved_at: datetime) -> list[tuple[str, dict[str, object]]]:
        today = horizon_start or date.today()
        end = horizon_end or date(today.year + 1, 12, 31)
        releases = [
            release
            for year in range(today.year, end.year + 1)
            for release in parse_bea_schedule_html(body, year=year)
            if today <= release.release_date <= end
        ]
        return [
            (
                release_event_id(release),
                release_to_catalyst_payload(release, retrieved_at=retrieved_at),
            )
            for release in releases
        ]

    return _collect_text_source(
        conn,
        source_id=SOURCE_ID,
        dataset_id=DATASET_ID,
        source_locator=SOURCE_LOCATOR,
        live=live,
        fixture_path=fixture_path,
        build_payloads=payloads,
    )


def collect_sec_completed_filings(
    conn: psycopg.Connection,
    *,
    live: bool,
    fixture_path: Path | None,
    companyfacts_path: Path | None = None,
    cik: str = "0000789019",
) -> ForwardCollectionResult:
    import json

    from aqil_research.forward.adapters.sec_edgar_filings import (
        DATASET_ID,
        FAIR_ACCESS_MIN_INTERVAL_SECONDS,
        SOURCE_ID,
        SOURCE_LOCATOR,
        SecFairAccessError,
        filing_event_id,
        filing_to_catalyst_payload,
        latest_reported_period_end,
        parse_submissions,
        sec_user_agent,
    )

    started = datetime.now(tz=UTC)
    mode = "live" if live else "fixture"
    rights = _rights_or_fail(
        conn,
        source_id=SOURCE_ID,
        dataset_id=DATASET_ID,
        source_locator=SOURCE_LOCATOR.format(cik=cik),
        mode=mode,
        started=started,
    )
    if isinstance(rights, ForwardCollectionResult):
        return rights

    try:
        if live:
            import time

            headers = {"User-Agent": sec_user_agent(), "Accept": "application/json"}
            submissions_url = SOURCE_LOCATOR.format(cik=cik)
            body = _fetch_html(submissions_url, fixture_path=None, headers=headers)
            time.sleep(FAIR_ACCESS_MIN_INTERVAL_SECONDS)
            facts_url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
            facts_body = _fetch_html(facts_url, fixture_path=None, headers=headers)
        else:
            if fixture_path is None:
                raise ValueError("SEC fixture collection requires --fixture")
            body = fixture_path.read_text(encoding="utf-8")
            facts_body = (
                companyfacts_path.read_text(encoding="utf-8") if companyfacts_path else "{}"
            )
        document = json.loads(body)
        facts = json.loads(facts_body)
    except (OSError, ValueError, SecFairAccessError, httpx.HTTPError) as exc:
        return _fail(
            conn,
            source_id=SOURCE_ID,
            dataset_id=DATASET_ID,
            source_locator=SOURCE_LOCATOR.format(cik=cik),
            mode=mode,
            started=started,
            outcome="failed_fetch",
            error_summary=str(exc),
            rights_record_id=rights.source_id,
        )

    period_end = latest_reported_period_end(facts)
    retrieved_at = datetime.now(tz=UTC)
    filings = parse_submissions(document)
    stored = [
        (
            filing_event_id(filing),
            filing_to_catalyst_payload(
                filing,
                retrieved_at=retrieved_at,
                live=live,
                reported_period_end=period_end,
            ),
        )
        for filing in filings
    ]
    return _store(
        conn,
        source_id=SOURCE_ID,
        dataset_id=DATASET_ID,
        source_locator=SOURCE_LOCATOR.format(cik=cik),
        mode=mode,
        started=started,
        rights_record_id=rights.source_id,
        payloads=stored,
    )


def collect_company_ir_watchlist(
    conn: psycopg.Connection,
    *,
    watchlist_path: Path,
) -> ForwardCollectionResult:
    from aqil_research.forward.adapters.company_ir_watchlist import (
        DATASET_ID,
        SOURCE_ID,
        entry_event_id,
        entry_to_catalyst_payload,
        load_watchlist,
    )

    started = datetime.now(tz=UTC)
    rights = _rights_or_fail(
        conn,
        source_id=SOURCE_ID,
        dataset_id=DATASET_ID,
        source_locator=str(watchlist_path),
        mode="fixture",
        started=started,
    )
    if isinstance(rights, ForwardCollectionResult):
        return rights
    retrieved_at = datetime.now(tz=UTC)
    entries = load_watchlist(watchlist_path)
    stored = [
        (entry_event_id(entry), entry_to_catalyst_payload(entry, retrieved_at=retrieved_at))
        for entry in entries
    ]
    return _store(
        conn,
        source_id=SOURCE_ID,
        dataset_id=DATASET_ID,
        source_locator=str(watchlist_path),
        mode="fixture",
        started=started,
        rights_record_id=rights.source_id,
        payloads=stored,
    )


def _collect_text_source(
    conn: psycopg.Connection,
    *,
    source_id: str,
    dataset_id: str,
    source_locator: str,
    live: bool,
    fixture_path: Path | None,
    build_payloads,
) -> ForwardCollectionResult:
    started = datetime.now(tz=UTC)
    mode = "live" if live else "fixture"
    rights = _rights_or_fail(
        conn,
        source_id=source_id,
        dataset_id=dataset_id,
        source_locator=source_locator,
        mode=mode,
        started=started,
    )
    if isinstance(rights, ForwardCollectionResult):
        return rights
    try:
        body = _fetch_html(source_locator, fixture_path=fixture_path if not live else None)
    except (OSError, httpx.HTTPError) as exc:
        return _fail(
            conn,
            source_id=source_id,
            dataset_id=dataset_id,
            source_locator=source_locator,
            mode=mode,
            started=started,
            outcome="failed_fetch",
            error_summary=str(exc),
            rights_record_id=rights.source_id,
        )
    retrieved_at = datetime.now(tz=UTC)
    return _store(
        conn,
        source_id=source_id,
        dataset_id=dataset_id,
        source_locator=source_locator,
        mode=mode,
        started=started,
        rights_record_id=rights.source_id,
        payloads=build_payloads(body, retrieved_at),
    )


def _rights_or_fail(
    conn: psycopg.Connection,
    *,
    source_id: str,
    dataset_id: str,
    source_locator: str,
    mode: str,
    started: datetime,
):
    rights = find_source_rights(load_source_rights(), source_id=source_id)
    if rights is None:
        return _fail(
            conn,
            source_id=source_id,
            dataset_id=dataset_id,
            source_locator=source_locator,
            mode=mode,
            started=started,
            outcome="failed_rights",
            error_summary="source not in register",
            rights_record_id=source_id,
        )
    try:
        assert_schedule_ingest(rights, source_id=source_id, dataset_id=dataset_id)
    except RightsGateError as exc:
        return _fail(
            conn,
            source_id=source_id,
            dataset_id=dataset_id,
            source_locator=source_locator,
            mode=mode,
            started=started,
            outcome="failed_rights",
            error_summary=str(exc),
            rights_record_id=rights.source_id,
        )
    return rights


def _store(
    conn: psycopg.Connection,
    *,
    source_id: str,
    dataset_id: str,
    source_locator: str,
    mode: str,
    started: datetime,
    rights_record_id: str,
    payloads: list[tuple[str, dict[str, object]]],
) -> ForwardCollectionResult:
    observed_at = datetime.now(tz=UTC)
    new = updated = unchanged = 0
    for event_id, payload in payloads:
        status = upsert_catalyst_event(conn, event_id, payload, observed_at=observed_at)
        if status == "new":
            new += 1
        elif status == "updated":
            updated += 1
        else:
            unchanged += 1
    result = ForwardCollectionResult(
        source_id=source_id,
        dataset_id=dataset_id,
        outcome="completed",
        collection_mode=mode,
        records_received=len(payloads),
        records_new=new,
        records_updated=updated,
        records_unchanged=unchanged,
    )
    _record_run(
        conn,
        result,
        started_at=started,
        finished_at=datetime.now(tz=UTC),
        rights_record_id=rights_record_id,
        source_locator=source_locator,
    )
    return result


def _fail(
    conn: psycopg.Connection,
    *,
    source_id: str,
    dataset_id: str,
    source_locator: str,
    mode: str,
    started: datetime,
    outcome: str,
    error_summary: str,
    rights_record_id: str,
) -> ForwardCollectionResult:
    result = ForwardCollectionResult(
        source_id=source_id,
        dataset_id=dataset_id,
        outcome=outcome,
        collection_mode=mode,
        records_received=0,
        records_new=0,
        records_updated=0,
        records_unchanged=0,
        error_summary=error_summary,
    )
    _record_run(
        conn,
        result,
        started_at=started,
        finished_at=datetime.now(tz=UTC),
        rights_record_id=rights_record_id,
        source_locator=source_locator,
    )
    return result
