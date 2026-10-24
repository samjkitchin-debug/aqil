"""Fetch one ECB SDMX CSV. History is not requested."""

from __future__ import annotations

import time
from urllib.parse import urlencode

import httpx

from aqil_research.adapters.ecb_hicp_core.constants import ACCESS_URL, API_ORIGIN

USER_AGENT = "AqilResearch/1.0 (local research retrieval)"
ALLOWED_HOST = "data-api.ecb.europa.eu"
MAX_RESPONSE_BYTES = 2_000_000
MAX_ATTEMPTS = 3
BACKOFF_BASE_S = 0.5
CONNECT_TIMEOUT_S = 10.0
READ_TIMEOUT_S = 60.0


class EcbHicpCoreClientError(Exception):
    """Raised when the ECB Data Portal CSV cannot be fetched."""


def series_csv_url() -> str:
    """Current series only. includeHistory is not a parameter."""
    query = urlencode((("format", "csvdata"),))
    if "includeHistory" in query:
        raise EcbHicpCoreClientError("includeHistory must not be requested")
    return f"{ACCESS_URL}?{query}"


def series_request_headers() -> dict[str, str]:
    return {"Accept": "text/csv", "User-Agent": USER_AGENT}


def fetch_series_csv() -> tuple[str, int]:
    """Download the current CSV. Returns text and the HTTP status."""
    url = series_csv_url()
    parsed_host = httpx.URL(url).host
    if parsed_host != ALLOWED_HOST or not url.startswith(f"{API_ORIGIN}/"):
        raise EcbHicpCoreClientError("refusing a non-ECB data host")
    if "includeHistory" in url:
        raise EcbHicpCoreClientError("includeHistory must not be requested")
    last_error = "ECB SDMX request failed"
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            with httpx.Client(
                timeout=httpx.Timeout(CONNECT_TIMEOUT_S, read=READ_TIMEOUT_S),
                follow_redirects=False,
            ) as client:
                response = client.get(url, headers=series_request_headers())
        except httpx.HTTPError as exc:
            last_error = str(exc)
        else:
            if response.status_code == 200 and len(response.content) <= MAX_RESPONSE_BYTES:
                return response.text, response.status_code
            if response.status_code == 200:
                raise EcbHicpCoreClientError("ECB SDMX response exceeds the size limit")
            last_error = f"ECB SDMX returned HTTP {response.status_code}"
            if 400 <= response.status_code < 500:
                break
        if attempt < MAX_ATTEMPTS:
            time.sleep(BACKOFF_BASE_S * attempt)
    raise EcbHicpCoreClientError(last_error)
