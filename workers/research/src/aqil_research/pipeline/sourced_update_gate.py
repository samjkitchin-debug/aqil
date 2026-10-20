"""Level A storage gate for publication items (AQ-014, AQ-036).

A fresh feed may contribute sourced updates. A stale, interrupted or
never-polled feed contributes none. Syndicated copies of one announcement
collapse to a single item. Accepted items are sourced only: this gate does
not allow publication and does not produce an investment conclusion.
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from aqil_research.events.cluster import SyndicatedDocument, cluster_syndicated_documents
from aqil_research.pipeline.feed_freshness import (
    FeedFreshnessPolicy,
    FeedFreshnessState,
    FeedPollSnapshot,
    evaluate_feed_freshness,
)


@dataclass(frozen=True, slots=True)
class PublicationItem:
    """One collected publication copy."""

    title: str
    canonical_url: str
    published_at: datetime | None
    retrieved_at: datetime
    source_id: str


@dataclass(frozen=True, slots=True)
class AcceptedSourcedUpdate:
    """A publication item that may be stored as a Level A sourced update."""

    title: str
    canonical_url: str
    published_at: datetime | None
    retrieved_at: datetime
    source_id: str
    status: Literal["sourced"] = "sourced"

    def __post_init__(self) -> None:
        if self.status != "sourced":
            raise ValueError("sourced update status must stay sourced")


@dataclass(frozen=True, slots=True)
class SourcedUpdateGateResult:
    """Items that may be stored, and the freshness decision that gated them."""

    freshness: FeedFreshnessState
    accepted: tuple[AcceptedSourcedUpdate, ...]


def gate_sourced_updates(
    items: Sequence[PublicationItem],
    snapshot: FeedPollSnapshot,
    policy: FeedFreshnessPolicy,
    *,
    now: datetime,
) -> SourcedUpdateGateResult:
    """Return Level A items that may be stored.

    Anything other than a fresh feed accepts nothing. Copies that share one
    announcement identity become one accepted item.
    """
    state = evaluate_feed_freshness(snapshot, policy, now=now)
    if state is not FeedFreshnessState.FRESH:
        return SourcedUpdateGateResult(freshness=state, accepted=())

    documents = tuple(
        SyndicatedDocument(
            document_id=f"{index:08d}",
            cluster_key=_announcement_cluster_key(item),
            outlet_id=item.source_id,
            published_at=item.published_at,
        )
        for index, item in enumerate(items)
    )
    clustered = cluster_syndicated_documents(documents)
    chosen = sorted(int(cluster.document_ids[0]) for cluster in clustered.clusters)
    accepted = tuple(_accept(items[index]) for index in chosen)
    if len(accepted) != clustered.independent_confirmation_count:
        return SourcedUpdateGateResult(freshness=state, accepted=())
    return SourcedUpdateGateResult(freshness=state, accepted=accepted)


def _accept(item: PublicationItem) -> AcceptedSourcedUpdate:
    return AcceptedSourcedUpdate(
        title=item.title,
        canonical_url=item.canonical_url,
        published_at=item.published_at,
        retrieved_at=item.retrieved_at,
        source_id=item.source_id,
    )


def _announcement_cluster_key(item: PublicationItem) -> str:
    """Identity of the announcement. Retrieval time does not make a new item."""
    published = "" if item.published_at is None else item.published_at.isoformat()
    raw = f"{item.source_id}\n{item.canonical_url}\n{item.title}\n{published}"
    return hashlib.sha256(raw.encode()).hexdigest()


__all__ = [
    "AcceptedSourcedUpdate",
    "PublicationItem",
    "SourcedUpdateGateResult",
    "gate_sourced_updates",
]
