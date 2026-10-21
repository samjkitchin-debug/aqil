"""Bounded HTTPS client for official BLS Employment Situation publication feeds."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import httpx

from aqil_research.adapters.bls_release.constants import (
    BLS_EMPSIT_ARCHIVE_URL,
    BLS_EMPSIT_RSS_URL,
)

ALLOWED_HOSTS = frozenset({"www.bls.gov"})
ALLOWED_PATH_PREFIXES = (
    "/feed/",
    "/bls/news-release/",
    "/news.release/",
)

# BLS refuses the default httpx agent. Identify this retrieval; do not imitate a browser.
AQIL_RETRIEVAL_USER_AGENT = "AqilResearch/1.0 (local research retrieval)"

MAX_RESPONSE_BYTES = 2_000_000
CONNECT_TIMEOUT_S = 10.0
READ_TIMEOUT_S = 30.0
MAX_ATTEMPTS = 3
BACKOFF_BASE_S = 0.5
MIN_REQUEST_INTERVAL_S = 0.25

_last_request_monotonic = 0.0


class BlsReleaseClientError(Exception):
    """Raised when a BLS publication feed cannot be fetched safely or successfully."""


@dataclass(frozen=True, slots=True)
class BlsReleaseFetchDiagnostics:
    endpoint: str
    attempts: int
    http_status: int | None
    response_bytes: int


@dataclass(frozen=True, slots=True)
class BlsReleaseFetchResult:
    body: bytes
    content_type: str | None
    diagnostics: BlsReleaseFetchDiagnostics


def fetch_empsit_publication_feed(
    *,
    live: bool,
    fixture_path: Path | None = None,
    use_archive_page: bool = False,
) -> BlsReleaseFetchResult:
    """Fetch RSS by default; optional archive HTML listing (same rights row)."""
    if not live:
        if fixture_path is None:
            raise BlsReleaseClientError("offline mode requires a fixture path")
        try:
            body = fixture_path.read_bytes()
        except OSError as exc:
            raise BlsReleaseClientError(str(exc)) from exc
        if len(body) > MAX_RESPONSE_BYTES:
            raise BlsReleaseClientError("fixture exceeds size limit")
        return BlsReleaseFetchResult(
            body=body,
            content_type=_guess_content_type(fixture_path),
            diagnostics=BlsReleaseFetchDiagnostics(
                endpoint=f"fixture://{fixture_path.name}",
                attempts=0,
                http_status=None,
                response_bytes=len(body),
            ),
        )

    url = BLS_EMPSIT_ARCHIVE_URL if use_archive_page else BLS_EMPSIT_RSS_URL
    _assert_url_allowed(url)
    attempts = 0
    http_status: int | None = None
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
                response = client.get(
                    url,
                    headers={
                        "Accept": "application/atom+xml, application/rss+xml, application/xml, */*",
                        "User-Agent": AQIL_RETRIEVAL_USER_AGENT,
                    },
                )
            http_status = response.status_code
            raw = response.content
            response_bytes = len(raw)
            if response_bytes > MAX_RESPONSE_BYTES:
                raise BlsReleaseClientError("response exceeds size limit")
            if http_status != 200:
                last_error = f"HTTP {http_status}"
                if 400 <= http_status < 500:
                    raise BlsReleaseClientError(last_error)
                if attempt < MAX_ATTEMPTS and http_status >= 500:
                    time.sleep(BACKOFF_BASE_S * attempt)
                    continue
                raise BlsReleaseClientError(last_error)
            content_type = response.headers.get("content-type")
            return BlsReleaseFetchResult(
                body=raw,
                content_type=content_type,
                diagnostics=BlsReleaseFetchDiagnostics(
                    endpoint=url,
                    attempts=attempts,
                    http_status=http_status,
                    response_bytes=response_bytes,
                ),
            )
        except BlsReleaseClientError:
            raise
        except httpx.HTTPError as exc:
            last_error = str(exc)
            if attempt < MAX_ATTEMPTS:
                time.sleep(BACKOFF_BASE_S * attempt)
                continue
            raise BlsReleaseClientError(last_error or "BLS feed request failed") from exc

    raise BlsReleaseClientError(last_error or "BLS feed request failed")


def _assert_url_allowed(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise BlsReleaseClientError(f"URL must use https: {url}")
    host = parsed.hostname
    if host not in ALLOWED_HOSTS:
        raise BlsReleaseClientError(f"host not allowlisted: {host}")
    path = parsed.path or "/"
    if not any(path.startswith(prefix) for prefix in ALLOWED_PATH_PREFIXES):
        raise BlsReleaseClientError(f"path not allowlisted: {path}")


def _guess_content_type(fixture_path: Path) -> str | None:
    suffix = fixture_path.suffix.lower()
    if suffix in {".rss", ".xml"}:
        return "application/rss+xml"
    if suffix in {".htm", ".html"}:
        return "text/html"
    return None


def _rate_limit() -> None:
    global _last_request_monotonic
    now = time.monotonic()
    elapsed = now - _last_request_monotonic
    if elapsed < MIN_REQUEST_INTERVAL_S:
        time.sleep(MIN_REQUEST_INTERVAL_S - elapsed)
    _last_request_monotonic = time.monotonic()
