"""In-memory and Postgres stores for sourced publication updates."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol, runtime_checkable
from uuid import uuid4

import psycopg

from aqil_research.adapters.bls_release.adapter import BlsEmpsitReleaseAdapter
from aqil_research.adapters.bls_release.normalize import SourcedUpdateDraft, to_sourced_update
from aqil_research.contracts.sourced_update import SourcedUpdate
from aqil_research.persistence.retrieval import insert_source_retrieval
from aqil_research.sources.rights import SourceRightsRecord


@dataclass(frozen=True, slots=True)
class SourcedUpdateAppendResult:
    inserted: int
    unchanged: int
    updates: tuple[SourcedUpdate, ...]
    retrieval_id: str | None


@runtime_checkable
class SourcedUpdateStore(Protocol):
    def persist_publication_fetch(
        self,
        *,
        rights: SourceRightsRecord,
        adapter: BlsEmpsitReleaseAdapter,
        retrieved_at: datetime,
        collection_mode: str,
        drafts: tuple[SourcedUpdateDraft, ...],
        response_fingerprint: str | None,
        endpoint_host: str | None,
        http_status: int | None,
        response_bytes: int | None,
        ingest_notes: list[str],
    ) -> SourcedUpdateAppendResult: ...


@dataclass
class InMemorySourcedUpdateStore:
    """Fixture and unit-test store without Postgres."""

    updates: list[SourcedUpdate] = field(default_factory=list)
    retrievals: list[str] = field(default_factory=list)
    _keys: set[tuple[str, str]] = field(default_factory=set)

    def persist_publication_fetch(
        self,
        *,
        rights: SourceRightsRecord,
        adapter: BlsEmpsitReleaseAdapter,
        retrieved_at: datetime,
        collection_mode: str,
        drafts: tuple[SourcedUpdateDraft, ...],
        response_fingerprint: str | None,
        endpoint_host: str | None,
        http_status: int | None,
        response_bytes: int | None,
        ingest_notes: list[str],
    ) -> SourcedUpdateAppendResult:
        _ = (
            rights,
            adapter,
            collection_mode,
            response_fingerprint,
            endpoint_host,
            http_status,
            response_bytes,
            ingest_notes,
        )
        retrieval_id = str(uuid4())
        self.retrievals.append(retrieval_id)
        inserted = 0
        unchanged = 0
        stored: list[SourcedUpdate] = []
        for draft in drafts:
            key = (rights.source_id, draft.content_hash)
            if key in self._keys:
                unchanged += 1
                existing = next(
                    row for row in self.updates if row.content_hash == draft.content_hash
                )
                stored.append(existing)
                continue
            row = to_sourced_update(draft, retrieval_id=retrieval_id, retrieved_at=retrieved_at)
            self._keys.add(key)
            self.updates.append(row)
            stored.append(row)
            inserted += 1
        return SourcedUpdateAppendResult(
            inserted=inserted,
            unchanged=unchanged,
            updates=tuple(stored),
            retrieval_id=retrieval_id,
        )


@dataclass(slots=True)
class PostgresSourcedUpdateStore:
    """Append sourced updates via research.source_retrievals then research.sourced_updates."""

    _conn: psycopg.Connection

    def persist_publication_fetch(
        self,
        *,
        rights: SourceRightsRecord,
        adapter: BlsEmpsitReleaseAdapter,
        retrieved_at: datetime,
        collection_mode: str,
        drafts: tuple[SourcedUpdateDraft, ...],
        response_fingerprint: str | None,
        endpoint_host: str | None,
        http_status: int | None,
        response_bytes: int | None,
        ingest_notes: list[str],
    ) -> SourcedUpdateAppendResult:
        retrieval_id = insert_source_retrieval(
            self._conn,
            rights=rights,
            adapter=adapter,
            retrieved_at=retrieved_at,
            collection_mode=collection_mode,
            endpoint_host=endpoint_host,
            request_series_ids=["empsit-archive"],
            request_year_start=None,
            request_year_end=None,
            attempt_count=max(
                1,
                adapter._last_fetch.diagnostics.attempts if adapter._last_fetch else 1,
            ),
            http_status=http_status,
            provider_status=None,
            response_byte_count=response_bytes,
            ingest_notes=ingest_notes,
            response_fingerprint=response_fingerprint,
        )
        inserted = 0
        unchanged = 0
        stored: list[SourcedUpdate] = []
        for draft in drafts:
            row = to_sourced_update(
                draft,
                retrieval_id=str(retrieval_id),
                retrieved_at=retrieved_at,
            )
            was_new = _insert_sourced_update(self._conn, row)
            if was_new:
                inserted += 1
            else:
                unchanged += 1
                row = _load_existing(self._conn, rights.source_id, draft.content_hash) or row
            stored.append(row)
        return SourcedUpdateAppendResult(
            inserted=inserted,
            unchanged=unchanged,
            updates=tuple(stored),
            retrieval_id=str(retrieval_id),
        )


def _insert_sourced_update(conn: psycopg.Connection, row: SourcedUpdate) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            """
            insert into research.sourced_updates (
              update_id, schema_version, source_id, title, canonical_url,
              published_at, retrieved_at, retrieval_id, content_hash,
              correction_of, status
            )
            values (
              %s::uuid, %s, %s, %s, %s, %s, %s, %s::uuid, %s, %s, %s
            )
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
        inserted_row = cur.fetchone()
        return inserted_row is not None


def _load_existing(
    conn: psycopg.Connection,
    source_id: str,
    content_hash: str,
) -> SourcedUpdate | None:
    with conn.cursor() as cur:
        cur.execute(
            """
            select update_id, schema_version, source_id, title, canonical_url,
                   published_at, retrieved_at, retrieval_id, content_hash,
                   correction_of, status
            from research.sourced_updates
            where source_id = %s and content_hash = %s
            limit 1
            """,
            (source_id, content_hash),
        )
        fetched = cur.fetchone()
    if fetched is None:
        return None
    return SourcedUpdate(
        update_id=str(fetched[0]),
        schema_version=fetched[1],
        source_id=fetched[2],
        title=fetched[3],
        canonical_url=fetched[4],
        published_at=fetched[5],
        retrieved_at=fetched[6],
        retrieval_id=str(fetched[7]),
        content_hash=fetched[8],
        correction_of=str(fetched[9]) if fetched[9] is not None else None,
        status=fetched[10],
    )
