"""Publication gate: spans, feed freshness, method cards and syndication."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from aqil_research.editorial.claim_verifier import (
    ClaimVerificationError,
    verify_claim_for_publication,
)

NOW = datetime(2026, 10, 20, 12, 0, tzinfo=UTC)
MAX_AGE_SECONDS = 6 * 60 * 60


def _method_card(**updates: object) -> dict[str, object]:
    path = Path(__file__).parent / "fixtures" / "sahm_method_card.v1.json"
    card = json.loads(path.read_text(encoding="utf-8"))
    card["licence_status"] = "permitted_private"
    card.update(updates)
    return card


def _feed(**updates: object) -> dict[str, object]:
    fresh_at = NOW - timedelta(hours=1)
    feed: dict[str, object] = {
        "source_id": "fixture_source",
        "last_success_at": fresh_at,
        "last_attempt_at": fresh_at,
        "last_attempt_succeeded": True,
        "in_flight": False,
        "partial_payload": False,
        "evaluated_at": NOW,
        "max_age_seconds": MAX_AGE_SECONDS,
    }
    feed.update(updates)
    return feed


def _documents(count: int = 10, cluster_key: str = "one-announcement") -> list[dict[str, str]]:
    return [
        {
            "document_id": f"copy-{index}",
            "cluster_key": cluster_key,
            "outlet_id": f"outlet-{index}",
        }
        for index in range(count)
    ]


def _claim() -> dict[str, object]:
    return {
        "statement": "Fixture excerpt records 4.5.",
        "cited_numbers": [
            {"value": "4.5", "source_span": "Fixture excerpt records 4.5."},
        ],
        "feed": _feed(),
        "method_card": _method_card(),
        "documents": _documents(),
        "confirmation_count": 1,
    }


def test_unverified_claim_blocks_publication() -> None:
    with pytest.raises(ClaimVerificationError):
        verify_claim_for_publication({})


def test_research_run_payload_stays_blocked() -> None:
    with pytest.raises(ClaimVerificationError):
        verify_claim_for_publication(
            {
                "verification_status": "unverified",
                "narrative": "Fixture calculation recorded 4.5.",
                "publication_allowed": False,
            },
        )


@pytest.mark.parametrize(
    ("statement", "value", "span"),
    [
        ("Fixture excerpt records 9.9.", "9.9", "Fixture excerpt records 4.5."),
        ("Fixture excerpt records 4.5.", "4.5", "Fixture excerpt records 14.5."),
        ("Fixture excerpt records 4.5.", "4.5", "Fixture excerpt records 4.50."),
    ],
)
def test_cited_number_outside_source_span_blocks_publication(
    statement: str,
    value: str,
    span: str,
) -> None:
    claim = _claim()
    claim["statement"] = statement
    claim["cited_numbers"] = [{"value": value, "source_span": span}]
    with pytest.raises(ClaimVerificationError, match="outside its source span"):
        verify_claim_for_publication(claim)


def test_statement_number_without_a_span_stays_blocked() -> None:
    claim = _claim()
    claim["statement"] = "Fixture excerpt records 4.5 and 9.9."
    with pytest.raises(ClaimVerificationError, match="9.9"):
        verify_claim_for_publication(claim)


def test_claim_without_cited_numbers_stays_blocked() -> None:
    claim = _claim()
    claim["cited_numbers"] = []
    with pytest.raises(ClaimVerificationError):
        verify_claim_for_publication(claim)


@pytest.mark.parametrize(
    ("updates", "message"),
    [
        (
            {
                "last_success_at": NOW - timedelta(hours=7),
                "last_attempt_at": NOW - timedelta(hours=7),
            },
            "stale",
        ),
        (
            {
                "last_attempt_at": NOW - timedelta(minutes=5),
                "last_attempt_succeeded": False,
            },
            "interrupted",
        ),
        ({"in_flight": True}, "interrupted"),
        ({"partial_payload": True}, "interrupted"),
        (
            {
                "last_success_at": None,
                "last_attempt_at": None,
                "last_attempt_succeeded": False,
            },
            "never_polled",
        ),
    ],
)
def test_unusable_feed_cannot_publish(updates: dict[str, object], message: str) -> None:
    claim = _claim()
    claim["feed"] = _feed(**updates)
    with pytest.raises(ClaimVerificationError, match=message):
        verify_claim_for_publication(claim)


def test_partial_feed_stays_blocked_when_caller_allows_partial() -> None:
    claim = _claim()
    feed = _feed(partial_payload=True)
    feed["allow_partial_payload"] = True
    claim["feed"] = feed
    with pytest.raises(ClaimVerificationError, match="interrupted"):
        verify_claim_for_publication(claim)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("primary_reference", " ", "origin"),
        ("original_universe", " ", "universe"),
        ("formula_specification", None, "equation"),
        ("limitations", [], "limitations"),
        ("licence_status", "unknown", "rights"),
    ],
)
def test_incomplete_method_card_cannot_publish(field: str, value: object, message: str) -> None:
    claim = _claim()
    claim["method_card"] = _method_card(**{field: value})
    with pytest.raises(ClaimVerificationError, match=message):
        verify_claim_for_publication(claim)


def test_ten_copies_of_one_announcement_count_as_one_confirmation() -> None:
    claim = _claim()
    claim["confirmation_count"] = 10
    with pytest.raises(ClaimVerificationError, match="1 independent"):
        verify_claim_for_publication(claim)
    claim["confirmation_count"] = 1
    decision = verify_claim_for_publication(claim)
    assert decision.independent_confirmation_count == 1


def test_raw_copies_do_not_inflate_independent_confirmations() -> None:
    claim = _claim()
    claim["documents"] = [
        {"document_id": "a1", "cluster_key": "origin-a"},
        {"document_id": "a2", "cluster_key": "origin-a"},
        {"document_id": "b1", "cluster_key": "origin-b"},
    ]
    claim["confirmation_count"] = 3
    with pytest.raises(ClaimVerificationError, match="2 independent"):
        verify_claim_for_publication(claim)
    claim["confirmation_count"] = 2
    decision = verify_claim_for_publication(claim)
    assert decision.independent_confirmation_count == 2


@pytest.mark.parametrize("missing_key", ["feed", "method_card", "documents", "confirmation_count"])
def test_missing_gate_evidence_stays_blocked(missing_key: str) -> None:
    claim = _claim()
    del claim[missing_key]
    with pytest.raises(ClaimVerificationError):
        verify_claim_for_publication(claim)
