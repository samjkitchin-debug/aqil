"""Postgres-backed ingestion (single fetch, retrieval row, append-only observations)."""

from __future__ import annotations

from datetime import datetime

import psycopg

from aqil_research.adapters.bls.adapter import BlsUnemploymentAdapter
from aqil_research.adapters.protocol import ProviderAdapter
from aqil_research.persistence.observation_store import PostgresObservationStore
from aqil_research.persistence.retrieval import insert_source_retrieval
from aqil_research.pipeline.ingestion import IngestOutcome, ingest_from_fetch
from aqil_research.sources.rights import SourceRightsRecord


def ingest_adapter_to_postgres(
    conn: psycopg.Connection,
    adapter: ProviderAdapter,
    rights: SourceRightsRecord,
    *,
    retrieved_at: datetime,
    collection_mode: str,
    optional: bool = False,
) -> tuple[PostgresObservationStore, IngestOutcome]:
    """Fetch once, record retrieval metadata, append observations."""
    # Rights gate + single fetch:
    from aqil_research.sources.rights_gate import assert_rights_for_ingest

    assert_rights_for_ingest(rights, adapter)
    fetch_result = adapter.fetch()

    endpoint_host = _endpoint_host(adapter)
    (
        series_ids,
        year_start,
        year_end,
        attempt_count,
        http_status,
        provider_status,
        response_bytes,
    ) = _diagnostics(adapter, fetch_result)
    ingest_notes = [error.message for error in fetch_result.errors] if fetch_result.errors else []

    retrieval_id = insert_source_retrieval(
        conn,
        rights=rights,
        adapter=adapter,
        retrieved_at=retrieved_at,
        collection_mode=collection_mode,
        endpoint_host=endpoint_host,
        request_series_ids=series_ids,
        request_year_start=year_start,
        request_year_end=year_end,
        attempt_count=attempt_count,
        http_status=http_status,
        provider_status=provider_status,
        response_byte_count=response_bytes,
        ingest_notes=ingest_notes,
    )
    store = PostgresObservationStore(conn, retrieval_id=retrieval_id)
    outcome = ingest_from_fetch(
        store,
        fetch_result,
        rights,
        optional=optional,
    )
    return store, outcome


def _endpoint_host(adapter: ProviderAdapter) -> str | None:
    if isinstance(adapter, BlsUnemploymentAdapter):
        return "api.bls.gov" if adapter.config.live else None
    return None


def _diagnostics(
    adapter: ProviderAdapter,
    fetch_result: object,
) -> tuple[list[str], int | None, int | None, int, int | None, str | None, int | None]:
    series_ids: list[str] = []
    year_start: int | None = None
    year_end: int | None = None
    attempt_count = 1
    http_status: int | None = None
    provider_status: str | None = None
    response_bytes: int | None = None
    if isinstance(adapter, BlsUnemploymentAdapter):
        series_ids = ["LNS14000000"]
        year_start = adapter.config.start_year
        year_end = adapter.config.end_year
        if hasattr(adapter, "_last_diagnostics"):
            diag = adapter._last_diagnostics  # noqa: SLF001
            if diag is not None:
                attempt_count = diag.attempts
                http_status = diag.http_status
                provider_status = diag.bls_status
                response_bytes = diag.response_bytes
    return (
        series_ids,
        year_start,
        year_end,
        attempt_count,
        http_status,
        provider_status,
        response_bytes,
    )
