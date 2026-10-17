"""Manual ETF holdings JSON import."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import psycopg
import pytest

from aqil_research.forward.holdings_import import (
    HoldingsImportValidationError,
    import_holdings_from_file,
    validate_holdings_document,
)
from aqil_research.persistence.config import research_database_url_or_local_default
from aqil_research.persistence.connection import research_connection

FIXTURE = (
    Path(__file__).resolve().parents[1] / "fixtures" / "forward" / "holdings_manual_import_ci.json"
)


def _db_available() -> bool:
    try:
        with psycopg.connect(research_database_url_or_local_default(), connect_timeout=2) as conn:
            with conn.cursor() as cur:
                cur.execute("select 1")
        return True
    except Exception:
        return False


pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def require_db() -> None:
    if not _db_available():
        pytest.skip("local Supabase not available")


def test_provider_holdings_requires_internal_retention_authorisation() -> None:
    document = {
        "etf_id": "etf:test",
        "as_of_date": "2026-01-01",
        "completeness": "top_holdings_partial",
        "source_id": "vanguard_uk_vwra_holdings",
        "source_locator": "https://example.com/holdings",
        "evidence_class": "provider_holdings",
        "lines": [{"line_id": "1", "holding_name": "X", "weight_percentage": "1"}],
    }
    with pytest.raises(HoldingsImportValidationError):
        validate_holdings_document(document)


def test_manual_holdings_import_idempotent(require_db: None) -> None:
    observed = datetime(2099, 1, 3, 12, 0, tzinfo=UTC)
    with research_connection() as conn:
        first = import_holdings_from_file(conn, FIXTURE, recorded_at=observed)
        assert first.outcome == "completed"
        assert first.row_status == "new"
        second = import_holdings_from_file(conn, FIXTURE, recorded_at=observed)
        assert second.outcome == "completed"
        assert second.row_status == "unchanged"
        assert first.snapshot_id == second.snapshot_id
