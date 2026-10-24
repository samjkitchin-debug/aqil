"""Blocked Wave 3 fragments stay disabled and do not clear first live use."""

from __future__ import annotations

from pathlib import Path

import psycopg
import pytest

from aqil_research.sources.rights import (
    FIRST_LIVE_OPERATIONS,
    M1Role,
    OperationalStatus,
    RightsDecision,
    load_source_rights,
)

FRAGMENTS = Path(__file__).resolve().parents[3] / "docs" / "sources" / "fragments"

BLOCKERS = {
    "imf_data_api.csv": "Credential required",
    "rbi_website.csv": "caching and links to",
    "mospi_website.csv": "No reuse sentence",
    "kosis_openapi.csv": "Credential required",
    "bok_ecos.csv": "Credential required",
    "dgbas_open_data.csv": "No keyless machine-readable series",
    "singstat_tablebuilder.csv": "does not grant",
    "mas_website.csv": "prior written permission of MAS",
    "dosm_opendosm.csv": "does not grant the six operations",
    "nso_vietnam.csv": "not a grant",
}


def _refuse_database(*args: object, **kwargs: object) -> None:
    raise AssertionError(f"database connection is not allowed: {args!r} {kwargs!r}")


@pytest.fixture(autouse=True)
def _no_database(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("psycopg.connect", _refuse_database)


@pytest.mark.parametrize("filename", sorted(BLOCKERS))
def test_blocked_fragment_is_not_a_live_series(filename: str) -> None:
    record = load_source_rights(FRAGMENTS / filename)[0]
    assert record.operational_status == OperationalStatus.DISABLED
    assert record.m1_role != M1Role.FIRST_LIVE_PROVIDER
    assert psycopg.connect is _refuse_database
    permitted = [
        operation
        for operation in FIRST_LIVE_OPERATIONS
        if record.decision_for(operation) == RightsDecision.PERMITTED
    ]
    assert len(permitted) < len(FIRST_LIVE_OPERATIONS)
    blob = " ".join(
        (
            record.auth_requirement,
            record.conditions,
            record.unresolved_questions,
            record.evidence_note,
        ),
    )
    assert BLOCKERS[filename] in blob
