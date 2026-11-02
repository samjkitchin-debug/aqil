"""Research database connection settings (worker principal, not service_role)."""

from __future__ import annotations

import os
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

DEFAULT_LOCAL_URL = "postgresql://research_worker:research_worker@127.0.0.1:55432/postgres"


def normalize_database_url(url: str) -> str:
    """Drop a libpq-only query parameter that psycopg rejects. Do not log the URL."""
    if "uselibpqcompat" not in url:
        return url
    parsed = urlparse(url)
    query = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if key != "uselibpqcompat"
    ]
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", urlencode(query), ""))


def research_database_url() -> str | None:
    raw = os.environ.get("RESEARCH_DATABASE_URL", "").strip()
    return normalize_database_url(raw) if raw else None


def research_database_url_or_local_default() -> str:
    return research_database_url() or DEFAULT_LOCAL_URL
