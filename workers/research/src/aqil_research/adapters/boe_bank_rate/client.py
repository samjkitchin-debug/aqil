"""Fetch the official Bank Rate CSV. Provisional data is not requested."""

from __future__ import annotations

import httpx

from aqil_research.adapters.boe_bank_rate.constants import ACCESS_URL, API_ORIGIN

USER_AGENT = "AqilResearch/1.0 (local research retrieval)"
ALLOWED_HOST = "www.bankofengland.co.uk"
MAX_RESPONSE_BYTES = 2_000_000
MAX_ATTEMPTS = 2
CONNECT_TIMEOUT_S = 10.0
READ_TIMEOUT_S = 60.0
RETRY_STATUSES = frozenset({429, 503})


class BoeBankRateClientError(Exception):
    """Raised when the Bank Rate CSV cannot be fetched."""


def series_csv_url() -> str:
    """Current published series. VPD and includeHistory are not parameters."""
    if "VPD=" in ACCESS_URL or "includeHistory" in ACCESS_URL:
        raise BoeBankRateClientError("provisional data and history must not be requested")
    return ACCESS_URL


def series_request_headers() -> dict[str, str]:
    return {"Accept": "text/csv", "User-Agent": USER_AGENT}


def fetch_series_csv() -> tuple[str, int]:
    """Download the current CSV. Returns text and the HTTP status."""
    url = series_csv_url()
    _require_boe_host(url)
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
                raise BoeBankRateClientError(str(exc)) from exc
            continue
        if response.status_code in RETRY_STATUSES and attempt < MAX_ATTEMPTS:
            continue
        if response.status_code != 200:
            raise BoeBankRateClientError(f"Bank of England returned HTTP {response.status_code}")
        if len(response.content) > MAX_RESPONSE_BYTES:
            raise BoeBankRateClientError("Bank of England response exceeds the size limit")
        return response.text, response.status_code
    raise BoeBankRateClientError(str(last_error or "Bank of England request was not completed"))


def _require_boe_host(url: str) -> None:
    parsed_host = httpx.URL(url).host
    if parsed_host != ALLOWED_HOST or not url.startswith(f"{API_ORIGIN}/"):
        raise BoeBankRateClientError("refusing a non-Bank of England data host")
    if "VPD=" in url or "includeHistory" in url:
        raise BoeBankRateClientError("provisional data and history must not be requested")
