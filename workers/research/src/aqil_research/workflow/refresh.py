"""One local refresh of the registered live sources.

Run `npm run research:refresh` when a person wants a new poll. This command
does not install a Windows task or a production schedule.

Cadence, when the command is used:
- Employment Situation publications: daily
- Consumer Price Index publications: daily
- Federal Reserve monetary-policy press: daily
- ECB monetary-policy press: daily
- BLS release calendar: daily
- SLOOS C&I lending standards: each refresh, from the Board data package
- CPI-U, payrolls, job openings, industrial production, bank credit,
  federal funds, the 10-year yield, and euro-area HICP: each refresh
- Unemployment series: weekly, and skipped when a live retrieval is newer

Each source uses its own database transaction. A failure is recorded and the
other sources still run. A second overlapping refresh does not write.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import psycopg

from aqil_research.persistence.connection import research_connection

LOCK_KEY = 410221001
SERIES_INTERVAL = timedelta(days=7)

CADENCE = {
    "bls_employment_situation_archive": "daily",
    "bls_cpi_archive": "daily",
    "federal_reserve_monetary_press": "daily",
    "ecb_monetary_press": "daily",
    "bls_ics_schedule": "daily",
    "federal_reserve_sloos_cil": "each_refresh",
    "bls_cpi_u_all_items": "each_refresh",
    "bls_ces_total_nonfarm_payrolls": "each_refresh",
    "bls_jolts_total_nonfarm_job_openings": "each_refresh",
    "federal_reserve_g17_total_ip": "each_refresh",
    "federal_reserve_h8_bank_credit": "each_refresh",
    "federal_reserve_h15_federal_funds_effective": "each_refresh",
    "federal_reserve_h15_treasury_10y_constant_maturity": "each_refresh",
    "ecb_sdw_hicp_sa": "each_refresh",
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


RefreshStep = tuple[str, Callable[[datetime], SourceRefreshResult]]


def latest_refresh_status() -> tuple[tuple[str, str, int, int, datetime, str], ...]:
    """Latest recorded outcome for each source. Does not poll a provider."""
    with research_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select distinct on (source_id)
                  source_id, outcome, inserted_count, unchanged_count, finished_at, detail
                from research.refresh_runs
                order by source_id, finished_at desc
                """
            )
            rows = cur.fetchall()
    return tuple(rows)


def series_is_due(last_success: datetime | None, now: datetime) -> bool:
    if last_success is None:
        return True
    return now - last_success >= SERIES_INTERVAL


def default_refresh_steps() -> tuple[RefreshStep, ...]:
    """Live official feeds only. Fixture paths are not accepted."""
    return (
        ("bls_employment_situation_archive", _refresh_bls_publications),
        ("bls_cpi_archive", _refresh_bls_cpi),
        ("federal_reserve_monetary_press", _refresh_fed_press),
        ("ecb_monetary_press", _refresh_ecb_press),
        ("bls_ics_schedule", _refresh_bls_calendar),
        ("federal_reserve_sloos_cil", _refresh_sloos),
        ("bls_cpi_u_all_items", _refresh_cpi_u),
        ("bls_ces_total_nonfarm_payrolls", _refresh_payrolls),
        ("bls_jolts_total_nonfarm_job_openings", _refresh_jolts),
        ("federal_reserve_g17_total_ip", _refresh_g17),
        ("federal_reserve_h8_bank_credit", _refresh_h8),
        ("federal_reserve_h15_federal_funds_effective", _refresh_h15_funds),
        ("federal_reserve_h15_treasury_10y_constant_maturity", _refresh_h15_ten_year),
        ("ecb_sdw_hicp_sa", _refresh_hicp),
    )


def run_registered_refresh(
    *,
    collected_at: datetime | None = None,
    include_series: bool = True,
    steps: Sequence[RefreshStep] | None = None,
) -> RefreshReport:
    """Poll each registered live source once, under one advisory lock."""
    now = collected_at or datetime.now(tz=UTC)
    with research_connection() as lock_conn:
        if not _try_lock(lock_conn):
            return RefreshReport(now, True, ())
        try:
            chosen = steps if steps is not None else default_refresh_steps()
            results = tuple(_run_one(now, source_id, action) for source_id, action in chosen)
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


