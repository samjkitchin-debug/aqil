from pathlib import Path

from aqil_research.forward.adapters.fed_fomc_calendar import (
    meeting_event_id,
    meeting_to_catalyst_payload,
    parse_fomc_calendar_html,
)


def test_parse_fomc_calendar_snippet() -> None:
    html = (
        Path(__file__)
        .parent.joinpath("fixtures/forward/fed_fomc_calendar_snippet.html")
        .read_text(
            encoding="utf-8",
        )
    )
    meetings = parse_fomc_calendar_html(html, min_year=2026, max_year=2027)
    ids = {meeting_event_id(m) for m in meetings}
    assert "event:verified:fed:fomc:2026-01-28" in ids
    assert "event:verified:fed:fomc:2026-10-28" in ids
    assert "event:verified:fed:fomc:2027-12-08" in ids


def test_catalyst_payload_is_verified_schedule() -> None:
    html = (
        Path(__file__)
        .parent.joinpath("fixtures/forward/fed_fomc_calendar_snippet.html")
        .read_text(
            encoding="utf-8",
        )
    )
    meeting = parse_fomc_calendar_html(html, min_year=2026, max_year=2026)[0]
    from datetime import UTC, datetime

    payload = meeting_to_catalyst_payload(meeting, retrieved_at=datetime(2026, 10, 18, tzinfo=UTC))
    assert payload["evidence_class"] == "verified_schedule"
    assert str(payload["source_locator"]).startswith("https://")
    assert payload["is_fixture"] is False
