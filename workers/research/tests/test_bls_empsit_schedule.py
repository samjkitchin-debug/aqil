from datetime import date
from pathlib import Path

from aqil_research.forward.adapters.bls_release_schedule import (
    parse_empsit_schedule_html,
    release_event_id,
    release_to_catalyst_payload,
)


def test_parse_empsit_schedule_table() -> None:
    html = (
        Path(__file__)
        .parent.joinpath(
            "fixtures/forward/bls_empsit_schedule_snippet.html",
        )
        .read_text(encoding="utf-8")
    )
    releases = parse_empsit_schedule_html(html)
    assert len(releases) == 2
    assert releases[0].release_date == date(2026, 11, 6)


def test_release_payload_evidence() -> None:
    html = (
        Path(__file__)
        .parent.joinpath(
            "fixtures/forward/bls_empsit_schedule_snippet.html",
        )
        .read_text(encoding="utf-8")
    )
    release = parse_empsit_schedule_html(html)[0]
    from datetime import UTC, datetime

    payload = release_to_catalyst_payload(release, retrieved_at=datetime(2026, 10, 18, tzinfo=UTC))
    assert payload["evidence_class"] == "verified_schedule"
    assert release_event_id(release) == "event:verified:bls:empsit:2026-11-06"
