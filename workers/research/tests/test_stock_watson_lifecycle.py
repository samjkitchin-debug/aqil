"""Isolated lifecycle tests for the 1988 filter update."""

from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import uuid4

import pytest

from aqil_research.contracts.observation import (
    AnalysisMode,
    AvailabilityPrecision,
    EconomicObservation,
    Frequency,
    QualityStatus,
    SeasonalAdjustment,
    SeriesProvenance,
)
from aqil_research.methods.stock_watson_1988 import gaussian_log_likelihood
from aqil_research.methods.stock_watson_1988_fit import (
    _filtered_factor,
    log_difference,
    standardise,
)
from aqil_research.persistence.connection import research_connection
from aqil_research.persistence.observation_store import PostgresObservationStore
from aqil_research.persistence.runs import save_research_run
from aqil_research.pipeline.models import ResearchRun
from aqil_research.workflow.stock_watson_reading import (
    FACTOR_LOCK,
    METHOD_ID,
    record_filter_update,
)
from db_guard import open_isolated_test_database

pytestmark = pytest.mark.integration

DATASETS = (
    ("fed.g17.IP.B50001.S", "federal_reserve_g17_total_ip"),
    ("bea.nipa.T20600.W875RX", "bea_real_personal_income_ex_transfers"),
    ("bea.nipa.U002BU.KPMT", "bea_real_manufacturing_trade_sales"),
    ("bls.ce.CES0000000001", "bls_ces_total_nonfarm_payrolls"),
)
LOADINGS = (0.8, 0.5, 0.6, 0.7)
FACTOR_AR = (0.3, 0.1)
IDIOSYNCRATIC = ((0.1, 0.0), (0.1, 0.0), (0.1, 0.0), (0.1, 0.0))
SCALES = (0.5, 0.5, 0.5, 0.5)


@pytest.fixture(scope="module")
def require_db() -> str:
    return open_isolated_test_database()


def _months(count: int, start: date = date(1997, 1, 1)) -> list[date]:
    months = []
    year, month = start.year, start.month
    for _ in range(count):
        months.append(date(year, month, 1))
        month += 1
        if month == 13:
            month = 1
            year += 1
    return months


def _insert(conn, periods: list[date], values: dict[str, list[float]], when: datetime) -> None:
    for (dataset_id, source_id), series_values in zip(DATASETS, values.values(), strict=True):
        retrieval_id = uuid4()
        with conn.cursor() as cur:
            cur.execute(
                """
                insert into research.source_retrievals (
                  retrieval_id, source_id, dataset_id, rights_record_id, provider_id,
                  adapter_id, adapter_version, retrieved_at, collection_mode,
                  endpoint_host, request_series_ids, attempt_count, http_status,
                  provider_status, response_byte_count, rights_decision_snapshot,
                  ingest_notes
                ) values (
                  %s, %s, %s, %s, 'test', 'lifecycle', '0', %s, 'live',
                  '127.0.0.1', %s, 1, 200, 'ok', 1, '{}'::jsonb, '{}'
                )
                """,
                (retrieval_id, source_id, dataset_id, source_id, when, [dataset_id]),
            )
        observations = tuple(
            EconomicObservation(
                observation_id=f"{dataset_id}-{period.isoformat()}-{when.timestamp()}",
                dataset_id=dataset_id,
                provider_id="test",
                source_id=source_id,
                rights_record_id=source_id,
                period_start=period,
                frequency=Frequency.MONTHLY,
                geography="US",
                unit="level",
                seasonal_adjustment=SeasonalAdjustment.SEASONALLY_ADJUSTED,
                raw_value=str(value),
                quality_status=QualityStatus.OBSERVED,
                series_provenance=SeriesProvenance.LATEST_REVISED,
                provider_vintage_date=period,
                source_release_at=when,
                availability_precision=AvailabilityPrecision.UNKNOWN,
                retrieved_at=when,
                first_seen_at=when,
                source_locator="lifecycle-test",
                adapter_version="test",
            )
            for period, value in zip(periods, series_values, strict=True)
        )
        PostgresObservationStore(conn, retrieval_id=retrieval_id).append_many(observations)


