"""One local refresh of the registered live sources.

Run `npm run research:refresh` when a person wants a new poll. This command
does not install a Windows task or a production schedule.

Cadence, when the command is used:
- Employment Situation publications: daily
- Federal Reserve monetary-policy press: daily
- BLS release calendar: daily
- Unemployment series: weekly, and skipped when a live retrieval is newer

Each source uses its own database transaction. A failure is recorded and the
other sources still run. A second overlapping refresh does not write.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import psycopg

from aqil_research.persistence.connection import research_connection

LOCK_KEY = 410221001
SERIES_INTERVAL = timedelta(days=7)

CADENCE = {
    "bls_employment_situation_archive": "daily",
    "federal_reserve_monetary_press": "daily",
    "bls_ics_schedule": "daily",
    "bls_cps_unemployment_rate": "weekly",
}


@dataclass(frozen=True, slots=True)
class SourceRefreshResult:
    source_id: str
    outcome: str
    inserted: int = 0
    unchanged: int = 0
    detail: str = ""


@dataclass(frozen=True, slots=True)
class RefreshReport:
    started_at: datetime
    overlapped: bool
    sources: tuple[SourceRefreshResult, ...]


def series_is_due(last_success: datetime | None, now: datetime) -> bool:
    if last_success is None:
        return True
    return now - last_success >= SERIES_INTERVAL


def run_registered_refresh(
    *,
    collected_at: datetime | None = None,
    include_series: bool = True,
) -> RefreshReport:
    """Poll each registered live source once, under one advisory lock."""
    now = collected_at or datetime.now(tz=UTC)
    with research_connection() as lock_conn:
        if not _try_lock(lock_conn):
            return RefreshReport(now, True, ())
        try:
            results = (
                _run_one(now, "bls_employment_situation_archive", _refresh_bls_publications),
                _run_one(now, "federal_reserve_monetary_press", _refresh_fed_press),
                _run_one(now, "bls_ics_schedule", _refresh_bls_calendar),
            )
            series = (
                _run_one(now, "bls_cps_unemployment_rate", _refresh_series)
                if include_series
                else SourceRefreshResult("bls_cps_unemployment_rate", "not_requested")
            )
            report = RefreshReport(now, False, (*results, series))
            _record(report)
            return report
        finally:
            _unlock(lock_conn)


def _run_one(
    now: datetime,
    source_id: str,
    action: Callable[[datetime], SourceRefreshResult],
) -> SourceRefreshResult:
    try:
        return action(now)
    except Exception as exc:
        return SourceRefreshResult(source_id, "failed", detail=type(exc).__name__)


def _refresh_bls_publications(now: datetime) -> SourceRefreshResult:
    from aqil_research.adapters.bls_release import PostgresSourcedUpdateStore, collect_bls_releases

    with research_connection() as conn:
        result = collect_bls_releases(
            PostgresSourcedUpdateStore(conn),
            live=True,
            retrieved_at=now,
        )
    return SourceRefreshResult(
        "bls_employment_situation_archive",
        str(result.outcome),
        inserted=result.updates_newly_stored,
        unchanged=result.updates_unchanged,
    )


def _refresh_fed_press(now: datetime) -> SourceRefreshResult:
    from aqil_research.adapters.fed_press.collect import collect_fed_monetary_press

    with research_connection() as conn:
        result = collect_fed_monetary_press(conn, live=True, retrieved_at=now)
    return SourceRefreshResult(
        "federal_reserve_monetary_press",
        result.outcome,
        inserted=result.inserted,
        unchanged=result.unchanged,
    )


def _refresh_bls_calendar(now: datetime) -> SourceRefreshResult:
    from aqil_research.forward.collect_bls_calendar import collect_bls_release_calendar

    with research_connection() as conn:
        result = collect_bls_release_calendar(conn, live=True, retrieved_at=now)
    return SourceRefreshResult(
        "bls_ics_schedule",
        result.outcome,
        inserted=result.stored_new,
        unchanged=result.unchanged,
    )


def _refresh_series(now: datetime) -> SourceRefreshResult:
    last_success = _latest_live_retrieval("bls_cps_unemployment_rate")
    if not series_is_due(last_success, now):
        return SourceRefreshResult(
            "bls_cps_unemployment_rate",
            "skipped_fresh",
            detail="last live retrieval is inside the weekly interval",
        )
    from aqil_research.collection.service import collect_bls_unemployment

    with research_connection() as conn:
        result, _store = collect_bls_unemployment(
            store_backend="postgres",
            collected_at=now,
            live=True,
            conn=conn,
        )
    return SourceRefreshResult("bls_cps_unemployment_rate", str(result.outcome))


def _latest_live_retrieval(source_id: str) -> datetime | None:
    with research_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select max(retrieved_at)
                from research.source_retrievals
                where source_id = %s and collection_mode = 'live'
                """,
                (source_id,),
            )
            row = cur.fetchone()
    if row is None or row[0] is None:
        return None
    value = row[0]
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _record(report: RefreshReport) -> None:
    with research_connection() as conn:
        with conn.cursor() as cur:
            for source in report.sources:
                cur.execute(
                    """
                    insert into research.refresh_runs (
                      started_at, finished_at, source_id, outcome, detail,
                      inserted_count, unchanged_count
                    )
                    values (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        report.started_at,
                        datetime.now(tz=UTC),
                        source.source_id,
                        source.outcome,
                        source.detail,
                        source.inserted,
                        source.unchanged,
                    ),
                )


def _try_lock(conn: psycopg.Connection) -> bool:
    with conn.cursor() as cur:
        cur.execute("select pg_try_advisory_lock(%s)", (LOCK_KEY,))
        row = cur.fetchone()
    return bool(row and row[0])


def _unlock(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute("select pg_advisory_unlock(%s)", (LOCK_KEY,))