def _refresh_bls_cpi(now: datetime) -> SourceRefreshResult:
    from aqil_research.adapters.bls_cpi.collect import collect_bls_cpi

    with research_connection() as conn:
        result = collect_bls_cpi(conn, live=True, retrieved_at=now)
    return SourceRefreshResult(
        "bls_cpi_archive",
        result.outcome,
        inserted=result.inserted,
        unchanged=result.unchanged,
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


def _refresh_ecb_press(now: datetime) -> SourceRefreshResult:
    from aqil_research.adapters.ecb_press.collect import collect_ecb_monetary_press

    with research_connection() as conn:
        result = collect_ecb_monetary_press(conn, live=True, retrieved_at=now)
    return SourceRefreshResult(
        "ecb_monetary_press",
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


def _refresh_sloos(now: datetime) -> SourceRefreshResult:
    from aqil_research.adapters.fed_sloos.adapter import FedSloosAdapter, FedSloosAdapterConfig
    from aqil_research.adapters.fed_sloos.parse import SOURCE_ID
    from aqil_research.collection.service import collect_registered_adapter
    from aqil_research.workflow.sloos_reading import load_sloos_priors, record_sloos_reading

    with research_connection() as conn:
        priors = load_sloos_priors(conn)
        collected, _store = collect_registered_adapter(
            store_backend="postgres",
            adapter=FedSloosAdapter(
                config=FedSloosAdapterConfig(live=True),
                retrieved_at=now,
                prior_points=priors,
            ),
            source_id=SOURCE_ID,
            collected_at=now,
            live=True,
            conn=conn,
        )
    if collected.outcome in {"failed_fetch", "failed_rights", "conflicts"}:
        return SourceRefreshResult(
            "federal_reserve_sloos_cil",
            collected.outcome,
            detail=collected.next_recommended_action,
        )
    with research_connection() as conn:
        reading = record_sloos_reading(conn, decision_at=now)
    return SourceRefreshResult(
        "federal_reserve_sloos_cil",
        reading.status,
        inserted=collected.observations_newly_stored,
        unchanged=collected.observations_unchanged,
        detail=reading.detail,
    )


_PRIOR_COLUMNS = frozenset(
    {
        "period_start",
        "observation_id",
        "raw_value",
        "provider_vintage_date",
        "source_release_at",
        "retrieved_at",
        "first_seen_at",
    }
)


def _load_stored_points(
    conn: psycopg.Connection,
    dataset_id: str,
    point_type: type,
) -> tuple[object, ...]:
    """Stored identities for one dataset, so an unchanged value keeps its row."""
    names = tuple(point_type.__dataclass_fields__)
    if not names or any(name not in _PRIOR_COLUMNS for name in names):
        raise RuntimeError(f"unexpected prior columns on {point_type.__name__}")
    query = (
        "select " + ", ".join(names) + " from research.economic_observations where dataset_id = %s"
    )
    with conn.cursor() as cur:
        cur.execute(query, (dataset_id,))
        rows = cur.fetchall()
    return tuple(point_type(*row) for row in rows)


def _refresh_registered(
    now: datetime,
    source_id: str,
    dataset_id: str,
    point_type: type,
    build: Callable[[datetime, tuple[object, ...]], object],
) -> SourceRefreshResult:
    """Live collect for one registered adapter. A failure stays on this source."""
    from aqil_research.collection.service import collect_registered_adapter

    with research_connection() as conn:
        priors = _load_stored_points(conn, dataset_id, point_type)
        collected, _store = collect_registered_adapter(
            store_backend="postgres",
            adapter=build(now, priors),
            source_id=source_id,
            collected_at=now,
            live=True,
            conn=conn,
        )
    if collected.outcome in {"failed_fetch", "failed_rights", "failed_validation", "conflicts"}:
        note = collected.ingest_notes[0] if collected.ingest_notes else ""
        detail = collected.next_recommended_action
        if note:
            detail = f"{detail}: {note}"
        return SourceRefreshResult(source_id, collected.outcome, detail=detail[:500])
    return SourceRefreshResult(
        source_id,
        str(collected.outcome),
        inserted=collected.observations_newly_stored,
        unchanged=collected.observations_unchanged,
    )


def _refresh_cpi_u(now: datetime) -> SourceRefreshResult:
    from aqil_research.adapters.bls_cpi_series.adapter import (
        BlsCpiSeriesAdapter,
        BlsCpiSeriesAdapterConfig,
    )
    from aqil_research.adapters.bls_cpi_series.parse import DATASET_ID, SOURCE_ID
    from aqil_research.adapters.bls_cpi_series.stability import StoredCpiPoint

    return _refresh_registered(
        now,
        SOURCE_ID,
        DATASET_ID,
        StoredCpiPoint,
        lambda retrieved, priors: BlsCpiSeriesAdapter(
            config=BlsCpiSeriesAdapterConfig(live=True),
            retrieved_at=retrieved,
            prior_points=priors,  # type: ignore[arg-type]
        ),
    )


def _refresh_payrolls(now: datetime) -> SourceRefreshResult:
    from aqil_research.adapters.bls_payrolls.adapter import (
        BlsPayrollsAdapter,
        BlsPayrollsAdapterConfig,
    )
    from aqil_research.adapters.bls_payrolls.constants import DATASET_ID, SOURCE_ID
    from aqil_research.adapters.bls_payrolls.stability import StoredPayrollPoint

    return _refresh_registered(
        now,
        SOURCE_ID,
        DATASET_ID,
        StoredPayrollPoint,
        lambda retrieved, priors: BlsPayrollsAdapter(
            config=BlsPayrollsAdapterConfig(live=True),
            retrieved_at=retrieved,
            prior_points=priors,  # type: ignore[arg-type]
        ),
    )


def _refresh_jolts(now: datetime) -> SourceRefreshResult:
    from aqil_research.adapters.bls_jolts.adapter import BlsJoltsAdapter, BlsJoltsAdapterConfig
    from aqil_research.adapters.bls_jolts.constants import DATASET_ID, SOURCE_ID
    from aqil_research.adapters.bls_jolts.stability import StoredJoltsPoint

    return _refresh_registered(
        now,
        SOURCE_ID,
        DATASET_ID,
        StoredJoltsPoint,
        lambda retrieved, priors: BlsJoltsAdapter(
            config=BlsJoltsAdapterConfig(live=True),
            retrieved_at=retrieved,
            prior_points=priors,  # type: ignore[arg-type]
        ),
    )


def _refresh_g17(now: datetime) -> SourceRefreshResult:
    from aqil_research.adapters.fed_g17.adapter import FedG17Adapter, FedG17AdapterConfig
    from aqil_research.adapters.fed_g17.parse import DATASET_ID, SOURCE_ID
    from aqil_research.adapters.fed_g17.stability import StoredG17Point

    return _refresh_registered(
        now,
        SOURCE_ID,
        DATASET_ID,
        StoredG17Point,
        lambda retrieved, priors: FedG17Adapter(
            config=FedG17AdapterConfig(live=True),
            retrieved_at=retrieved,
            prior_points=priors,  # type: ignore[arg-type]
        ),
    )


def _refresh_h8(now: datetime) -> SourceRefreshResult:
    from aqil_research.adapters.fed_h8.adapter import FedH8Adapter, FedH8AdapterConfig
    from aqil_research.adapters.fed_h8.parse import DATASET_ID, SOURCE_ID
    from aqil_research.adapters.fed_h8.stability import StoredH8Point

    return _refresh_registered(
        now,
        SOURCE_ID,
        DATASET_ID,
        StoredH8Point,
        lambda retrieved, priors: FedH8Adapter(
            config=FedH8AdapterConfig(live=True),
            retrieved_at=retrieved,
            prior_points=priors,  # type: ignore[arg-type]
        ),
    )


def _refresh_h15_funds(now: datetime) -> SourceRefreshResult:
    from aqil_research.adapters.fed_h15.adapter import FedH15Adapter, FedH15AdapterConfig
    from aqil_research.adapters.fed_h15.series import FEDERAL_FUNDS
    from aqil_research.adapters.fed_h15.stability import StoredH15Point

    return _refresh_registered(
        now,
        FEDERAL_FUNDS.source_id,
        FEDERAL_FUNDS.dataset_id,
        StoredH15Point,
        lambda retrieved, priors: FedH15Adapter(
            series=FEDERAL_FUNDS,
            config=FedH15AdapterConfig(live=True),
            retrieved_at=retrieved,
            prior_points=priors,  # type: ignore[arg-type]
        ),
    )


def _refresh_h15_ten_year(now: datetime) -> SourceRefreshResult:
    from aqil_research.adapters.fed_h15.adapter import FedH15Adapter, FedH15AdapterConfig
    from aqil_research.adapters.fed_h15.series import TREASURY_10Y
    from aqil_research.adapters.fed_h15.stability import StoredH15Point

    return _refresh_registered(
        now,
        TREASURY_10Y.source_id,
        TREASURY_10Y.dataset_id,
        StoredH15Point,
        lambda retrieved, priors: FedH15Adapter(
            series=TREASURY_10Y,
            config=FedH15AdapterConfig(live=True),
            retrieved_at=retrieved,
            prior_points=priors,  # type: ignore[arg-type]
        ),
    )


def _refresh_hicp(now: datetime) -> SourceRefreshResult:
    from aqil_research.adapters.ecb_sdw.adapter import EcbSdwAdapter, EcbSdwAdapterConfig
    from aqil_research.adapters.ecb_sdw.constants import DATASET_ID, SOURCE_ID
    from aqil_research.adapters.ecb_sdw.stability import StoredEcbPoint

    return _refresh_registered(
        now,
        SOURCE_ID,
        DATASET_ID,
        StoredEcbPoint,
        lambda retrieved, priors: EcbSdwAdapter(
            config=EcbSdwAdapterConfig(live=True),
            retrieved_at=retrieved,
            prior_points=priors,  # type: ignore[arg-type]
        ),
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
