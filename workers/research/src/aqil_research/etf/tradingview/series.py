"""Turn one price payload into validated daily observations.

The documented candle route returns one close for the requested adjustment.
That close is stored as adjusted_close. It is not copied into a raw close,
and a dividends request is not labelled a total-return index.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

from aqil_research.etf.history.quality import TARGET_END, TARGET_START, HistoryBar, history_findings
from aqil_research.etf.prices.models import PriceObservation

SPLITS_DEFINITION = "tradingview adjustment=splits; split-adjusted close; not a raw close"
DIVIDENDS_DEFINITION = (
    "tradingview adjustment=dividends; splits and cash dividends; not a total-return index"
)
SPLITS_SOURCE = "tradingview_data_api"
DIVIDENDS_SOURCE = "tradingview_data_api_dividends"
_ZONES = {"XLON": "Europe/London", "XAMS": "Europe/Amsterdam", "XETR": "Europe/Berlin"}
_CLOSE = {"XLON": time(16, 30), "XAMS": time(17, 30), "XETR": time(17, 30)}


@dataclass(frozen=True)
class Candle:
    session_date: date
    timestamp: int
    close: Decimal
    high: Decimal | None
    low: Decimal | None
    completed: bool


@dataclass(frozen=True)
class ParsedSeries:
    symbol: str
    currency: str | None
    candles: tuple[Candle, ...]
    findings: tuple[str, ...]


def parse_price_payload(
    payload: object,
    *,
    mic: str,
    expected_currency: str,
    inception_year: int,
    retrieved_at: datetime,
    adjustment: str,
) -> ParsedSeries:
    """Parse history, drop bars that must not be stored, and list the findings."""

    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, dict):
        return ParsedSeries("", None, (), ("price payload has no data object",))
    symbol = str(data.get("symbol") or "")
    info = data.get("info") if isinstance(data.get("info"), dict) else {}
    currency = str(info.get("currency_code") or "") or None
    history = data.get("history") if isinstance(data.get("history"), list) else []
    current = data.get("current") if isinstance(data.get("current"), dict) else None
    current_time = current.get("time") if current else None
    findings: list[str] = []
    if currency != expected_currency:
        findings.append(f"payload currency {currency or 'missing'} is not {expected_currency}")
    if currency == "GBX" and expected_currency == "GBP":
        findings.append("GBX must not be read as GBP")
    parsed: list[Candle] = []
    for row in history:
        if not isinstance(row, dict):
            findings.append("a history row was not an object")
            continue
        candle = _candle(row, mic=mic, retrieved_at=retrieved_at, current_time=current_time)
        if candle is None:
            findings.append("a history row had no usable time or close")
            continue
        parsed.append(candle)
    accepted, extra = _accept(
        parsed,
        currency=currency,
        expected_currency=expected_currency,
        inception_year=inception_year,
        adjustment=adjustment,
    )
    findings.extend(extra)
    return ParsedSeries(symbol, currency, tuple(accepted), tuple(findings))


def observations_for(
    series: ParsedSeries,
    *,
    listing_key: str,
    adjustment: str,
    retrieved_at: datetime,
    locator: str,
) -> tuple[PriceObservation, ...]:
    """Store the vendor close once. Do not invent a second adjusted copy."""

    if series.currency is None:
        return ()
    source_id = DIVIDENDS_SOURCE if adjustment == "dividends" else SPLITS_SOURCE
    definition = DIVIDENDS_DEFINITION if adjustment == "dividends" else SPLITS_DEFINITION
    rows: list[PriceObservation] = []
    for candle in series.candles:
        observed = datetime.fromtimestamp(candle.timestamp, UTC)
        rows.append(
            PriceObservation(
                listing_key=listing_key,
                session_date=candle.session_date,
                value=candle.close,
                currency=series.currency,
                quote_unit=series.currency,
                price_type="adjusted_close",
                observation_time=observed,
                retrieved_at=retrieved_at,
                delay_class="end_of_day",
                adjustment_status="adjusted",
                adjustment_definition=definition,
                quality="accepted",
                source_id=source_id,
                source_locator=locator,
                revision=1,
            )
        )
    return tuple(rows)


def _candle(
    row: dict[str, object],
    *,
    mic: str,
    retrieved_at: datetime,
    current_time: object,
) -> Candle | None:
    raw_time = row.get("time")
    if not isinstance(raw_time, int):
        return None
    close = _decimal(row.get("close"))
    if close is None:
        return None
    session = _session_date(raw_time, mic)
    completed = not _unfinished(session, raw_time, current_time, mic, retrieved_at)
    return Candle(
        session_date=session,
        timestamp=raw_time,
        close=close,
        high=_decimal(row.get("max")),
        low=_decimal(row.get("min")),
        completed=completed,
    )


def _accept(
    candles: list[Candle],
    *,
    currency: str | None,
    expected_currency: str,
    inception_year: int,
    adjustment: str,
) -> tuple[list[Candle], list[str]]:
    findings: list[str] = []
    if currency != expected_currency:
        return [], findings
    inception = date(inception_year, 1, 1)
    kept: list[Candle] = []
    by_day: dict[date, Candle] = {}
    for candle in candles:
        if candle.session_date < TARGET_START or candle.session_date > TARGET_END:
            continue
        if candle.session_date < inception:
            findings.append(f"{candle.session_date.isoformat()} is before inception")
            continue
        if not candle.completed:
            findings.append(f"{candle.session_date.isoformat()} is not a completed session")
            continue
        if candle.close <= 0:
            findings.append(f"{candle.session_date.isoformat()} close is not positive")
            continue
        if candle.high is not None and candle.low is not None:
            if candle.low > candle.high or candle.close > candle.high or candle.close < candle.low:
                findings.append(
                    f"{candle.session_date.isoformat()} high/low does not contain the close"
                )
                continue
        previous = by_day.get(candle.session_date)
        if previous is not None and previous.close != candle.close:
            findings.append(f"{candle.session_date.isoformat()} has conflicting closes")
            by_day.pop(candle.session_date, None)
            continue
        by_day[candle.session_date] = candle
    kept = [by_day[day] for day in sorted(by_day)]
    source = DIVIDENDS_SOURCE if adjustment == "dividends" else SPLITS_SOURCE
    shared = history_findings(
        tuple(
            HistoryBar(
                session_date=candle.session_date,
                close=candle.close,
                currency=expected_currency,
                quote_unit=expected_currency,
                price_type="adjusted_close",
                completed_session=True,
                source_id=source,
            )
            for candle in kept
        ),
        expected_currency=expected_currency,
        inception=inception,
    )
    findings.extend(shared)
    return kept, findings


def _session_date(timestamp: int, mic: str) -> date:
    instant = datetime.fromtimestamp(timestamp, UTC)
    if instant.timetz().replace(tzinfo=None) == time(0, 0):
        return instant.date()
    zone = ZoneInfo(_ZONES.get(mic, "Europe/London"))
    return instant.astimezone(zone).date()


def _unfinished(
    session: date,
    timestamp: int,
    current_time: object,
    mic: str,
    retrieved_at: datetime,
) -> bool:
    if session > TARGET_END:
        return True
    if current_time != timestamp:
        return False
    zone = ZoneInfo(_ZONES.get(mic, "Europe/London"))
    local_retrieval = retrieved_at.astimezone(zone)
    if session != local_retrieval.date():
        return False
    return local_retrieval.time() < _CLOSE.get(mic, time(17, 30))


def _decimal(value: object) -> Decimal | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None