"""Federal Reserve monetary-policy press parsing and refresh isolation."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

from aqil_research.adapters.fed_press.parse import parse_monetary_press_feed
from aqil_research.workflow.refresh import SourceRefreshResult, _run_one, series_is_due

FIXTURE = (
    Path(__file__).resolve().parents[1] / "fixtures" / "fed_press" / "press_monetary_sample.xml"
)


def test_parse_official_press_item() -> None:
    items = parse_monetary_press_feed(FIXTURE.read_bytes())
    assert len(items) == 1
    assert items[0].title == "Federal Reserve issues FOMC statement"
    assert items[0].canonical_url.endswith("/monetary20260916a.htm")
    assert items[0].published_at == datetime(2026, 9, 16, 18, 0, tzinfo=UTC)


def test_series_weekly_interval() -> None:
    now = datetime(2026, 10, 22, tzinfo=UTC)
    assert series_is_due(now - timedelta(days=6), now) is False
    assert series_is_due(now - timedelta(days=8), now) is True
    assert series_is_due(None, now) is True


def test_failed_source_does_not_stop_the_next() -> None:
    now = datetime(2026, 10, 22, tzinfo=UTC)

    def fail(moment: datetime) -> SourceRefreshResult:
        raise RuntimeError(str(moment))

    def succeed(moment: datetime) -> SourceRefreshResult:
        return SourceRefreshResult("federal_reserve_monetary_press", "completed", unchanged=1)

    failed = _run_one(now, "bls_employment_situation_archive", fail)
    kept = _run_one(now, "federal_reserve_monetary_press", succeed)
    assert failed.outcome == "failed"
    assert failed.detail == "RuntimeError"
    assert kept.outcome == "completed"
    assert kept.unchanged == 1
