"""Insert validated prices into an existing instruments listing.

postgres is refused. A missing listing is not invented. Replay skips an
identical close and does not delete.
"""

from __future__ import annotations

from dataclasses import dataclass

import psycopg

from aqil_research.etf.prices.models import PriceObservation
from aqil_research.etf.prices.persist import plan_price_writes

PRESERVED_DATABASES = frozenset({"postgres"})


class PriceStoreError(RuntimeError):
    """Raised when a database write must not proceed."""


@dataclass(frozen=True)
class StoreResult:
    inserted: int
    skipped: int
    issue: str | None = None


REFUSED_ISIN = "IE00B1XNHC34"


def assert_database_name(name: str) -> None:
    if name in PRESERVED_DATABASES:
        raise PriceStoreError(f"refusing to write the preserved database {name}")


def assert_series_allowed(*, isin: str, currency: str) -> None:
    """INRG's London row is GBX. It is not the approved USD listing."""

    if isin == REFUSED_ISIN or currency == "GBX":
        raise PriceStoreError("INRG is not stored; the London row is GBX, not USD")


def ensure_listing(
    conn: psycopg.Connection,
    *,
    isin: str,
    mic: str,
    ticker: str,
    currency: str,
    umbrella_name: str,
    domicile_iso2: str,
    sub_fund_name: str,
    distribution_policy: str,
) -> str:
    """Resolve one listing. A second call does not insert another share class."""

    name = conn.execute("select current_database()").fetchone()
    assert_database_name("" if name is None else str(name[0]))
    assert_series_allowed(isin=isin, currency=currency)
    existing = _listing_id(conn, isin, mic, ticker, currency)
    if existing is not None:
        return existing
    umbrella_id = _umbrella_id(conn, umbrella_name, domicile_iso2)
    sub_fund_id = _sub_fund_id(conn, umbrella_id, sub_fund_name, currency)
    share_class_id = _share_class_id(conn, sub_fund_id, isin, distribution_policy)
    conn.execute(
        """
        insert into instruments.listings (share_class_id, mic, trading_currency, ticker)
        values (%s, %s, %s, %s)
        on conflict (share_class_id, mic, trading_currency, ticker) do nothing
        """,
        (share_class_id, mic, currency, ticker),
    )
    listing_id = _listing_id(conn, isin, mic, ticker, currency)
    if listing_id is None:
        raise PriceStoreError("listing insert did not resolve")
    return listing_id


def store_observations(
    conn: psycopg.Connection,
    observations: tuple[PriceObservation, ...],
    *,
    isin: str,
    mic: str,
    ticker: str,
    currency: str,
) -> StoreResult:
    """Append changed rows for one listing. Identical rows are skipped."""

    name = conn.execute("select current_database()").fetchone()
    assert_database_name("" if name is None else str(name[0]))
    assert_series_allowed(isin=isin, currency=currency)
    listing = conn.execute(
        """
        select listings.listing_id::text
        from instruments.listings as listings
        join instruments.share_classes as share_classes
          on share_classes.share_class_id = listings.share_class_id
        where share_classes.isin = %s
          and listings.mic = %s
          and listings.ticker = %s
          and listings.trading_currency = %s
        """,
        (isin, mic, ticker, currency),
    ).fetchone()
    if listing is None:
        return StoreResult(0, 0, "listing is not in the ETF database")
    listing_id = str(listing[0])
    existing = _existing(conn, listing_id, observations)
    writes = plan_price_writes(existing, observations)
    inserted = 0
    skipped = 0
    for write in writes:
        if write.action == "skip":
            skipped += 1
            continue
        row = write.observation
        conn.execute(
            """
            insert into instruments.market_price_observations (
              listing_id, session_date, value, currency, quote_unit, price_type,
              observation_time, retrieved_at, delay_class, adjustment_status,
              adjustment_definition, quality, source_id, source_locator, revision
            )
            values (
              %s, %s, %s, %s, %s, %s,
              %s, %s, %s, %s,
              %s, %s, %s, %s, %s
            )
            """,
            (
                listing_id,
                row.session_date,
                row.value,
                row.currency,
                row.quote_unit,
                row.price_type,
                row.observation_time,
                row.retrieved_at,
                row.delay_class,
                row.adjustment_status,
                row.adjustment_definition,
                row.quality,
                row.source_id,
                row.source_locator,
                row.revision,
            ),
        )
        inserted += 1
    return StoreResult(inserted, skipped, None)


