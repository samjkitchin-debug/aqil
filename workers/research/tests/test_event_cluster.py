"""AQ-036 — syndicated repeats cluster to one independent confirmation."""

from __future__ import annotations

from datetime import UTC, datetime

from aqil_research.events.cluster import (
    SyndicatedDocument,
    cluster_syndicated_documents,
    independent_confirmation_count,
)

ORIGIN = "press-release-hash-abc123"
BASE_TIME = datetime(2026, 10, 20, 8, 0, tzinfo=UTC)


def test_ten_copies_of_one_announcement_form_one_cluster() -> None:
    documents = tuple(
        SyndicatedDocument(
            document_id=f"doc-{index}",
            cluster_key=ORIGIN,
            outlet_id=f"outlet-{index}",
            published_at=BASE_TIME,
        )
        for index in range(10)
    )
    result = cluster_syndicated_documents(documents)
    assert result.raw_document_count == 10
    assert result.independent_confirmation_count == 1
    assert len(result.clusters) == 1
    assert len(result.clusters[0].document_ids) == 10
    assert independent_confirmation_count(documents) == 1


def test_independent_origins_count_separately() -> None:
    documents = (
        SyndicatedDocument(document_id="a1", cluster_key="origin-a"),
        SyndicatedDocument(document_id="a2", cluster_key="origin-a"),
        SyndicatedDocument(document_id="b1", cluster_key="origin-b"),
    )
    result = cluster_syndicated_documents(documents)
    assert result.raw_document_count == 3
    assert result.independent_confirmation_count == 2
