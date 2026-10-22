"""Download the official CE flat files. This client does not call the BLS Public Data API."""

from __future__ import annotations

import time
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx

from aqil_research.adapters.bls_payrolls.constants import (
    DATA_URL,
    DATATYPE_URL,
    SEASONAL_URL,
    SERIES_URL,
)
from aqil_research.adapters.bls_release.client import AQIL_RETRIEVAL_USER_AGENT

ALLOWED_HOST = "download.bls.gov"
ALLOWED_PREFIX = "/pub/time.series/ce/"
MAX_BYTES = 8_000_000
MAX_ATTEMPTS = 3
BACKOFF_BASE_S = 0.5
TIMEOUT_S = 60.0


class PayrollClientError(RuntimeError):
    """An official CE flat file could not be read."""


@dataclass(frozen=True, slots=True)
class PayrollFetchDiagnostics:
    endpoint: str
    attempts: int
    http_status: int | None
    bls_status: str | None
    response_bytes: int


@dataclass(frozen=True, slots=True)
class PayrollFlatFiles:
    series_text: str
    datatype_text: str
    seasonal_text: str
    data_text: str
    diagnostics: PayrollFetchDiagnostics


def fetch_payroll_files() -> PayrollFlatFiles:
    """Fetch the series binding files and the total-nonfarm employment file."""
    _assert_url(SERIES_URL)
    _assert_url(DATATYPE_URL)
    _assert_url(SEASONAL_URL)
    _assert_url(DATA_URL)
    if "AllCESSeries" in DATA_URL or "/pub/time.series/ln/" in DATA_URL:
        raise PayrollClientError("payroll retrieval must not use another BLS database")
    attempts = 0
    total_bytes = 0
    texts: dict[str, str] = {}
    with httpx.Client(timeout=TIMEOUT_S, follow_redirects=False) as client:
        for url in (SERIES_URL, DATATYPE_URL, SEASONAL_URL, DATA_URL):
            body, used, status = _get(client, url)
            attempts += used
            total_bytes += len(body)
            if status != 200:
                raise PayrollClientError(f"CE file returned HTTP {status}")
            texts[url] = body.decode("utf-8")
    return PayrollFlatFiles(
        series_text=texts[SERIES_URL],
        datatype_text=texts[DATATYPE_URL],
        seasonal_text=texts[SEASONAL_URL],
        data_text=texts[DATA_URL],
        diagnostics=PayrollFetchDiagnostics(
            endpoint=DATA_URL,
            attempts=attempts,
            http_status=200,
            bls_status="ok",
            response_bytes=total_bytes,
        ),
    )


def _get(client: httpx.Client, url: str) -> tuple[bytes, int, int]:
    last_error = "CE file request failed"
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = client.get(url, headers={"User-Agent": AQIL_RETRIEVAL_USER_AGENT})
        except httpx.HTTPError as exc:
            last_error = "CE file request failed"
            if attempt == MAX_ATTEMPTS:
                raise PayrollClientError(last_error) from exc
            time.sleep(BACKOFF_BASE_S * attempt)
            continue
        if response.status_code == 200:
            if len(response.content) > MAX_BYTES:
                raise PayrollClientError("CE file exceeded the size cap")
            return response.content, attempt, response.status_code
        last_error = f"CE file returned HTTP {response.status_code}"
        if 400 <= response.status_code < 500 or attempt == MAX_ATTEMPTS:
            raise PayrollClientError(last_error)
        time.sleep(BACKOFF_BASE_S * attempt)
    raise PayrollClientError(last_error)


def _assert_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != ALLOWED_HOST:
        raise PayrollClientError("CE file URL is not the BLS download host")
    if not parsed.path.startswith(ALLOWED_PREFIX):
        raise PayrollClientError("CE file URL is outside the CE flat-file directory")
