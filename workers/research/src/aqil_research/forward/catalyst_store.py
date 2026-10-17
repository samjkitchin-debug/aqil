"""Idempotent catalyst persistence with schedule revision history."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

import psycopg


def _normalize_instant(value: object) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)
    return None


def _schedule_times_equal(previous_at: object, new_at: object) -> bool:
    return _normalize_instant(previous_at) == _normalize_instant(new_at)


def _coerce_payload(previous_payload: object) -> dict[str, object] | None:
    if isinstance(previous_payload, dict):
        return previous_payload
    if isinstance(previous_payload, str):
        parsed = json.loads(previous_payload)
        return parsed if isinstance(parsed, dict) else None
    return None


def _stable_payload(payload: dict[str, object]) -> dict[str, object]:
    stable = dict(payload)
    stable.pop("retrieved_at", None)
    return stable


def upsert_catalyst_event(
    conn: psycopg.Connection,
    event_id: str,
    payload: dict[str, object],
    *,
    observed_at: datetime,
) -> str:
    """Insert or refresh verification time. Record schedule revisions on change."""
    with conn.cursor() as cur:
        cur.execute(
            """
            select scheduled_at, payload
            from forward.catalyst_events
            where event_id = %s
            """,
            (event_id,),
        )
        existing = cur.fetchone()
        if existing is None:
            cur.execute(
                """
                insert into forward.catalyst_events (
                  event_id, category, subject_type, subject_id, title, scheduled_at, timezone,
                  date_precision, status, source_id, source_locator, provider_published_at,
                  first_observed_at, last_verified_at, payload, evidence_class, recorded_at
                )
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s)
                """,
                _insert_args(event_id, payload, observed_at),
            )
            return "new"

        previous_at, previous_payload = existing
        new_at = payload.get("scheduled_at")
        if not _schedule_times_equal(previous_at, new_at):
            cur.execute(
                """
                insert into forward.catalyst_event_revisions (
                  event_id, previous_scheduled_at, new_scheduled_at, observed_at, reason, source_id
                )
                values (%s, %s, %s, %s, %s, %s)
                """,
                (
                    event_id,
                    previous_at,
                    new_at,
                    observed_at,
                    "schedule_changed_on_source_refresh",
                    payload["source_id"],
                ),
            )
            cur.execute(
                """
                update forward.catalyst_events
                set scheduled_at = %s,
                    last_verified_at = %s,
                    payload = %s::jsonb,
                    date_precision = %s,
                    status = %s,
                    title = %s
                where event_id = %s
                """,
                (
                    new_at,
                    observed_at,
                    json.dumps(payload),
                    payload["date_precision"],
                    payload["status"],
                    payload["title"],
                    event_id,
                ),
            )
            return "updated"

        prev_stable = _stable_payload(prev) if (prev := _coerce_payload(previous_payload)) else None
        if prev_stable is not None and prev_stable != _stable_payload(payload):
            cur.execute(
                """
                update forward.catalyst_events
                set last_verified_at = %s,
                    payload = %s::jsonb
                where event_id = %s
                """,
                (observed_at, json.dumps(payload), event_id),
            )
            return "updated"

        cur.execute(
            """
            update forward.catalyst_events
            set last_verified_at = %s
            where event_id = %s
            """,
            (observed_at, event_id),
        )
        return "unchanged"


def _insert_args(
    event_id: str,
    payload: dict[str, object],
    observed_at: datetime,
) -> tuple[Any, ...]:
    return (
        event_id,
        payload["category"],
        payload["subject_type"],
        payload["subject_id"],
        payload["title"],
        payload.get("scheduled_at"),
        payload.get("timezone"),
        payload["date_precision"],
        payload["status"],
        payload["source_id"],
        payload["source_locator"],
        payload.get("provider_published_at"),
        observed_at,
        observed_at,
        json.dumps(payload),
        payload["evidence_class"],
        observed_at,
    )
