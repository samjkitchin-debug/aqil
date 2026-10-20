"""Level A publication items stay sourced, clustered and fail-closed."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from aqil_research.pipeline.feed_freshness import (
    FeedFreshnessPolicy,
    FeedFreshnessState,
    FeedPollSnapshot,
)
from aqil_research.pipeline.sourced_update_gate import (
    AcceptedSourcedUpdate,
    PublicationItem,
    gate_sourced_updates,
)

NOW = datetime(2026, 10, 20, 12, 0, tzinfo=UTC)
POLICY = FeedFreshnessPolicy(max_age=timedelta(hours=6))
SOURCE_ID = "bls_employment_situation_archive"
SEPTEMBER_URL = "https://www.bls.gov/news.release/archives/empsit_10022026.htm"
AUGUST_URL = "https://www.bls.gov/news.release/archives/empsit_09042026.htm"


def _fresh_snapshot() -> FeedPollSnapshot:
    return FeedPollSnapshot(
        source_id=SOURCE_ID,
        last_success_at=NOW - timedelta(hours=1),
        last_attempt_at=NOW - timedelta(hours=1),
        last_attempt_succeeded=True,
    )


def _item(
    *,
    title: str = "Employment Situation, September 2026",
    canonical_url: str = SEPTEMBER_URL,
    published_at: datetime | None = datetime(2026, 10, 2, 12, 30, tzinfo=UTC),
    retrieved_at: datetime = NOW,
) -> PublicationItem:
    return PublicationItem(
        title=title,
        canonical_url=canonical_url,
        published_at=published_at,
        retrieved_at=retrieved_at,
        source_id=SOURCE_ID,
    )


def test_ten_identical_items_collapse_to_one() -> None:
    item = _item()
    result = gate_sourced_updates(
        tuple(_item() for _ in range(10)),
        _fresh_snapshot(),
        POLICY,
        now=NOW,
    )
    assert result.freshness is FeedFreshnessState.FRESH
    assert len(result.accepted) == 1
    accepted = result.accepted[0]
    assert accepted == AcceptedSourcedUpdate(
        title=item.title,
        canonical_url=item.canonical_url,
        published_at=item.published_at,
        retrieved_at=item.retrieved_at,
        source_id=item.source_id,
    )
    assert accepted.status == "sourced"
    assert "publication_allowed" not in AcceptedSourcedUpdate.__dataclass_fields__


def test_stale_feed_accepts_none() -> None:
    snapshot = FeedPollSnapshot(
        source_id=SOURCE_ID,
        last_success_at=NOW - timedelta(hours=12),
        last_attempt_at=NOW - timedelta(hours=12),
        last_attempt_succeeded=True,
    )
    result = gate_sourced_updates(
        tuple(_item() for _ in range(10)),
        snapshot,
        POLICY,
        now=NOW,
    )
    assert result.freshness is FeedFreshnessState.STALE
    assert result.accepted == ()


def test_interrupted_feed_accepts_none() -> None:
    snapshot = FeedPollSnapshot(
        source_id=SOURCE_ID,
        last_success_at=NOW - timedelta(minutes=30),
        last_attempt_at=NOW - timedelta(minutes=5),
        last_attempt_succeeded=False,
    )
    result = gate_sourced_updates((_item(),), snapshot, POLICY, now=NOW)
    assert result.freshness is FeedFreshnessState.INTERRUPTED
    assert result.accepted == ()


def test_never_polled_feed_accepts_none() -> None:
    snapshot = FeedPollSnapshot(
        source_id=SOURCE_ID,
        last_success_at=None,
        last_attempt_at=None,
        last_attempt_succeeded=False,
    )
    result = gate_sourced_updates((_item(),), snapshot, POLICY, now=NOW)
    assert result.freshness is FeedFreshnessState.NEVER_POLLED
    assert result.accepted == ()


def test_two_independent_items_stay_two() -> None:
    september = _item()
    august = _item(
        title="Employment Situation, August 2026",
        canonical_url=AUGUST_URL,
        published_at=datetime(2026, 9, 4, 12, 30, tzinfo=UTC),
    )
    result = gate_sourced_updates(
        (september, august),
        _fresh_snapshot(),
        POLICY,
        now=NOW,
    )
    assert result.freshness is FeedFreshnessState.FRESH
    assert len(result.accepted) == 2
    assert {item.title for item in result.accepted} == {september.title, august.title}
    assert {item.canonical_url for item in result.accepted} == {
        september.canonical_url,
        august.canonical_url,
    }
    assert all(item.status == "sourced" for item in result.accepted)


def test_status_other_than_sourced_is_rejected() -> None:
    with pytest.raises(ValueError, match="sourced"):
        AcceptedSourcedUpdate(
            title="Employment Situation, September 2026",
            canonical_url=SEPTEMBER_URL,
            published_at=datetime(2026, 10, 2, 12, 30, tzinfo=UTC),
            retrieved_at=NOW,
            source_id=SOURCE_ID,
            status="published",  # type: ignore[arg-type]
        )
