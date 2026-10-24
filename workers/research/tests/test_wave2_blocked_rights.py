"""Blocked Wave 2 candidates stay disabled and are not cleared for ingest."""

from __future__ import annotations

from pathlib import Path

import psycopg

from aqil_research.sources.rights import (
    FIRST_LIVE_OPERATIONS,
    M1Role,
    OperationalStatus,
    RightsDecision,
    load_source_rights,
)

ROOT = Path(__file__).resolve().parents[3] / "docs" / "sources" / "fragments"
BLOCKED = (
    "boj_fm01_call_rate.csv",
    "boj_fm08_foreign_exchange.csv",
    "nbs_cpi.csv",
    "nbs_industrial_production.csv",
    "pboc_policy_rate.csv",
    "pboc_exchange_rate.csv",
)


def _refuse_database(*args: object, **kwargs: object) -> None:
    raise AssertionError(f"database connection is not allowed: {args!r} {kwargs!r}")


def test_blocked_fragments_are_not_ingest_ready(monkeypatch) -> None:
    monkeypatch.setattr("psycopg.connect", _refuse_database)
    assert psycopg.connect is _refuse_database
    for name in BLOCKED:
        records = load_source_rights(ROOT / name)
        assert len(records) == 1
        record = records[0]
        assert record.operational_status == OperationalStatus.DISABLED
        assert record.m1_role == M1Role.UNRESOLVED
        assert record.terms_url in record.evidence_urls
        assert record.terms_url.startswith("https://")
        permitted = [
            operation
            for operation in FIRST_LIVE_OPERATIONS
            if record.decision_for(operation) == RightsDecision.PERMITTED
        ]
        assert len(permitted) < len(FIRST_LIVE_OPERATIONS)
        assert "not ingest-ready" in record.evidence_note.lower()
