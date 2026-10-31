"""Failure isolation for one daily cycle. Publishers are not called."""

from __future__ import annotations

import subprocess
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest

from aqil_research.adapters.source_registry import (
    InvalidObservationUnit,
    ParsedSource,
    RightsBlocked,
    SourceIdentity,
    TransientSourceError,
)
from aqil_research.contracts.observation import (
    AvailabilityPrecision,
    EconomicObservation,
    Frequency,
    QualityStatus,
    SeasonalAdjustment,
    SeriesProvenance,
)
from aqil_research.methods.protocol import bind_dependency
from aqil_research.methods.registry import MethodRegistry
from aqil_research.vintages.store import InMemoryObservationStore
from aqil_research.workflow.daily_cycle import (
    classify_source_freshness,
    run_daily_cycle,
    schedule_is_missed,
)
from aqil_research.workflow.refresh import LOCK_KEY
from db_guard import open_isolated_test_database

NOW = datetime(2026, 11, 1, 6, 0, tzinfo=UTC)
ROOT = Path(__file__).resolve().parents[3]
MIGRATION = ROOT / "supabase" / "migrations" / "20261101120000_research_cycles.sql"


def test_a_missed_utc_day_does_not_depend_on_a_scheduler() -> None:
    assert schedule_is_missed(None, NOW) is True
    assert schedule_is_missed(NOW - timedelta(days=1), NOW) is True
    assert schedule_is_missed(NOW, NOW) is False


def test_a_quarterly_series_is_not_stale_after_one_empty_day() -> None:
    assert (
        classify_source_freshness(
            data_frequency="quarterly",
            latest_period=date(2026, 7, 1),
            today=date(2026, 11, 1),
            last_outcome="unchanged",
        )
        == "unchanged"
    )
    assert (
        classify_source_freshness(
            data_frequency="monthly",
            latest_period=date(2026, 1, 1),
            today=date(2026, 11, 1),
            last_outcome="unchanged",
        )
        == "stale"
    )
    assert (
        classify_source_freshness(
            data_frequency="monthly",
            latest_period=None,
            today=date(2026, 11, 1),
            last_outcome="rights_blocked",
        )
        == "rights-blocked"
    )


@pytest.fixture(scope="module")
def database_url() -> str:
    url = open_isolated_test_database()
    if not url.rstrip("/").endswith("/aqil_research_test"):
        raise RuntimeError("refusing to prepare a cycle table outside aqil_research_test")
    _ensure_cycle_tables()
    return url


def test_one_source_fails_and_the_next_source_continues(database_url: str) -> None:
    store = InMemoryObservationStore()
    report = _cycle(
        database_url,
        store,
        (ScriptedSource("broken", ("boom",)), ScriptedSource("kept", (_obs("kept.series"),))),
        _registry(("KEPT", ("kept.series",))),
    )
    assert _outcome(report, "broken") == "failed"
    assert _outcome(report, "kept") == "success"
    assert report.status == "partial"
    assert {row.dataset_id for row in store.all_observations()} == {"kept.series"}


def test_an_invalid_unit_does_not_replace_a_valid_observation(database_url: str) -> None:
    store = InMemoryObservationStore()
    store.append(_obs("priced.series"))
    before = len(store.all_observations())
    report = _cycle(
        database_url,
        store,
        (ScriptedSource("priced", ("bad-unit",)),),
        _registry(),
    )
    assert _outcome(report, "priced") == "invalid"
    assert len(store.all_observations()) == before
    assert store.all_observations()[0].unit == "level"


def test_one_method_fails_and_another_method_continues(database_url: str) -> None:
    calls: list[str] = []

    def execute(_conn, method_id: str, _registry) -> str:
        if method_id == "FAILS":
            raise RuntimeError("fit")
        calls.append(method_id)
        return "appended"

    store = InMemoryObservationStore()
    report = _cycle(
        database_url,
        store,
        (ScriptedSource("both", (_obs("shared.series"),)),),
        _registry(("FAILS", ("shared.series",)), ("KEEPS", ("shared.series",))),
        execute=execute,
    )
    assert _outcome(report, "FAILS") == "failed"
    assert _outcome(report, "KEEPS") == "success"
    assert calls == ["KEEPS"]


def test_a_missing_upstream_series_skips_only_that_method(database_url: str) -> None:
    calls: list[str] = []

    def execute(_conn, method_id: str, _registry) -> str:
        calls.append(method_id)
        return "appended"

    store = InMemoryObservationStore()
    report = _cycle(
        database_url,
        store,
        (ScriptedSource("present", (_obs("present.series"),)),),
        _registry(("MISSING", ("absent.series",)), ("PRESENT", ("present.series",))),
        execute=execute,
    )
    assert _outcome(report, "MISSING") == "skipped"
    assert "missing inputs" in _detail(report, "MISSING")
    assert calls == ["PRESENT"]


