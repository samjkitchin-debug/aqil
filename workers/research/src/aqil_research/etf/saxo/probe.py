"""Optional local read-only Saxo quote check.

Production OAuth is not enabled. A 403 does not stop the price programme and
does not store a quote. Chart history is not used as the current quote.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from pydantic import BaseModel, ConfigDict

SIM_MARKER = "/sim/openapi"
INFO_PRICES = "/trade/v1/infoprices"
CHARTS = "/chart/v3/charts"
ALLOWED_PATHS = frozenset({INFO_PRICES, CHARTS})


class SaxoResponse(Protocol):
    status_code: int


class SaxoProbeResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str
    http_status: int | None
    stored: bool
    blocks_programme: bool
    reason: str


def probe_saxo_read(
    *,
    base_url: str | None,
    token: str | None,
    path: str,
    transport: Callable[[str], SaxoResponse] | None = None,
) -> SaxoProbeResult:
    """Probe one allow-listed simulation GET. Missing credentials skip the call."""

    if path not in ALLOWED_PATHS:
        return SaxoProbeResult(
            path=path,
            http_status=None,
            stored=False,
            blocks_programme=False,
            reason="That Saxo path is not an allow-listed read.",
        )
    if base_url is None or SIM_MARKER not in base_url:
        return SaxoProbeResult(
            path=path,
            http_status=None,
            stored=False,
            blocks_programme=False,
            reason="Production Saxo is not enabled. The simulation base URL is absent.",
        )
    if not token:
        return SaxoProbeResult(
            path=path,
            http_status=None,
            stored=False,
            blocks_programme=False,
            reason="No local Saxo read token is set, so the quote was not requested.",
        )
    if transport is None:
        return SaxoProbeResult(
            path=path,
            http_status=None,
            stored=False,
            blocks_programme=False,
            reason="No Saxo transport was provided, so the quote was not requested.",
        )
    response = transport(f"{base_url.rstrip('/')}{path}")
    if response.status_code == 403:
        return SaxoProbeResult(
            path=path,
            http_status=403,
            stored=False,
            blocks_programme=False,
            reason="Saxo returned HTTP 403. The quote was not stored.",
        )
    if response.status_code != 200:
        return SaxoProbeResult(
            path=path,
            http_status=response.status_code,
            stored=False,
            blocks_programme=False,
            reason="Saxo did not return a usable quote. Nothing was stored.",
        )
    return SaxoProbeResult(
        path=path,
        http_status=200,
        stored=False,
        blocks_programme=False,
        reason=(
            "Saxo returned HTTP 200. The body was not stored. "
            "A chart close is not the current quote."
        ),
    )
