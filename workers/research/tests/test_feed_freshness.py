"""AQ-014 — stale or interrupted feeds fail closed."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from aqil_research.pipeline.feed_freshness import (
    FeedFreshnessError,
    FeedFreshnessPolicy,
    FeedFreshnessState,
    FeedPollSnapshot,
    IngestBudgetExhaustedError,
    IngestRetryBudget,
    assert_feed_fresh_for_ingest,
    assert_retry_budget,
    evaluate_feed_freshness,
    poll_idempotency_key,
)

NOW = datetime(2026, 10, 20, 12, 0, tzinfo=UTC)
POLICY = FeedFreshnessPolicy(max_age=timedelta(hours=6))


def test_fresh_feed_passes_ingest_gate() -> None:
    snapshot = FeedPollSnapshot(
        source_id="bls_cps_unemployment_rate",
        last_success_at=NOW - timedelta(hours=1),
        last_attempt_at=NOW - timedelta(hours=1),
        last_attempt_succeeded=True,
    )
    state = evaluate_feed_freshness(snapshot, POLICY, now=NOW)
    assert state == FeedFreshnessState.FRESH
    assert_feed_fresh_for_ingest(state)


def test_stale_feed_fails_closed() -> None:
    snapshot = FeedPollSnapshot(
        source_id="bls_cps_unemployment_rate",
        last_success_at=NOW - timedelta(hours=12),
        last_attempt_at=NOW - timedelta(hours=12),
        last_attempt_succeeded=True,
    )
    state = evaluate_feed_freshness(snapshot, POLICY, now=NOW)
    assert state == FeedFreshnessState.STALE
    with pytest.raises(FeedFreshnessError, match="stale"):
        assert_feed_fresh_for_ingest(state)


def test_interrupted_poll_fails_closed() -> None:
    snapshot = FeedPollSnapshot(
        source_id="news_wire",
        last_success_at=NOW - timedelta(minutes=30),
        last_attempt_at=NOW - timedelta(minutes=5),
        last_attempt_succeeded=False,
    )
    state = evaluate_feed_freshness(snapshot, POLICY, now=NOW)
    assert state == FeedFreshnessState.INTERRUPTED
    with pytest.raises(FeedFreshnessError, match="interrupted"):
        assert_feed_fresh_for_ingest(state)


def test_in_flight_poll_fails_closed() -> None:
    snapshot = FeedPollSnapshot(
        source_id="news_wire",
        last_success_at=NOW - timedelta(minutes=30),
        last_attempt_at=NOW - timedelta(minutes=1),
        last_attempt_succeeded=True,
        in_flight=True,
    )
    state = evaluate_feed_freshness(snapshot, POLICY, now=NOW)
    assert state == FeedFreshnessState.INTERRUPTED
    with pytest.raises(FeedFreshnessError):
        assert_feed_fresh_for_ingest(state)


def test_partial_payload_fails_closed_by_default() -> None:
    snapshot = FeedPollSnapshot(
        source_id="news_wire",
        last_success_at=NOW - timedelta(minutes=10),
        last_attempt_at=NOW - timedelta(minutes=10),
        last_attempt_succeeded=True,
        partial_payload=True,
    )
    state = evaluate_feed_freshness(snapshot, POLICY, now=NOW)
    assert state == FeedFreshnessState.INTERRUPTED


def test_never_polled_fails_closed() -> None:
    snapshot = FeedPollSnapshot(
        source_id="new_source",
        last_success_at=None,
        last_attempt_at=None,
        last_attempt_succeeded=False,
    )
    state = evaluate_feed_freshness(snapshot, POLICY, now=NOW)
    assert state == FeedFreshnessState.NEVER_POLLED
    with pytest.raises(FeedFreshnessError, match="never_polled"):
        assert_feed_fresh_for_ingest(state)


def test_retry_budget_and_idempotency_key() -> None:
    budget = IngestRetryBudget(max_attempts=3, attempts_used=3)
    with pytest.raises(IngestBudgetExhaustedError):
        assert_retry_budget(budget)
    assert poll_idempotency_key("src", "2026-10-20T08:00Z") == poll_idempotency_key(
        "src",
        "2026-10-20T08:00Z",
    )
    assert poll_idempotency_key("src", "a") != poll_idempotency_key("src", "b")