def _insert_one(conn, dataset: tuple[str, str], period: date, value: float, when: datetime) -> None:
    dataset_id, source_id = dataset
    retrieval_id = uuid4()
    with conn.cursor() as cur:
        cur.execute(
            """
            insert into research.source_retrievals (
              retrieval_id, source_id, dataset_id, rights_record_id, provider_id,
              adapter_id, adapter_version, retrieved_at, collection_mode,
              endpoint_host, request_series_ids, attempt_count, http_status,
              provider_status, response_byte_count, rights_decision_snapshot,
              ingest_notes
            ) values (
              %s, %s, %s, %s, 'test', 'lifecycle', '0', %s, 'live',
              '127.0.0.1', %s, 1, 200, 'ok', 1, '{}'::jsonb, '{}'
            )
            """,
            (retrieval_id, source_id, dataset_id, source_id, when, [dataset_id]),
        )
    PostgresObservationStore(conn, retrieval_id=retrieval_id).append_many(
        (
            EconomicObservation(
                observation_id=f"{dataset_id}-{period.isoformat()}-one",
                dataset_id=dataset_id,
                provider_id="test",
                source_id=source_id,
                rights_record_id=source_id,
                period_start=period,
                frequency=Frequency.MONTHLY,
                geography="US",
                unit="level",
                seasonal_adjustment=SeasonalAdjustment.SEASONALLY_ADJUSTED,
                raw_value=str(value),
                quality_status=QualityStatus.OBSERVED,
                series_provenance=SeriesProvenance.LATEST_REVISED,
                provider_vintage_date=period,
                source_release_at=when,
                availability_precision=AvailabilityPrecision.UNKNOWN,
                retrieved_at=when,
                first_seen_at=when,
                source_locator="lifecycle-test",
                adapter_version="test",
            ),
        )
    )


def _seed_run(conn, periods: list[date], columns: list[list[float]]) -> str:
    growth = [log_difference(column) for column in columns]
    moments = {}
    panel = []
    for name, values in zip(("production", "income", "sales", "payroll"), growth, strict=True):
        standardised, mean, scale = standardise(values)
        moments[name] = {"mean": mean, "scale": scale}
        panel.append(standardised)
    observations = tuple(tuple(panel[s][t] for s in range(4)) for t in range(len(panel[0])))
    likelihood = gaussian_log_likelihood(
        observations,
        loadings=LOADINGS,
        factor_ar=FACTOR_AR,
        idiosyncratic_ar=IDIOSYNCRATIC,
        idiosyncratic_innovation_scale=SCALES,
    )
    path = _filtered_factor(
        observations,
        loadings=LOADINGS,
        factor_ar=FACTOR_AR,
        idiosyncratic_ar=IDIOSYNCRATIC,
        idiosyncratic_innovation_scale=SCALES,
    )
    run_id = str(uuid4())
    now = datetime(2026, 8, 1, tzinfo=UTC)
    save_research_run(
        conn,
        ResearchRun(
            run_id=run_id,
            executed_at=now,
            execution_status="completed",
            dataset_id=DATASETS[0][0],
            input_dataset_ids=[item[0] for item in DATASETS],
            source_id=DATASETS[0][1],
            rights_record_id=DATASETS[0][1],
            analysis_mode=AnalysisMode.LATEST_REVISED,
            analysis_type="coincident_factor",
            decision_at=now,
            evaluation_period=periods[-1].isoformat(),
            method_id=METHOD_ID,
            method_version="0.1.0",
            implementation_hash="lifecycle",
            config_id="lifecycle",
            config_hash="lifecycle",
            input_snapshot_hash="lifecycle",
            data_sufficiency="sufficient",
            calculation={
                "loadings_ip_income_sales_payroll": list(LOADINGS),
                "factor_ar": list(FACTOR_AR),
                "idiosyncratic_ar": [list(pair) for pair in IDIOSYNCRATIC],
                "idiosyncratic_scale": list(SCALES),
                "log_likelihood": likelihood,
                "filtered_factor": list(path),
                "moments": moments,
                "sample_levels": [periods[0].isoformat(), periods[-1].isoformat()],
                "publication_allowed": False,
            },
            statistical_interpretation="lifecycle fixture",
            causal_hypothesis="none",
            investment_implication="no_action",
            assumptions=["fixture"],
            limitations=["fixture"],
            observation_ids=[],
            reproduction={"kind": "fixture"},
            narrative="fixture",
            publication_allowed=False,
        ),
    )
    return run_id


