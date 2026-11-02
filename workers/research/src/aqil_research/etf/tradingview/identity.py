"""Match a search payload to one approved listing.

An ISIN match is required. A ticker hit without that ISIN is refused.
VWRP, VWCE, Canadian CNDX, SJPA, SPEX, London ICHN, and US-listed SMH are refused.
"""

from __future__ import annotations

from dataclasses import dataclass

from aqil_research.etf.register.universe import UniverseInstrument

_FORBIDDEN_TICKERS = frozenset({"VWRP", "VWCE", "SJPA", "SPEX"})
_US_VENUES = frozenset({"NASDAQ", "NYSE", "AMEX", "ARCA", "BATS", "CBOE"})
_CANADA_VENUES = frozenset({"TSX", "TSXV", "NEO", "CSE"})
_LSE_VENUES = frozenset({"LSE", "XLON"})


@dataclass(frozen=True)
class MatchedSymbol:
    research_symbol: str
    isin: str
    tv_symbol: str
    ticker: str
    exchange: str
    currency: str
    mic: str


@dataclass(frozen=True)
class MatchFailure:
    research_symbol: str
    isin: str
    issue: str


def match_search_payload(
    payload: object,
    instrument: UniverseInstrument,
) -> MatchedSymbol | MatchFailure:
    """Return one listing or a recorded reason. Never guess a ticker-only row."""

    markets = _markets(payload)
    if markets is None:
        return MatchFailure(
            instrument.research_symbol,
            instrument.isin,
            "search payload has no markets",
        )
    isin_rows = [row for row in markets if _isin(row) == instrument.isin]
    if not isin_rows:
        return MatchFailure(
            instrument.research_symbol,
            instrument.isin,
            "no row carried the approved ISIN; ticker-only matches are refused",
        )
    currency_rows = [row for row in isin_rows if _currency(row) == instrument.listing_currency]
    if not currency_rows:
        seen = sorted({_currency(row) or "missing" for row in isin_rows})
        return MatchFailure(
            instrument.research_symbol,
            instrument.isin,
            f"ISIN rows were not quoted in {instrument.listing_currency} ({', '.join(seen)})",
        )
    venue_rows = [row for row in currency_rows if _venue_ok(row, instrument)]
    if not venue_rows:
        same_venue = [row for row in isin_rows if _venue_ok(row, instrument)]
        if same_venue:
            quoted = ", ".join(sorted({_currency(row) or "missing" for row in same_venue}))
            return MatchFailure(
                instrument.research_symbol,
                instrument.isin,
                (
                    f"{instrument.preferred_exchange} is quoted in {quoted}, "
                    f"not {instrument.listing_currency}; the unit was not rescaled"
                ),
            )
        return MatchFailure(
            instrument.research_symbol,
            instrument.isin,
            f"ISIN rows did not match {instrument.preferred_exchange}",
        )
    allowed = [row for row in venue_rows if not _forbidden(row, instrument)]
    if not allowed:
        return MatchFailure(
            instrument.research_symbol,
            instrument.isin,
            "the row is a refused substitute listing",
        )
    ticker_rows = [
        row for row in allowed if _ticker(row) == instrument.preferred_listing_ticker
    ]
    if not ticker_rows:
        return MatchFailure(
            instrument.research_symbol,
            instrument.isin,
            f"venue rows did not use ticker {instrument.preferred_listing_ticker}",
        )
    if len(ticker_rows) > 1:
        names = ", ".join(sorted(_full_name(row) for row in ticker_rows))
        return MatchFailure(
            instrument.research_symbol,
            instrument.isin,
            f"more than one ISIN listing matched ({names})",
        )
    chosen = ticker_rows[0]
    full_name = _full_name(chosen)
    if ":" not in full_name:
        return MatchFailure(
            instrument.research_symbol,
            instrument.isin,
            "the matched row has no exchange symbol",
        )
    return MatchedSymbol(
        research_symbol=instrument.research_symbol,
        isin=instrument.isin,
        tv_symbol=full_name,
        ticker=_ticker(chosen),
        exchange=_exchange(chosen),
        currency=instrument.listing_currency,
        mic=instrument.mic,
    )


def _markets(payload: object) -> list[dict[str, object]] | None:
    if not isinstance(payload, dict):
        return None
    data = payload.get("data")
    if not isinstance(data, dict):
        return None
    markets = data.get("markets")
    if not isinstance(markets, list):
        return None
    return [row for row in markets if isinstance(row, dict)]


def _isin(row: dict[str, object]) -> str:
    return str(row.get("isin") or "").strip().upper()


def _currency(row: dict[str, object]) -> str:
    return str(row.get("currency_code") or "").strip().upper()


def _ticker(row: dict[str, object]) -> str:
    return str(row.get("symbol") or "").strip().upper()


def _exchange(row: dict[str, object]) -> str:
    return str(row.get("exchange") or row.get("source_id") or "").strip()


def _source(row: dict[str, object]) -> str:
    return str(row.get("source_id") or "").strip().upper()


def _full_name(row: dict[str, object]) -> str:
    raw = row.get("full_name") or row.get("id") or ""
    return str(raw).strip().upper()


def _venue_ok(row: dict[str, object], instrument: UniverseInstrument) -> bool:
    source = _source(row)
    exchange = str(row.get("exchange") or "").upper()
    full_name = _full_name(row)
    prefix = full_name.split(":", 1)[0]
    tokens = {source, exchange, prefix}
    if instrument.mic == "XLON":
        return bool(tokens & _LSE_VENUES)
    if instrument.mic == "XAMS":
        blob = " ".join(tokens)
        if tokens & {"AMS", "XAMS"} or "AMSTERDAM" in blob:
            return True
        return "EURONEXT" in tokens and _ticker(row) == instrument.preferred_listing_ticker
    if instrument.mic == "XETR":
        return bool(tokens & {"XETR", "XETRA"})
    return False


def _forbidden(row: dict[str, object], instrument: UniverseInstrument) -> bool:
    ticker = _ticker(row)
    source = _source(row)
    full_name = _full_name(row)
    prefix = full_name.split(":", 1)[0]
    venues = {source, prefix}
    if ticker in _FORBIDDEN_TICKERS:
        return True
    if instrument.research_symbol == "CNDX" and venues & _CANADA_VENUES:
        return True
    if instrument.research_symbol == "SMH" and venues & _US_VENUES:
        return True
    if instrument.research_symbol == "ICHN" and venues & _LSE_VENUES:
        return True
    return False