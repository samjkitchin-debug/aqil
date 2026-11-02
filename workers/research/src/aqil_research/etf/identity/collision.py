"""Ticker collisions. A ticker is not a share class.

CNDX on a Canadian venue is a different fund from the London listing of that
ticker. This module does not store an ISIN and does not cite an issuer.
"""

from __future__ import annotations

CANADIAN_CNDX_MICS = frozenset({"XTSE", "XTSX", "NEOE"})


def listing_attachment_refusal(*, ticker: str, mic: str) -> str | None:
    """Refuse a listing that must not be attached by ticker alone."""

    if ticker.strip().upper() == "CNDX" and mic.strip().upper() in CANADIAN_CNDX_MICS:
        return (
            "CNDX on this venue is a different fund from the London ticker "
            "and must not be attached to that share class."
        )
    return None


def listings_share_a_cited_class(
    *,
    cited_isin: str | None,
    left_ticker: str,
    left_mic: str,
    right_ticker: str,
    right_mic: str,
) -> bool:
    """Two listings share a share class only after an ISIN citation.

    A missing ISIN refuses the pair. A refused venue refuses the pair even
    when a caller passes an ISIN.
    """

    if cited_isin is None or not cited_isin.strip():
        return False
    if listing_attachment_refusal(ticker=left_ticker, mic=left_mic) is not None:
        return False
    if listing_attachment_refusal(ticker=right_ticker, mic=right_mic) is not None:
        return False
    return True
