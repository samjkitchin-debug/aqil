"""ECB press parsing keeps monetary-policy items and drops speeches."""

from datetime import UTC, datetime
from pathlib import Path

from aqil_research.adapters.ecb_press.parse import parse_ecb_press_feed

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "ecb_press" / "press_sample.xml"


def test_parse_keeps_governing_council_decision_only() -> None:
    items = parse_ecb_press_feed(FIXTURE.read_bytes())
    assert len(items) == 1
    assert items[0].title.startswith("Decisions taken by the Governing Council")
    assert items[0].canonical_url == (
        "https://www.ecb.europa.eu/press/govcdec/otherdec/2026/html/ecb.gc261002~54c6b5672b.en.html"
    )
    assert items[0].published_at == datetime(2026, 10, 2, 13, 0, tzinfo=UTC)
