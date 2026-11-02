"""Store the cached ETF series. This script does not call the network."""

from __future__ import annotations

import json
import sys
from datetime import UTC, date, datetime, time
from decimal import Decimal
from pathlib import Path

import psycopg

from aqil_research.etf.history.manifest import dataset_manifest
from aqil_research.etf.prices.models import PriceObservation
from aqil_research.etf.register.universe import load_universe_v1
from aqil_research.etf.tradingview.persist import (
    PriceStoreError,
    ensure_listing,
    store_observations,
)

LOCAL_ETF_URL = "postgresql://research_worker:research_worker@127.0.0.1:55432/aqil_etf"
RETRIEVED_AT = datetime(2026, 11, 2, 22, 0, tzinfo=UTC)
CACHE = Path(__file__).resolve().parents[1] / ".local" / "tradingview" / "validated"
MANIFEST = (
    Path(__file__).resolve().parents[3]
    / "docs"
    / "sources"
    / "etf"
    / "history"
    / "aqil_etf_history_v1_2026-11.json"
)


def main() -> int:
    instruments = [row for row in load_universe_v1() if row.research_symbol != "INRG"]
    counts: dict[str, int] = {}
    with psycopg.connect(LOCAL_ETF_URL, connect_timeout=5) as conn:
        database = conn.execute("select current_database()").fetchone()
        if database is None or database[0] != "aqil_etf":
            print("refusing a database other than aqil_etf")
            return 2
        first = _store_all(conn, instruments)
        conn.commit()
        second = _store_all(conn, instruments)
        conn.commit()
        for symbol, result in first.items():
            counts[symbol] = _count(conn, symbol)
            print(
                f"{symbol} inserted={result.inserted} skipped={result.skipped} "
                f"replay_inserted={second[symbol].inserted} db_count={counts[symbol]}"
            )
        readback = _read_vwra(conn)
        print(
            "vwra_read "
            f"count={readback[0]} first={readback[1]} last={readback[2]} "
            f"currency={readback[3]} raw_close_count={readback[4]}"
        )
    _write_manifest(counts)
    replay_ok = all(result.inserted == 0 for result in second.values())
    print(f"replay_idempotent={replay_ok}")
    return 0 if replay_ok else 1


def _store_all(conn: psycopg.Connection, instruments: list) -> dict:
    results = {}
    for instrument in instruments:
        path = CACHE / f"{instrument.research_symbol}.json"
        observations = _observations(path, instrument)
        try:
            ensure_listing(
                conn,
                isin=instrument.isin,
                mic=instrument.mic,
                ticker=instrument.preferred_listing_ticker,
                currency=instrument.listing_currency,
                umbrella_name=instrument.issuer,
                domicile_iso2="IE",
                sub_fund_name=instrument.share_class_name,
                distribution_policy=instrument.distribution_policy.lower(),
            )
            results[instrument.research_symbol] = store_observations(
                conn,
                observations,
                isin=instrument.isin,
                mic=instrument.mic,
                ticker=instrument.preferred_listing_ticker,
                currency=instrument.listing_currency,
            )
        except PriceStoreError as exc:
            print(f"{instrument.research_symbol} blocked: {exc}")
            raise
    return results


def _observations(path: Path, instrument) -> tuple[PriceObservation, ...]:
    if not path.is_file():
        raise PriceStoreError(f"cached series is missing for {instrument.research_symbol}")
    rows = json.loads(path.read_text(encoding="utf-8"))
    observations: list[PriceObservation] = []
    symbol = f"{instrument.preferred_exchange}:{instrument.preferred_listing_ticker}"
    if instrument.mic == "XAMS":
        symbol = f"EURONEXT:{instrument.preferred_listing_ticker}"
    if instrument.mic == "XETR":
        symbol = f"XETR:{instrument.preferred_listing_ticker}"
    if instrument.mic == "XLON":
        symbol = f"LSE:{instrument.preferred_listing_ticker}"
    locator = (
        "https://api.tradingviewapi.com/api/price/"
        f"{symbol}?timeframe=D&type=Japanese&adjustment=splits"
    )
    for row in rows:
        if row.get("price_type") != "adjusted_close":
            continue
        if row.get("currency") != instrument.listing_currency:
            raise PriceStoreError(
                f"{instrument.research_symbol} cache currency is not {instrument.listing_currency}"
            )
        session = date.fromisoformat(row["session_date"])
        observations.append(
            PriceObservation(
                listing_key=f"{instrument.mic}:{instrument.preferred_listing_ticker}",
                session_date=session,
                value=Decimal(row["value"]),
                currency=row["currency"],
                quote_unit=row["currency"],
                price_type="adjusted_close",
                observation_time=datetime.combine(session, time.min, tzinfo=UTC),
                retrieved_at=RETRIEVED_AT,
                delay_class="end_of_day",
                adjustment_status="adjusted",
                adjustment_definition=row["adjustment_definition"],
                quality="accepted",
                source_id=row["source_id"],
                source_locator=locator,
                revision=1,
            )
        )
    return tuple(observations)


def _count(conn: psycopg.Connection, symbol: str) -> int:
    row = conn.execute(
        """
        select count(*)
        from instruments.market_price_observations as prices
        join instruments.listings as listings on listings.listing_id = prices.listing_id
        where listings.ticker = %s
          and prices.price_type = 'adjusted_close'
          and prices.source_id = 'tradingview_data_api'
        """,
        (symbol,),
    ).fetchone()
    return 0 if row is None else int(row[0])


def _read_vwra(conn: psycopg.Connection) -> tuple[int, str, str, str, int]:
    rows = conn.execute(
        """
        select price_type, currency, to_char(session_date, 'YYYY-MM-DD')
        from instruments.market_price_observations as prices
        join instruments.listings as listings on listings.listing_id = prices.listing_id
        join instruments.share_classes as share_classes
          on share_classes.share_class_id = listings.share_class_id
        where share_classes.isin = 'IE00BK5BQT80'
          and prices.quality <> 'rejected'
        order by prices.session_date, prices.revision
        """
    ).fetchall()
    adjusted = [row for row in rows if row[0] == "adjusted_close"]
    closes = [row for row in rows if row[0] == "close"]
    if not adjusted:
        return 0, "", "", "", len(closes)
    return len(adjusted), adjusted[0][2], adjusted[-1][2], adjusted[0][1], len(closes)


def _write_manifest(counts: dict[str, int]) -> None:
    rows = load_universe_v1()
    histories = {
        row.research_symbol: "stored" if counts.get(row.research_symbol, 0) else "not ingested"
        for row in rows
    }
    total = sum(counts.values())
    manifest = dataset_manifest(
        rows,
        stored_price_observations=total,
        licensed_storage="founder retention stored" if total else "not established",
        histories=histories,
    )
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())