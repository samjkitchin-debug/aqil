"""Refresh the two BEA series and avoid a duplicate factor run."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from uuid import uuid4

import httpx

from aqil_research.adapters.bea_workbook import (
    BeaMonth,
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
SERIES = (
    (
        "bea_real_personal_income_ex_transfers",
        "bea.nipa.T20600.W875RX",
        INCOME_URL,
        "millions_chained_2017_dollars",
        personal_income_ex_transfers,
        ["T20600-M line 36 W875RX"],
    ),
    (
        "bea_real_manufacturing_trade_sales",
        "bea.nipa.U002BU.KPMT",
        SALES_URL,
        "millions_chained_2017_dollars",
        manufacturing_trade_sales,
        ["U002BU-M line 1 KPMT"],
    ),
)


def _download(url: str) -> bytes:
    response = httpx.get(
        url,
        headers={"User-Agent": "AqilResearch/1.0 (local research retrieval)"},
        timeout=120,
        follow_redirects=True,
    )
    response.raise_for_status()
    if not response.content.startswith(b"PK"):
        raise RuntimeError("BEA response was not a workbook")
    return response.content


def _retrieval(conn, source_id: str, dataset_id: str, payload: bytes, notes: list[str]):
    fingerprint = hashlib.sha256(payload).hexdigest()
    with conn.cursor() as cur:
        cur.execute(
            """
            select retrieval_id from research.source_retrievals
            where dataset_id = %s and response_fingerprint = %s
            """,
            (dataset_id, fingerprint),
        )
        found = cur.fetchone()
        if found:
            return found[0], False
        retrieval_id = uuid4()
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
    return retrieval_id, True


GDP_URL = "https://apps.bea.gov/national/Release/XLS/Survey/Section1All_xls.xlsx"
GDP_SOURCE_ID = "bea_real_gross_domestic_product"
GDP_DATASET_ID = "bea.nipa.T10106.A191RX"


def store_real_gross_domestic_product(conn, now: datetime) -> tuple[int, int, BeaMonth, BeaMonth]:
    """Ingest Table 1.1.6 line 1. This is revised quarterly GDP, not a nowcast."""
    from aqil_research.adapters.bea_workbook import real_gross_domestic_product

    payload = _download(GDP_URL)
    extracted = real_gross_domestic_product(payload)
    if extracted.published_on > now.date():
        raise RuntimeError("BEA publication date is after this retrieval")
    published = datetime(
        extracted.published_on.year,
        extracted.published_on.month,
        extracted.published_on.day,
        tzinfo=UTC,
    )
    notes = [
        f"{extracted.sheet_name} line {extracted.line_number} {extracted.account_code}",
        extracted.unit_text,
        f"published {extracted.published_on.isoformat()}",
    ]
    retrieval_id, _created = _retrieval(conn, GDP_SOURCE_ID, GDP_DATASET_ID, payload, notes)
    observations = tuple(
        EconomicObservation(
            observation_id=f"{GDP_SOURCE_ID}-{item.period_start.isoformat()}",
            dataset_id=GDP_DATASET_ID,
            provider_id="bea",
            source_id=GDP_SOURCE_ID,
            rights_record_id=GDP_SOURCE_ID,
            period_start=item.period_start,
            frequency=Frequency.QUARTERLY,
            geography="US",
            unit="millions_chained_2017_dollars",
            seasonal_adjustment=SeasonalAdjustment.SEASONALLY_ADJUSTED,
            raw_value=item.value,
            quality_status=QualityStatus.OBSERVED,
            series_provenance=SeriesProvenance.LATEST_REVISED,
            provider_vintage_date=extracted.published_on,
            source_release_at=published,
            availability_precision=AvailabilityPrecision.UNKNOWN,
            retrieved_at=now,
            first_seen_at=now,
            source_locator=GDP_URL,
            adapter_version="bea-workbook-0.1.0",
        )
        for item in extracted.quarters
    )
    result = PostgresObservationStore(conn, retrieval_id=retrieval_id).append_many(observations)
    return result.inserted, result.unchanged, extracted.quarters[0], extracted.quarters[-1]


def refresh_bea_series(conn, source_id: str, now: datetime) -> tuple[int, int]:
    spec = next(item for item in SERIES if item[0] == source_id)
    _, dataset_id, url, unit, parser, notes = spec
    payload = _download(url)
    months = parser(payload)
    retrieval_id, _created = _retrieval(conn, source_id, dataset_id, payload, notes)
    observations = tuple(
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
            source_locator=url,
            adapter_version="bea-workbook-0.1.0",
        )
        for item in months
    )
    result = PostgresObservationStore(conn, retrieval_id=retrieval_id).append_many(observations)
    return result.inserted, result.unchanged
