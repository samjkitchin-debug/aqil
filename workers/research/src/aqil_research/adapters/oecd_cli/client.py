"""Fetch one OECD composite-leading-indicator CSV. History is not requested."""

from __future__ import annotations

import httpx

from aqil_research.adapters.oecd_cli.constants import ACCESS_URL, API_ORIGIN

USER_AGENT = "AqilResearch/1.0 (local research retrieval)"
ALLOWED_HOST = "sdmx.oecd.org"
MAX_RESPONSE_BYTES = 2_000_000
MAX_ATTEMPTS = 2
CONNECT_TIMEOUT_S = 10.0
READ_TIMEOUT_S = 60.0
RETRY_STATUSES = frozenset({429, 503})


class OecdCliClientError(Exception):
    """Raised when the OECD CLI CSV cannot be fetched."""


def series_csv_url() -> str:
    """Current series only. includeHistory is not a parameter of this query."""
    if "includeHistory" in ACCESS_URL:
        raise OecdCliClientError("includeHistory must not be requested")
    return ACCESS_URL


def series_request_headers() -> dict[str, str]:
    return {"Accept": "text/csv", "User-Agent": USER_AGENT}


def fetch_series_csv() -> tuple[str, int]:
    """Download the current CSV. Returns text and the HTTP status."""
    url = series_csv_url()
    parsed_host = httpx.URL(url).host
    if parsed_host != ALLOWED_HOST or not url.startswith(f"{API_ORIGIN}/"):
        raise OecdCliClientError("refusing a non-OECD data host")
    if "includeHistory" in url:
        raise OecdCliClientError("includeHistory must not be requested")
    last_error: Exception | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            with httpx.Client(
                timeout=httpx.Timeout(CONNECT_TIMEOUT_S, read=READ_TIMEOUT_S),
                follow_redirects=False,
            ) as client:
                response = client.get(url, headers=series_request_headers())
        except httpx.HTTPError as exc:
            last_error = exc
            if attempt == MAX_ATTEMPTS:
                raise OecdCliClientError(str(exc)) from exc
            continue
        if response.status_code in RETRY_STATUSES and attempt < MAX_ATTEMPTS:
            continue
        if response.status_code != 200:
            raise OecdCliClientError(f"OECD SDMX returned HTTP {response.status_code}")
        if len(response.content) > MAX_RESPONSE_BYTES:
            raise OecdCliClientError("OECD SDMX response exceeds the size limit")
        return response.text, response.status_code
    raise OecdCliClientError(str(last_error or "OECD SDMX request was not completed"))
