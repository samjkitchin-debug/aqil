"""Read-only audit of the stored CNDX and VWRA price rows.

This module does not download a series and does not score a coefficient.
"""

from __future__ import annotations

from pathlib import Path

import psycopg

from aqil_research.long_horizon.pilot import LOCAL_ETF_URL, repo_root


def load_facts(connection: psycopg.Connection) -> dict[str, object]:
    """What the stored rows are. Empty tables stay empty."""
    connection.read_only = True
    with connection.cursor() as cursor:
        cursor.execute("select current_database()")
        if cursor.fetchone()[0] != "aqil_etf":
            raise RuntimeError("the return audit reads aqil_etf")
        cursor.execute(
            """
            select l.ticker, l.mic, l.trading_currency, s.isin, s.distribution_policy,
                   p.currency, p.quote_unit, p.price_type, p.adjustment_status,
                   count(*)::int, min(p.session_date), max(p.session_date)
            from instruments.listings l
            join instruments.share_classes s on s.share_class_id = l.share_class_id
            join instruments.market_price_observations p on p.listing_id = l.listing_id
            where l.ticker in ('CNDX', 'VWRA')
            group by 1, 2, 3, 4, 5, 6, 7, 8, 9
            order by 1, 8
            """
        )
        prices = cursor.fetchall()
        cursor.execute("select count(*)::int from instruments.nav_observations")
        nav = int(cursor.fetchone()[0])
        cursor.execute("select count(*)::int from instruments.fund_returns")
        fund_returns = int(cursor.fetchone()[0])
        cursor.execute("select count(*)::int from instruments.benchmark_returns")
        benchmark_returns = int(cursor.fetchone()[0])
        cursor.execute("select count(*)::int from instruments.fx_observations")
        fx = int(cursor.fetchone()[0])
        cursor.execute(
            """
            select price_type, adjustment_status, count(*)::int
            from instruments.market_price_observations
            group by 1, 2
            order by 1, 2
            """
        )
        price_types = cursor.fetchall()
    return {
        "prices": prices,
        "nav": nav,
        "fund_returns": fund_returns,
        "benchmark_returns": benchmark_returns,
        "fx": fx,
        "price_types": price_types,
    }


def render(facts: dict[str, object]) -> str:
    """UK English audit. Economic investment claims stay blocked."""
    lines = [
        "# Return audit",
        "",
        "Retrospective price description. This is not a total-return study and not a "
        "point-in-time signal. `publication_allowed` stays false. This record is not Verified.",
        "",
        "## What is stored",
        "",
        "The only stored market-price rows for these listings are split-adjusted closes. "
        "A split-adjusted close stays a split-adjusted close. It is not relabelled as a "
        "distribution-adjusted total return, an issuer net asset value, the Nasdaq-100 "
        "index, or an investor return after costs and foreign exchange.",
        "",
        "| Ticker | MIC | Listing currency | ISIN | Distribution policy | "
        "Price currency | Quote | Price type | Adjustment | Sessions | First | Last |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | ---: | --- | --- |",
    ]
    prices = facts["prices"]
    if not isinstance(prices, list):
        raise RuntimeError("price rows are missing")
    for row in prices:
        (
            ticker,
            mic,
            trading_currency,
            isin,
            policy,
            currency,
            quote,
            price_type,
            adjustment,
            count,
            first,
            last,
        ) = row
        lines.append(
            f"| {ticker} | {mic} | {trading_currency} | {isin} | {policy} | {currency} | "
            f"{quote} | {price_type} | {adjustment} | {count} | {first} | {last} |"
        )
    lines.extend(
        [
            "",
            "Both stored listings are US dollars on XLON. The matched comparison therefore "
            "uses common eligible sessions, the same adjustment convention, and US dollars. "
            "No foreign-exchange conversion is applied.",
            "",
            "## What is absent",
            "",
            f"Issuer NAV rows in `instruments.nav_observations`: {facts['nav']}.",
            f"Share-class fund returns in `instruments.fund_returns`: {facts['fund_returns']}.",
            f"Benchmark returns in `instruments.benchmark_returns`: {facts['benchmark_returns']}.",
            f"Foreign-exchange rows in `instruments.fx_observations`: {facts['fx']}.",
            "",
            "Stored price types across the market-price table:",
            "",
        ]
    )
    for price_type, adjustment, count in facts["price_types"]:
        lines.append(f"- `{price_type}` / `{adjustment}`: {count} rows.")
    lines.extend(
        [
            "",
            "No rights-cleared official total-return or distribution series for these share "
            "classes is stored in the repository tables above. Saxo chart pages cited in the "
            "source notes were not written to `instruments` and are not used here. No new "
            "vendor file was downloaded. No Nasdaq-100 index history was constructed. No "
            "Singapore-dollar investor return was constructed.",
            "",
            "## Gap",
            "",
            "The bounded gap is the difference between a split-adjusted listing close and a "
            "distribution-adjusted total return, and between that close and an investor result "
            "after fund expenses and currency conversion. Both share classes are stored as "
            "accumulating. An accumulating class does not authorise adding a dividend on top "
            "of the close, and a price change alone is not stored as a total return. Until a "
            "rights-cleared total-return series is already in the repository, economic "
            "investment claims stay blocked. Exploratory research on the stored split-adjusted "
            "closes may proceed and must keep that label.",
            "",
            "Common eligible sessions for a CNDX and VWRA comparison start on or after the "
            "later first stored session. VWRA's first stored session is 2019-07-25. CNDX "
            "sessions before its own first stored session are refused and are not filled.",
            "",
        ]
    )
    return "\n".join(lines)


def write_audit(folder: Path | None = None) -> Path:
    target = folder or (repo_root() / "docs" / "research" / "cndx-discovery")
    target.mkdir(parents=True, exist_ok=True)
    path = target / "return-audit.md"
    with psycopg.connect(LOCAL_ETF_URL) as connection:
        text = render(load_facts(connection))
    path.write_text(text, encoding="utf-8")
    return path
