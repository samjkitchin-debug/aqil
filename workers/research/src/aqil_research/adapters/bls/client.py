"""Bounded HTTPS client for the official BLS Public Data API."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import httpx

BLS_API_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
ALLOWED_HOSTS = frozenset({"api.bls.gov"})
MAX_REQUEST_BYTES = 8_192
MAX_RESPONSE_BYTES = 2_000_000
CONNECT_TIMEOUT_S = 10.0
READ_TIMEOUT_S = 30.0
MAX_ATTEMPTS = 3
BACKOFF_BASE_S = 0.5
MIN_REQUEST_INTERVAL_S = 0.25

_last_request_monotonic = 0.0


class BlsClientError(Exception):
    """Raised when the BLS API cannot be called safely or successfully."""


@dataclass(frozen=True, slots=True)
class BlsRequestDiagnostics:
    endpoint: str
    attempts: int
    http_status: int | None
    bls_status: str | None
    response_bytes: int
    series_id: str
    start_year: int
    end_year: int


@dataclass(frozen=True, slots=True)
class BlsApiResponse:
    payload: dict[str, Any]
    diagnostics: BlsRequestDiagnostics


def fetch_timeseries(
    series_id: str,
    start_year: int,
    end_year: int,
    *,
    live: bool,
    fixture_payload: dict[str, Any] | None = None,
) -> BlsApiResponse:
    """Fetch one series window. Offline mode uses a fixture payload only."""
    if not live:
        if fixture_payload is None:
            raise BlsClientError("offline mode requires a fixture payload")
        return BlsApiResponse(
            payload=fixture_payload,
            diagnostics=BlsRequestDiagnostics(
                endpoint="fixture://offline",
                attempts=0,
                http_status=None,
                bls_status=str(fixture_payload.get("status")),
                response_bytes=len(json.dumps(fixture_payload)),
                series_id=series_id,
                start_year=start_year,
                end_year=end_year,
            ),
        )

    _assert_url_allowed(BLS_API_URL)
    body = _build_request_body(series_id, start_year, end_year)
    encoded = json.dumps(body, separators=(",", ":")).encode("utf-8")
    if len(encoded) > MAX_REQUEST_BYTES:
        raise BlsClientError("request body exceeds size limit")

    attempts = 0
    http_status: int | None = None
    bls_status: str | None = None
    response_bytes = 0
    last_error: str | None = None

    for attempt in range(1, MAX_ATTEMPTS + 1):
        attempts = attempt
        _rate_limit()
        try:
            with httpx.Client(
                timeout=httpx.Timeout(
                    READ_TIMEOUT_S,
                    connect=CONNECT_TIMEOUT_S,
                    read=READ_TIMEOUT_S,
                    write=CONNECT_TIMEOUT_S,
                    pool=CONNECT_TIMEOUT_S,
                ),
                follow_redirects=False,
            ) as client:
                response = client.post(
                    BLS_API_URL,
                    content=encoded,
                    headers={"Content-Type": "application/json", "Accept": "application/json"},
                )
            http_status = response.status_code
            raw = response.content
            response_bytes = len(raw)
            if response_bytes > MAX_RESPONSE_BYTES:
                raise BlsClientError("response exceeds size limit")
            if http_status != 200:
                last_error = f"HTTP {http_status}"
                if 400 <= http_status < 500:
                    raise BlsClientError(last_error)
                if attempt < MAX_ATTEMPTS and http_status >= 500:
                    time.sleep(BACKOFF_BASE_S * attempt)
                    continue
                raise BlsClientError(last_error)
            payload = json.loads(raw.decode("utf-8"))
            if not isinstance(payload, dict):
                raise BlsClientError("response is not a JSON object")
            bls_status = str(payload.get("status", ""))
            if bls_status != "REQUEST_SUCCEEDED":
                message = payload.get("message", bls_status)
                raise BlsClientError(f"BLS status {bls_status}: {message}")
            return BlsApiResponse(
                payload=payload,
                diagnostics=BlsRequestDiagnostics(
                    endpoint=BLS_API_URL,
                    attempts=attempts,
                    http_status=http_status,
                    bls_status=bls_status,
                    response_bytes=response_bytes,
                    series_id=series_id,
                    start_year=start_year,
                    end_year=end_year,
                ),
            )
        except BlsClientError:
            raise
        except json.JSONDecodeError as exc:
            raise BlsClientError(f"invalid JSON response: {exc}") from exc
        except httpx.HTTPError as exc:
            last_error = str(exc)
            if attempt < MAX_ATTEMPTS:
                time.sleep(BACKOFF_BASE_S * attempt)
                continue
            raise BlsClientError(last_error or "BLS request failed") from exc

    raise BlsClientError(last_error or "BLS request failed")


def _build_request_body(series_id: str, start_year: int, end_year: int) -> dict[str, object]:
    if end_year < start_year:
        raise BlsClientError("end_year cannot precede start_year")
    api_key = os.environ.get("BLS_API_KEY", "").strip()
    inclusive_years = end_year - start_year + 1
    max_years = 20 if api_key else 10
    if inclusive_years > max_years:
        raise BlsClientError(
            f"BLS API allows at most {max_years} inclusive years per request "
            f"(requested {inclusive_years})",
        )
    body: dict[str, object] = {
        "seriesid": [series_id],
        "startyear": str(start_year),
        "endyear": str(end_year),
    }
    if api_key:
        body["registrationkey"] = api_key
    return body


def _assert_url_allowed(url: str) -> None:
    host = urlparse(url).hostname
    if host not in ALLOWED_HOSTS:
        raise BlsClientError(f"host not allowlisted: {host}")


def _rate_limit() -> None:
    global _last_request_monotonic
    now = time.monotonic()
    elapsed = now - _last_request_monotonic
    if elapsed < MIN_REQUEST_INTERVAL_S:
        time.sleep(MIN_REQUEST_INTERVAL_S - elapsed)
    _last_request_monotonic = time.monotonic()
