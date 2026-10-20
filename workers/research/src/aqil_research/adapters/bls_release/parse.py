"""Parse official BLS RSS or Atom publication feeds (offline-safe)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin, urlparse
from xml.etree import ElementTree as ET

from aqil_research.adapters.bls_release.client import ALLOWED_HOSTS, ALLOWED_PATH_PREFIXES

_ATOM = "http://www.w3.org/2005/Atom"


@dataclass(frozen=True, slots=True)
class ParsedReleaseItem:
    title: str
    canonical_url: str
    published_at: datetime | None


def parse_publication_feed(body: bytes, *, base_url: str) -> tuple[ParsedReleaseItem, ...]:
    """Return normalised release rows from RSS 2.0 or Atom."""
    text = body.decode("utf-8", errors="replace").strip()
    if not text:
        raise ValueError("empty feed body")
    root = ET.fromstring(text)
    tag = _local_name(root.tag)
    if tag == "rss":
        return _parse_rss(root, base_url=base_url)
    if tag == "feed":
        return _parse_atom(root, base_url=base_url)
    raise ValueError(f"unsupported feed root element: {tag}")


def _parse_rss(root: ET.Element, *, base_url: str) -> tuple[ParsedReleaseItem, ...]:
    channel = root.find("channel")
    if channel is None:
        raise ValueError("RSS feed missing channel")
    items: list[ParsedReleaseItem] = []
    for item in channel.findall("item"):
        title = _text(item.find("title"))
        link = _text(item.find("link"))
        guid = _text(item.find("guid"))
        url = link or guid
        if not title or not url:
            continue
        published = _parse_pub_date(_text(item.find("pubDate")))
        items.append(
            _build_item(title=title, raw_url=url, published_at=published, base_url=base_url),
        )
    if not items:
        raise ValueError("RSS feed contained no usable items")
    return tuple(items)


def _parse_atom(root: ET.Element, *, base_url: str) -> tuple[ParsedReleaseItem, ...]:
    ns = {"atom": _ATOM}
    items: list[ParsedReleaseItem] = []
    for entry in root.findall("atom:entry", ns):
        title = _text(entry.find("atom:title", ns))
        href: str | None = None
        for link_el in entry.findall("atom:link", ns):
            rel = link_el.get("rel")
            if rel is None or rel == "alternate":
                href = link_el.get("href")
                if href:
                    break
        updated = _text(entry.find("atom:updated", ns)) or _text(entry.find("atom:published", ns))
        published = _parse_iso_datetime(updated)
        if not title or not href:
            continue
        items.append(
            _build_item(title=title, raw_url=href, published_at=published, base_url=base_url),
        )
    if not items:
        raise ValueError("Atom feed contained no usable entries")
    return tuple(items)


def _build_item(
    *,
    title: str,
    raw_url: str,
    published_at: datetime | None,
    base_url: str,
) -> ParsedReleaseItem:
    canonical = _canonical_bls_url(raw_url, base_url=base_url)
    clean_title = re.sub(r"\s+", " ", title.strip())
    if not clean_title:
        raise ValueError("release item title is empty")
    return ParsedReleaseItem(
        title=clean_title,
        canonical_url=canonical,
        published_at=published_at,
    )


def _canonical_bls_url(raw_url: str, *, base_url: str) -> str:
    absolute = urljoin(base_url, raw_url.strip())
    parsed = urlparse(absolute)
    if parsed.scheme != "https":
        raise ValueError(f"release URL must be https: {absolute}")
    if parsed.hostname not in ALLOWED_HOSTS:
        raise ValueError(f"release URL host not allowlisted: {parsed.hostname}")
    path = parsed.path or "/"
    if not any(path.startswith(prefix) for prefix in ALLOWED_PATH_PREFIXES):
        raise ValueError(f"release URL path not allowlisted: {path}")
    if parsed.query or parsed.fragment:
        raise ValueError("release URL must not include query or fragment")
    return f"https://{parsed.hostname}{path}"


def _parse_pub_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = parsedate_to_datetime(value.strip())
    except (TypeError, ValueError, IndexError):
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _text(element: ET.Element | None) -> str | None:
    if element is None or element.text is None:
        return None
    return element.text.strip()


def _local_name(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[-1]
    return tag
