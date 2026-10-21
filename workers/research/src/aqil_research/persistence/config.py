"""Research database connection settings (worker principal, not service_role)."""

from __future__ import annotations

import os

DEFAULT_LOCAL_URL = "postgresql://research_worker:research_worker@127.0.0.1:55432/postgres"


def research_database_url() -> str | None:
    return os.environ.get("RESEARCH_DATABASE_URL", "").strip() or None


def research_database_url_or_local_default() -> str:
    return research_database_url() or DEFAULT_LOCAL_URL
