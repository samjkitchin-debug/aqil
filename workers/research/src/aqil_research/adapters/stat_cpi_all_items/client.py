"""Fetch one Statistics Bureau CPI CSV. History is not requested."""

from __future__ import annotations

import httpx

from aqil_research.adapters.bls_release.client import AQIL_RETRIEVAL_USER_AGENT
from aqil_research.adapters.stat_cpi_all_items.constants import ACCESS_URL, API_ORIGIN

ALLOWED_HOST = "www.stat.go.jp"
MAX_RESPONSE_BYTES = 1_000_000
MAX_ATTEMPTS = 1
CONNECT_TIMEOUT_S = 10.0
READ_TIMEOUT_S = 60.0


class StatCpiClientError(Exception):
    """Raised when the Statistics Bureau CPI CSV cannot be fetched."""


def cpi_csv_url() -> str:
    """Current reference file only. includeHistory is not a parameter."""
    if "includeHistory" in ACCESS_URL:
        raise StatCpiClientError("includeHistory must not be requested")
    return ACCESS_URL


def cpi_request_headers() -> dict[str, str]:
    return {"Accept": "text/csv", "User-Agent": AQIL_RETRIEVAL_USER_AGENT}


def fetch_cpi_csv() -> tuple[bytes, int]:
    """Download the current CSV once. Returns bytes and the HTTP status."""
    url = cpi_csv_url()
    _require_allowed(url)
    last_error = "Statistics Bureau CPI request failed"
    for _attempt in range(MAX_ATTEMPTS):
        try:
            with httpx.Client(
                timeout=httpx.Timeout(CONNECT_TIMEOUT_S, read=READ_TIMEOUT_S),
                follow_redirects=False,
            ) as client:
                response = client.get(url, headers=cpi_request_headers())
        except httpx.HTTPError as exc:
            last_error = str(exc)
            continue
        if response.status_code != 200:
            last_error = f"Statistics Bureau CPI CSV returned HTTP {response.status_code}"
            continue
        if len(response.content) > MAX_RESPONSE_BYTES:
            raise StatCpiClientError("Statistics Bureau CPI CSV exceeds the size limit")
        return response.content, response.status_code
    raise StatCpiClientError(last_error)


def _require_allowed(url: str) -> None:
    parsed = httpx.URL(url)
    if parsed.host != ALLOWED_HOST or not url.startswith(f"{API_ORIGIN}/"):
        raise StatCpiClientError("refusing a non-Statistics-Bureau host")
    if "includeHistory" in url:
        raise StatCpiClientError("includeHistory must not be requested")
