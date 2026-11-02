"""Run the existing Sahm calculator on the stored live unemployment sample.

Fixture rows are not a backfill. October 2025 is not interpolated.
publication_allowed stays false. A matching stored run is left in place.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, date, datetime

import psycopg

from aqil_research.contracts.observation import AnalysisMode
from aqil_research.methods.configs import SAHM_PUBLISHED
from aqil_research.methods.evaluation import classify_sahm_window
from aqil_research.methods.registry import default_method_registry
from aqil_research.methods.sahm import SAHM_METHOD_ID, SahmMethodError, run_sahm
from aqil_research.persistence.connection import research_connection
from aqil_research.persistence.observation_store import load_observations_for_dataset
from aqil_research.persistence.reproduce import verify_stored_run_replay
from aqil_research.persistence.runs import save_research_run
from aqil_research.pipeline.models import ResearchExecutionRequest, ResearchRun
from aqil_research.pipeline.orchestrate import execute_research_run
from aqil_research.sources.rights import load_source_rights
from aqil_research.vintages.store import InMemoryObservationStore

DATASET_ID = "bls.ln.LNS14000000"
SOURCE_ID = "bls_cps_unemployment_rate"

LONG_HISTORY_BLOCKER = (
    "A match to the long SAHMREALTIME history is blocked. "
    "AQ-103 is out of scope. "
    "This is a short latest-revised calculation, not the real-time Sahm series, "
    "and not a decades-long unemployment history. "
    "History before the stored live sample is not backfilled, "
    "and October 2025 is not interpolated."
)


@dataclass(frozen=True, slots=True)
class SahmIndicator:
    evaluation_period: date
    three_month_average: str
    prior_twelve_month_low_of_average: str
    gap_percentage_points: str
    triggered: bool


@dataclass(frozen=True, slots=True)
class SahmShortSampleResult:
    status: str
    run_id: str | None
    publication_allowed: bool | None
    replay_match: bool | None
    live_months: tuple[date, ...]
    october_2025_present: bool
    fixture_rows_excluded: int
    eligible: tuple[date, ...]
    permanently_invalid: tuple[date, ...]
    awaiting_observations: tuple[date, ...]
    indicators: tuple[SahmIndicator, ...]
    prior_run_ids: tuple[str, ...]
    long_history_blocker: str
    detail: str


def record_sahm_short_sample(
    conn: psycopg.Connection,
    *,
    decision_at: datetime | None = None,
) -> SahmShortSampleResult:
    """Append one published-config run for the latest complete live window."""
    now = decision_at or datetime.now(tz=UTC)
    prior_run_ids = _sahm_run_ids(conn)
    live_ids = _live_latest_revised_ids(conn)
    fixture_rows_excluded = _fixture_row_count(conn)
    rows = tuple(
        row
        for row in load_observations_for_dataset(conn, DATASET_ID)
        if row.observation_id in live_ids
    )
    store = InMemoryObservationStore()
    store.append_many(rows)
    by_period = store.as_of(DATASET_ID, now, AnalysisMode.LATEST_REVISED)
    live_months = tuple(sorted(by_period))
    october = date(2025, 10, 1)
    if not live_months:
        return _empty(prior_run_ids, fixture_rows_excluded, "no stored live unemployment months")

    eligible, permanent, awaiting = _classify_span(
        set(live_months),
        live_months[0],
        live_months[-1],
    )
    indicators: list[SahmIndicator] = []
    for evaluation in eligible:
        try:
            output = run_sahm(by_period, evaluation, SAHM_PUBLISHED)
        except SahmMethodError as exc:
            return SahmShortSampleResult(
                status="refused",
                run_id=None,
                publication_allowed=None,
                replay_match=None,
                live_months=live_months,
                october_2025_present=october in by_period,
                fixture_rows_excluded=fixture_rows_excluded,
                eligible=eligible,
                permanently_invalid=permanent,
                awaiting_observations=awaiting,
                indicators=(),
                prior_run_ids=prior_run_ids,
                long_history_blocker=LONG_HISTORY_BLOCKER,
                detail=str(exc),
            )
        indicators.append(
            SahmIndicator(
                evaluation_period=output.evaluation_period,
                three_month_average=str(output.three_month_average),
                prior_twelve_month_low_of_average=str(output.prior_twelve_month_low_of_average),
                gap_percentage_points=str(output.gap_percentage_points),
                triggered=output.triggered,
            )
        )
    if not eligible:
        return SahmShortSampleResult(
            status="refused",
            run_id=None,
            publication_allowed=None,
            replay_match=None,
            live_months=live_months,
            october_2025_present=october in by_period,
            fixture_rows_excluded=fixture_rows_excluded,
            eligible=eligible,
            permanently_invalid=permanent,
            awaiting_observations=awaiting,
            indicators=tuple(indicators),
            prior_run_ids=prior_run_ids,
            long_history_blocker=LONG_HISTORY_BLOCKER,
            detail="No evaluation month has a complete Sahm window.",
        )

    latest = eligible[-1]
    request = ResearchExecutionRequest(
        source_id=SOURCE_ID,
        dataset_id=DATASET_ID,
        decision_at=now,
        analysis_mode=AnalysisMode.LATEST_REVISED,
        evaluation_period=latest.isoformat(),
        method_id=SAHM_METHOD_ID,
        method_config=SAHM_PUBLISHED.model_dump(mode="json"),
        collect=False,
    )
    run = execute_research_run(
        request,
        store=store,
        rights_records=load_source_rights(),
        method_registry=default_method_registry(),
        executed_at=now,
    )
    if run.publication_allowed:
        raise RuntimeError("publication_allowed must stay false")
    if run.execution_status != "completed" or run.data_sufficiency != "sufficient":
        return SahmShortSampleResult(
            status="refused",
            run_id=None,
            publication_allowed=False,
            replay_match=None,
            live_months=live_months,
            october_2025_present=october in by_period,
            fixture_rows_excluded=fixture_rows_excluded,
            eligible=eligible,
            permanently_invalid=permanent,
            awaiting_observations=awaiting,
            indicators=tuple(indicators),
            prior_run_ids=prior_run_ids,
            long_history_blocker=LONG_HISTORY_BLOCKER,
            detail=run.missing_data_reason or run.narrative,
        )

    existing = _matching_run_id(conn, run)
    if existing is not None:
        return SahmShortSampleResult(
            status="unchanged",
            run_id=existing,
            publication_allowed=False,
            replay_match=None,
            live_months=live_months,
            october_2025_present=october in by_period,
            fixture_rows_excluded=fixture_rows_excluded,
            eligible=eligible,
            permanently_invalid=permanent,
            awaiting_observations=awaiting,
            indicators=tuple(indicators),
            prior_run_ids=prior_run_ids,
            long_history_blocker=LONG_HISTORY_BLOCKER,
            detail="A stored run already matches this live window.",
        )

    save_research_run(conn, run)
    replay = verify_stored_run_replay(conn, run.run_id)
    if not replay.full_match:
        raise RuntimeError("Sahm short-sample replay did not match; the insert will be rolled back")
    return SahmShortSampleResult(
        status="appended",
        run_id=run.run_id,
        publication_allowed=run.publication_allowed,
        replay_match=True,
        live_months=live_months,
        october_2025_present=october in by_period,
        fixture_rows_excluded=fixture_rows_excluded,
        eligible=eligible,
        permanently_invalid=permanent,
        awaiting_observations=awaiting,
        indicators=tuple(indicators),
        prior_run_ids=prior_run_ids,
        long_history_blocker=LONG_HISTORY_BLOCKER,
        detail=run.narrative,
    )


def _classify_span(
    present: set[date],
    first: date,
    last: date,
) -> tuple[tuple[date, ...], tuple[date, ...], tuple[date, ...]]:
    eligible: list[date] = []
    permanent: list[date] = []
    awaiting: list[date] = []
    for evaluation in _calendar_months(first, last):
        finding = classify_sahm_window(present, evaluation)
        if finding.status == "eligible":
            eligible.append(evaluation)
        elif finding.status == "permanently_invalid":
            permanent.append(evaluation)
        else:
            awaiting.append(evaluation)
    return tuple(eligible), tuple(permanent), tuple(awaiting)


def _calendar_months(start: date, end: date) -> tuple[date, ...]:
    months: list[date] = []
    cursor = date(start.year, start.month, 1)
    last = date(end.year, end.month, 1)
    while cursor <= last:
        months.append(cursor)
        year = cursor.year + (cursor.month // 12)
        month = cursor.month % 12 + 1
        cursor = date(year, month, 1)
    return tuple(months)


def _live_latest_revised_ids(conn: psycopg.Connection) -> frozenset[str]:
    with conn.cursor() as cur:
        cur.execute(
            """
            select observation.observation_id
            from research.economic_observations as observation
            join research.source_retrievals as retrieval
              on retrieval.retrieval_id = observation.retrieval_id
            where observation.dataset_id = %s
              and retrieval.collection_mode = 'live'
              and observation.series_provenance = 'latest_revised'
            """,
            (DATASET_ID,),
        )
        return frozenset(str(row[0]) for row in cur.fetchall())


def _fixture_row_count(conn: psycopg.Connection) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """
            select count(*)
            from research.economic_observations as observation
            join research.source_retrievals as retrieval
              on retrieval.retrieval_id = observation.retrieval_id
            where observation.dataset_id = %s
              and retrieval.collection_mode = 'fixture'
            """,
            (DATASET_ID,),
        )
        row = cur.fetchone()
    return int(row[0]) if row else 0


def _sahm_run_ids(conn: psycopg.Connection) -> tuple[str, ...]:
    with conn.cursor() as cur:
        cur.execute(
            """
            select run_id
            from research.research_runs
            where method_id = %s
            order by executed_at
            """,
            (SAHM_METHOD_ID,),
        )
        return tuple(str(row[0]) for row in cur.fetchall())


def _matching_run_id(conn: psycopg.Connection, run: ResearchRun) -> str | None:
    with conn.cursor() as cur:
        cur.execute(
            """
            select run_id
            from research.research_runs
            where method_id = %s
              and config_id = %s
              and evaluation_period = %s::date
              and input_snapshot_hash = %s
              and implementation_hash = %s
              and method_version = %s
              and data_sufficiency = %s
              and publication_allowed = false
            order by executed_at desc
            limit 1
            """,
            (
                run.method_id,
                run.config_id,
                run.evaluation_period,
                run.input_snapshot_hash,
                run.implementation_hash,
                run.method_version,
                run.data_sufficiency,
            ),
        )
        row = cur.fetchone()
    if row is None:
        return None
    return str(row[0])


def _empty(
    prior_run_ids: tuple[str, ...],
    fixture_rows_excluded: int,
    detail: str,
) -> SahmShortSampleResult:
    return SahmShortSampleResult(
        status="blocked",
        run_id=None,
        publication_allowed=None,
        replay_match=None,
        live_months=(),
        october_2025_present=False,
        fixture_rows_excluded=fixture_rows_excluded,
        eligible=(),
        permanently_invalid=(),
        awaiting_observations=(),
        indicators=(),
        prior_run_ids=prior_run_ids,
        long_history_blocker=LONG_HISTORY_BLOCKER,
        detail=detail,
    )


def _scrub(text: str) -> str:
    text = re.sub(r"://[^@\s]+@", "://***@", text)
    return re.sub(r"password=\S+", "password=***", text, flags=re.IGNORECASE)


def main() -> int:
    try:
        with research_connection() as conn:
            result = record_sahm_short_sample(conn)
    except Exception as exc:
        print("status=blocked")
        print("database_unreachable=true")
        print(f"error_type={type(exc).__name__}")
        print(_scrub(str(exc))[:400])
        print(LONG_HISTORY_BLOCKER)
        return 1
    print(f"status={result.status}")
    print(f"run_id={result.run_id}")
    print(f"publication_allowed={result.publication_allowed}")
    print(f"replay_match={result.replay_match}")
    print(f"live_month_count={len(result.live_months)}")
    if result.live_months:
        print(f"live_first={result.live_months[0].isoformat()}")
        print(f"live_last={result.live_months[-1].isoformat()}")
    print(f"october_2025_present={result.october_2025_present}")
    print(f"fixture_rows_excluded={result.fixture_rows_excluded}")
    print("eligible=" + ",".join(item.isoformat() for item in result.eligible))
    print(
        "permanently_invalid=" + ",".join(item.isoformat() for item in result.permanently_invalid)
    )
    print(
        "awaiting_observations="
        + ",".join(item.isoformat() for item in result.awaiting_observations)
    )
    for item in result.indicators:
        print(
            "indicator="
            f"{item.evaluation_period.isoformat()}|"
            f"{item.three_month_average}|"
            f"{item.prior_twelve_month_low_of_average}|"
            f"{item.gap_percentage_points}|"
            f"{item.triggered}"
        )
    print("prior_run_ids=" + ",".join(result.prior_run_ids))
    print(f"detail={result.detail}")
    print(result.long_history_blocker)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
