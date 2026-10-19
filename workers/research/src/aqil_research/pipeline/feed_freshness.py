"""Feed poll freshness, retry budget and idempotency — fail closed when unusable (AQ-014)."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum


class FeedFreshnessState(StrEnum):
    FRESH = "fresh"
    STALE = "stale"
    INTERRUPTED = "interrupted"
    NEVER_POLLED = "never_polled"


class FeedFreshnessError(Exception):
    """Raised when a feed cannot be used for ingest or downstream research."""


@dataclass(frozen=True, slots=True)
class FeedPollSnapshot:
    """Last-known poll lifecycle for one source feed."""

    source_id: str
    last_success_at: datetime | None
    last_attempt_at: datetime | None
    last_attempt_succeeded: bool
    in_flight: bool = False
    partial_payload: bool = False


@dataclass(frozen=True, slots=True)
class FeedFreshnessPolicy:
    max_age: timedelta
    allow_partial_payload: bool = False


@dataclass(frozen=True, slots=True)
class IngestRetryBudget:
    max_attempts: int
    attempts_used: int = 0

    def remaining(self) -> int:
        return max(0, self.max_attempts - self.attempts_used)

    def with_attempt(self) -> IngestRetryBudget:
        return IngestRetryBudget(
            max_attempts=self.max_attempts,
            attempts_used=self.attempts_used + 1,
        )


class IngestBudgetExhaustedError(Exception):
    """Raised when a poll would exceed the configured retry budget."""


def poll_idempotency_key(source_id: str, window_label: str) -> str:
    """Stable key for one scheduled poll window (duplicate polls are no-ops)."""
    raw = f"{source_id}:{window_label}"
    return hashlib.sha256(raw.encode()).hexdigest()


def evaluate_feed_freshness(
    snapshot: FeedPollSnapshot,
    policy: FeedFreshnessPolicy,
    *,
    now: datetime,
) -> FeedFreshnessState:
    """Classify feed usability. Stale and interrupted states must not silently fill gaps."""
    if snapshot.in_flight:
        return FeedFreshnessState.INTERRUPTED
    if snapshot.last_attempt_at is not None and not snapshot.last_attempt_succeeded:
        return FeedFreshnessState.INTERRUPTED
    if snapshot.partial_payload and not policy.allow_partial_payload:
        return FeedFreshnessState.INTERRUPTED
    if snapshot.last_success_at is None:
        return FeedFreshnessState.NEVER_POLLED
    if now - snapshot.last_success_at > policy.max_age:
        return FeedFreshnessState.STALE
    return FeedFreshnessState.FRESH


def assert_feed_fresh_for_ingest(state: FeedFreshnessState) -> None:
    """Fail closed unless the feed is explicitly fresh."""
    if state == FeedFreshnessState.FRESH:
        return
    raise FeedFreshnessError(
        f"feed freshness is {state.value}; ingest blocked (no silent backfill)",
    )


def assert_retry_budget(budget: IngestRetryBudget) -> None:
    if budget.remaining() <= 0:
        raise IngestBudgetExhaustedError(
            f"retry budget exhausted ({budget.attempts_used}/{budget.max_attempts} attempts)",
        )


__all__ = [
    "FeedFreshnessError",
    "FeedFreshnessPolicy",
    "FeedFreshnessState",
    "FeedPollSnapshot",
    "IngestBudgetExhaustedError",
    "IngestRetryBudget",
    "assert_feed_fresh_for_ingest",
    "assert_retry_budget",
    "evaluate_feed_freshness",
    "poll_idempotency_key",
]
