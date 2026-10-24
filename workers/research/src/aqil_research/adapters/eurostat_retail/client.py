"""Fetch one Eurostat JSON statistics series. History flags are not sent."""

from __future__ import annotations

import time
from urllib.parse import urlencode

import httpx

from aqil_research.adapters.eurostat_retail.constants import ACCESS_URL, API_ORIGIN, QUERY

USER_AGENT = "AqilResearch/1.0 (local research retrieval)"

ALLOWED_HOST = "ec.europa.eu"

MAX_RESPONSE_BYTES = 2_000_000

MAX_ATTEMPTS = 3

BACKOFF_BASE_S = 0.5

CONNECT_TIMEOUT_S = 10.0

READ_TIMEOUT_S = 90.0


class EurostatClientError(Exception):
    """Raised when the Eurostat JSON series cannot be fetched."""


def series_json_url() -> str:
    """Current filtered series. includeHistory is not a parameter."""

    query = urlencode(QUERY)

    if "includeHistory" in query:
        raise EurostatClientError("includeHistory must not be requested")

    return f"{ACCESS_URL}?{query}"


def series_request_headers() -> dict[str, str]:

    return {"Accept": "application/json", "User-Agent": USER_AGENT}


def fetch_series_json() -> tuple[str, int]:
    """Download the current JSON. Returns text and the HTTP status."""

    url = series_json_url()

    parsed_host = httpx.URL(url).host

    if parsed_host != ALLOWED_HOST or not url.startswith(f"{API_ORIGIN}/eurostat/"):
        raise EurostatClientError("refusing a non-Eurostat host")

    if "includeHistory" in url:
        raise EurostatClientError("includeHistory must not be requested")

    last_error = "Eurostat request failed"

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
                raise EurostatClientError("Eurostat response exceeds the size limit")

            last_error = f"Eurostat returned HTTP {response.status_code}"

            if 400 <= response.status_code < 500:
                break

        if attempt < MAX_ATTEMPTS:
            time.sleep(BACKOFF_BASE_S * attempt)

    raise EurostatClientError(last_error)
