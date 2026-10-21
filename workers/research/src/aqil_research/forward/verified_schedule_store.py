"""Persist verified BLS calendar rows in the existing catalyst table."""

from __future__ import annotations

from datetime import datetime

import psycopg

from aqil_research.forward.adapters.bls_ics_schedule import (
    SOURCE_ID,
    SOURCE_LOCATOR,
    BlsIcsRelease,
    release_event_id,
    release_to_catalyst_payload,
)
from aqil_research.persistence.retrieval import rights_decision_snapshot
from aqil_research.sources.rights import SourceRightsRecord


def insert_calendar_retrieval(
    conn: psycopg.Connection,
    *,
    rights: SourceRightsRecord,
    retrieved_at: datetime,
    collection_mode: str,
    http_status: int | None,
    response_byte_count: int | None,
    ingest_notes: list[str],
) -> str:
    with conn.cursor() as cur:
        cur.execute(
            """
            insert into research.source_retrievals (
              source_id, dataset_id, rights_record_id, provider_id,
              adapter_id, adapter_version, retrieved_at, collection_mode,
              endpoint_host, request_series_ids, attempt_count, http_status,
              response_byte_count, rights_decision_snapshot, ingest_notes
            )
            values (
              %s, %s, %s, 'bls', 'bls_ics_schedule', '1.0.0', %s, %s,
              %s, %s, 1, %s, %s, %s::jsonb, %s
            )
            returning retrieval_id::text
            """,
            (
                rights.source_id,
                rights.dataset_id,
                rights.source_id,
                retrieved_at,
                collection_mode,
                "www.bls.gov" if collection_mode == "live" else None,
                ["bls.ics"],
                http_status,
                response_byte_count,
                psycopg.types.json.Json(rights_decision_snapshot(rights)),
                ingest_notes,
            ),
        )
        row = cur.fetchone()
    if row is None:
        raise RuntimeError("failed to insert calendar retrieval")
    return str(row[0])


def upsert_verified_release(
    conn: psycopg.Connection,
    release: BlsIcsRelease,
    *,
    retrieved_at: datetime,
) -> str:
    """Insert a confirmed future release, or refresh its verification time.

    A changed start time is appended as a revision, then the current row is updated.
    Returns new, unchanged, or revised.
    """
    if release.stamp_basis not in {"utc", "us-eastern"}:
        raise ValueError("only a stated clock time can be stored")
    if release.status.upper() != "CONFIRMED":
        raise ValueError("an unconfirmed calendar entry cannot be stored as verified")

    payload = release_to_catalyst_payload(release, retrieved_at=retrieved_at)
    event_id = release_event_id(release)
    scheduled_at = release.starts_at
    with conn.cursor() as cur:
        cur.execute(
            """
            select scheduled_at
            from forward.catalyst_events
            where event_id = %s
            """,
            (event_id,),
        )
        existing = cur.fetchone()
        if existing is None:
            cur.execute(
                """
                insert into forward.catalyst_events (
                  event_id, schema_version, category, subject_type, subject_id,
                  title, scheduled_at, timezone, date_precision, status,
                  source_id, source_locator, provider_published_at,
                  first_observed_at, last_verified_at, payload, evidence_class
                )
                values (
                  %s, '1.0', %s, %s, %s,
                  %s, %s, %s, 'confirmed', %s,
                  %s, %s, null,
                  %s, %s, %s::jsonb, 'verified_schedule'
                )
                """,
                (
                    event_id,
                    payload["category"],
                    payload["subject_type"],
                    payload["subject_id"],
                    release.summary,
                    scheduled_at,
                    payload["timezone"],
                    payload["status"],
                    SOURCE_ID,
                    SOURCE_LOCATOR,
                    retrieved_at,
                    retrieved_at,
                    psycopg.types.json.Json(payload),
                ),
            )
            return "new"

        previous = existing[0]
        if previous == scheduled_at:
            cur.execute(
                """
                update forward.catalyst_events
                set last_verified_at = %s
                where event_id = %s
                  and source_id = %s
                  and evidence_class = 'verified_schedule'
                """,
                (retrieved_at, event_id, SOURCE_ID),
            )
            return "unchanged"

        cur.execute(
            """
            insert into forward.catalyst_event_revisions (
              event_id, previous_scheduled_at, new_scheduled_at,
              observed_at, reason, source_id
            )
            values (%s, %s, %s, %s, %s, %s)
            """,
            (
                event_id,
                previous,
                scheduled_at,
                retrieved_at,
                "The official calendar stated a different start time.",
                SOURCE_ID,
            ),
        )
        cur.execute(
            """
            update forward.catalyst_events
            set scheduled_at = %s,
                last_verified_at = %s,
                payload = %s::jsonb
            where event_id = %s
              and source_id = %s
              and evidence_class = 'verified_schedule'
            """,
            (
                scheduled_at,
                retrieved_at,
                psycopg.types.json.Json(payload),
                event_id,
                SOURCE_ID,
            ),
        )
        return "revised"
