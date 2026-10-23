"""Unverified ETF identity candidates. Shared types stay in etf.contracts."""

from aqil_research.etf.identity.catalogue import (
    ANCHOR_ISIN,
    ANCHOR_SOURCE_ID,
    ANCHOR_SOURCE_LOCATOR,
    ANCHOR_TICKER,
    CandidateShareClass,
    anchor_identity,
    candidate_catalogue,
    ticker_change_keeps_share_class,
)

__all__ = [
    "ANCHOR_ISIN",
    "ANCHOR_SOURCE_ID",
    "ANCHOR_SOURCE_LOCATOR",
    "ANCHOR_TICKER",
    "CandidateShareClass",
    "anchor_identity",
    "candidate_catalogue",
    "ticker_change_keeps_share_class",
]
