"""Live fetch of the Board H.15 data package. No API key is required."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

import httpx

from aqil_research.adapters.bls_release.client import AQIL_RETRIEVAL_USER_AGENT
from aqil_research.adapters.fed_h15.series import PACKAGE_URL

MAX_PACKAGE_BYTES = 12_000_000


class H15ClientError(RuntimeError):
    """The official H.15 package could not be read. A non-200 response stops."""


@dataclass(frozen=True, slots=True)
class H15Download:
    url: str
    status_code: int
    content: bytes


def download_h15_package() -> H15Download:
    """Download the Board H.15 zip. Any status other than HTTP 200 stops."""
    parsed = urlparse(PACKAGE_URL)
    if parsed.scheme != "https" or parsed.hostname != "www.federalreserve.gov":
        raise H15ClientError("H.15 package URL is not the Board host")
    try:
        response = httpx.get(
            PACKAGE_URL,
            headers={"User-Agent": AQIL_RETRIEVAL_USER_AGENT},
            timeout=120.0,
            follow_redirects=False,
        )
    except httpx.HTTPError as exc:
        raise H15ClientError("H.15 package request failed") from exc
    if response.status_code != 200:
        raise H15ClientError(f"H.15 package returned HTTP {response.status_code}")
    if len(response.content) > MAX_PACKAGE_BYTES:
        raise H15ClientError("H.15 package exceeded the size cap")
    if not response.content:
        raise H15ClientError("H.15 package was empty")
    return H15Download(
        url=PACKAGE_URL,
        status_code=response.status_code,
        content=response.content,
    )
