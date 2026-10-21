"""Bounded fetch of the official BLS selected-release calendar."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

import httpx

from aqil_research.adapters.bls_release.client import AQIL_RETRIEVAL_USER_AGENT
from aqil_research.forward.adapters.bls_ics_schedule import SOURCE_LOCATOR

MAX_RESPONSE_BYTES = 2_000_000
CONNECT_TIMEOUT_S = 10.0
READ_TIMEOUT_S = 30.0


class BlsCalendarClientError(Exception):
    """Raised when the official calendar cannot be fetched."""


def fetch_bls_ics(*, live: bool, fixture_path: Path | None = None) -> tuple[str, int | None]:
    """Return the calendar text and the HTTP status, if a live request was made."""
    if not live:
        if fixture_path is None:
            raise BlsCalendarClientError("offline mode requires a fixture path")
        text = fixture_path.read_text(encoding="utf-8")
        if len(text.encode("utf-8")) > MAX_RESPONSE_BYTES:
            raise BlsCalendarClientError("fixture exceeds size limit")
        return text, None

    parsed = urlparse(SOURCE_LOCATOR)
    if parsed.scheme != "https" or parsed.hostname != "www.bls.gov":
        raise BlsCalendarClientError("calendar URL is not the official BLS host")
    if parsed.path != "/schedule/news_release/bls.ics":
        raise BlsCalendarClientError("calendar path is not the official iCalendar")

    with httpx.Client(
        timeout=httpx.Timeout(READ_TIMEOUT_S, connect=CONNECT_TIMEOUT_S),
        follow_redirects=False,
    ) as client:
        response = client.get(
            SOURCE_LOCATOR,
            headers={
                "Accept": "text/calendar",
                "User-Agent": AQIL_RETRIEVAL_USER_AGENT,
            },
        )
    if response.status_code != 200:
        raise BlsCalendarClientError(f"HTTP {response.status_code}")
    if len(response.content) > MAX_RESPONSE_BYTES:
        raise BlsCalendarClientError("response exceeds size limit")
    return response.text, response.status_code
