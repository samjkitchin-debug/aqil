"""Store one BEA real-GDP growth vintage on the local research database.

Latest-revised rows are not rewritten. The import refuses any database that is
not loopback port 55432 database postgres. It does not call FRED or ALFRED.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from urllib.parse import urlparse
from uuid import uuid4

import httpx
import psycopg

from aqil_research.adapters.bea_gdp_vintage.parse import (
    ADAPTER_VERSION,
    DATASET_ID,
    SOURCE_ID,
    UNIT,
    WORKBOOK_URL,
    RealGdpVintagePoint,
    RealGdpVintageWorkbook,
    parse_real_gdp_vintage_workbook,
    release_date_boundary,
    series_checksum,
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
from aqil_research.persistence.retrieval import rights_decision_snapshot
from aqil_research.sources.rights import (
    RightsOperation,
    find_source_rights,
    load_source_rights,
    source_usable,
)
from aqil_research.vintages.store import AppendResult

LOCAL_DATABASE_URL = "postgresql://research_worker:research_worker@127.0.0.1:55432/postgres"
_ALLOWED_HOST = "apps.bea.gov"
_ALLOWED_PATH = "/national/xls/gdp-gdi-vintage-history.xlsx"


class VintageIngestError(RuntimeError):
    """The vintage workbook was not stored."""


def assert_local_research_database(database_url: str) -> None:
    parsed = urlparse(database_url)
    if parsed.hostname != "127.0.0.1" or parsed.port != 55432:
        raise VintageIngestError("the vintage import writes only to loopback port 55432")
    if parsed.path.strip("/") != "postgres":
        raise VintageIngestError("the vintage import writes only to the local postgres database")


def download_workbook() -> tuple[bytes, int]:
    response = httpx.get(
        WORKBOOK_URL,
        headers={"User-Agent": "AqilResearch/1.0 (local research retrieval)"},
        timeout=120,
        follow_redirects=False,
    )
    if response.status_code != 200:
        raise VintageIngestError(f"BEA workbook returned HTTP {response.status_code}")
    final = urlparse(str(response.url))
    if final.hostname != _ALLOWED_HOST or final.path != _ALLOWED_PATH:
        raise VintageIngestError("BEA workbook URL did not stay on the registered path")
    if not response.content.startswith(b"PK"):
        raise VintageIngestError("BEA response was not a workbook")
    return response.content, response.status_code


def observations_from_points(
    points: tuple[RealGdpVintagePoint, ...],
    *,
    retrieved_at: datetime,
) -> tuple[EconomicObservation, ...]:
    if retrieved_at.tzinfo is None:
        raise VintageIngestError("retrieved_at must be timezone-aware")
    retrieved = retrieved_at.astimezone(UTC)
    rows: list[EconomicObservation] = []
    for point in points:
        if point.release_date > retrieved.date():
            raise VintageIngestError("a printed release date is after this retrieval")
        boundary = release_date_boundary(point.release_date)
        rows.append(
            EconomicObservation(
                observation_id=(
                    f"bea-real-gdp-pct-{point.period_start.isoformat()}-"
                    f"{point.release_date.isoformat()}"
                ),
                dataset_id=DATASET_ID,
                provider_id="bea",
                source_id=SOURCE_ID,
                rights_record_id=SOURCE_ID,
                period_start=point.period_start,
                period_end=point.period_end,
                frequency=Frequency.QUARTERLY,
                geography="US",
                unit=UNIT,
                seasonal_adjustment=SeasonalAdjustment.UNKNOWN,
                raw_value=point.raw_value,
                quality_status=QualityStatus.OBSERVED,
                series_provenance=SeriesProvenance.PROVIDER_VINTAGE,
                provider_vintage_date=point.release_date,
                source_release_at=boundary,
                earliest_model_available_at=None,
                availability_precision=AvailabilityPrecision.DATE,
                retrieved_at=retrieved,
                first_seen_at=retrieved,
                source_locator=f"{WORKBOOK_URL}#{point.quarter_label}/{point.vintage_label}",
                adapter_version=ADAPTER_VERSION,
            )
        )
    return tuple(rows)


def store_real_gdp_vintage(
    conn: psycopg.Connection,
    payload: bytes,
    *,
    retrieved_at: datetime,
    http_status: int,
) -> tuple[AppendResult, RealGdpVintageWorkbook, str, str]:
    record = find_source_rights(load_source_rights(), source_id=SOURCE_ID)
    if record is None or record.dataset_id != DATASET_ID:
        raise VintageIngestError("the BEA vintage rights row is missing")
    if not source_usable(record, RightsOperation.RAW_DATA_RETENTION):
        raise VintageIngestError("retention of this BEA workbook is not permitted")
    if not source_usable(record, RightsOperation.HISTORICAL_ARCHIVING):
        raise VintageIngestError("historical archiving of this BEA workbook is not permitted")
    parsed = parse_real_gdp_vintage_workbook(payload)
    if parsed.updated_on > retrieved_at.astimezone(UTC).date():
        raise VintageIngestError("workbook last-updated date is after this retrieval")
    file_hash = hashlib.sha256(payload).hexdigest()
    checksum = series_checksum(parsed.points)
    observations = observations_from_points(parsed.points, retrieved_at=retrieved_at)
    notes = [
        "Vintage History real GDP percent change from the preceding period",
        "not Table 1.1.6 A191RX and not a chained-dollar level",
        f"workbook updated {parsed.updated_on.isoformat()}",
        f"file sha256 {file_hash}",
        f"series sha256 {checksum}",
        (
            f"points {len(parsed.points)} quarters {parsed.distinct_quarters} "
            f"releases {parsed.distinct_release_dates} "
            f"unpublished real GDP cells {parsed.skipped_unpublished}"
        ),
    ]
    retrieval_id = _retrieval(
        conn,
        payload_hash=file_hash,
        http_status=http_status,
        byte_count=len(payload),
        notes=notes,
        snapshot=rights_decision_snapshot(record),
        retrieved_at=retrieved_at.astimezone(UTC),
        year_start=min(point.period_start.year for point in parsed.points),
        year_end=max(point.period_start.year for point in parsed.points),
    )
    result = PostgresObservationStore(conn, retrieval_id=retrieval_id).append_many(observations)
    return result, parsed, file_hash, checksum


def _retrieval(
    conn: psycopg.Connection,
    *,
    payload_hash: str,
    http_status: int,
    byte_count: int,
    notes: list[str],
    snapshot: dict[str, str],
    retrieved_at: datetime,
    year_start: int,
    year_end: int,
):
    with conn.cursor() as cur:
        cur.execute(
            """
            select retrieval_id from research.source_retrievals
            where dataset_id = %s and response_fingerprint = %s
            """,
            (DATASET_ID, payload_hash),
        )
        found = cur.fetchone()
        if found:
            return found[0]
        retrieval_id = uuid4()
        cur.execute(
            """
            insert into research.source_retrievals (
              retrieval_id, source_id, dataset_id, rights_record_id, provider_id,
              adapter_id, adapter_version, retrieved_at, collection_mode,
              endpoint_host, request_series_ids, request_year_start, request_year_end,
              attempt_count, http_status, provider_status, response_byte_count,
              rights_decision_snapshot, ingest_notes, response_fingerprint
            ) values (
              %s, %s, %s, %s, 'bea', 'bea_gdp_vintage', %s, %s, 'live',
              %s, %s, %s, %s, 1, %s, 'ok', %s, %s::jsonb, %s, %s
            )
            """,
            (
                retrieval_id,
                SOURCE_ID,
                DATASET_ID,
                SOURCE_ID,
                ADAPTER_VERSION,
                retrieved_at,
                _ALLOWED_HOST,
                [DATASET_ID],
                year_start,
                year_end,
                http_status,
                byte_count,
                psycopg.types.json.Json(snapshot),
                notes,
                payload_hash,
            ),
        )
    return retrieval_id
