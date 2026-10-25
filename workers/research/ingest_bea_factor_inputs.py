"""Insert the two BEA factor inputs into research.economic_observations."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from uuid import uuid4

import httpx
import psycopg

from aqil_research.adapters.bea_workbook import (
    manufacturing_trade_sales,
    personal_income_ex_transfers,
)
from aqil_research.contracts.observation import (
    AvailabilityPrecision,
    EconomicObservation,
    Frequency,
    QualityStatus,
    SeasonalAdjustment,
    SeriesProvenance,
)
from aqil_research.persistence.observation_store import PostgresObservationStore

INCOME_URL = "https://apps.bea.gov/national/Release/XLS/Survey/Section2All_xls.xlsx"
SALES_URL = "https://apps.bea.gov/national/Release/XLS/Underlying/Section0All_xls.xlsx"
PUBLISHED = datetime(2026, 9, 30, tzinfo=UTC)


def _fetch(url: str) -> bytes:
    response = httpx.get(
        url,
        headers={"User-Agent": "AqilResearch/1.0 (local research retrieval)"},
        timeout=120,
        follow_redirects=True,
    )
    response.raise_for_status()
    if response.content[:2] != b"PK":
        raise RuntimeError(f"not a workbook: {url}")
    return response.content


def _observations(dataset_id: str, source_id: str, unit: str, locator: str, months, now: datetime):
    built = []
    for item in months:
        built.append(
            EconomicObservation(
                observation_id=f"{source_id}-{item.period_start.isoformat()}",
                dataset_id=dataset_id,
                provider_id="bea",
                source_id=source_id,
                rights_record_id=source_id,
                period_start=item.period_start,
                frequency=Frequency.MONTHLY,
                geography="US",
                unit=unit,
                seasonal_adjustment=SeasonalAdjustment.SEASONALLY_ADJUSTED,
                raw_value=item.value,
                quality_status=QualityStatus.OBSERVED,
                series_provenance=SeriesProvenance.LATEST_REVISED,
                provider_vintage_date=PUBLISHED.date(),
                source_release_at=PUBLISHED,
                availability_precision=AvailabilityPrecision.UNKNOWN,
                retrieved_at=now,
                first_seen_at=now,
                source_locator=locator,
                adapter_version="bea-workbook-0.1.0",
            )
        )
    return tuple(built)


def _store(conn, source_id, dataset_id, payload, notes):
    fingerprint = hashlib.sha256(payload).hexdigest()
    retrieval_id = uuid4()
    with conn.cursor() as cur:
        cur.execute(
            """
            insert into research.source_retrievals (
              retrieval_id, source_id, dataset_id, rights_record_id, provider_id,
              adapter_id, adapter_version, retrieved_at, collection_mode,
              endpoint_host, request_series_ids, attempt_count, http_status,
              provider_status, response_byte_count, rights_decision_snapshot,
              ingest_notes, response_fingerprint
            ) values (
              %s, %s, %s, %s, 'bea', 'bea_workbook', '0.1.0', now(), 'live',
              'apps.bea.gov', %s, 1, 200, 'ok', %s, '{}'::jsonb, %s, %s
            )
            """,
            (
                retrieval_id,
                source_id,
                dataset_id,
                source_id,
                [dataset_id],
                len(payload),
                notes,
                fingerprint,
            ),
        )
    return retrieval_id


def main() -> None:
    now = datetime.now(UTC)
    income_bytes = _fetch(INCOME_URL)
    sales_bytes = _fetch(SALES_URL)
    income = personal_income_ex_transfers(income_bytes)
    sales = manufacturing_trade_sales(sales_bytes)
    conn = psycopg.connect("postgresql://research_worker:research_worker@127.0.0.1:55432/postgres")
    income_id = _store(
        conn,
        "bea_real_personal_income_ex_transfers",
        "bea.nipa.T20600.W875RX",
        income_bytes,
        ["T20600-M line 36 W875RX"],
    )
    sales_id = _store(
        conn,
        "bea_real_manufacturing_trade_sales",
        "bea.nipa.U002BU.KPMT",
        sales_bytes,
        ["U002BU-M line 1 KPMT"],
    )
    income_result = PostgresObservationStore(conn, retrieval_id=income_id).append_many(
        _observations(
            "bea.nipa.T20600.W875RX",
            "bea_real_personal_income_ex_transfers",
            "millions_chained_2017_dollars",
            INCOME_URL,
            income,
            now,
        )
    )
    sales_result = PostgresObservationStore(conn, retrieval_id=sales_id).append_many(
        _observations(
            "bea.nipa.U002BU.KPMT",
            "bea_real_manufacturing_trade_sales",
            "millions_chained_2017_dollars",
            SALES_URL,
            sales,
            now,
        )
    )
    conn.commit()
    conn.close()
    print("income", len(income), income[0].period_start, income[-1].period_start, income_result)
    print("sales", len(sales), sales[0].period_start, sales[-1].period_start, sales_result)


if __name__ == "__main__":
    main()
