"""Wave 2 rights fragments that are not cleared for collection."""

from __future__ import annotations

from pathlib import Path

from aqil_research.sources.rights import (
    FIRST_LIVE_OPERATIONS,
    M1Role,
    OperationalStatus,
    RightsDecision,
    load_source_rights,
)

ROOT = Path(__file__).resolve().parents[3] / "docs" / "sources" / "fragments"


def _load(name: str):
    return load_source_rights(ROOT / name)[0]


def test_blocked_fragments_are_not_first_live_sources() -> None:
    expected = {
        "sbj_cpi_all_items.csv": "credential required",
        "sbj_cpi_all_items_less_fresh_food.csv": "credential required",
        "boj_fm01_call_rate.csv": "rights pending",
        "boj_fm08_yen.csv": "rights pending",
        "nbs_national_data.csv": "technically blocked",
        "pboc_statistics.csv": "technically blocked",
    }
    for name, marker in expected.items():
        record = _load(name)
        assert record.m1_role == M1Role.UNRESOLVED
        assert record.operational_status == OperationalStatus.DISABLED
        assert record.terms_url in record.evidence_urls
        blocked = [
            operation
            for operation in FIRST_LIVE_OPERATIONS
            if record.decision_for(operation) != RightsDecision.PERMITTED
        ]
        assert blocked, name
        note = " ".join(record.evidence_note.lower().split())
        conditions = " ".join(record.conditions.lower().split())
        assert marker in note or marker in conditions
    china = _load("nbs_national_data.csv")
    assert "year-to-date" in china.conditions
    assert china.redistribution == RightsDecision.PROHIBITED
    pboc = _load("pboc_statistics.csv")
    assert pboc.commercial_publication == RightsDecision.PROHIBITED
    assert pboc.automated_access == RightsDecision.PROHIBITED