def test_the_same_cycle_run_twice_does_not_repeat_methods(database_url: str) -> None:
    calls: list[str] = []

    def execute(_conn, method_id: str, _registry) -> str:
        calls.append(method_id)
        return "appended"

    store = InMemoryObservationStore()
    source = ScriptedSource("stable", (_obs("stable.series"),))
    registry = _registry(("STABLE", ("stable.series",)))
    first = _cycle(database_url, store, (source,), registry, execute=execute)
    second = _cycle(database_url, store, (source,), registry, execute=execute)
    assert _outcome(first, "STABLE") == "success"
    assert _outcome(second, "STABLE") == "skipped"
    assert calls == ["STABLE"]
    holder = psycopg.connect(database_url)
    try:
        assert holder.execute("select pg_try_advisory_lock(%s)", (LOCK_KEY,)).fetchone()[0] is True
        overlapped = _cycle(database_url, store, (source,), registry, execute=execute)
        assert overlapped.overlapped is True
        assert overlapped.events == ()
        assert calls == ["STABLE"]
    finally:
        holder.execute("select pg_advisory_unlock(%s)", (LOCK_KEY,))
        holder.close()


def test_a_transient_source_failure_is_retried_and_then_kept(database_url: str) -> None:
    sleeps: list[int] = []
    store = InMemoryObservationStore()
    report = _cycle(
        database_url,
        store,
        (ScriptedSource("flaky", ("transient", _obs("flaky.series"))),),
        _registry(("FLAKY", ("flaky.series",))),
        sleep=lambda: sleeps.append(1),
    )
    assert sleeps == [1]
    assert _outcome(report, "flaky") == "success"
    assert len(store.all_observations()) == 1


def test_a_missed_day_is_recorded_on_the_cycle(database_url: str) -> None:
    with psycopg.connect(database_url) as conn:
        latest = conn.execute("select max(started_at) from research.research_cycles").fetchone()
        anchor = latest[0] if latest and latest[0] is not None else NOW
        if anchor.tzinfo is None:
            anchor = anchor.replace(tzinfo=UTC)
        anchor = anchor + timedelta(days=3)
        conn.execute(
            """
            insert into research.research_cycles (
              cycle_id, started_at, finished_at, status, expected_on
            ) values (%s, %s, %s, 'completed', %s)
            """,
            (str(uuid4()), anchor, anchor, anchor.date()),
        )
        conn.commit()
    later = anchor + timedelta(days=1)
    store = InMemoryObservationStore()
    with psycopg.connect(database_url) as conn:
        report = run_daily_cycle(
            conn,
            now=later,
            connectors=(),
            registry=MethodRegistry(),
            store=store,
            execute=lambda _conn, _method_id, _registry: "appended",
        )
        conn.commit()
    assert report.missed is True
    assert any(event.outcome == "missed" for event in report.events)


def test_a_revised_observation_reruns_only_the_dependent_method(database_url: str) -> None:
    calls: list[str] = []

    def execute(_conn, method_id: str, _registry) -> str:
        calls.append(method_id)
        return "appended"

    store = InMemoryObservationStore()
    first_rows = (_obs("alpha.series", "1"), _obs("beta.series", "1"))
    revised = (_obs("alpha.series", "2", vintage=date(2026, 2, 1)),)
    source = ScriptedSource("panel", (first_rows, revised))
    registry = _registry(("ALPHA", ("alpha.series",)), ("BETA", ("beta.series",)))
    _cycle(database_url, store, (source,), registry, execute=execute)
    calls.clear()
    second = _cycle(database_url, store, (source,), registry, execute=execute)
    assert calls == ["ALPHA"]
    assert _outcome(second, "BETA") == "skipped"
    assert len(store.all_observations()) == 3


def test_a_rights_block_is_not_retried(database_url: str) -> None:
    sleeps: list[int] = []
    store = InMemoryObservationStore()
    report = _cycle(
        database_url,
        store,
        (ScriptedSource("closed", ("rights",)),),
        _registry(),
        sleep=lambda: sleeps.append(1),
    )
    assert sleeps == []
    assert _outcome(report, "closed") == "rights_blocked"


def test_no_input_change_preserves_the_last_result(database_url: str) -> None:
    calls: list[str] = []

    def execute(_conn, method_id: str, _registry) -> str:
        calls.append(method_id)
        return "appended"

    store = InMemoryObservationStore()
    source = ScriptedSource("quiet", (_obs("quiet.series"),))
    registry = _registry(("QUIET", ("quiet.series",)))
    _cycle(database_url, store, (source,), registry, execute=execute)
    assert calls == ["QUIET"]
    again = _cycle(database_url, store, (source,), registry, execute=execute)
    assert calls == ["QUIET"]
    assert _outcome(again, "QUIET") == "skipped"
    assert "last result" in _detail(again, "QUIET")


