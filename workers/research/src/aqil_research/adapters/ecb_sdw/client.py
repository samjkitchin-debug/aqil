"""Fetch one ECB SDMX CSV. History is not requested."""

from __future__ import annotations

from urllib.parse import urlencode

import httpx

from aqil_research.adapters.ecb_sdw.constants import ACCESS_URL, API_ORIGIN

USER_AGENT = "AqilResearch/1.0 (local research retrieval)"
ALLOWED_HOST = "data-api.ecb.europa.eu"
MAX_RESPONSE_BYTES = 2_000_000
CONNECT_TIMEOUT_S = 10.0
READ_TIMEOUT_S = 60.0


class EcbSdwClientError(Exception):
    """Raised when the ECB Data Portal CSV cannot be fetched."""


def series_csv_url() -> str:
    """Current series only. includeHistory is not a parameter."""
    query = urlencode((("format", "csvdata"),))
    if "includeHistory" in query:
        raise EcbSdwClientError("includeHistory must not be requested")
    return f"{ACCESS_URL}?{query}"


def series_request_headers() -> dict[str, str]:
    return {"Accept": "text/csv", "User-Agent": USER_AGENT}


def fetch_series_csv() -> tuple[str, int]:
    """Download the current CSV. Returns text and the HTTP status."""
    url = series_csv_url()
    parsed_host = httpx.URL(url).host
    if parsed_host != ALLOWED_HOST or not url.startswith(f"{API_ORIGIN}/"):
        raise EcbSdwClientError("refusing a non-ECB data host")
    if "includeHistory" in url:
        raise EcbSdwClientError("includeHistory must not be requested")
    try:
        with httpx.Client(
            timeout=httpx.Timeout(CONNECT_TIMEOUT_S, read=READ_TIMEOUT_S),
            follow_redirects=False,
        ) as client:
            response = client.get(url, headers=series_request_headers())
    except httpx.HTTPError as exc:
        raise EcbSdwClientError(str(exc)) from exc
    if response.status_code != 200:
        raise EcbSdwClientError(f"ECB SDMX returned HTTP {response.status_code}")
    if len(response.content) > MAX_RESPONSE_BYTES:
        raise EcbSdwClientError("ECB SDMX response exceeds the size limit")
    return response.text, response.status_code
