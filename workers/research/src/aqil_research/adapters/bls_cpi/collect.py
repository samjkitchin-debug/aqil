"""Collect CPI news releases through the existing BLS publication parser."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import psycopg

from aqil_research.adapters.bls_cpi.constants import (
    ADAPTER_ID,
    ADAPTER_VERSION,
    DATASET_ID,
    FEED_URL,
    SOURCE_ID,
)
from aqil_research.adapters.bls_release.client import (
    BlsReleaseClientError,
    fetch_empsit_publication_feed,
)
from aqil_research.adapters.bls_release.parse import parse_publication_feed
from aqil_research.adapters.protocol import ProviderIdentity
from aqil_research.contracts.sourced_update import SourcedUpdate
from aqil_research.persistence.retrieval import insert_source_retrieval
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
class _CpiIdentity:
    identity: ProviderIdentity


@dataclass(frozen=True, slots=True)
class CpiCollectResult:
    outcome: str
    inserted: int
    unchanged: int


def collect_bls_cpi(
    conn: psycopg.Connection,
    *,
    live: bool,
    fixture_path: Path | None = None,
    retrieved_at: datetime | None = None,
) -> CpiCollectResult:
    now = retrieved_at or datetime.now(tz=UTC)
    rights = find_source_rights(load_source_rights(), source_id=SOURCE_ID)
    if rights is None or not source_usable(rights, RightsOperation.AUTOMATED_ACCESS):
        return CpiCollectResult("failed_rights", 0, 0)
    if not source_usable(rights, RightsOperation.RAW_DATA_RETENTION):
        return CpiCollectResult("failed_rights", 0, 0)
    try:
        fetched = fetch_empsit_publication_feed(
            live=live,
            fixture_path=fixture_path,
            feed_url=None if not live else FEED_URL,
        )
        parsed = parse_publication_feed(fetched.body, base_url=FEED_URL)
    except (BlsReleaseClientError, ValueError):
        return CpiCollectResult("failed_fetch", 0, 0)

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
    gated = gate_sourced_updates(
        items,
        FeedPollSnapshot(
            source_id=SOURCE_ID,
            last_success_at=now,
            last_attempt_at=now,
            last_attempt_succeeded=True,
            partial_payload=False,
        ),
        FeedFreshnessPolicy(max_age=_MAX_AGE),
        now=now,
    )
    if gated.freshness is not FeedFreshnessState.FRESH:
        return CpiCollectResult(f"rejected_{gated.freshness.value}", 0, 0)

    adapter = _CpiIdentity(
        ProviderIdentity(
            adapter_id=ADAPTER_ID,
            adapter_version=ADAPTER_VERSION,
            source_id=SOURCE_ID,
            dataset_id=DATASET_ID,
        )
    )
    retrieval_id = insert_source_retrieval(
        conn,
        rights=rights,
        adapter=adapter,
        retrieved_at=now,
        collection_mode="live" if live else "fixture",
        endpoint_host="www.bls.gov" if live else "fixture",
        request_series_ids=["cpi-archive"],
        request_year_start=None,
        request_year_end=None,
        attempt_count=max(1, fetched.diagnostics.attempts),
        http_status=fetched.diagnostics.http_status,
        provider_status=None,
        response_byte_count=fetched.diagnostics.response_bytes,
        ingest_notes=["CPI news-release feed"],
    )
    inserted = 0
    unchanged = 0
    for item in gated.accepted:
        content_hash = _content_hash(item.title, item.canonical_url, item.published_at)
        row = SourcedUpdate(
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
        )
        if _insert_update(conn, row):
            inserted += 1
        else:
            unchanged += 1
    return CpiCollectResult("completed", inserted, unchanged)


def _content_hash(title: str, canonical_url: str, published_at: datetime | None) -> str:
    payload = {
        "source_id": SOURCE_ID,
        "title": title,
        "canonical_url": canonical_url,
        "published_at": published_at.isoformat() if published_at is not None else None,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


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
