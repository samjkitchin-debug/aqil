"""Replaceable price adapters. Persistence lives outside this module.

A missing key or an HTTP 401 or 403 is a recorded failure. It is not an empty
price. This module does not invent a bar.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime
from decimal import Decimal
from typing import Protocol
from urllib.parse import urlencode

import httpx

from aqil_research.etf.prices.models import AdapterCapabilities, ProviderBar, ProviderQuote

EODHD_SOURCE_ID = "eodhd_global_etf_eod"
TWELVE_DATA_SOURCE_ID = "twelve_data_global_etf_eod"
EODHD_ORIGIN = "https://eodhd.com"
TWELVE_DATA_ORIGIN = "https://api.twelvedata.com"

_EODHD_EXCHANGE = {"XLON": "LSE", "XETR": "XETRA"}


class PriceTransportError(Exception):
    """Raised when a price request cannot be completed."""


class HttpPayload(Protocol):
    status_code: int
    text: str

    def json(self) -> object: ...


Transport = Callable[[str], HttpPayload]


class PriceAdapter(Protocol):
    """One provider. A second provider can replace it without changing identity."""

    def capabilities(self) -> AdapterCapabilities: ...

    def daily_bars_url(self, *, ticker: str, mic: str) -> str: ...

    def quote_url(self, *, ticker: str, mic: str) -> str | None: ...

    def fetch_daily_bars(
        self,
        *,
        ticker: str,
        mic: str,
        transport: Transport | None = None,
    ) -> tuple[str, tuple[ProviderBar, ...]]: ...

    def fetch_quote(
        self,
        *,
        ticker: str,
        mic: str,
        transport: Transport | None = None,
    ) -> tuple[str, ProviderQuote | None]: ...


def eodhd_symbol(ticker: str, mic: str) -> str | None:
    """Map a listing to an EODHD symbol. An unknown venue is not guessed."""

    exchange = _EODHD_EXCHANGE.get(mic.strip().upper())
    if exchange is None:
        return None
    return f"{ticker.strip().upper()}.{exchange}"


def eodhd_capabilities() -> AdapterCapabilities:
    return AdapterCapabilities(
        source_id=EODHD_SOURCE_ID,
        daily_close=True,
        adjusted_close=True,
        quote=False,
        quote_entitlement="The end-of-day candidate has no quote entitlement in this adapter.",
    )


def twelve_data_capabilities() -> AdapterCapabilities:
    return AdapterCapabilities(
        source_id=TWELVE_DATA_SOURCE_ID,
        daily_close=True,
        adjusted_close=True,
        quote=True,
        quote_entitlement=(
            "A quote is requested only when the key allows it. A 401 is not stored as a quote."
        ),
    )


def build_eodhd_bars_url(*, ticker: str, mic: str, token: str | None) -> str | None:
    symbol = eodhd_symbol(ticker, mic)
    if symbol is None:
        return None
    query = urlencode({"api_token": token or "", "fmt": "json"})
    return f"{EODHD_ORIGIN}/api/eod/{symbol}?{query}"


def build_twelve_data_bars_url(*, ticker: str, mic: str, token: str | None) -> str:
    query = urlencode(
        {
            "symbol": ticker.strip().upper(),
            "mic_code": mic.strip().upper(),
            "interval": "1day",
            "apikey": token or "",
        }
    )
    return f"{TWELVE_DATA_ORIGIN}/time_series?{query}"


def build_twelve_data_quote_url(*, ticker: str, mic: str, token: str | None) -> str:
    query = urlencode(
        {
            "symbol": ticker.strip().upper(),
            "mic_code": mic.strip().upper(),
            "apikey": token or "",
        }
    )
    return f"{TWELVE_DATA_ORIGIN}/quote?{query}"


def _default_transport(url: str) -> HttpPayload:
    return httpx.get(url, timeout=20.0)


def fetch_eodhd_bars(
    *,
    ticker: str,
    mic: str,
    token: str | None,
    transport: Transport | None = None,
) -> tuple[str, tuple[ProviderBar, ...]]:
    """Retrieve EODHD daily bars. No token and no body means no bars."""

    if not token:
        return "absent_key", ()
    url = build_eodhd_bars_url(ticker=ticker, mic=mic, token=token)
    if url is None:
        return "unsupported_venue", ()
    return _fetch_bars(
        url,
        transport or _default_transport,
        lambda body: parse_eodhd_bars(body, ticker=ticker, mic=mic),
    )


def fetch_twelve_data_bars(
    *,
    ticker: str,
    mic: str,
    token: str | None,
    transport: Transport | None = None,
) -> tuple[str, tuple[ProviderBar, ...]]:
    if not token:
        return "absent_key", ()
    url = build_twelve_data_bars_url(ticker=ticker, mic=mic, token=token)
    return _fetch_bars(
        url,
        transport or _default_transport,
        lambda body: parse_twelve_data_bars(body, ticker=ticker, mic=mic),
    )


def fetch_twelve_data_quote(
    *,
    ticker: str,
    mic: str,
    token: str | None,
    transport: Transport | None = None,
) -> tuple[str, ProviderQuote | None]:
    if not token:
        return "absent_key", None
    url = build_twelve_data_quote_url(ticker=ticker, mic=mic, token=token)
    caller = transport or _default_transport
    try:
        response = caller(url)
    except httpx.HTTPError as exc:
        raise PriceTransportError(str(exc)) from exc
    status = _http_status(response.status_code)
    if status != "ok":
        return status, None
    try:
        body = response.json()
    except Exception as exc:
        raise PriceTransportError("quote body was not JSON") from exc
    if not isinstance(body, dict):
        return "invalid", None
    return "ok", parse_twelve_data_quote(body, ticker=ticker, mic=mic)


def parse_eodhd_bars(body: object, *, ticker: str, mic: str) -> tuple[ProviderBar, ...]:
    """Parse EODHD rows. Currency is not invented when the body omits it."""

    if not isinstance(body, list):
        return ()
    bars: list[ProviderBar] = []
    for row in body:
        if not isinstance(row, dict) or "date" not in row or "close" not in row:
            continue
        adjusted = row.get("adjusted_close")
        bars.append(
            ProviderBar(
                ticker=ticker,
                mic=mic,
                session_date=date.fromisoformat(str(row["date"])[:10]),
                close=_decimal(row.get("close")),
                adjusted_close=_decimal(adjusted) if adjusted is not None else None,
                currency=_text(row.get("currency")),
                quote_unit=_text(row.get("currency")),
                adjustment_definition=(
                    "EODHD adjusted_close is a separate field from close."
                    if adjusted is not None
                    else None
                ),
                observation_time=None,
                volume=_decimal(row.get("volume")) if row.get("volume") is not None else None,
            )
        )
    return tuple(bars)


def parse_twelve_data_bars(body: object, *, ticker: str, mic: str) -> tuple[ProviderBar, ...]:
    if not isinstance(body, dict):
        return ()
    meta = body.get("meta") if isinstance(body.get("meta"), dict) else {}
    currency = _text(meta.get("currency")) if isinstance(meta, dict) else None
    values = body.get("values")
    if not isinstance(values, list):
        return ()
    bars: list[ProviderBar] = []
    for row in values:
        if not isinstance(row, dict) or "datetime" not in row or "close" not in row:
            continue
        bars.append(
            ProviderBar(
                ticker=ticker,
                mic=mic,
                session_date=date.fromisoformat(str(row["datetime"])[:10]),
                close=_decimal(row.get("close")),
                adjusted_close=None,
                currency=currency,
                quote_unit=currency,
                adjustment_definition=None,
                observation_time=None,
                volume=_decimal(row.get("volume")) if row.get("volume") is not None else None,
            )
        )
    return tuple(bars)


def parse_twelve_data_quote(body: dict, *, ticker: str, mic: str) -> ProviderQuote:
    currency = _text(body.get("currency"))
    return ProviderQuote(
        ticker=ticker,
        mic=mic,
        bid=_decimal(body.get("bid")) if body.get("bid") not in (None, "") else None,
        ask=_decimal(body.get("ask")) if body.get("ask") not in (None, "") else None,
        last=_decimal(body.get("close")) if body.get("close") not in (None, "") else None,
        currency=currency,
        quote_unit=currency,
        delay_class="unknown",
        observation_time=_timestamp(body.get("timestamp")),
    )


def _fetch_bars(url: str, transport: Transport, parse) -> tuple[str, tuple[ProviderBar, ...]]:
    try:
        response = transport(url)
    except httpx.HTTPError as exc:
        raise PriceTransportError(str(exc)) from exc
    status = _http_status(response.status_code)
    if status != "ok":
        return status, ()
    try:
        body = response.json()
    except Exception as exc:
        raise PriceTransportError("price body was not JSON") from exc
    return "ok", tuple(parse(body))


def _http_status(code: int) -> str:
    if code == 200:
        return "ok"
    if code == 401:
        return "unauthorised"
    if code == 403:
        return "forbidden"
    return "invalid"


def _decimal(value: object) -> Decimal | None:
    if value is None or value == "":
        return None
    return Decimal(str(value))


def _text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip().upper()
    return text or None


def _timestamp(value: object) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(int(value), datetime.UTC)
    text = str(value)
    if text.isdigit():
        return datetime.fromtimestamp(int(text), datetime.UTC)
    return datetime.fromisoformat(text.replace("Z", "+00:00"))
