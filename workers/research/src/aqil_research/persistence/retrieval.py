"""Persist immutable source retrieval records."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

import psycopg

from aqil_research.adapters.protocol import ProviderAdapter
from aqil_research.sources.rights import RightsDecision, RightsOperation, SourceRightsRecord


def rights_decision_snapshot(rights: SourceRightsRecord) -> dict[str, str]:
    """Permitted operations only — no credentials or URLs."""
    snapshot: dict[str, str] = {
        "source_id": rights.source_id,
        "dataset_id": rights.dataset_id,
        "operational_status": rights.operational_status.value,
    }
    for operation in RightsOperation:
        decision = rights.decision_for(operation)
        if decision == RightsDecision.PERMITTED:
            snapshot[f"permitted_{operation.value}"] = "true"
    return snapshot


def insert_source_retrieval(
    conn: psycopg.Connection,
    *,
    rights: SourceRightsRecord,
    adapter: ProviderAdapter,
    retrieved_at: datetime,
    collection_mode: str,
    endpoint_host: str | None,
    request_series_ids: list[str],
    request_year_start: int | None,
    request_year_end: int | None,
    attempt_count: int,
    http_status: int | None,
    provider_status: str | None,
    response_byte_count: int | None,
    ingest_notes: list[str],
) -> UUID:
    identity = adapter.identity
    safe_attempts = max(1, attempt_count)
    with conn.cursor() as cur:
        cur.execute(
            """
            insert into research.source_retrievals (
              source_id, dataset_id, rights_record_id, provider_id,
              adapter_id, adapter_version, retrieved_at, collection_mode,
              endpoint_host, request_series_ids, request_year_start, request_year_end,
              attempt_count, http_status, provider_status, response_byte_count,
              rights_decision_snapshot, ingest_notes
            )
            values (
              %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
              %s::jsonb, %s
            )
            returning retrieval_id
            """,
            (
                identity.source_id,
                identity.dataset_id,
                rights.source_id,
                "bls",
                identity.adapter_id,
                identity.adapter_version,
                retrieved_at,
                collection_mode,
                endpoint_host,
                request_series_ids,
                request_year_start,
                request_year_end,
                safe_attempts,
                http_status,
                provider_status,
                response_byte_count,
                psycopg.types.json.Json(rights_decision_snapshot(rights)),
                ingest_notes,
            ),
        )
        row = cur.fetchone()
        if row is None:
            raise RuntimeError("failed to insert source_retrieval")
        return row[0]
