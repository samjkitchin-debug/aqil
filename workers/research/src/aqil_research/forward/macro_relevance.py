"""Qualitative macro-event relevance for ETF research (no fabricated weights)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MacroRelevance:
    transmission_mechanism: str
    geographic_exposure: str
    sector_exposure: str
    confidence: str
    rationale: str


def assess_macro_relevance(event_category: str) -> MacroRelevance:
    if event_category == "central_bank_meeting":
        return MacroRelevance(
            transmission_mechanism=(
                "Policy rate expectations and financial conditions can affect global "
                "risk appetite and discount rates."
            ),
            geographic_exposure="Global diversified ETFs include substantial US exposure.",
            sector_exposure="Broad equity indices; rate-sensitive sectors may react first.",
            confidence="qualitative_only",
            rationale=(
                "No ETF-level numerical impact is estimated without a verified holdings "
                "link and a published transmission model."
            ),
        )
    if event_category == "us_employment_report":
        return MacroRelevance(
            transmission_mechanism=(
                "Labour-market surprises can shift growth and policy expectations, "
                "affecting global equity and bond pricing."
            ),
            geographic_exposure="US labour data primarily concerns US economic conditions.",
            sector_exposure="Cyclical sectors may be more sensitive than defensives.",
            confidence="qualitative_only",
            rationale=(
                "Materiality for a specific ETF requires fresh holdings and an explicit "
                "mapping rule; this release is classified at macro level only."
            ),
        )
    return MacroRelevance(
        transmission_mechanism="Unknown for this event category.",
        geographic_exposure="Unknown",
        sector_exposure="Unknown",
        confidence="insufficient_evidence",
        rationale="Event category is not mapped in the macro relevance framework.",
    )
