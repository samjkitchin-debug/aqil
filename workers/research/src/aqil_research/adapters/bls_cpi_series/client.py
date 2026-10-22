"""Fetch the narrow BLS CPI-U flat files. This is not the CPI Atom feed."""

from __future__ import annotations

import time
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx

from aqil_research.adapters.bls_release.client import AQIL_RETRIEVAL_USER_AGENT

SERIES_FILE_URL = "https://download.bls.gov/pub/time.series/cu/cu.series"
DATA_FILE_URL = "https://download.bls.gov/pub/time.series/cu/cu.data.1.AllItems"
ALLOWED_HOST = "download.bls.gov"
ALLOWED_PATH_PREFIX = "/pub/time.series/cu/"

# cu.series is about 1.3 MB and cu.data.1.AllItems is about 2.7 MB.
# The cap stays above those files and below the rest of the CU directory.
MAX_SERIES_BYTES = 4_000_000
MAX_DATA_BYTES = 8_000_000
CONNECT_TIMEOUT_S = 10.0
READ_TIMEOUT_S = 60.0
MAX_ATTEMPTS = 3
BACKOFF_BASE_S = 0.5


class CpiClientError(Exception):
    """The official CU flat file could not be fetched safely."""


@dataclass(frozen=True, slots=True)
class CpiFlatFileText:
    series_text: str
    data_text: str
    series_bytes: int
    data_bytes: int
    series_status: int
    data_status: int


def assert_cpi_download_url(url: str) -> None:
    """Allow only the public CU directory on the BLS download host."""
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != ALLOWED_HOST:
        raise CpiClientError("CPI flat file URL is not the BLS download host")
    if parsed.username or parsed.password or parsed.port not in {None, 443}:
        raise CpiClientError("CPI flat file URL is not the BLS download host")
    if not parsed.path.startswith(ALLOWED_PATH_PREFIX):
        raise CpiClientError("CPI flat file path is outside the CU directory")


def fetch_cpi_flat_files() -> CpiFlatFileText:
    """Download cu.series and the all-items data file. Nothing is written to a database."""
    series_text, series_status, series_bytes = _get_text(SERIES_FILE_URL, MAX_SERIES_BYTES)
    data_text, data_status, data_bytes = _get_text(DATA_FILE_URL, MAX_DATA_BYTES)
    return CpiFlatFileText(
        series_text=series_text,
        data_text=data_text,
        series_bytes=series_bytes,
        data_bytes=data_bytes,
        series_status=series_status,
        data_status=data_status,
    )


def _get_text(url: str, max_bytes: int) -> tuple[str, int, int]:
    assert_cpi_download_url(url)
    last_error = "CPI flat file request failed"
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            text, status, size = _read_once(url, max_bytes)
        except CpiClientError as exc:
            if "exceeded the size cap" in str(exc) or "not UTF-8" in str(exc):
                raise
            last_error = str(exc)
            if "HTTP 4" in last_error or attempt == MAX_ATTEMPTS:
                raise
            time.sleep(BACKOFF_BASE_S * attempt)
            continue
        except httpx.HTTPError as exc:
            last_error = "CPI flat file request failed"
            if attempt == MAX_ATTEMPTS:
                raise CpiClientError(last_error) from exc
            time.sleep(BACKOFF_BASE_S * attempt)
            continue
        return text, status, size
    raise CpiClientError(last_error)


def _read_once(url: str, max_bytes: int) -> tuple[str, int, int]:
    timeout = httpx.Timeout(READ_TIMEOUT_S, connect=CONNECT_TIMEOUT_S)
    with httpx.Client(timeout=timeout, follow_redirects=False) as client:
        with client.stream(
            "GET",
            url,
            headers={
                "Accept": "text/plain",
                "User-Agent": AQIL_RETRIEVAL_USER_AGENT,
            },
        ) as response:
            status = response.status_code
            if status != 200:
                raise CpiClientError(f"CPI flat file returned HTTP {status}")
            chunks: list[bytes] = []
            total = 0
            for chunk in response.iter_bytes():
                total += len(chunk)
                if total > max_bytes:
                    raise CpiClientError("CPI flat file exceeded the size cap")
                chunks.append(chunk)
    try:
        text = b"".join(chunks).decode("utf-8")
    except UnicodeDecodeError as exc:
        raise CpiClientError("CPI flat file is not UTF-8") from exc
    return text, status, total
