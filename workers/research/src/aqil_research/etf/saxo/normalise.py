"""Normalise a LIVE Saxo payload. This module does not call Saxo or store a row."""

from __future__ import annotations


def live_quote_kinds(body: dict) -> tuple[str, ...]:
    """Name the quote fields that were present.

    NoAccess is a refusal. A missing last is not copied from bid or ask.
    """

    quote = body.get("Quote") if isinstance(body, dict) else None
    if not isinstance(quote, dict):
        return ()
    bid_type = quote.get("PriceTypeBid")
    ask_type = quote.get("PriceTypeAsk")
    if bid_type == "NoAccess" or ask_type == "NoAccess":
        return ("refused",)
    kinds: list[str] = []
    if quote.get("Bid") is not None:
        kinds.append("bid")
    if quote.get("Ask") is not None:
        kinds.append("ask")
    if quote.get("Last") is not None:
        kinds.append("last")
    return tuple(kinds)


def live_chart_kind(body: dict) -> str:
    """A chart close stays a close. It is not labelled as the last trade."""

    data = body.get("Data") if isinstance(body, dict) else None
    if not isinstance(data, list) or not data:
        return "no-bars"
    if any(isinstance(row, dict) and row.get("Last") is not None for row in data):
        return "last"
    if any(isinstance(row, dict) and row.get("Close") is not None for row in data):
        return "close"
    return "no-bars"
