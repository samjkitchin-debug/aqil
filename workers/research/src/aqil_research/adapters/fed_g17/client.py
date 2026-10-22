"""Live fetch of one Board G.17 series. No API key is required.

The full G.17 zip is not requested. This client reads the preformatted Table 4
package and stops when that URL is not HTTP 200. It does not switch provider.
"""

from __future__ import annotations

import csv
import time
from urllib.parse import urlparse

import httpx

from aqil_research.adapters.bls_release.client import AQIL_RETRIEVAL_USER_AGENT
from aqil_research.adapters.fed_g17.package import G17PackageError, extract_total_index
from aqil_research.adapters.fed_g17.parse import SERIES_ID

PACKAGE_URL = (
    "https://www.federalreserve.gov/datadownload/Output.aspx"
    "?rel=G17&series=5d88c03b0036f0334d78f6bafefc5101"
    "&lastobs=&from=&to=&filetype=csv&label=include&layout=seriesrow&type=package"
)
MAX_PACKAGE_BYTES = 2_000_000
MAX_ATTEMPTS = 3
BACKOFF_BASE_S = 0.5


class G17ClientError(RuntimeError):
    """The official G.17 package could not be read."""


def fetch_g17_bundle() -> dict[str, object]:
    """Fetch the total industrial production index from the Board package."""
    parsed = urlparse(PACKAGE_URL)
    if parsed.scheme != "https" or parsed.hostname != "www.federalreserve.gov":
        raise G17ClientError("G.17 package URL is not the Board host")
    last_error = "G.17 package request failed"
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            with httpx.stream(
                "GET",
                PACKAGE_URL,
                headers={"User-Agent": AQIL_RETRIEVAL_USER_AGENT},
                timeout=60.0,
                follow_redirects=False,
            ) as response:
                if response.status_code != 200:
                    last_error = f"G.17 package returned HTTP {response.status_code}"
                    if 400 <= response.status_code < 500 or attempt == MAX_ATTEMPTS:
                        raise G17ClientError(last_error)
                else:
                    try:
                        return _bundle_from_response(response)
                    except G17PackageError as exc:
                        raise G17ClientError(str(exc)) from exc
        except G17ClientError:
            raise
        except httpx.HTTPError as exc:
            last_error = "G.17 package request failed"
            if attempt == MAX_ATTEMPTS:
                raise G17ClientError(last_error) from exc
        time.sleep(BACKOFF_BASE_S * attempt)
    raise G17ClientError(last_error)


def _bundle_from_response(response: httpx.Response) -> dict[str, object]:
    header_line: str | None = None
    seen = 0
    for line in response.iter_lines():
        if not line.strip():
            continue
        seen += len(line.encode("utf-8")) + 1
        if seen > MAX_PACKAGE_BYTES:
            raise G17ClientError("G.17 package exceeded the size cap")
        if header_line is None:
            header_line = line.lstrip("\ufeff")
            continue
        cells = next(csv.reader([line]))
        if len(cells) > 4 and cells[4].strip() == SERIES_ID:
            extracted = extract_total_index(f"{header_line}\n{line}\n")
            return _with_locator(extracted)
    raise G17ClientError(f"{SERIES_ID} was not in the G.17 package")


def _with_locator(extracted: dict[str, object]) -> dict[str, object]:
    rows = extracted.get("observations")
    if not isinstance(rows, list):
        raise G17ClientError("G.17 package did not contain observations")
    located = [{**row, "source_locator": PACKAGE_URL} for row in rows]
    return {**extracted, "http_status": 200, "observations": located}
