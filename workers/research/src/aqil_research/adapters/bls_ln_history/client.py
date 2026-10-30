"""Download the official LN flat files. This client does not call the BLS API or FRED."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

import httpx

from aqil_research.adapters.bls_ln_history.constants import DATA_URL, SERIES_ID, SERIES_URL
from aqil_research.adapters.bls_release.client import AQIL_RETRIEVAL_USER_AGENT

ALLOWED_HOST = "download.bls.gov"
ALLOWED_PREFIX = "/pub/time.series/ln/"
MAX_SERIES_BYTES = 20_000_000
MAX_DATA_BYTES = 500_000_000
TIMEOUT = httpx.Timeout(180.0, connect=20.0)


class LnClientError(RuntimeError):
    """An official LN flat file could not be read."""


@dataclass(frozen=True, slots=True)
class LnFlatFiles:
    series_text: str
    data_text: str
    series_bytes: int
    data_bytes: int


def assert_ln_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != ALLOWED_HOST:
        raise LnClientError("LN file URL is not the BLS download host")
    if not parsed.path.startswith(ALLOWED_PREFIX):
        raise LnClientError("LN file URL is outside the LN flat-file directory")
    if parsed.path not in {urlparse(SERIES_URL).path, urlparse(DATA_URL).path}:
        raise LnClientError("LN file URL is not the series file or ln.data.1.AllData")


def fetch_unemployment_flat_files() -> LnFlatFiles:
    """Download ln.series and the LNS14000000 rows of ln.data.1.AllData."""
    assert_ln_url(SERIES_URL)
    assert_ln_url(DATA_URL)
    series_text, series_bytes = _get_text(SERIES_URL, MAX_SERIES_BYTES)
    data_text, data_bytes = _matching_lines(DATA_URL, MAX_DATA_BYTES)
    return LnFlatFiles(
        series_text=series_text,
        data_text=data_text,
        series_bytes=series_bytes,
        data_bytes=data_bytes,
    )


def _get_text(url: str, max_bytes: int) -> tuple[str, int]:
    content = _read(url, max_bytes)
    try:
        return content.decode("utf-8"), len(content)
    except UnicodeDecodeError as exc:
        raise LnClientError("LN file is not UTF-8") from exc


def _matching_lines(url: str, max_bytes: int) -> tuple[str, int]:
    """Keep the header and LNS14000000. Other series in the file are not stored."""
    assert_ln_url(url)
    kept: list[str] = []
    total = 0
    pending = b""
    header_seen = False
    with httpx.Client(timeout=TIMEOUT, follow_redirects=False) as client:
        with client.stream(
            "GET",
            url,
            headers={"User-Agent": AQIL_RETRIEVAL_USER_AGENT},
        ) as response:
            if response.status_code != 200:
                raise LnClientError(f"LN file returned HTTP {response.status_code}")
            for chunk in response.iter_bytes():
                total += len(chunk)
                if total > max_bytes:
                    raise LnClientError("LN data file exceeded the size cap")
                pending += chunk
                while b"\n" in pending:
                    raw, pending = pending.split(b"\n", 1)
                    text = raw.decode("utf-8").rstrip("\r")
                    if not header_seen:
                        kept.append(text)
                        header_seen = True
                        continue
                    series_id = text.split("\t", 1)[0].strip()
                    if series_id == SERIES_ID:
                        kept.append(text)
            if pending:
                text = pending.decode("utf-8").rstrip("\r")
                series_id = text.split("\t", 1)[0].strip()
                if series_id == SERIES_ID:
                    kept.append(text)
    if not header_seen:
        raise LnClientError("LN data file was empty")
    return "\n".join(kept) + "\n", total


def _read(url: str, max_bytes: int) -> bytes:
    assert_ln_url(url)
    with httpx.Client(timeout=TIMEOUT, follow_redirects=False) as client:
        response = client.get(url, headers={"User-Agent": AQIL_RETRIEVAL_USER_AGENT})
    if response.status_code != 200:
        raise LnClientError(f"LN file returned HTTP {response.status_code}")
    if len(response.content) > max_bytes:
        raise LnClientError("LN file exceeded the size cap")
    return response.content
