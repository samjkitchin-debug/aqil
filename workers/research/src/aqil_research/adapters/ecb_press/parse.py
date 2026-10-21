"""Parse ECB press RSS and keep monetary-policy items only."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse
from xml.etree import ElementTree as ET

from aqil_research.adapters.ecb_press.constants import ALLOWED_HOST, ALLOWED_PATH_PREFIXES


@dataclass(frozen=True, slots=True)
class EcbPressItem:
    title: str
    canonical_url: str
    published_at: datetime | None


def parse_ecb_press_feed(body: bytes) -> tuple[EcbPressItem, ...]:
    root = ET.fromstring(body)
    channel = root.find("channel")
    if channel is None:
        raise ValueError("ECB press feed has no channel")
    items: list[EcbPressItem] = []
    for node in channel.findall("item"):
        title = re.sub(r"\s+", " ", (node.findtext("title") or "").strip())
        link = (node.findtext("link") or "").strip()
        if not title or not link:
            continue
        canonical = _policy_url(link)
        if canonical is None:
            continue
        items.append(
            EcbPressItem(
                title=title,
                canonical_url=canonical,
                published_at=_parse_pub_date(node.findtext("pubDate")),
            )
        )
    return tuple(items)


def _policy_url(raw_url: str) -> str | None:
    parsed = urlparse(raw_url.strip())
    if parsed.scheme != "https" or parsed.hostname != ALLOWED_HOST:
        return None
    if parsed.query or parsed.fragment:
        return None
    path = re.sub(r"/{2,}", "/", parsed.path)
    if not any(path.startswith(prefix) for prefix in ALLOWED_PATH_PREFIXES):
        return None
    return f"https://{parsed.hostname}{path}"


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