class ScriptedSource:
    def __init__(self, source_id: str, plan: tuple[object, ...]) -> None:
        self.source_id = source_id
        self.plan = plan
        self.calls = 0

    def identity(self) -> SourceIdentity:
        return SourceIdentity(
            source_id=self.source_id,
            cadence="monthly",
            enabled=True,
            rights_record_id=self.source_id,
            dataset_ids=(),
            data_frequency="monthly",
        )

    def fetch(self, now: datetime) -> object:
        del now
        step = self.plan[min(self.calls, len(self.plan) - 1)]
        self.calls += 1
        if step == "boom":
            raise RuntimeError("provider down")
        if step == "transient":
            raise TransientSourceError("timeout")
        if step == "rights":
            raise RightsBlocked("terms do not permit collection")
        if step == "bad-unit":
            return "bad-unit"
        return step

    def parse(self, fetched: object) -> ParsedSource:
        if fetched == "bad-unit":
            return ParsedSource((_obs("priced.series", unit="not-a-unit"),))
        if isinstance(fetched, EconomicObservation):
            return ParsedSource((fetched,))
        if isinstance(fetched, tuple):
            return ParsedSource(fetched)
        return ParsedSource(())

    def validate(self, parsed: ParsedSource) -> ParsedSource:
        for observation in parsed.observations:
            if observation.unit != "level":
                raise InvalidObservationUnit(observation.dataset_id)
        return parsed

    def refresh(self, now: datetime) -> object:
        del now
        return None


class _Method:
    def __init__(self, method_id: str, datasets: tuple[str, ...]) -> None:
        self.method_id = method_id
        self.method_version = "0"
        self._datasets = datasets

    def required_dataset_ids(self) -> tuple[str, ...]:
        return self._datasets

    def dependency(self):
        return bind_dependency(
            self._datasets,
            frequency=("monthly",),
            minimum_history="one observation",
            parameter_policy="none",
            new_observation_requires_recalculation=True,
            refit_is_different_command=False,
        )


def _registry(*methods: tuple[str, tuple[str, ...]]) -> MethodRegistry:
    registry = MethodRegistry()
    for method_id, datasets in methods:
        registry.register(_Method(method_id, datasets))
    return registry


def _cycle(url, store, connectors, registry, execute=None, sleep=None):
    def _execute(_conn, method_id: str, _registry) -> str:
        return "appended"

    with psycopg.connect(url) as conn:
        report = run_daily_cycle(
            conn,
            now=NOW,
            connectors=connectors,
            registry=registry,
            store=store,
            execute=execute or _execute,
            sleep=sleep,
        )
        conn.commit()
        return report


def _outcome(report, subject_id: str) -> str:
    return next(event.outcome for event in report.events if event.subject_id == subject_id)


def _detail(report, subject_id: str) -> str:
    return next(event.detail for event in report.events if event.subject_id == subject_id)


def _obs(
    dataset_id: str,
    value: str = "1",
    *,
    vintage: date | None = None,
    unit: str = "level",
) -> EconomicObservation:
    period = date(2026, 1, 1)
    vintage_date = vintage or period
    return EconomicObservation(
        observation_id=f"{dataset_id}-{vintage_date.isoformat()}-{value}-{unit}",
        dataset_id=dataset_id,
        provider_id="test",
        source_id="test",
        rights_record_id="test",
        period_start=period,
        frequency=Frequency.MONTHLY,
        geography="US",
        unit=unit,
        seasonal_adjustment=SeasonalAdjustment.SEASONALLY_ADJUSTED,
        raw_value=value,
        quality_status=QualityStatus.OBSERVED,
        series_provenance=SeriesProvenance.LATEST_REVISED,
        provider_vintage_date=vintage_date,
        source_release_at=NOW,
        availability_precision=AvailabilityPrecision.UNKNOWN,
        retrieved_at=NOW,
        first_seen_at=NOW,
        adapter_version="test",
    )


def _ensure_cycle_tables() -> None:
    probe = subprocess.run(
        [
            "docker",
            "exec",
            "supabase_db_ojvswermsbbaltjohqph",
            "psql",
            "-U",
            "postgres",
            "-d",
            "aqil_research_test",
            "-tA",
            "-c",
            "select to_regclass('research.research_cycles')",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    if probe.stdout.strip():
        return
    subprocess.run(
        [
            "docker",
            "exec",
            "-i",
            "supabase_db_ojvswermsbbaltjohqph",
            "psql",
            "-U",
            "postgres",
            "-d",
            "aqil_research_test",
            "-v",
            "ON_ERROR_STOP=1",
        ],
        input=MIGRATION.read_text(encoding="utf-8"),
        text=True,
        check=True,
    )
