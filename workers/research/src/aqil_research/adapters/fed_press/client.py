"""Bounded client for the Board's monetary-policy press feed."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import httpx

from aqil_research.adapters.bls_release.client import AQIL_RETRIEVAL_USER_AGENT
from aqil_research.adapters.fed_press.constants import FEED_URL

MAX_RESPONSE_BYTES = 2_000_000
MAX_ATTEMPTS = 3
BACKOFF_BASE_S = 0.5


class FedPressClientError(Exception):
    """The official feed could not be read."""


@dataclass(frozen=True, slots=True)
class FedPressFetchResult:
    body: bytes
    http_status: int | None
    endpoint_host: str


def fetch_monetary_press_feed(*, live: bool, fixture_path: Path | None) -> FedPressFetchResult:
    if not live:
        if fixture_path is None:
            raise FedPressClientError("offline collection requires a fixture")
        return FedPressFetchResult(fixture_path.read_bytes(), None, "fixture")
    parsed = urlparse(FEED_URL)
    if parsed.scheme != "https" or parsed.hostname != "www.federalreserve.gov":
        raise FedPressClientError("feed URL is not the registered Board host")
    last_error = "monetary policy feed request failed"
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = httpx.get(
                FEED_URL,
                headers={
                    "User-Agent": AQIL_RETRIEVAL_USER_AGENT,
                    "Accept": "application/rss+xml, application/xml, text/xml",
                },
                timeout=30.0,
                follow_redirects=False,
            )
        except httpx.HTTPError as exc:
            last_error = "monetary policy feed request failed"
            if attempt < MAX_ATTEMPTS:
                time.sleep(BACKOFF_BASE_S * attempt)
                continue
            raise FedPressClientError(last_error) from exc
        if response.status_code == 200:
            if len(response.content) > MAX_RESPONSE_BYTES:
                raise FedPressClientError("monetary policy feed exceeded the size cap")
            return FedPressFetchResult(
                response.content, response.status_code, parsed.hostname or ""
            )
        last_error = f"monetary policy feed returned HTTP {response.status_code}"
        if 400 <= response.status_code < 500 or attempt == MAX_ATTEMPTS:
            raise FedPressClientError(last_error)
        time.sleep(BACKOFF_BASE_S * attempt)
    raise FedPressClientError(last_error)
