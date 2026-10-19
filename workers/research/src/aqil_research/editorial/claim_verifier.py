"""Publication gate for claims (AQ-013, AQ-014, AQ-030, AQ-036).

A claim is published only when every cited number is inside its source span,
the feed is fresh, the method card can enter the registry, and the confirmation
count equals the independent event-cluster count. Anything else stays blocked.
This gate does not create research conclusions.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from pydantic import ValidationError

from aqil_research.contracts.method_card import MethodCard
from aqil_research.events.cluster import SyndicatedDocument, cluster_syndicated_documents
from aqil_research.methods.card_registry import (
    MethodCardRegistryError,
    MethodologyCardRegistry,
)
from aqil_research.pipeline.feed_freshness import (
    FeedFreshnessError,
    FeedFreshnessPolicy,
    FeedPollSnapshot,
    assert_feed_fresh_for_ingest,
    evaluate_feed_freshness,
)

_NUMBER_TOKEN = re.compile(r"-?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?")


class ClaimVerificationError(Exception):
    """Raised when a claim cannot be published."""


@dataclass(frozen=True, slots=True)
class PublicationDecision:
    """Result of a claim that passed the publication gate."""

    independent_confirmation_count: int


def verify_claim_for_publication(claim: dict[str, Any]) -> PublicationDecision:
    """Publish only a claim whose numbers, feed, method card and confirmations check out."""
    if not isinstance(claim, dict):
        raise ClaimVerificationError("unsupported claim; publication blocked")
    status = claim.get("verification_status")
    if status is not None and status != "supported":
        raise ClaimVerificationError("unsupported claim; publication blocked")
    _assert_cited_numbers_inside_source_spans(claim)
    _assert_feed_can_publish(claim)
    _assert_method_card_can_publish(claim)
    return _assert_independent_confirmations(claim)


def _assert_cited_numbers_inside_source_spans(claim: dict[str, Any]) -> None:
    statement = claim.get("statement")
    if not isinstance(statement, str) or not statement.strip():
        raise ClaimVerificationError("unsupported claim; publication blocked")
    raw_cited = claim.get("cited_numbers")
    if not isinstance(raw_cited, list) or not raw_cited:
        raise ClaimVerificationError("unsupported claim; publication blocked")

    covered: list[tuple[str, str]] = []
    for item in raw_cited:
        if not isinstance(item, dict):
            raise ClaimVerificationError("unsupported claim; publication blocked")
        value = item.get("value")
        span = item.get("source_span")
        if not isinstance(value, str) or not isinstance(span, str):
            raise ClaimVerificationError(
                "cited number is outside its source span; publication blocked",
            )
        token = value.strip()
        if not _is_number_token(token) or not _number_in_span(token, span):
            raise ClaimVerificationError(
                f"cited number {token!r} is outside its source span; publication blocked",
            )
        covered.append((token, span))

    for token in _NUMBER_TOKEN.findall(statement):
        if not any(token == cited and _number_in_span(cited, span) for cited, span in covered):
            raise ClaimVerificationError(
                f"cited number {token!r} is outside its source span; publication blocked",
            )


def _assert_feed_can_publish(claim: dict[str, Any]) -> None:
    feed = claim.get("feed")
    if not isinstance(feed, dict):
        raise ClaimVerificationError("unsupported claim; feed freshness is missing")
    try:
        snapshot = FeedPollSnapshot(
            source_id=_require_text(feed, "source_id"),
            last_success_at=_optional_datetime(
                feed.get("last_success_at"), field="last_success_at"
            ),
            last_attempt_at=_optional_datetime(
                feed.get("last_attempt_at"), field="last_attempt_at"
            ),
            last_attempt_succeeded=_require_bool(feed, "last_attempt_succeeded"),
            in_flight=_require_bool(feed, "in_flight"),
            partial_payload=_require_bool(feed, "partial_payload"),
        )
        evaluated_at = _require_datetime(feed.get("evaluated_at"), field="evaluated_at")
        max_age_seconds = feed.get("max_age_seconds")
        if type(max_age_seconds) is not int or max_age_seconds <= 0:
            raise ClaimVerificationError("unsupported claim; feed max age is missing")
        policy = FeedFreshnessPolicy(
            max_age=timedelta(seconds=max_age_seconds),
            allow_partial_payload=False,
        )
        state = evaluate_feed_freshness(snapshot, policy, now=evaluated_at)
        assert_feed_fresh_for_ingest(state)
    except FeedFreshnessError as exc:
        raise ClaimVerificationError(str(exc)) from exc


def _assert_method_card_can_publish(claim: dict[str, Any]) -> None:
    raw_card = claim.get("method_card")
    if not isinstance(raw_card, dict):
        raise ClaimVerificationError("unsupported claim; method card is missing")
    try:
        card = MethodCard.model_validate(raw_card)
    except ValidationError as exc:
        raise ClaimVerificationError(
            "method card is incomplete or invalid; publication blocked",
        ) from exc
    try:
        MethodologyCardRegistry().register(card)
    except MethodCardRegistryError as exc:
        raise ClaimVerificationError(str(exc)) from exc


def _assert_independent_confirmations(claim: dict[str, Any]) -> PublicationDecision:
    raw_documents = claim.get("documents")
    if not isinstance(raw_documents, list) or not raw_documents:
        raise ClaimVerificationError("unsupported claim; source documents are missing")
    documents: list[SyndicatedDocument] = []
    for item in raw_documents:
        if not isinstance(item, dict):
            raise ClaimVerificationError("unsupported claim; source documents are missing")
        document_id = item.get("document_id")
        cluster_key = item.get("cluster_key")
        if not isinstance(document_id, str) or not document_id.strip():
            raise ClaimVerificationError("unsupported claim; source documents are missing")
        if not isinstance(cluster_key, str) or not cluster_key.strip():
            raise ClaimVerificationError("unsupported claim; source documents are missing")
        outlet_id = item.get("outlet_id")
        if outlet_id is not None and not isinstance(outlet_id, str):
            raise ClaimVerificationError("unsupported claim; source documents are missing")
        documents.append(
            SyndicatedDocument(
                document_id=document_id,
                cluster_key=cluster_key,
                outlet_id=outlet_id,
                published_at=_optional_datetime(item.get("published_at"), field="published_at"),
            ),
        )
    clustered = cluster_syndicated_documents(tuple(documents))
    counted = clustered.independent_confirmation_count
    stated = claim.get("confirmation_count")
    label = "confirmation" if counted == 1 else "confirmations"
    if type(stated) is not int or stated != counted:
        raise ClaimVerificationError(
            "claim confirmation count does not match "
            f"{counted} independent {label}; publication blocked",
        )
    return PublicationDecision(independent_confirmation_count=counted)


def _is_number_token(value: str) -> bool:
    return _NUMBER_TOKEN.fullmatch(value) is not None


def _number_in_span(value: str, span: str) -> bool:
    pattern = re.compile(rf"(?<![\d.,]){re.escape(value)}(?![\d,]|\.\d)")
    return pattern.search(span) is not None


def _require_text(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ClaimVerificationError(f"unsupported claim; {key} is missing")
    return value


def _require_bool(payload: dict[str, Any], key: str) -> bool:
    value = payload.get(key)
    if type(value) is not bool:
        raise ClaimVerificationError(f"unsupported claim; {key} is missing")
    return value


def _optional_datetime(value: object, *, field: str) -> datetime | None:
    if value is None:
        return None
    return _require_datetime(value, field=field)


def _require_datetime(value: object, *, field: str) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError as exc:
            raise ClaimVerificationError(
                f"unsupported claim; {field} is not a timestamp",
            ) from exc
    else:
        raise ClaimVerificationError(f"unsupported claim; {field} is not a timestamp")
    if parsed.tzinfo is None:
        raise ClaimVerificationError(f"unsupported claim; {field} lacks a timezone")
    return parsed
