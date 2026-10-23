"""Holdings coverage stays closed unless the rights gate is permitted."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
from pydantic import ValidationError

from aqil_research.etf.contracts import (
    holdings_cleared_for_read,
    load_etf_rights_fragment,
)
from aqil_research.etf.holdings import (
    HoldingsCoverage,
    HoldingsStatus,
    coverage_for_record,
    top_ten_overlap,
)
from aqil_research.sources.rights import (
    AttributionRequirement,
    M1Role,
    OperationalStatus,
    RightsDecision,
    SourceRightsRecord,
    find_source_rights,
    load_source_rights,
)

REPO_ROOT = Path(__file__).resolve().parents[4]
FRAGMENTS = REPO_ROOT / "docs" / "sources" / "etf" / "fragments"
_MISSING_OVERLAP = (
    "Top-ten overlap is partial. "
    "Missing or restricted holdings are not treated as an empty portfolio."
)


def test_fragments_have_insufficient_coverage() -> None:
    paths = sorted(FRAGMENTS.glob("*.csv"))
    assert paths, "ETF rights fragments are missing"
    for path in paths:
        record = load_etf_rights_fragment(path)
        assert not holdings_cleared_for_read(record)
        coverage = coverage_for_record(record)
        assert coverage.status == HoldingsStatus.INSUFFICIENT
        assert coverage.line_count == 0
        assert coverage.rights_gate in {"prohibited", "unknown", "disabled"}
        assert coverage.reason.startswith("The source was not fetched.")


def test_registered_holdings_rows_have_insufficient_coverage() -> None:
    records = load_source_rights()
    expected = {
        "vanguard_uk_vwra_holdings": "prohibited",
        "ishares_ucits_holdings": "disabled",
    }
    for source_id, gate in expected.items():
        record = find_source_rights(records, source_id=source_id)
        assert record is not None
        assert not holdings_cleared_for_read(record)
        coverage = coverage_for_record(record)
        assert coverage.status == HoldingsStatus.INSUFFICIENT
        assert coverage.line_count == 0
        assert coverage.rights_gate == gate
        assert coverage.reason.startswith("The source was not fetched.")


def test_synthetic_permitted_record_is_partial_without_a_file() -> None:
    record = _record(
        RightsDecision.PERMITTED,
        RightsDecision.PERMITTED,
        OperationalStatus.ENABLED,
    )
    assert holdings_cleared_for_read(record)
    coverage = coverage_for_record(record)
    assert coverage.status == HoldingsStatus.PARTIAL
    assert coverage.rights_gate == "permitted"
    assert coverage.line_count == 0
    assert coverage.reason == "No holdings file has been supplied by the caller."
    assert coverage.status != HoldingsStatus.FULL


def test_closed_gates_match_the_record() -> None:
    prohibited = coverage_for_record(
        _record(RightsDecision.PROHIBITED, RightsDecision.PERMITTED, OperationalStatus.ENABLED),
    )
    unknown = coverage_for_record(
        _record(RightsDecision.UNKNOWN, RightsDecision.UNKNOWN, OperationalStatus.ENABLED),
    )
    disabled = coverage_for_record(
        _record(RightsDecision.PERMITTED, RightsDecision.PERMITTED, OperationalStatus.DISABLED),
    )
    assert prohibited.rights_gate == "prohibited"
    assert unknown.rights_gate == "unknown"
    assert disabled.rights_gate == "disabled"
    assert prohibited.line_count == unknown.line_count == disabled.line_count == 0
    assert prohibited.status == unknown.status == disabled.status == HoldingsStatus.INSUFFICIENT


def test_coverage_rejects_holding_lines() -> None:
    with pytest.raises(ValidationError):
        HoldingsCoverage(
            status=HoldingsStatus.INSUFFICIENT,
            rights_gate="prohibited",
            line_count=0,
            reason="The source was not fetched.",
            lines=[],  # type: ignore[call-arg]
        )


def test_top_ten_overlap_refuses_restricted_holdings() -> None:
    result = top_ten_overlap(
        left_line_count=10,
        right_line_count=10,
        rights_cleared=False,
        shared_names=("Name A", "Name B"),
    )
    assert result == {
        "label": "partial",
        "computed": False,
        "reason": _MISSING_OVERLAP,
    }


def test_top_ten_overlap_with_empty_names_is_partial() -> None:
    result = top_ten_overlap(
        left_line_count=10,
        right_line_count=8,
        rights_cleared=True,
    )
    assert result["label"] == "partial"
    assert result["computed"] is False
    assert "overlap_count" not in result


def test_top_ten_overlap_with_a_missing_count_is_partial() -> None:
    result = top_ten_overlap(
        left_line_count=0,
        right_line_count=10,
        rights_cleared=True,
        shared_names=("Name A",),
    )
    assert result == {
        "label": "partial",
        "computed": False,
        "reason": _MISSING_OVERLAP,
    }


def test_top_ten_overlap_counts_only_supplied_names() -> None:
    result = top_ten_overlap(
        left_line_count=10,
        right_line_count=10,
        rights_cleared=True,
        shared_names=("Name A", "Name B"),
    )
    assert result["label"] == "partial"
    assert result["computed"] is True
    assert result["overlap_count"] == 2
    assert "%" not in str(result["reason"])


def _record(
    automated_access: RightsDecision,
    redistribution: RightsDecision,
    status: OperationalStatus,
) -> SourceRightsRecord:
    return SourceRightsRecord(
        source_id="fixture_etf_holdings",
        dataset_id="fixture.etf.holdings",
        provider_name="Fixture",
        publication_name="Fixture",
        geography="IE",
        series_or_dataset_code="fixture",
        category="etf_holdings",
        access_description="In-memory fixture. No provider was contacted.",
        access_url="https://example.com/access",
        terms_url="https://example.com/terms",
        evidence_urls=("https://example.com/terms",),
        auth_requirement="None.",
        automated_access=automated_access,
        internal_computation=RightsDecision.UNKNOWN,
        raw_data_retention=RightsDecision.UNKNOWN,
        historical_archiving=RightsDecision.UNKNOWN,
        redistribution=redistribution,
        commercial_publication=RightsDecision.UNKNOWN,
        ai_processing=RightsDecision.UNKNOWN,
        ai_model_training=RightsDecision.UNKNOWN,
        attribution=AttributionRequirement.UNKNOWN,
        m1_role=M1Role.UNRESOLVED,
        operational_status=status,
        conditions="Fixture only.",
        revision_behaviour="None.",
        unresolved_questions="None.",
        evidence_note="Not a provider assessment.",
        assessed_on=date(2026, 10, 23),
    )
