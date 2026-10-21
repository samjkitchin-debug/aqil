"""Live fetch of the Board SLOOS data package. No API key is required."""

from __future__ import annotations

import time
from urllib.parse import urlparse

import httpx

from aqil_research.adapters.bls_release.client import AQIL_RETRIEVAL_USER_AGENT
from aqil_research.adapters.fed_sloos.package import SloosPackageError, observations_from_package
from aqil_research.adapters.fed_sloos.parse import SERIES_ID

PACKAGE_URL = "https://www.federalreserve.gov/datadownload/Output.aspx?rel=SLOOS&filetype=zip"
MAX_PACKAGE_BYTES = 2_000_000
MAX_ATTEMPTS = 3
BACKOFF_BASE_S = 0.5


class SloosClientError(RuntimeError):
    """The official SLOOS package could not be read."""


def fetch_sloos_bundle() -> dict[str, object]:
    """Fetch SUBLPDCILS_N.Q from the Board package.

    The former JSON address returned HTTP 404. This package is the file the
    Board still publishes without a key.
    """
    parsed = urlparse(PACKAGE_URL)
    if parsed.scheme != "https" or parsed.hostname != "www.federalreserve.gov":
        raise SloosClientError("SLOOS package URL is not the Board host")
    last_error = "SLOOS package request failed"
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = httpx.get(
                PACKAGE_URL,
                headers={"User-Agent": AQIL_RETRIEVAL_USER_AGENT},
                timeout=60.0,
                follow_redirects=False,
            )
        except httpx.HTTPError as exc:
            last_error = "SLOOS package request failed"
            if attempt < MAX_ATTEMPTS:
                time.sleep(BACKOFF_BASE_S * attempt)
                continue
            raise SloosClientError(last_error) from exc
        if response.status_code == 200:
            if len(response.content) > MAX_PACKAGE_BYTES:
                raise SloosClientError("SLOOS package exceeded the size cap")
            try:
                observations = observations_from_package(response.content)
            except SloosPackageError as exc:
                raise SloosClientError(str(exc)) from exc
            return {
                "series_id": SERIES_ID,
                "observations": [{**row, "source_locator": PACKAGE_URL} for row in observations],
            }
        last_error = f"SLOOS package returned HTTP {response.status_code}"
        if 400 <= response.status_code < 500 or attempt == MAX_ATTEMPTS:
            raise SloosClientError(last_error)
        time.sleep(BACKOFF_BASE_S * attempt)
    raise SloosClientError(last_error)
