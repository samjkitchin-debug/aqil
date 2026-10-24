"""Fetch one Cabinet Office machinery-orders workbook. History is not requested."""

from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse

import httpx

from aqil_research.adapters.bls_release.client import AQIL_RETRIEVAL_USER_AGENT
from aqil_research.adapters.cao_mo_private_ex_volatile.constants import (
    API_ORIGIN,
    CATALOGUE_URL,
)

ALLOWED_HOST = "www.esri.cao.go.jp"
WORKBOOK_PATH = re.compile(r"/jp/stat/juchu/\d{4}/\d{4}chouki-1\.xlsx")
MAX_CATALOGUE_BYTES = 500_000
MAX_WORKBOOK_BYTES = 2_000_000
MAX_ATTEMPTS = 1
CONNECT_TIMEOUT_S = 10.0
READ_TIMEOUT_S = 60.0


class CaoMoClientError(Exception):
    """Raised when the machinery-orders workbook cannot be fetched."""


def catalogue_url() -> str:
    """Current catalogue only. includeHistory is not a parameter."""
    if "includeHistory" in CATALOGUE_URL:
        raise CaoMoClientError("includeHistory must not be requested")
    return CATALOGUE_URL


def request_headers() -> dict[str, str]:
    return {"User-Agent": AQIL_RETRIEVAL_USER_AGENT}


def workbook_url_from_catalogue(html: str) -> str:
    """Return the single current chouki-1 workbook linked from the catalogue."""
    found: list[str] = []
    for match in re.finditer(r'href="([^"]+)"', html, flags=re.IGNORECASE):
        href = match.group(1).replace("&amp;", "&")
        absolute = urljoin(CATALOGUE_URL, href)
        parsed = urlparse(absolute)
        if parsed.scheme != "https" or parsed.hostname != ALLOWED_HOST:
            continue
        if WORKBOOK_PATH.fullmatch(parsed.path) is None:
            continue
        if parsed.query or parsed.fragment:
            raise CaoMoClientError("machinery-orders workbook URL must not carry a query")
        if "includeHistory" in absolute:
            raise CaoMoClientError("includeHistory must not be requested")
        found.append(absolute)
    unique = tuple(dict.fromkeys(found))
    if len(unique) != 1:
        raise CaoMoClientError(f"expected one chouki-1 workbook link, found {len(unique)}")
    return unique[0]


def fetch_workbook() -> tuple[bytes, int, str]:
    """Download the current workbook once. Returns bytes, status, and file URL."""
    catalogue = _get_once(catalogue_url(), MAX_CATALOGUE_BYTES)
    file_url = workbook_url_from_catalogue(catalogue.text)
    workbook = _get_once(file_url, MAX_WORKBOOK_BYTES)
    return workbook.content, workbook.status_code, file_url


def _get_once(url: str, size_limit: int) -> httpx.Response:
    _require_allowed(url)
    last_error = "Cabinet Office machinery-orders request failed"
    response: httpx.Response | None = None
    for _attempt in range(MAX_ATTEMPTS):
        try:
            with httpx.Client(
                timeout=httpx.Timeout(CONNECT_TIMEOUT_S, read=READ_TIMEOUT_S),
                follow_redirects=False,
            ) as client:
                response = client.get(url, headers=request_headers())
        except httpx.HTTPError as exc:
            last_error = str(exc)
            continue
        if response.status_code != 200:
            last_error = f"Cabinet Office machinery orders returned HTTP {response.status_code}"
            continue
        if len(response.content) > size_limit:
            raise CaoMoClientError(
                "Cabinet Office machinery-orders response exceeds the size limit",
            )
        return response
    raise CaoMoClientError(last_error)


def _require_allowed(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != ALLOWED_HOST:
        raise CaoMoClientError("refusing a non-Cabinet-Office host")
    if not url.startswith(f"{API_ORIGIN}/"):
        raise CaoMoClientError("refusing a non-Cabinet-Office host")
    if "includeHistory" in url:
        raise CaoMoClientError("includeHistory must not be requested")
