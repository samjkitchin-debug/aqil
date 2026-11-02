"""One daily research cycle.

Sources run inside their own error boundary. A failed source or method does
not stop the others. ``--refit`` is never implied. Results are appended.
A missed UTC day is visible from the last cycle start, whether or not a
scheduler fired.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from uuid import uuid4

import psycopg
from psycopg.pq import TransactionStatus

from aqil_research.adapters.source_registry import (
    InvalidObservationUnit,
    RightsBlocked,
    SourceConnector,
    TransientSourceError,
)
from aqil_research.methods.protocol import AnalyticalMethod
from aqil_research.methods.registry import MethodRegistry
from aqil_research.vintages.store import AppendResult, ObservationStore
from aqil_research.workflow.refresh import LOCK_KEY, SourceRefreshResult

ExecuteMethod = Callable[[psycopg.Connection, str, MethodRegistry], str]
Sleep = Callable[[], None]


@dataclass(frozen=True, slots=True)
class CycleEvent:
    phase: str
    subject_id: str
    outcome: str
    detail: str = ""


@dataclass(slots=True)
class CycleReport:
    cycle_id: str
    started_at: datetime
    finished_at: datetime | None
    status: str
    overlapped: bool
    events: tuple[CycleEvent, ...] = ()
    missed: bool = False


@dataclass(slots=True)
class _Draft:
    events: list[CycleEvent] = field(default_factory=list)

    def add(self, phase: str, subject_id: str, outcome: str, detail: str = "") -> None:
        self.events.append(CycleEvent(phase, subject_id, outcome, detail))


def schedule_is_missed(last_started_at: datetime | None, now: datetime) -> bool:
    """True when no cycle has started on this UTC day."""
    if last_started_at is None:
        return True
    started = (
        last_started_at
        if last_started_at.tzinfo is not None
        else last_started_at.replace(tzinfo=UTC)
    )
    current = now if now.tzinfo is not None else now.replace(tzinfo=UTC)
    return started.astimezone(UTC).date() < current.astimezone(UTC).date()


def latest_cycle_start(conn: psycopg.Connection) -> datetime | None:
    row = conn.execute(
        """
        select max(started_at)
        from research.research_cycles
        where status <> 'overlapped'
        """
    ).fetchone()
    if row is None or row[0] is None:
        return None
    value = row[0]
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def run_daily_cycle(
    conn: psycopg.Connection,
    *,
    now: datetime,
    connectors: tuple[SourceConnector, ...],
    registry: MethodRegistry,
    store: ObservationStore,
    execute: ExecuteMethod,
    sleep: Sleep | None = None,
    transient_attempts: int = 3,
    available_datasets: Callable[[], set[str]] | None = None,
) -> CycleReport:
    """Run one cycle on this connection. An overlapping caller does not write."""
    current = now if now.tzinfo is not None else now.replace(tzinfo=UTC)
    if not _try_lock(conn):
        return CycleReport(str(uuid4()), current, current, "overlapped", True, missed=False)
    try:
        missed = schedule_is_missed(latest_cycle_start(conn), current)
        cycle_id = str(uuid4())
        draft = _Draft()
        if missed:
            draft.add("schedule", "daily", "missed", "the last cycle start is before this UTC day")
        changed: set[str] = set()
        source_failed = False
        for connector in connectors:
            identity = connector.identity()
            if not identity.enabled:
                draft.add("source", identity.source_id, "skipped", "disabled")
                continue
            outcome, detail, datasets = _run_source(
                connector,
                current,
                store,
                sleep or (lambda: None),
                transient_attempts,
            )
            if outcome == "failed":
                source_failed = True
            if outcome in {"inserted", "revised"}:
                changed.update(datasets)
                draft.add("source", identity.source_id, "success", detail or outcome)
            else:
                draft.add("source", identity.source_id, outcome, detail)
        present = available_datasets() if available_datasets is not None else _datasets(store)
        method_failed = False
        for method in registry.enabled():
            outcome, detail = _run_method(conn, method, registry, present, changed, execute)
            if outcome == "failed":
                method_failed = True
            draft.add("method", method.method_id, outcome, detail)
        status = "partial" if source_failed or method_failed else "completed"
        finished = current
        _persist(conn, cycle_id, current, finished, status, draft.events)
        return CycleReport(
            cycle_id,
            current,
            finished,
            status,
            False,
            tuple(draft.events),
            missed,
        )
    finally:
        if conn.info.transaction_status == TransactionStatus.INERROR:
            conn.rollback()
        _unlock(conn)


def _run_source(
    connector: SourceConnector,
    now: datetime,
    store: ObservationStore,
    sleep: Sleep,
    transient_attempts: int,
) -> tuple[str, str, set[str]]:
    attempts = 0
    while True:
        attempts += 1
        try:
            fetched = connector.fetch(now)
            parsed = connector.parse(fetched)
            validated = connector.validate(parsed)
            break
        except RightsBlocked as exc:
            return "rights_blocked", exc.detail, set()
        except InvalidObservationUnit as exc:
            return "invalid", str(exc), set()
        except TransientSourceError as exc:
            if attempts >= transient_attempts:
                return "failed", str(exc), set()
            sleep()
            continue
        except Exception as exc:
            return "failed", type(exc).__name__, set()
    if not validated.observations:
        return "unchanged", validated.detail, set()
    try:
        result = store.append_many(validated.observations)
    except Exception as exc:
        return "failed", type(exc).__name__, set()
    if not isinstance(result, AppendResult):
        return "failed", "append", set()
    datasets = {row.dataset_id for row in validated.observations}
    if result.inserted > 0:
        return "inserted", validated.detail, datasets
    return "unchanged", validated.detail, set()


def _run_method(
    conn: psycopg.Connection,
    method: AnalyticalMethod,
    registry: MethodRegistry,
    present: set[str],
    changed: set[str],
    execute: ExecuteMethod,
) -> tuple[str, str]:
    dependency = method.dependency()
    if not dependency.new_observation_requires_recalculation:
        return "skipped", "a new observation does not require recalculation"
    required = set(method.required_dataset_ids())
    if not required.issubset(present):
        missing = ", ".join(sorted(required - present))
        return "skipped", f"missing inputs: {missing}"
    if required.isdisjoint(changed):
        return "skipped", "inputs unchanged; the last result is kept"
    if dependency.refit_is_different_command:
        # The default command calculates. A refit is never implied here.
        pass
    try:
        detail = execute(conn, method.method_id, registry)
    except Exception as exc:
        return "failed", type(exc).__name__
    return "success", detail


def _datasets(store: ObservationStore) -> set[str]:
    return {row.dataset_id for row in store.all_observations()}


def _persist(
    conn: psycopg.Connection,
    cycle_id: str,
    started: datetime,
    finished: datetime,
    status: str,
    events: list[CycleEvent],
) -> None:
    conn.execute(
        """
        insert into research.research_cycles (
          cycle_id, started_at, finished_at, status, expected_on, detail
        ) values (%s, %s, %s, %s, %s, '')
        """,
        (cycle_id, started, finished, status, started.date()),
    )
    for event in events:
        conn.execute(
            """
            insert into research.research_cycle_events (
              cycle_id, phase, subject_id, outcome, detail, recorded_at
            ) values (%s, %s, %s, %s, %s, %s)
            """,
            (cycle_id, event.phase, event.subject_id, event.outcome, event.detail, finished),
        )


def _try_lock(conn: psycopg.Connection) -> bool:
    row = conn.execute("select pg_try_advisory_lock(%s)", (LOCK_KEY,)).fetchone()
    return bool(row and row[0])


def _unlock(conn: psycopg.Connection) -> None:
    conn.execute("select pg_advisory_unlock(%s)", (LOCK_KEY,))


def record_refresh_cycle(
    conn: psycopg.Connection,
    now: datetime,
    sources: tuple[SourceRefreshResult, ...],
) -> CycleReport:
    """Persist one cycle for a refresh that already fetched. ``--refit`` is not used."""
    from aqil_research.methods.registry import default_method_registry
    from aqil_research.pipeline.execute_method import execute_registered_method
    from aqil_research.workflow.refresh import source_dataset_ids

    current = now if now.tzinfo is not None else now.replace(tzinfo=UTC)
    draft = _Draft()
    changed: set[str] = set()
    source_failed = False
    for source in sources:
        outcome, detail, datasets = _refresh_event(source, source_dataset_ids)
        if outcome in {"failed", "invalid"}:
            source_failed = True
        if outcome == "success":
            changed.update(datasets)
        draft.add("source", source.source_id, outcome, detail)
        if outcome != "failed":
            _add_stale_event(conn, draft, source.source_id, current.date())
    registry = default_method_registry()
    present = {
        row[0]
        for row in conn.execute("select distinct dataset_id from research.economic_observations")
    }
    method_failed = False

    def execute(connection: psycopg.Connection, method_id: str, chosen: MethodRegistry) -> str:
        run = execute_registered_method(connection, method_id, registry=chosen)
        return run.run_id

    for method in registry.enabled():
        outcome, detail = _run_method(conn, method, registry, present, changed, execute)
        if outcome == "failed":
            method_failed = True
        draft.add("method", method.method_id, outcome, detail)
    status = "partial" if source_failed or method_failed else "completed"
    cycle_id = str(uuid4())
    _persist(conn, cycle_id, current, current, status, draft.events)
    return CycleReport(cycle_id, current, current, status, False, tuple(draft.events), False)


def _refresh_event(
    source: SourceRefreshResult,
    dataset_ids,
) -> tuple[str, str, set[str]]:
    outcome = source.outcome
    detail = source.detail or outcome
    inserted = source.inserted
    if outcome in {"failed", "failed_fetch", "conflicts"}:
        return "failed", detail, set()
    if outcome == "failed_rights":
        return "rights_blocked", detail, set()
    if outcome == "failed_validation":
        return "invalid", detail, set()
    if outcome in {"absent", "locked", "insufficient"}:
        return "blocked", detail, set()
    if outcome == "filter_update":
        return "success", detail, set(dataset_ids(source.source_id))
    if inserted > 0:
        return "success", detail, set(dataset_ids(source.source_id))
    if outcome in {"unchanged", "completed", "success", "skipped_fresh", "not_requested"}:
        return "unchanged", detail, set()
    return "failed", detail, set()


def _add_stale_event(
    conn: psycopg.Connection,
    draft: _Draft,
    source_id: str,
    today: date,
) -> None:
    from aqil_research.workflow.refresh import _DATA_FREQUENCY, source_dataset_ids

    owned = source_dataset_ids(source_id)
    frequency = _DATA_FREQUENCY.get(source_id)
    if not owned or frequency is None:
        return
    row = conn.execute(
        """
        select max(period_start)
        from research.economic_observations
        where dataset_id = any(%s)
        """,
        (list(owned),),
    ).fetchone()
    latest = None if row is None else row[0]
    freshness = classify_source_freshness(
        data_frequency=frequency,
        latest_period=latest,
        today=today,
        last_outcome="unchanged",
    )
    if freshness == "stale":
        draft.add("source", source_id, "stale", "the latest stored period is outside its cadence")


def classify_source_freshness(
    *,
    data_frequency: str,
    latest_period: date | None,
    today: date,
    last_outcome: str | None,
) -> str:
    """Classify one source from its own publication cadence.

    A quarterly series is not stale because yesterday had no new row.
    """
    if last_outcome in {"rights_blocked", "disabled"}:
        return "rights-blocked"
    if last_outcome == "failed":
        return "technically blocked"
    if data_frequency == "discontinued":
        return "discontinued"
    if latest_period is None:
        return "technically blocked"
    grace = {"daily": 21, "weekly": 28, "monthly": 75, "quarterly": 200}.get(data_frequency, 75)
    age = (today - latest_period).days
    if age > grace:
        return "stale"
    if last_outcome in {"skipped_fresh", "not_requested"}:
        return "not due"
    if last_outcome == "unchanged":
        return "unchanged"
    return "active"
