"""Sample listings from the 2 November 2026 symbol search.

These rows are ticker, MIC, and trading-currency candidates. They are not
ISINs, not share classes, and not permission to store a price.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from aqil_research.etf.identity.collision import listing_attachment_refusal


class SampleListing(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ticker: str
    mic: str
    trading_currency: str
    cited_isin: str | None = None


SAMPLE_LISTINGS: tuple[SampleListing, ...] = (
    SampleListing(ticker="VWRA", mic="XLON", trading_currency="USD"),
    SampleListing(ticker="EIMI", mic="XLON", trading_currency="USD"),
    SampleListing(ticker="CNDX", mic="XLON", trading_currency="USD"),
    SampleListing(ticker="IUIT", mic="XLON", trading_currency="USD"),
    SampleListing(ticker="IWMO", mic="XLON", trading_currency="USD"),
    SampleListing(ticker="VWCE", mic="XETR", trading_currency="EUR"),
)


def candidate_listings() -> tuple[SampleListing, ...]:
    """Drop a listing the collision guard refuses. A candidate is not a citation."""

    return tuple(
        listing
        for listing in SAMPLE_LISTINGS
        if listing.cited_isin is None
        and listing_attachment_refusal(ticker=listing.ticker, mic=listing.mic) is None
    )