def _count(conn) -> int:
    return conn.execute(
        "select count(*) from research.research_runs where method_id = %s",
        (METHOD_ID,),
    ).fetchone()[0]


def test_filter_update_lifecycle(require_db: str) -> None:
    del require_db
    periods = _months(40)
    base = {
        "production": [100 + i for i in range(40)],
        "income": [200 + 0.5 * i for i in range(40)],
        "sales": [300 + 0.2 * i for i in range(40)],
        "payroll": [400 + i for i in range(40)],
    }
    when = datetime(2026, 8, 1, tzinfo=UTC)
    with research_connection() as conn:
        _insert(conn, periods, base, when)
        original = _seed_run(conn, periods, list(base.values()))
        assert record_filter_update(conn, decision_at=when).status == "unchanged"
        assert record_filter_update(conn, decision_at=when).status == "unchanged"
        assert _count(conn) == 1

        year = periods[-1].year + (1 if periods[-1].month == 12 else 0)
        month = 1 if periods[-1].month == 12 else periods[-1].month + 1
        nxt = [date(year, month, 1)]
        extended = {name: [values[-1] + 1] for name, values in base.items()}
        _insert(conn, nxt, extended, datetime(2026, 8, 2, tzinfo=UTC))
        updated = record_filter_update(conn, decision_at=datetime(2026, 8, 2, tzinfo=UTC))
        assert updated.status == "filter_update"
        assert _count(conn) == 2
        assert (
            conn.execute(
                "select run_id from research.research_runs where run_id = %s",
                (original,),
            ).fetchone()[0]
            == original
        )

        _insert(
            conn,
            [periods[10]],
            {name: [values[10] * 1.05] for name, values in base.items()},
            datetime(2026, 8, 3, tzinfo=UTC),
        )
        revised = record_filter_update(conn, decision_at=datetime(2026, 8, 3, tzinfo=UTC))
        assert revised.status == "filter_update"
        assert _count(conn) == 3

        following_year = year + (1 if month == 12 else 0)
        following_month = 1 if month == 12 else month + 1
        later = date(following_year, following_month, 1)
        _insert_one(
            conn,
            DATASETS[0],
            later,
            999.0,
            datetime(2026, 8, 4, tzinfo=UTC),
        )
        waiting = record_filter_update(conn, decision_at=datetime(2026, 8, 4, tzinfo=UTC))
        assert waiting.status == "unchanged"
        assert _count(conn) == 3

    holder = __import__("psycopg").connect(open_isolated_test_database())
    try:
        assert holder.execute("select pg_try_advisory_lock(%s)", (FACTOR_LOCK,)).fetchone()[0]
        holder.commit()
        with research_connection() as conn:
            before = _count(conn)
            blocked = record_filter_update(conn, decision_at=when)
            assert blocked.status == "locked"
            assert _count(conn) == before
    finally:
        holder.execute("select pg_advisory_unlock(%s)", (FACTOR_LOCK,))
        holder.commit()
        holder.close()

    with research_connection() as conn:
        _insert(
            conn,
            [periods[5]],
            {name: [-1.0] for name in base},
            datetime(2026, 8, 5, tzinfo=UTC),
        )
        completed_before = conn.execute(
            """
            select count(*) from research.research_runs
            where method_id = %s and execution_status = 'completed'
            """,
            (METHOD_ID,),
        ).fetchone()[0]
        failed = record_filter_update(conn, decision_at=datetime(2026, 8, 5, tzinfo=UTC))
        assert failed.status == "failed"
        completed_after = conn.execute(
            """
            select count(*) from research.research_runs
            where method_id = %s and execution_status = 'completed'
            """,
            (METHOD_ID,),
        ).fetchone()[0]
        assert completed_after == completed_before
        diagnostic = conn.execute(
            """
            select execution_status, calculation->>'update_kind'
            from research.research_runs
            where method_id = %s
            order by executed_at desc
            limit 1
            """,
            (METHOD_ID,),
        ).fetchone()
        assert diagnostic == ("failed_method", "filter_failure")
        still = record_filter_update(conn, decision_at=datetime(2026, 8, 6, tzinfo=UTC))
        assert still.status == "failed"
