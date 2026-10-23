"""ETF eligibility vetting.

Seven dimensions follow docs/03 section 6. Missing hard evidence stays UNKNOWN.
EXCLUDED is used only for a disqualifying fact the caller cites. There is no
rank, weight, or score. Investor fit is separate and is not personal advice.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

from aqil_research.etf.contracts import EvidenceStatus

HoldingsRights = Literal["permitted", "prohibited", "unknown"]
Eligibility = Literal["CORE", "CONDITIONAL", "EXCLUDED", "UNKNOWN"]
FitStatus = Literal["UNKNOWN", "insufficient", "cited"]

_BLOCKING_EVIDENCE = frozenset({"unverified", "unavailable", "insufficient"})
_ANCHOR_ISIN = "IE00BK5BQT80"

_FIT_NOTE = (
    "Investor fit for a Singapore long-horizon audience is unknown. "
    "No ETF eligibility rule with a permitted citation is available. "
    "Fit is not a universal quality rank and is not personal advice."
)


class DimensionId(StrEnum):
    """Section 6 dimensions. The values are the public ids."""

    IDENTITY = "identity"
    STRUCTURE = "structure"
    COST = "cost"
    BENCHMARK = "benchmark"
    HOLDINGS = "holdings"
    SCALE = "scale"
    PERFORMANCE = "performance"


class DimensionFinding(BaseModel):
    """One dimension. A rights block is insufficient evidence, not an exclusion."""

    model_config = ConfigDict(extra="forbid")

    dimension: DimensionId
    evidence_status: EvidenceStatus
    hard_gate_open: bool
    note: str


class QualityAssessment(BaseModel):
    """Eligibility without a rank, weight, or score."""

    model_config = ConfigDict(extra="forbid")

    eligibility: Eligibility
    evidence_status: EvidenceStatus
    findings: tuple[DimensionFinding, ...]

    @model_validator(mode="after")
    def findings_cover_each_dimension_once(self) -> QualityAssessment:
        if len(self.findings) != 7:
            raise ValueError("quality assessment requires exactly seven dimension findings")
        dimensions = {finding.dimension for finding in self.findings}
        if len(dimensions) != 7:
            raise ValueError("quality assessment dimensions must be unique")
        blocked = any(
            finding.hard_gate_open or finding.evidence_status in _BLOCKING_EVIDENCE
            for finding in self.findings
        )
        if self.eligibility == "CORE" and blocked:
            raise ValueError("CORE requires every dimension cited and no open hard gate")
        cited = any(finding.evidence_status == "cited" for finding in self.findings)
        if self.eligibility == "CONDITIONAL" and not cited:
            raise ValueError("CONDITIONAL requires cited evidence; absence of evidence is UNKNOWN")
        return self


class InvestorFit(BaseModel):
    """Audience fit. It is not a copy of eligibility and it is not a rank."""

    model_config = ConfigDict(extra="forbid")

    audience: Literal["singapore_long_horizon"]
    fit_status: FitStatus
    note: str


class EvidenceInput(BaseModel):
    """Caller summary. This module does not read holdings, brokers, or policy files."""

    model_config = ConfigDict(extra="forbid")

    isin: str | None
    identity_cited: bool
    structure_cited: bool
    cost_cited: bool
    benchmark_cited: bool
    holdings_rights: HoldingsRights
    scale_cited: bool
    performance_cited: bool
    cited_disqualification: str | None = None


def assess_quality(evidence: EvidenceInput) -> QualityAssessment:
    """Return UNKNOWN unless every dimension is cited, or the caller cites an exclusion."""
    findings = (
        _identity(evidence),
        _structure(evidence),
        _cost(evidence),
        _benchmark(evidence),
        _holdings(evidence),
        _scale(evidence),
        _performance(evidence),
    )
    if _cited_disqualification(evidence) is not None:
        return QualityAssessment(
            eligibility="EXCLUDED",
            evidence_status="cited",
            findings=findings,
        )
    if _core_allowed(findings):
        return QualityAssessment(
            eligibility="CORE",
            evidence_status="cited",
            findings=findings,
        )
    return QualityAssessment(
        eligibility="UNKNOWN",
        evidence_status=_gap_status(findings),
        findings=findings,
    )


def assess_fit(evidence: EvidenceInput) -> InvestorFit:
    """Fit stays UNKNOWN. The stored policy has no cited ETF eligibility rule."""
    del evidence
    return InvestorFit(
        audience="singapore_long_horizon",
        fit_status="UNKNOWN",
        note=_FIT_NOTE,
    )


def assess_anchor() -> tuple[QualityAssessment, InvestorFit]:
    """Unverified anchor IE00BK5BQT80. Holdings rights are prohibited. No invented exclusion."""
    evidence = EvidenceInput(
        isin=_ANCHOR_ISIN,
        identity_cited=False,
        structure_cited=False,
        cost_cited=False,
        benchmark_cited=False,
        holdings_rights="prohibited",
        scale_cited=False,
        performance_cited=False,
        cited_disqualification=None,
    )
    return assess_quality(evidence), assess_fit(evidence)


def _cited_disqualification(evidence: EvidenceInput) -> str | None:
    text = (evidence.cited_disqualification or "").strip()
    return text or None


def _core_allowed(findings: tuple[DimensionFinding, ...]) -> bool:
    return all(
        finding.evidence_status == "cited" and not finding.hard_gate_open for finding in findings
    )


def _gap_status(findings: tuple[DimensionFinding, ...]) -> EvidenceStatus:
    statuses = {finding.evidence_status for finding in findings}
    for status in ("insufficient", "unavailable", "unverified"):
        if status in statuses:
            return status
    return "unverified"


def _identity(evidence: EvidenceInput) -> DimensionFinding:
    isin = (evidence.isin or "").strip()
    if evidence.identity_cited and isin:
        return DimensionFinding(
            dimension=DimensionId.IDENTITY,
            evidence_status="cited",
            hard_gate_open=False,
            note="Official ISIN and share class are cited.",
        )
    if not isin:
        return DimensionFinding(
            dimension=DimensionId.IDENTITY,
            evidence_status="insufficient",
            hard_gate_open=True,
            note="Official ISIN and share class are missing.",
        )
    return DimensionFinding(
        dimension=DimensionId.IDENTITY,
        evidence_status="unverified",
        hard_gate_open=True,
        note="The ISIN is only an internal anchor. Official share-class proof is not cited.",
    )


def _structure(evidence: EvidenceInput) -> DimensionFinding:
    if evidence.structure_cited:
        return DimensionFinding(
            dimension=DimensionId.STRUCTURE,
            evidence_status="cited",
            hard_gate_open=False,
            note=(
                "Distribution, domicile, issuer, and replication are cited. "
                "A US domicile or a distributing share class is not an exclusion by itself."
            ),
        )
    return DimensionFinding(
        dimension=DimensionId.STRUCTURE,
        evidence_status="unverified",
        hard_gate_open=True,
        note=(
            "Distribution, domicile, issuer, and replication are not cited. "
            "A US domicile or a distributing share class is not an exclusion by itself."
        ),
    )


def _cost(evidence: EvidenceInput) -> DimensionFinding:
    if evidence.cost_cited:
        return DimensionFinding(
            dimension=DimensionId.COST,
            evidence_status="cited",
            hard_gate_open=False,
            note="TER and tracking difference are cited. An issuer TER is not total cost.",
        )
    return DimensionFinding(
        dimension=DimensionId.COST,
        evidence_status="unavailable",
        hard_gate_open=True,
        note="TER and tracking difference are unavailable. An issuer TER is not total cost.",
    )


def _benchmark(evidence: EvidenceInput) -> DimensionFinding:
    if evidence.benchmark_cited:
        return DimensionFinding(
            dimension=DimensionId.BENCHMARK,
            evidence_status="cited",
            hard_gate_open=False,
            note="Index method is cited. Price and total-return series are kept apart.",
        )
    return DimensionFinding(
        dimension=DimensionId.BENCHMARK,
        evidence_status="unverified",
        hard_gate_open=True,
        note="Index method is not cited. Price and total-return series are kept apart.",
    )


def _holdings(evidence: EvidenceInput) -> DimensionFinding:
    if evidence.holdings_rights == "permitted":
        return DimensionFinding(
            dimension=DimensionId.HOLDINGS,
            evidence_status="cited",
            hard_gate_open=False,
            note=(
                "Diversification and holdings are cited under a permitted source. "
                "This assessment does not read holdings."
            ),
        )
    if evidence.holdings_rights == "prohibited":
        return DimensionFinding(
            dimension=DimensionId.HOLDINGS,
            evidence_status="insufficient",
            hard_gate_open=False,
            note=(
                "A prohibited holdings source is insufficient evidence, "
                "not a disqualification of the fund."
            ),
        )
    return DimensionFinding(
        dimension=DimensionId.HOLDINGS,
        evidence_status="insufficient",
        hard_gate_open=False,
        note="Holdings rights are unknown. Diversification evidence is insufficient.",
    )


def _scale(evidence: EvidenceInput) -> DimensionFinding:
    if evidence.scale_cited:
        return DimensionFinding(
            dimension=DimensionId.SCALE,
            evidence_status="cited",
            hard_gate_open=False,
            note="AUM and liquidity are cited. No live spread is used.",
        )
    return DimensionFinding(
        dimension=DimensionId.SCALE,
        evidence_status="unverified",
        hard_gate_open=True,
        note="AUM and liquidity are not cited. No live spread is used.",
    )


def _performance(evidence: EvidenceInput) -> DimensionFinding:
    if evidence.performance_cited:
        return DimensionFinding(
            dimension=DimensionId.PERFORMANCE,
            evidence_status="cited",
            hard_gate_open=False,
            note=("Fund performance and benchmark performance are cited and labelled separately."),
        )
    return DimensionFinding(
        dimension=DimensionId.PERFORMANCE,
        evidence_status="unverified",
        hard_gate_open=True,
        note=(
            "Fund performance and benchmark performance are not cited. "
            "They stay labelled separately."
        ),
    )


__all__ = [
    "DimensionFinding",
    "DimensionId",
    "EvidenceInput",
    "InvestorFit",
    "QualityAssessment",
    "assess_anchor",
    "assess_fit",
    "assess_quality",
]
