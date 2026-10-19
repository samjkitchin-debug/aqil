"""Cluster syndicated copies vs independent evidence (AQ-036)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class SyndicatedDocument:
    """One collected document instance; cluster_key identifies the underlying origin event."""

    document_id: str
    cluster_key: str
    outlet_id: str | None = None
    published_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class EventCluster:
    cluster_key: str
    document_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SyndicationClusterResult:
    clusters: tuple[EventCluster, ...]
    raw_document_count: int
    independent_confirmation_count: int


def cluster_syndicated_documents(
    documents: tuple[SyndicatedDocument, ...],
) -> SyndicationClusterResult:
    """Group reprints; ten copies of one announcement form one cluster."""
    grouped: dict[str, list[str]] = {}
    for doc in documents:
        grouped.setdefault(doc.cluster_key, []).append(doc.document_id)

    clusters = tuple(
        EventCluster(cluster_key=key, document_ids=tuple(sorted(ids)))
        for key, ids in sorted(grouped.items())
    )
    independent = len(clusters)
    return SyndicationClusterResult(
        clusters=clusters,
        raw_document_count=len(documents),
        independent_confirmation_count=independent,
    )


def independent_confirmation_count(documents: tuple[SyndicatedDocument, ...]) -> int:
    """Convenience wrapper — syndicated repeats do not inflate confirmation count."""
    return cluster_syndicated_documents(documents).independent_confirmation_count


__all__ = [
    "EventCluster",
    "SyndicatedDocument",
    "SyndicationClusterResult",
    "cluster_syndicated_documents",
    "independent_confirmation_count",
]
