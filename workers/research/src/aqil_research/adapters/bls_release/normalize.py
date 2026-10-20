"""Normalise parsed releases to the sourced_update contract."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4

from aqil_research.adapters.bls_release.constants import SOURCE_ID
from aqil_research.adapters.bls_release.parse import ParsedReleaseItem
from aqil_research.contracts.sourced_update import SourcedUpdate


@dataclass(frozen=True, slots=True)
class SourcedUpdateDraft:
    title: str
    canonical_url: str
    published_at: datetime | None
    content_hash: str


def drafts_from_items(items: tuple[ParsedReleaseItem, ...]) -> tuple[SourcedUpdateDraft, ...]:
    drafts: list[SourcedUpdateDraft] = []
    seen: set[str] = set()
    for item in items:
        content_hash = content_hash_for_item(
            title=item.title,
            canonical_url=item.canonical_url,
            published_at=item.published_at,
        )
        if content_hash in seen:
            continue
        seen.add(content_hash)
        drafts.append(
            SourcedUpdateDraft(
                title=item.title,
                canonical_url=item.canonical_url,
                published_at=item.published_at,
                content_hash=content_hash,
            ),
        )
    return tuple(drafts)


def content_hash_for_item(
    *,
    title: str,
    canonical_url: str,
    published_at: datetime | None,
) -> str:
    payload = {
        "source_id": SOURCE_ID,
        "title": title,
        "canonical_url": canonical_url,
        "published_at": published_at.isoformat() if published_at is not None else None,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def to_sourced_update(
    draft: SourcedUpdateDraft,
    *,
    retrieval_id: str,
    retrieved_at: datetime,
) -> SourcedUpdate:
    return SourcedUpdate(
        update_id=str(uuid4()),
        source_id=SOURCE_ID,
        title=draft.title,
        canonical_url=draft.canonical_url,
        published_at=draft.published_at,
        retrieved_at=retrieved_at,
        retrieval_id=retrieval_id,
        content_hash=draft.content_hash,
        correction_of=None,
        status="sourced",
    )


def feed_response_fingerprint(body: bytes, *, adapter_id: str, adapter_version: str) -> str:
    meta = f"{adapter_id}:{adapter_version}:{SOURCE_ID}"
    digest = hashlib.sha256(body).hexdigest()
    return hashlib.sha256(f"{meta}:{digest}".encode()).hexdigest()
