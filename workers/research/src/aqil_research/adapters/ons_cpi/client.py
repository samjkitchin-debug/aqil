"""Fetch one ONS CPI CSV. Annual and quarterly rows in the file are not a second request."""

from __future__ import annotations

import httpx

from aqil_research.adapters.ons_cpi.constants import ACCESS_URL, API_ORIGIN

USER_AGENT = "AqilResearch/1.0 (local research retrieval)"
ALLOWED_HOST = "www.ons.gov.uk"
MAX_RESPONSE_BYTES = 2_000_000
MAX_ATTEMPTS = 1
CONNECT_TIMEOUT_S = 10.0
READ_TIMEOUT_S = 60.0


class OnsCpiClientError(Exception):
    """Raised when the ONS CPI CSV cannot be fetched."""


def series_csv_url() -> str:
    """Current series file. includeHistory is not a parameter of this download."""
    if "includeHistory" in ACCESS_URL:
        raise OnsCpiClientError("includeHistory must not be requested")
    if "d7bt/mm23" not in ACCESS_URL:
        raise OnsCpiClientError("refusing a URL that is not the bound CPI series")
    return ACCESS_URL


def series_request_headers() -> dict[str, str]:
    return {"Accept": "text/csv", "User-Agent": USER_AGENT}


def fetch_series_csv() -> tuple[str, int]:
    """Download the current CSV. One attempt. Returns text and the HTTP status."""
    url = series_csv_url()
    parsed = httpx.URL(url)
    if parsed.host != ALLOWED_HOST or not url.startswith(f"{API_ORIGIN}/"):
        raise OnsCpiClientError("refusing a non-ONS host")
    if MAX_ATTEMPTS != 1:
        raise OnsCpiClientError("the ONS client does not retry")
    try:
        with httpx.Client(
            timeout=httpx.Timeout(CONNECT_TIMEOUT_S, read=READ_TIMEOUT_S),
            follow_redirects=False,
        ) as client:
            response = client.get(url, headers=series_request_headers())
    except httpx.HTTPError as exc:
        raise OnsCpiClientError(str(exc)) from exc
    if response.status_code != 200:
        raise OnsCpiClientError(f"ONS returned HTTP {response.status_code}")
    if len(response.content) > MAX_RESPONSE_BYTES:
        raise OnsCpiClientError("ONS response exceeds the size limit")
    return response.text, response.status_code
