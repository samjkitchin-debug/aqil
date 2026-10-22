"""Download the official JT flat files. This client does not call the BLS Public Data API."""

from __future__ import annotations

import time
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx

from aqil_research.adapters.bls_jolts.constants import (
    DATA_URL,
    DATAELEMENT_URL,
    INDUSTRY_URL,
    RATELEVEL_URL,
    SEASONAL_URL,
    SERIES_URL,
)
from aqil_research.adapters.bls_release.client import AQIL_RETRIEVAL_USER_AGENT

ALLOWED_HOST = "download.bls.gov"
ALLOWED_PREFIX = "/pub/time.series/jt/"
MAX_BYTES = 16_000_000
MAX_ATTEMPTS = 3
BACKOFF_BASE_S = 0.5
TIMEOUT_S = 90.0


class JoltsClientError(RuntimeError):
    """An official JT flat file could not be read."""


@dataclass(frozen=True, slots=True)
class JoltsFetchDiagnostics:
    endpoint: str
    attempts: int
    http_status: int | None
    bls_status: str | None
    response_bytes: int


@dataclass(frozen=True, slots=True)
class JoltsFlatFiles:
    series_text: str
    seasonal_text: str
    industry_text: str
    dataelement_text: str
    ratelevel_text: str
    data_text: str
    diagnostics: JoltsFetchDiagnostics


def fetch_jolts_files() -> JoltsFlatFiles:
    """Fetch the series binding files and jt.data.2.JobOpenings only."""
    urls = (
        SERIES_URL,
        SEASONAL_URL,
        INDUSTRY_URL,
        DATAELEMENT_URL,
        RATELEVEL_URL,
        DATA_URL,
    )
    for url in urls:
        _assert_url(url)
    if not DATA_URL.endswith("/jt.data.2.JobOpenings"):
        raise JoltsClientError("job openings must be read from jt.data.2.JobOpenings")
    attempts = 0
    total_bytes = 0
    texts: dict[str, str] = {}
    with httpx.Client(timeout=TIMEOUT_S, follow_redirects=False) as client:
        for url in urls:
            body, used, status = _get(client, url)
            attempts += used
            total_bytes += len(body)
            if status != 200:
                raise JoltsClientError(f"JT file returned HTTP {status}")
            texts[url] = body.decode("utf-8")
    return JoltsFlatFiles(
        series_text=texts[SERIES_URL],
        seasonal_text=texts[SEASONAL_URL],
        industry_text=texts[INDUSTRY_URL],
        dataelement_text=texts[DATAELEMENT_URL],
        ratelevel_text=texts[RATELEVEL_URL],
        data_text=texts[DATA_URL],
        diagnostics=JoltsFetchDiagnostics(
            endpoint=DATA_URL,
            attempts=attempts,
            http_status=200,
            bls_status="ok",
            response_bytes=total_bytes,
        ),
    )


def _get(client: httpx.Client, url: str) -> tuple[bytes, int, int]:
    last_error = "JT file request failed"
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = client.get(url, headers={"User-Agent": AQIL_RETRIEVAL_USER_AGENT})
        except httpx.HTTPError as exc:
            last_error = "JT file request failed"
            if attempt == MAX_ATTEMPTS:
                raise JoltsClientError(last_error) from exc
            time.sleep(BACKOFF_BASE_S * attempt)
            continue
        if response.status_code == 200:
            if len(response.content) > MAX_BYTES:
                raise JoltsClientError("JT file exceeded the size cap")
            return response.content, attempt, response.status_code
        last_error = f"JT file returned HTTP {response.status_code}"
        if 400 <= response.status_code < 500 or attempt == MAX_ATTEMPTS:
            raise JoltsClientError(last_error)
        time.sleep(BACKOFF_BASE_S * attempt)
    raise JoltsClientError(last_error)


def _assert_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != ALLOWED_HOST:
        raise JoltsClientError("JT file URL is not the BLS download host")
    if not parsed.path.startswith(ALLOWED_PREFIX):
        raise JoltsClientError("JT file URL is outside the JT flat-file directory")
