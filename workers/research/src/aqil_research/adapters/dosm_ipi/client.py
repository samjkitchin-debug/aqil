"""Fetch the DOSM industrial production CSV. No key and no history parameter."""

from __future__ import annotations

import httpx

from aqil_research.adapters.dosm_ipi.constants import ACCESS_URL, API_ORIGIN

USER_AGENT = "AqilResearch/1.0 (local research retrieval)"
ALLOWED_HOST = "storage.dosm.gov.my"
MAX_RESPONSE_BYTES = 2_000_000
MAX_ATTEMPTS = 1
CONNECT_TIMEOUT_S = 10.0
READ_TIMEOUT_S = 60.0


class DosmIpiClientError(Exception):
    """Raised when the industrial production CSV cannot be fetched."""


def series_csv_url() -> str:
    if "includeHistory" in ACCESS_URL or "?" in ACCESS_URL:
        raise DosmIpiClientError("the DOSM request must not add a history query")
    return ACCESS_URL


def series_request_headers() -> dict[str, str]:
    return {"Accept": "text/csv", "User-Agent": USER_AGENT}


def fetch_series_csv() -> tuple[str, int]:
    url = series_csv_url()
    parsed = httpx.URL(url)
    if parsed.host != ALLOWED_HOST or not url.startswith(f"{API_ORIGIN}/"):
        raise DosmIpiClientError("refusing a non-DOSM host")
    if MAX_ATTEMPTS != 1:
        raise DosmIpiClientError("the DOSM client does not retry")
    try:
        with httpx.Client(
            timeout=httpx.Timeout(CONNECT_TIMEOUT_S, read=READ_TIMEOUT_S),
            follow_redirects=False,
        ) as client:
            response = client.get(url, headers=series_request_headers())
    except httpx.HTTPError as exc:
        raise DosmIpiClientError(str(exc)) from exc
    if response.status_code != 200:
        raise DosmIpiClientError(f"DOSM returned HTTP {response.status_code}")
    if len(response.content) > MAX_RESPONSE_BYTES:
        raise DosmIpiClientError("DOSM response exceeds the size limit")
    return response.text, response.status_code
