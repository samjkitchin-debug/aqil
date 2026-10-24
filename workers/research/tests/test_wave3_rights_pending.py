"""Load Wave 3 fragments that are not ingest-ready and keep them closed."""

from __future__ import annotations

from pathlib import Path

import pytest

from aqil_research.sources.rights import (
    FIRST_LIVE_OPERATIONS,
    AttributionRequirement,
    M1Role,
    OperationalStatus,
    RightsDecision,
    load_source_rights,
)

FRAGMENTS = Path(__file__).resolve().parents[3] / "docs" / "sources" / "fragments"

PENDING = {
    "imf_data_reuse.csv": "rights pending",
    "oecd_cli_g20.csv": "rights pending",
    "oecd_data_reuse.csv": "rights pending",
    "mospi_cpi.csv": "credential required",
    "rbi_dbie.csv": "rights pending",
    "kosis_openapi.csv": "credential required",
    "bok_ecos.csv": "credential required",
    "taiwan_moea_industrial_production.csv": "HTTP 403",
    "singstat_tablebuilder.csv": "No series is stored",
    "mas_statistics.csv": "credential required",
    "vietnam_nso.csv": "rights pending",
}


@pytest.mark.parametrize("filename", sorted(PENDING))
def test_fragment_is_not_ingest_ready(filename: str) -> None:
    record = load_source_rights(FRAGMENTS / filename)[0]
    assert record.m1_role != M1Role.FIRST_LIVE_PROVIDER
    assert record.operational_status == OperationalStatus.DISABLED
    assert record.terms_url.startswith("https://")
    assert record.terms_url in record.evidence_urls
    permitted = [
        operation
        for operation in FIRST_LIVE_OPERATIONS
        if record.decision_for(operation) == RightsDecision.PERMITTED
    ]
    cleared = (
        len(permitted) == len(FIRST_LIVE_OPERATIONS)
        and record.attribution == AttributionRequirement.REQUIRED
        and record.operational_status == OperationalStatus.ENABLED
    )
    assert cleared is False
    note = " ".join(
        (
            record.auth_requirement,
            record.conditions,
            record.unresolved_questions,
            record.evidence_note,
        )
    )
    assert PENDING[filename].lower() in note.lower()
