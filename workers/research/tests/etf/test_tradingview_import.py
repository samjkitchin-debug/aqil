"""Offline TradingView import checks. These tests do not open a socket."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from aqil_research.etf.contracts.rights import load_etf_rights_fragment
from aqil_research.etf.history.manifest import dataset_manifest
from aqil_research.etf.prices.persist import storage_allowed
from aqil_research.etf.register.universe import load_universe_v1
from aqil_research.etf.tradingview.budget import BudgetLedger, BudgetStop
from aqil_research.etf.tradingview.client import TradingViewClient
from aqil_research.etf.tradingview.identity import MatchFailure, match_search_payload
from aqil_research.etf.tradingview.persist import PriceStoreError, assert_database_name
from aqil_research.etf.tradingview.series import observations_for, parse_price_payload

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "src" / "aqil_research" / "etf" / "tradingview"
RIGHTS = ROOT.parents[1] / "docs" / "sources" / "etf" / "fragments" / "tradingview_data_api.csv"


def test_package_does_not_embed_the_api_key() -> None:
    for path in PACKAGE.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert 'TRADINGVIEW_API_KEY="' not in text
        assert "TRADINGVIEW_API_KEY='" not in text
        assert "Bearer " not in text or "Bearer {api_key}" in text


def test_identity_requires_the_approved_isin_and_venue() -> None:
    vwra = next(row for row in load_universe_v1() if row.research_symbol == "VWRA")
    matched = match_search_payload(_markets(_listing()), vwra)
    assert not isinstance(matched, MatchFailure)
    assert matched.tv_symbol == "LSE:VWRA"
    ticker_only = _listing()
    ticker_only["isin"] = ""
    refused = match_search_payload(_markets(ticker_only), vwra)
    assert isinstance(refused, MatchFailure)
    canadian = _listing(symbol="CNDX", isin="IE00B53SZB19", source_id="TSX", full_name="TSX:CNDX")
    cndx = next(row for row in load_universe_v1() if row.research_symbol == "CNDX")
    assert isinstance(match_search_payload(_markets(canadian), cndx), MatchFailure)
    substitute = _listing(symbol="VWRP", full_name="LSE:VWRP")
    assert isinstance(match_search_payload(_markets(substitute), vwra), MatchFailure)
    ichn = next(row for row in load_universe_v1() if row.research_symbol == "ICHN")
    amsterdam = _listing(
        symbol="ICHN",
        isin="IE00BJ5JPG56",
        currency_code="USD",
        exchange="Euronext",
        source_id="EURONEXT",
        full_name="EURONEXT:ICHN",
    )
    ichn_match = match_search_payload(_markets(amsterdam), ichn)
    assert not isinstance(ichn_match, MatchFailure)
    assert ichn_match.tv_symbol == "EURONEXT:ICHN"
    inrg = next(row for row in load_universe_v1() if row.research_symbol == "INRG")
    gbx = _listing(
        symbol="INRG",
        isin="IE00B1XNHC34",
        currency_code="GBX",
        exchange="LSE",
        source_id="LSE",
        full_name="LSE:INRG",
    )
    refused_gbx = match_search_payload(_markets(gbx), inrg)
    assert isinstance(refused_gbx, MatchFailure)
    assert "GBX" in refused_gbx.issue


def test_split_close_is_not_copied_and_an_open_session_is_dropped() -> None:
    vwra = next(row for row in load_universe_v1() if row.research_symbol == "VWRA")
    open_session = datetime(2026, 11, 2, 10, 0, tzinfo=UTC)
    parsed = parse_price_payload(
        _prices(),
        mic=vwra.mic,
        expected_currency="USD",
        inception_year=2019,
        retrieved_at=open_session,
        adjustment="splits",
    )
    assert all(candle.session_date.isoformat() != "2018-06-01" for candle in parsed.candles)
    assert all(candle.session_date.isoformat() != "2026-11-02" for candle in parsed.candles)
    assert any("GBX" not in item for item in parsed.findings)
    gbx = parse_price_payload(
        _prices(currency="GBX"),
        mic=vwra.mic,
        expected_currency="USD",
        inception_year=2019,
        retrieved_at=datetime(2026, 11, 2, 18, 0, tzinfo=UTC),
        adjustment="splits",
    )
    assert gbx.candles == ()
    rows = observations_for(
        parsed,
        listing_key="XLON:VWRA",
        adjustment="splits",
        retrieved_at=open_session,
        locator="https://api.tradingviewapi.com/api/price/LSE:VWRA",
    )
    assert rows
    assert {row.price_type for row in rows} == {"adjusted_close"}
    dividends = observations_for(
        parsed,
        listing_key="XLON:VWRA",
        adjustment="dividends",
        retrieved_at=open_session,
        locator="https://api.tradingviewapi.com/api/price/LSE:VWRA",
    )
    assert dividends[0].source_id != rows[0].source_id
    assert "not a total-return index" in (dividends[0].adjustment_definition or "")


def test_ledger_caps_the_host_and_does_not_retry_401(tmp_path: Path) -> None:
    clock = _Clock(datetime(2026, 11, 3, tzinfo=UTC))
    ledger = BudgetLedger(tmp_path / "ledger.json", clock=clock.now, sleeper=lambda _seconds: None)
    with pytest.raises(BudgetStop):
        ledger.reserve("identity", "GET", "https://example.com/api/price")
    calls: list[int] = []

    def transport(url: str, api_key: str) -> tuple[int, dict[str, str], bytes]:
        assert url.startswith("https://api.tradingviewapi.com/")
        assert api_key == "test-key"
        calls.append(1)
        return 401, {}, b"{}"

    client = TradingViewClient(
        ledger,
        tmp_path / "cache",
        api_key="test-key",
        transport=transport,
    )
    with pytest.raises(BudgetStop):
        client.search_market("identity", "IE00BK5BQT80")
    assert calls == [1]


def test_cache_replay_and_one_429_retry_do_not_use_the_network_again(tmp_path: Path) -> None:
    clock = _Clock(datetime(2026, 11, 3, tzinfo=UTC))
    ledger = BudgetLedger(tmp_path / "ledger.json", clock=clock.now, sleeper=lambda _seconds: None)
    calls: list[int] = []

    def transport(url: str, _api_key: str) -> tuple[int, dict[str, str], bytes]:
        calls.append(1)
        if len(calls) == 1:
            return 429, {"Retry-After": "0"}, b""
        return 200, {}, b'{"success": true, "data": {"markets": []}}'

    client = TradingViewClient(
        ledger,
        tmp_path / "cache",
        api_key="test-key",
        transport=transport,
    )
    payload = client.search_market("identity", "IE00BK5BQT80")
    assert payload["success"] is True
    again = client.search_market("identity", "IE00BK5BQT80")
    assert again["success"] is True
    assert calls == [1, 1]
    assert ledger.used() == 2


def test_manifest_stays_at_zero_until_a_count_is_supplied() -> None:
    manifest = dataset_manifest(load_universe_v1())
    assert manifest["stored_price_observations"] == 0
    assert manifest["licensed_storage"] == "not established"


def test_postgres_is_refused_and_founder_storage_is_private() -> None:
    with pytest.raises(PriceStoreError):
        assert_database_name("postgres")
    record = load_etf_rights_fragment(RIGHTS)
    assert storage_allowed(record, display_audience="founder") is True
    assert storage_allowed(record, display_audience="any_signed_in") is False


class _Clock:
    def __init__(self, instant: datetime) -> None:
        self.instant = instant

    def now(self) -> datetime:
        return self.instant


def _listing(**overrides: str) -> dict[str, object]:
    row: dict[str, object] = {
        "symbol": "VWRA",
        "isin": "IE00BK5BQT80",
        "currency_code": "USD",
        "exchange": "LSE",
        "source_id": "LSE",
        "full_name": "LSE:VWRA",
        "found_by_isin": True,
    }
    row.update(overrides)
    return row


def _markets(row: dict[str, object]) -> dict[str, object]:
    return {"success": True, "data": {"markets": [row]}}


def _prices(currency: str = "USD") -> dict[str, object]:
    current = {"time": 1793577600, "close": 140}
    return {
        "success": True,
        "data": {
            "symbol": "LSE:VWRA",
            "current": current,
            "info": {"currency_code": currency},
            "history": [
                {"time": 1527811200, "open": 50, "close": 0, "max": 51, "min": 49},
                {"time": 1527897600, "open": 80, "close": 90, "max": 91, "min": 79},
                {"time": 1793318400, "open": 120, "close": 121, "max": 122, "min": 119},
                {"time": current["time"], "open": 139, "close": 140, "max": 141, "min": 138},
            ],
        },
    }


def test_high_low_conflict_is_rejected() -> None:
    parsed = parse_price_payload(
        {
            "data": {
                "symbol": "LSE:VWRA",
                "info": {"currency_code": "USD"},
                "history": [
                    {"time": 1793318400, "close": 150, "max": 140, "min": 130},
                ],
            }
        },
        mic="XLON",
        expected_currency="USD",
        inception_year=2019,
        retrieved_at=datetime(2026, 11, 2, 18, 0, tzinfo=UTC),
        adjustment="splits",
    )
    assert parsed.candles == ()
    assert any("high/low" in item for item in parsed.findings)
    assert Decimal("150") not in {candle.close for candle in parsed.candles}