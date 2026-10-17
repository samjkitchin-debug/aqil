"""Schedule and payload equality for catalyst upserts."""

from __future__ import annotations

from datetime import UTC, datetime

from aqil_research.forward.catalyst_store import (
    _coerce_payload,
    _schedule_times_equal,
    _stable_payload,
)


def test_schedule_times_equal_across_db_and_iso_string() -> None:
    db_value = datetime(2026, 10, 28, 18, 0, tzinfo=UTC)
    iso_value = "2026-10-28T18:00:00+00:00"
    assert _schedule_times_equal(db_value, iso_value)


def test_stable_payload_ignores_retrieved_at() -> None:
    first = {"event_id": "x", "retrieved_at": "2026-01-01T00:00:00+00:00"}
    second = {"event_id": "x", "retrieved_at": "2026-01-02T00:00:00+00:00"}
    assert _stable_payload(first) == _stable_payload(second)


def test_coerce_payload_from_json_string() -> None:
    parsed = _coerce_payload('{"event_id": "a"}')
    assert parsed == {"event_id": "a"}
