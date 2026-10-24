"""Refresh isolation on the disposable database, and the official source list."""

from __future__ import annotations

from datetime import datetime

import psycopg
import pytest

from aqil_research.persistence.config import DEFAULT_LOCAL_URL
from aqil_research.persistence.test_database import require_test_database_url
from aqil_research.workflow.refresh import (
    LOCK_KEY,
    SourceRefreshResult,
    default_refresh_steps,
    run_registered_refresh,
)
from db_guard import open_isolated_test_database

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def require_db() -> str:
    return open_isolated_test_database()


def test_default_steps_are_official_live_sources() -> None:
    names = [name for name, _action in default_refresh_steps()]
    assert names == [
        "bls_employment_situation_archive",
        "bls_cpi_archive",
        "federal_reserve_monetary_press",
        "ecb_monetary_press",
        "bls_ics_schedule",
        "federal_reserve_sloos_cil",
        "bls_cpi_u_all_items",
        "bls_ces_total_nonfarm_payrolls",
        "bls_jolts_total_nonfarm_job_openings",
        "federal_reserve_g17_total_ip",
        "federal_reserve_h8_bank_credit",
        "federal_reserve_h15_federal_funds_effective",
        "federal_reserve_h15_treasury_10y_constant_maturity",
        "ecb_sdw_hicp_sa",
        "ecb_hicp_core",
        "ecb_fm_deposit_facility",
        "eurostat_gdp_real_ea21",
        "eurostat_unemployment_ea21",
        "eurostat_industrial_production_ea21",
        "eurostat_retail_volume_ea21",
        "stat_cpi_2025_all_items_reference",
        "cao_mo_private_ex_volatile_sa_monthly",
        "bis_gli_usd_credit_nonbanks",
        "ons_mm23_cpi_d7bt",
        "boe_official_bank_rate",
        "dosm_ipi_abs",
    ]


def test_failed_source_does_not_drop_the_next_result(require_db: str) -> None:
    def fail(_now: datetime) -> SourceRefreshResult:
        raise RuntimeError("provider unavailable")

    def succeed(_now: datetime) -> SourceRefreshResult:
        return SourceRefreshResult("bls_cpi_archive", "completed", unchanged=2)

    before = _dev_counts()
    report = run_registered_refresh(
        steps=(
            ("bls_employment_situation_archive", fail),
            ("bls_cpi_archive", succeed),
        ),
        include_series=False,
    )
    assert report.overlapped is False
    assert report.sources[0].outcome == "failed"
    assert report.sources[1].outcome == "completed"
    assert report.sources[1].unchanged == 2
    with psycopg.connect(require_db) as conn:
        row = conn.execute(
            """
            select outcome from research.refresh_runs
            where source_id = 'bls_employment_situation_archive'
            order by finished_at desc
            limit 1
            """
        ).fetchone()
    assert row is not None
    assert row[0] == "failed"
    assert _dev_counts() == before


def test_overlapping_refresh_does_not_write(require_db: str) -> None:
    holder = psycopg.connect(require_test_database_url())
    try:
        locked = holder.execute("select pg_try_advisory_lock(%s)", (LOCK_KEY,)).fetchone()
        assert locked is not None and locked[0] is True
        holder.commit()
        with psycopg.connect(require_db) as conn:
            before = conn.execute("select count(*) from research.refresh_runs").fetchone()
        report = run_registered_refresh(include_series=False)
        assert report.overlapped is True
        assert report.sources == ()
        with psycopg.connect(require_db) as conn:
            after = conn.execute("select count(*) from research.refresh_runs").fetchone()
        assert before == after
    finally:
        holder.execute("select pg_advisory_unlock(%s)", (LOCK_KEY,))
        holder.commit()
        holder.close()


def _dev_counts() -> tuple[int, int, int, int]:
    query = """
        select
          (select count(*) from research.economic_observations o
            join research.source_retrievals r on r.retrieval_id = o.retrieval_id
            where r.collection_mode = 'live'
              and r.source_id = 'bls_cps_unemployment_rate'),
          (select count(*) from research.sourced_updates
            where source_id = 'bls_employment_situation_archive'),
          (select count(*) from research.sourced_updates
            where source_id = 'federal_reserve_monetary_press'),
          (select count(*) from forward.catalyst_events
            where source_id = 'bls_ics_schedule' and scheduled_at > now())
    """
    with psycopg.connect(DEFAULT_LOCAL_URL, connect_timeout=2) as conn:
        conn.execute("set default_transaction_read_only = on")
        row = conn.execute(query).fetchone()
    assert row is not None
    return tuple(int(value) for value in row)
