"""Parse the Board monetary-policy RSS feed. Official item links only."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse
from xml.etree import ElementTree as ET

from aqil_research.adapters.fed_press.constants import ALLOWED_HOSTS, ALLOWED_PATH_PREFIX


@dataclass(frozen=True, slots=True)
class FedPressItem:
    title: str
    canonical_url: str
    published_at: datetime | None


def parse_monetary_press_feed(body: bytes) -> tuple[FedPressItem, ...]:
    root = ET.fromstring(body)
    channel = root.find("channel")
    if channel is None:
        raise ValueError("monetary policy feed has no channel")
    items: list[FedPressItem] = []
    for node in channel.findall("item"):
        title = re.sub(r"\s+", " ", (node.findtext("title") or "").strip())
        link = (node.findtext("link") or "").strip()
        if not title or not link:
            continue
        items.append(
            FedPressItem(
                title=title,
                canonical_url=_canonical_press_url(link),
                published_at=_parse_pub_date(node.findtext("pubDate")),
            )
        )
    return tuple(items)


def _canonical_press_url(raw_url: str) -> str:
    parsed = urlparse(raw_url.strip())
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
        raise ValueError(f"press URL host not allowlisted: {parsed.hostname}")
    if not parsed.path.startswith(ALLOWED_PATH_PREFIX):
        raise ValueError(f"press URL path not allowlisted: {parsed.path}")
    if parsed.query or parsed.fragment:
        raise ValueError("press URL must not include a query or fragment")
    return f"https://{parsed.hostname}{parsed.path}"


def _parse_pub_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value.strip())
    except (TypeError, ValueError, IndexError):
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)
