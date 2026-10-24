"""Fetch one METI industrial production workbook. History is not a request parameter."""

from __future__ import annotations

import time

import httpx

from aqil_research.adapters.meti_iip_production.constants import ACCESS_URL, API_ORIGIN

USER_AGENT = "AqilResearch/1.0 (local research retrieval)"
ALLOWED_HOST = "www.meti.go.jp"
MAX_RESPONSE_BYTES = 2_000_000
MAX_ATTEMPTS = 3
BACKOFF_BASE_S = 0.5
CONNECT_TIMEOUT_S = 10.0
READ_TIMEOUT_S = 60.0


class MetiIipClientError(Exception):
    """Raised when the METI production workbook cannot be fetched."""


def series_workbook_url() -> str:
    """Current workbook only. includeHistory is not a parameter of this file."""
    if "includeHistory" in ACCESS_URL:
        raise MetiIipClientError("includeHistory must not be requested")
    return ACCESS_URL


def series_request_headers() -> dict[str, str]:
    return {
        "Accept": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "User-Agent": USER_AGENT,
    }


def fetch_workbook() -> tuple[bytes, int]:
    """Download the current workbook. Returns bytes and the HTTP status."""
    url = series_workbook_url()
    parsed = httpx.URL(url)
    if (
        parsed.host != ALLOWED_HOST
        or parsed.scheme != "https"
        or not url.startswith(
            f"{API_ORIGIN}/",
        )
    ):
        raise MetiIipClientError("refusing a non-METI data host")
    if "includeHistory" in url:
        raise MetiIipClientError("includeHistory must not be requested")
    last_error = "METI workbook request failed"
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            with httpx.Client(
                timeout=httpx.Timeout(CONNECT_TIMEOUT_S, read=READ_TIMEOUT_S),
                follow_redirects=False,
            ) as client:
                response = client.get(url, headers=series_request_headers())
        except httpx.HTTPError as exc:
            last_error = "METI workbook request failed"
            if attempt == MAX_ATTEMPTS:
                raise MetiIipClientError(last_error) from exc
            time.sleep(BACKOFF_BASE_S * attempt)
            continue
        if response.status_code != 200:
            last_error = f"METI workbook returned HTTP {response.status_code}"
            if 400 <= response.status_code < 500 or attempt == MAX_ATTEMPTS:
                raise MetiIipClientError(last_error)
            time.sleep(BACKOFF_BASE_S * attempt)
            continue
        if len(response.content) > MAX_RESPONSE_BYTES:
            raise MetiIipClientError("METI workbook exceeds the size limit")
        return response.content, response.status_code
    raise MetiIipClientError(last_error)
