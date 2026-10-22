"""Live fetch of the Board H.8 data package. No API key is required.

The package notice points readers to FRED after the Data Download Program
retires. This client does not call FRED. If this Board URL is not HTTP 200,
the fetch stops.
"""

from __future__ import annotations

import time
from urllib.parse import urlparse

import httpx

from aqil_research.adapters.bls_release.client import AQIL_RETRIEVAL_USER_AGENT
from aqil_research.adapters.fed_h8.package import H8PackageError, series_from_h8_bytes

PACKAGE_URL = "https://www.federalreserve.gov/datadownload/Output.aspx?rel=H8&filetype=zip"
MAX_PACKAGE_BYTES = 20_000_000
MAX_ATTEMPTS = 3
BACKOFF_BASE_S = 0.5


class H8ClientError(RuntimeError):
    """The official H.8 package could not be read."""


def fetch_h8_bundle() -> dict[str, object]:
    """Fetch B1001NCBA from the Board package."""
    parsed = urlparse(PACKAGE_URL)
    if parsed.scheme != "https" or parsed.hostname != "www.federalreserve.gov":
        raise H8ClientError("H.8 package URL is not the Board host")
    last_error = "H.8 package request failed"
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = httpx.get(
                PACKAGE_URL,
                headers={"User-Agent": AQIL_RETRIEVAL_USER_AGENT},
                timeout=120.0,
                follow_redirects=False,
            )
        except httpx.HTTPError as exc:
            last_error = "H.8 package request failed"
            if attempt < MAX_ATTEMPTS:
                time.sleep(BACKOFF_BASE_S * attempt)
                continue
            raise H8ClientError(last_error) from exc
        if response.status_code == 200:
            if len(response.content) > MAX_PACKAGE_BYTES:
                raise H8ClientError("H.8 package exceeded the size cap")
            try:
                payload = series_from_h8_bytes(response.content)
            except H8PackageError as exc:
                raise H8ClientError(str(exc)) from exc
            return _with_locator(payload)
        last_error = f"H.8 package returned HTTP {response.status_code}"
        if 400 <= response.status_code < 500 or attempt == MAX_ATTEMPTS:
            raise H8ClientError(last_error)
        time.sleep(BACKOFF_BASE_S * attempt)
    raise H8ClientError(last_error)


def _with_locator(payload: dict[str, object]) -> dict[str, object]:
    rows = payload.get("observations")
    if not isinstance(rows, list):
        return payload
    located = [
        {**row, "source_locator": PACKAGE_URL} if isinstance(row, dict) else row for row in rows
    ]
    return {**payload, "observations": located}
