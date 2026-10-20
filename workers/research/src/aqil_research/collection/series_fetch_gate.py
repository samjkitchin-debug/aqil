"""Apply shared feed-freshness rules to a one-shot series API fetch."""

from __future__ import annotations

from datetime import datetime, timedelta

from aqil_research.pipeline.feed_freshness import (
    FeedFreshnessError,
    FeedFreshnessPolicy,
    FeedPollSnapshot,
    assert_feed_fresh_for_ingest,
    evaluate_feed_freshness,
)

# Monthly BLS CPS unemployment: refuse partial windows for current ingest.
DEFAULT_BLS_SERIES_MAX_AGE = timedelta(days=45)


class SeriesFetchNotUsableError(FeedFreshnessError):
    """Raised when a series response must not be persisted as current data."""


def assert_series_fetch_usable_for_ingest(
    *,
    source_id: str,
    retrieved_at: datetime,
    fetch_succeeded: bool,
    partial_payload: bool,
    policy: FeedFreshnessPolicy | None = None,
) -> None:
    """Fail closed when the fetch lifecycle or payload is not usable for ingest."""
    if not fetch_succeeded:
        raise SeriesFetchNotUsableError("series fetch did not succeed")
    snapshot = FeedPollSnapshot(
        source_id=source_id,
        last_success_at=retrieved_at,
        last_attempt_at=retrieved_at,
        last_attempt_succeeded=True,
        partial_payload=partial_payload,
    )
    resolved = policy or FeedFreshnessPolicy(
        max_age=DEFAULT_BLS_SERIES_MAX_AGE,
        allow_partial_payload=False,
    )
    state = evaluate_feed_freshness(snapshot, resolved, now=retrieved_at)
    try:
        assert_feed_fresh_for_ingest(state)
    except FeedFreshnessError as exc:
        raise SeriesFetchNotUsableError(str(exc)) from exc
