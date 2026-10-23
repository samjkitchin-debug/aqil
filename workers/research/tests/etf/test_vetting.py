"""ETF vetting stays UNKNOWN when hard evidence is missing."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from aqil_research.etf.vetting import (
    DimensionFinding,
    DimensionId,
    EvidenceInput,
    InvestorFit,
    QualityAssessment,
    assess_anchor,
    assess_fit,
    assess_quality,
)

_DIMENSIONS = (
    DimensionId.IDENTITY,
    DimensionId.STRUCTURE,
    DimensionId.COST,
    DimensionId.BENCHMARK,
    DimensionId.HOLDINGS,
    DimensionId.SCALE,
    DimensionId.PERFORMANCE,
)


def _input(**overrides: object) -> EvidenceInput:
    payload: dict[str, object] = {
        "isin": "IE00BK5BQT80",
        "identity_cited": True,
        "structure_cited": True,
        "cost_cited": True,
        "benchmark_cited": True,
        "holdings_rights": "permitted",
        "scale_cited": True,
        "performance_cited": True,
        "cited_disqualification": None,
    }
    payload.update(overrides)
    return EvidenceInput.model_validate(payload)


def _cited_findings() -> tuple[DimensionFinding, ...]:
    return tuple(
        DimensionFinding(
            dimension=dimension,
            evidence_status="cited",
            hard_gate_open=False,
            note="Cited in this fixture.",
        )
        for dimension in _DIMENSIONS
    )


def test_seven_findings_and_no_score() -> None:
    quality, _fit = assess_anchor()
    assert len(quality.findings) == 7
    assert tuple(finding.dimension for finding in quality.findings) == _DIMENSIONS
    assert len({finding.dimension for finding in quality.findings}) == 7
    assert "score" not in QualityAssessment.model_fields
    assert "rank" not in QualityAssessment.model_fields
    assert "weight" not in QualityAssessment.model_fields
    assert not hasattr(quality, "score")
    with pytest.raises(ValidationError):
        QualityAssessment.model_validate(
            {
                "eligibility": "UNKNOWN",
                "evidence_status": "unverified",
                "findings": [finding.model_dump() for finding in quality.findings],
                "score": 1,
            }
        )


def test_anchor_is_unknown_without_an_invented_exclusion() -> None:
    anchor_input = EvidenceInput(
        isin="IE00BK5BQT80",
        identity_cited=False,
        structure_cited=False,
        cost_cited=False,
        benchmark_cited=False,
        holdings_rights="prohibited",
        scale_cited=False,
        performance_cited=False,
        cited_disqualification=None,
    )
    quality, fit = assess_anchor()
    assert quality == assess_quality(anchor_input)
    assert fit == assess_fit(anchor_input)
    assert quality.eligibility == "UNKNOWN"
    assert quality.eligibility != "EXCLUDED"
    assert quality.eligibility != "CONDITIONAL"
    identity = quality.findings[0]
    holdings = quality.findings[4]
    assert identity.dimension is DimensionId.IDENTITY
    assert identity.evidence_status == "unverified"
    assert holdings.dimension is DimensionId.HOLDINGS
    assert holdings.evidence_status == "insufficient"
    assert holdings.hard_gate_open is False
    assert "disqualification of the fund" in holdings.note


def test_core_rejected_when_holdings_rights_prohibited() -> None:
    assessment = assess_quality(_input(holdings_rights="prohibited"))
    assert assessment.eligibility == "UNKNOWN"
    holdings = next(
        finding for finding in assessment.findings if finding.dimension is DimensionId.HOLDINGS
    )
    assert holdings.evidence_status == "insufficient"
    assert holdings.hard_gate_open is False
    with pytest.raises(ValidationError):
        QualityAssessment(
            eligibility="CORE",
            evidence_status="cited",
            findings=assessment.findings,
        )


def test_core_when_every_dimension_is_cited() -> None:
    assessment = assess_quality(_input())
    assert assessment.eligibility == "CORE"
    assert assessment.evidence_status == "cited"
    assert all(
        finding.evidence_status == "cited" and finding.hard_gate_open is False
        for finding in assessment.findings
    )
    built = QualityAssessment(
        eligibility="CORE",
        evidence_status="cited",
        findings=_cited_findings(),
    )
    assert built.eligibility == "CORE"


def test_excluded_only_from_a_caller_citation() -> None:
    reason = "Caller cited an identity contradiction."
    excluded = assess_quality(_input(cited_disqualification=reason))
    assert excluded.eligibility == "EXCLUDED"
    assert excluded.evidence_status == "cited"
    assert assess_quality(_input(cited_disqualification=None)).eligibility != "EXCLUDED"
    assert assess_quality(_input(cited_disqualification="  ")).eligibility != "EXCLUDED"
    anchor, _fit = assess_anchor()
    assert anchor.eligibility == "UNKNOWN"
    assert reason not in " ".join(finding.note for finding in anchor.findings)


def test_missing_evidence_is_unknown_rather_than_excluded() -> None:
    missing_isin = assess_quality(_input(isin=None, identity_cited=False))
    assert missing_isin.eligibility == "UNKNOWN"
    assert missing_isin.findings[0].evidence_status == "insufficient"
    unavailable_cost = assess_quality(_input(cost_cited=False))
    assert unavailable_cost.eligibility == "UNKNOWN"
    assert unavailable_cost.findings[2].evidence_status == "unavailable"
    unknown_rights = assess_quality(_input(holdings_rights="unknown"))
    assert unknown_rights.eligibility == "UNKNOWN"
    assert unknown_rights.findings[4].evidence_status == "insufficient"
    assert unknown_rights.findings[4].hard_gate_open is False


def test_absence_is_not_conditional() -> None:
    quality, _fit = assess_anchor()
    assert quality.eligibility != "CONDITIONAL"
    with pytest.raises(ValidationError):
        QualityAssessment(
            eligibility="CONDITIONAL",
            evidence_status="unverified",
            findings=quality.findings,
        )


def test_structure_does_not_exclude_us_domicile_or_distributing() -> None:
    quality, _fit = assess_anchor()
    structure = quality.findings[1]
    assert structure.dimension is DimensionId.STRUCTURE
    assert structure.evidence_status == "unverified"
    assert "not an exclusion by itself" in structure.note
    assert quality.eligibility == "UNKNOWN"


def test_fit_is_not_a_quality_rank() -> None:
    cited = _input()
    excluded_input = _input(cited_disqualification="Caller cited a disqualifying fact.")
    core = assess_quality(cited)
    excluded = assess_quality(excluded_input)
    core_fit = assess_fit(cited)
    excluded_fit = assess_fit(excluded_input)
    anchor_fit = assess_anchor()[1]
    assert core.eligibility == "CORE"
    assert excluded.eligibility == "EXCLUDED"
    assert core_fit.fit_status == "UNKNOWN"
    assert excluded_fit.fit_status == "UNKNOWN"
    assert anchor_fit.fit_status == "UNKNOWN"
    assert core_fit == excluded_fit == anchor_fit
    assert core_fit.fit_status != core.eligibility
    assert "rank" not in InvestorFit.model_fields
    assert "score" not in InvestorFit.model_fields
    assert "not a universal quality rank" in core_fit.note
    assert "not personal advice" in core_fit.note
    assert core_fit.audience == "singapore_long_horizon"


def test_same_input_is_reproducible() -> None:
    evidence = _input(holdings_rights="prohibited", cost_cited=False, identity_cited=False)
    first = assess_quality(evidence)
    second = assess_quality(evidence)
    assert first.eligibility == second.eligibility
    assert tuple(finding.dimension for finding in first.findings) == tuple(
        finding.dimension for finding in second.findings
    )
    assert first == second
    assert assess_anchor() == assess_anchor()


def test_findings_must_be_seven_unique_dimensions() -> None:
    findings = list(_cited_findings())
    with pytest.raises(ValidationError):
        QualityAssessment(
            eligibility="UNKNOWN",
            evidence_status="cited",
            findings=tuple(findings[:6]),
        )
    findings[6] = findings[0]
    with pytest.raises(ValidationError):
        QualityAssessment(
            eligibility="UNKNOWN",
            evidence_status="cited",
            findings=tuple(findings),
        )
