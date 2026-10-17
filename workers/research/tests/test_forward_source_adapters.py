"""Official BLS iCalendar, BEA schedule, EDGAR filings, and IR watchlist."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from aqil_research.forward.adapters.bea_release_schedule import (
    parse_bea_schedule_html,
)
from aqil_research.forward.adapters.bea_release_schedule import (
    release_to_catalyst_payload as bea_payload,
)
from aqil_research.forward.adapters.bls_ics_schedule import (
    parse_bls_ics,
    release_to_catalyst_payload,
)
from aqil_research.forward.adapters.company_ir_watchlist import (
    WatchlistIntegrityError,
    entry_to_catalyst_payload,
    load_watchlist,
)
from aqil_research.forward.adapters.sec_edgar_filings import (
    filing_to_catalyst_payload,
    latest_reported_period_end,
    parse_submissions,
)
from aqil_research.sources.rights import RightsOperation, find_source_rights, load_source_rights

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "forward"


def test_bls_ics_parses_utc_stamps_and_records_eastern_calendar() -> None:
    releases = parse_bls_ics((FIXTURES / "bls_ics_sample.ics").read_text(encoding="utf-8"))
    assert len(releases) == 2
    employment = releases[0]
    assert employment.starts_at == datetime(2008, 4, 4, 12, 30, tzinfo=UTC)
    payload = release_to_catalyst_payload(
        employment,
        retrieved_at=datetime(2026, 10, 18, tzinfo=UTC),
    )
    assert payload["timezone"] == "America/New_York"
    assert payload["evidence_class"] == "verified_schedule"
    assert "next_earnings_date" not in payload


def test_bea_schedule_keeps_an_unstated_timezone_unstated() -> None:
    html = (FIXTURES / "bea_schedule_snippet.html").read_text(encoding="utf-8")
    releases = parse_bea_schedule_html(html, year=2026)
    assert len(releases) == 2
    payload = bea_payload(releases[0], retrieved_at=datetime(2026, 10, 18, tzinfo=UTC))
    assert payload["timezone"] is None
    assert payload["clock_timezone_stated"] is False
    assert payload["published_clock"] == "8:30 AM"
    assert payload["scheduled_at"] == "2026-10-29T00:00:00+00:00"


def test_edgar_completed_filings_do_not_infer_a_future_earnings_date() -> None:
    document = json.loads((FIXTURES / "sec_submissions_sample.json").read_text(encoding="utf-8"))
    facts = json.loads((FIXTURES / "sec_companyfacts_sample.json").read_text(encoding="utf-8"))
    filings = parse_submissions(document)
    assert [filing.form for filing in filings] == ["8-K", "10-Q"]
    assert latest_reported_period_end(facts) == "2025-09-30"
    payload = filing_to_catalyst_payload(
        filings[0],
        retrieved_at=datetime(2026, 10, 18, tzinfo=UTC),
        live=False,
        reported_period_end="2025-09-30",
    )
    assert payload["status"] == "completed"
    assert payload["evidence_class"] == "synthetic_demonstration"
    forbidden = {"next_earnings_date", "consensus", "estimated_eps"}
    assert forbidden.isdisjoint(payload)
    live_payload = filing_to_catalyst_payload(
        filings[0],
        retrieved_at=datetime(2026, 10, 18, tzinfo=UTC),
        live=True,
    )
    assert live_payload["evidence_class"] == "verified_announcement"
    assert str(live_payload["source_locator"]).startswith("https://www.sec.gov/")


def test_ir_watchlist_keeps_unknown_dates_unknown() -> None:
    entries = load_watchlist(FIXTURES / "company_ir_watchlist.json")
    assert entries
    assert {entry.date_status for entry in entries} == {"unknown"}
    payload = entry_to_catalyst_payload(
        entries[0],
        retrieved_at=datetime(2026, 10, 18, tzinfo=UTC),
    )
    assert payload["date_precision"] == "unknown"
    assert payload["scheduled_at"] is None
    assert payload["evidence_class"] == "watchlist_unverified"
    assert payload["etf_weight_linked"] is False


def test_unknown_watchlist_row_cannot_carry_a_date(tmp_path: Path) -> None:
    path = tmp_path / "watchlist.json"
    path.write_text(
        json.dumps(
            {
                "issuers": [
                    {
                        "issuer_id": "issuer:test",
                        "legal_name": "Example",
                        "ticker": "EX",
                        "ir_events_url": "https://example.com/ir",
                        "date_status": "unknown",
                        "scheduled_date": "2026-11-01",
                        "first_observed_at": None,
                        "note": "",
                    },
                ],
            },
        ),
        encoding="utf-8",
    )
    with pytest.raises(WatchlistIntegrityError):
        load_watchlist(path)


def test_vanguard_and_ishares_automated_collection_stay_closed() -> None:
    rows = load_source_rights()
    vanguard = find_source_rights(rows, source_id="vanguard_uk_vwra_holdings")
    ishares = find_source_rights(rows, source_id="ishares_ucits_holdings")
    assert vanguard is not None
    assert ishares is not None
    assert vanguard.decision_for(RightsOperation.AUTOMATED_ACCESS).value == "prohibited"
    assert ishares.operational_status.value == "disabled"
    bls = find_source_rights(rows, source_id="bls_ics_schedule")
    assert bls is not None
    assert bls.decision_for(RightsOperation.AUTOMATED_ACCESS).value == "permitted"
    assert bls.decision_for(RightsOperation.AI_PROCESSING).value == "unknown"