def _existing(
    conn: psycopg.Connection,
    listing_id: str,
    incoming: tuple[PriceObservation, ...],
) -> tuple[PriceObservation, ...]:
    if not incoming:
        return ()
    source_ids = sorted({row.source_id for row in incoming})
    stored: list[PriceObservation] = []
    for source_id in source_ids:
        rows = conn.execute(
            """
            select session_date, value, currency, quote_unit, price_type,
                   observation_time, retrieved_at, delay_class, adjustment_status,
                   adjustment_definition, quality, source_id, source_locator, revision
            from instruments.market_price_observations
            where listing_id = %s and source_id = %s
            """,
            (listing_id, source_id),
        ).fetchall()
        for row in rows:
            stored.append(
                PriceObservation(
                    listing_key=incoming[0].listing_key,
                    session_date=row[0],
                    value=row[1],
                    currency=row[2],
                    quote_unit=row[3],
                    price_type=row[4],
                    observation_time=row[5],
                    retrieved_at=row[6],
                    delay_class=row[7],
                    adjustment_status=row[8],
                    adjustment_definition=row[9],
                    quality=row[10],
                    source_id=row[11],
                    source_locator=row[12],
                    revision=row[13],
                )
            )
    return tuple(stored)


def _listing_id(
    conn: psycopg.Connection,
    isin: str,
    mic: str,
    ticker: str,
    currency: str,
) -> str | None:
    row = conn.execute(
        """
        select listings.listing_id::text
        from instruments.listings as listings
        join instruments.share_classes as share_classes
          on share_classes.share_class_id = listings.share_class_id
        where share_classes.isin = %s
          and listings.mic = %s
          and listings.ticker = %s
          and listings.trading_currency = %s
        """,
        (isin, mic, ticker, currency),
    ).fetchone()
    return None if row is None else str(row[0])


def _umbrella_id(conn: psycopg.Connection, legal_name: str, domicile_iso2: str) -> str:
    found = conn.execute(
        """
        select umbrella_id::text
        from instruments.umbrellas
        where legal_name = %s and domicile_iso2 = %s
        order by recorded_at
        limit 1
        """,
        (legal_name, domicile_iso2),
    ).fetchone()
    if found is not None:
        return str(found[0])
    created = conn.execute(
        """
        insert into instruments.umbrellas (legal_name, domicile_iso2)
        values (%s, %s)
        returning umbrella_id::text
        """,
        (legal_name, domicile_iso2),
    ).fetchone()
    if created is None:
        raise PriceStoreError("umbrella insert did not resolve")
    return str(created[0])


def _sub_fund_id(
    conn: psycopg.Connection,
    umbrella_id: str,
    legal_name: str,
    currency: str,
) -> str:
    found = conn.execute(
        """
        select sub_fund_id::text
        from instruments.sub_funds
        where umbrella_id = %s and legal_name = %s and base_currency = %s
        order by recorded_at
        limit 1
        """,
        (umbrella_id, legal_name, currency),
    ).fetchone()
    if found is not None:
        return str(found[0])
    created = conn.execute(
        """
        insert into instruments.sub_funds (umbrella_id, legal_name, base_currency)
        values (%s, %s, %s)
        returning sub_fund_id::text
        """,
        (umbrella_id, legal_name, currency),
    ).fetchone()
    if created is None:
        raise PriceStoreError("sub-fund insert did not resolve")
    return str(created[0])


def _share_class_id(
    conn: psycopg.Connection,
    sub_fund_id: str,
    isin: str,
    distribution_policy: str,
) -> str:
    found = conn.execute(
        "select share_class_id::text from instruments.share_classes where isin = %s",
        (isin,),
    ).fetchone()
    if found is not None:
        return str(found[0])
    created = conn.execute(
        """
        insert into instruments.share_classes (
          sub_fund_id, isin, distribution_policy, hedge_status, evidence_status
        )
        values (%s, %s, %s, 'unknown', 'unverified')
        returning share_class_id::text
        """,
        (sub_fund_id, isin, distribution_policy),
    ).fetchone()
    if created is None:
        raise PriceStoreError("share class insert did not resolve")
    return str(created[0])