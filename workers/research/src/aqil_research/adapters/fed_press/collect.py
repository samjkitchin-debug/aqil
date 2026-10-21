"""Collect Board monetary-policy press releases through the publication gate."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4
from xml.etree.ElementTree import ParseError

import psycopg

from aqil_research.adapters.fed_press.client import FedPressClientError, fetch_monetary_press_feed
from aqil_research.adapters.fed_press.constants import (
    ADAPTER_ID,
    ADAPTER_VERSION,
    DATASET_ID,
    SOURCE_ID,
)
from aqil_research.adapters.fed_press.parse import parse_monetary_press_feed
from aqil_research.contracts.sourced_update import SourcedUpdate
from aqil_research.pipeline.amendments import link_amendment
from aqil_research.pipeline.feed_freshness import (
    FeedFreshnessPolicy,
    FeedFreshnessState,
    FeedPollSnapshot,
)
from aqil_research.pipeline.sourced_update_gate import PublicationItem, gate_sourced_updates
from aqil_research.sources.rights import (
    RightsOperation,
    find_source_rights,
    load_source_rights,
    source_usable,
)

_MAX_AGE = timedelta(hours=6)


@dataclass(frozen=True, slots=True)
class FedPressCollectResult:
    outcome: str
    inserted: int
    unchanged: int
    received: int


def collect_fed_monetary_press(
    conn: psycopg.Connection,
    *,
    live: bool,
    fixture_path: Path | None = None,
    retrieved_at: datetime | None = None,
) -> FedPressCollectResult:
    now = retrieved_at or datetime.now(tz=UTC)
    rights = find_source_rights(load_source_rights(), source_id=SOURCE_ID)
    if rights is None or not source_usable(rights, RightsOperation.AUTOMATED_ACCESS):
        return FedPressCollectResult("failed_rights", 0, 0, 0)
    if not source_usable(rights, RightsOperation.RAW_DATA_RETENTION):
        return FedPressCollectResult("failed_rights", 0, 0, 0)

    try:
        fetched = fetch_monetary_press_feed(live=live, fixture_path=fixture_path)
        parsed = parse_monetary_press_feed(fetched.body)
    except (FedPressClientError, ValueError, ParseError):
        return FedPressCollectResult("failed_fetch", 0, 0, 0)

    items = tuple(
        PublicationItem(
            title=item.title,
            canonical_url=item.canonical_url,
            published_at=item.published_at,
            retrieved_at=now,
            source_id=SOURCE_ID,
        )
        for item in parsed
        if item.published_at is not None and item.published_at <= now
    )
    snapshot = FeedPollSnapshot(
        source_id=SOURCE_ID,
        last_success_at=now,
        last_attempt_at=now,
        last_attempt_succeeded=True,
        partial_payload=False,
    )
    gated = gate_sourced_updates(
        items,
        snapshot,
        FeedFreshnessPolicy(max_age=_MAX_AGE),
        now=now,
    )
    if gated.freshness is not FeedFreshnessState.FRESH:
        return FedPressCollectResult(f"rejected_{gated.freshness.value}", 0, 0, len(parsed))

    retrieval_id = _insert_retrieval(
        conn,
        rights_id=rights.source_id,
        retrieved_at=now,
        collection_mode="live" if live else "fixture",
        http_status=fetched.http_status,
        response_bytes=len(fetched.body),
        endpoint_host=fetched.endpoint_host,
    )
    inserted = 0
    unchanged = 0
    for item in gated.accepted:
        content_hash = _content_hash(item.title, item.canonical_url, item.published_at)
        row = link_amendment(
            conn,
            SourcedUpdate(
                update_id=str(uuid4()),
                source_id=SOURCE_ID,
                title=item.title,
                canonical_url=item.canonical_url,
                published_at=item.published_at,
                retrieved_at=now,
                retrieval_id=str(retrieval_id),
                content_hash=content_hash,
                correction_of=None,
                status="sourced",
            ),
        )
        if _insert_update(conn, row):
            inserted += 1
        else:
            unchanged += 1
    return FedPressCollectResult("completed", inserted, unchanged, len(parsed))


def _content_hash(title: str, canonical_url: str, published_at: datetime | None) -> str:
    payload = {
        "source_id": SOURCE_ID,
        "title": title,
        "canonical_url": canonical_url,
        "published_at": published_at.isoformat() if published_at is not None else None,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _insert_retrieval(
    conn: psycopg.Connection,
    *,
    rights_id: str,
    retrieved_at: datetime,
    collection_mode: str,
    http_status: int | None,
    response_bytes: int,
    endpoint_host: str,
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
              %s, %s, %s, 'federal_reserve', %s, %s, %s, %s, %s, '{}', 1, %s, %s,
              %s::jsonb, %s
            )
            returning retrieval_id
            """,
            (
                SOURCE_ID,
                DATASET_ID,
                rights_id,
                ADAPTER_ID,
                ADAPTER_VERSION,
                retrieved_at,
                collection_mode,
                endpoint_host,
                http_status,
                response_bytes,
                json.dumps({"source_id": SOURCE_ID, "automated_access": "permitted"}),
                ["monetary policy press feed"],
            ),
        )
        row = cur.fetchone()
    if row is None:
        raise RuntimeError("press retrieval was not stored")
    return str(row[0])


def _insert_update(conn: psycopg.Connection, row: SourcedUpdate) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            """
            insert into research.sourced_updates (
              update_id, schema_version, source_id, title, canonical_url,
              published_at, retrieved_at, retrieval_id, content_hash,
              correction_of, status
            )
            values (%s::uuid, %s, %s, %s, %s, %s, %s, %s::uuid, %s, %s, %s)
            on conflict (source_id, content_hash) do nothing
            returning update_id
            """,
            (
                row.update_id,
                row.schema_version,
                row.source_id,
                row.title,
                row.canonical_url,
                row.published_at,
                row.retrieved_at,
                row.retrieval_id,
                row.content_hash,
                row.correction_of,
                row.status,
            ),
        )
        return cur.fetchone() is not None
