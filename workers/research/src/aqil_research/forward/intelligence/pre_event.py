"""Deterministic pre-event research assessments (no probability estimates)."""

from __future__ import annotations

from datetime import UTC, datetime


def _expected_information(event_payload: dict[str, object], category: str) -> str:
    explicit = event_payload.get("expected_information")
    if isinstance(explicit, str) and explicit.strip():
        return explicit.strip()
    if category == "central_bank_meeting":
        return (
            "Federal funds rate decision, policy statement and, when published, "
            "economic projections."
        )
    if category == "us_employment_report":
        return (
            "Employment situation indicators such as payrolls and unemployment, "
            "as published in the official release."
        )
    return "Official release contents as published by the source."


def build_macro_pre_event_scenario(
    *,
    event_payload: dict[str, object],
    macro_rationale: str,
    transmission: str,
    geographic_exposure: str,
) -> dict[str, object]:
    """Structured conditional scenario for a verified macro calendar event."""
    event_id = str(event_payload["event_id"])
    category = str(event_payload.get("category", ""))
    precision = str(event_payload.get("date_precision", "unknown"))
    return {
        "schema_version": "1.0",
        "evidence_class": "research_assessment",
        "event_id": event_id,
        "headline": f"Pre-event assessment — {event_payload.get('title', event_id)}",
        "known_facts": [
            f"Schedule evidence: verified official calendar ({event_payload.get('source_id')}).",
            f"Source locator: {event_payload.get('source_locator', 'unknown')}.",
            f"Date precision on record: {precision}.",
            f"Geographic context (qualitative): {geographic_exposure}",
        ],
        "expected_information": _expected_information(event_payload, category),
        "upside_case": (
            "If published figures or the policy decision imply stronger growth or easier "
            "financial conditions than the prior macro baseline, risk sentiment could "
            "improve — ETF-level impact is not quantified here."
        ),
        "downside_case": (
            "If the outcome implies weaker growth, persistent inflation pressure or tighter "
            "policy than the prior baseline, global risk assets may reprice — diversified "
            "ETF exposure is not modelled numerically."
        ),
        "inconclusive": macro_rationale,
        "transmission_note": transmission,
        "evidence_gaps": [
            "No verified analyst consensus or market-implied expectations ingested.",
            "No ETF-level numerical materiality without an authorised holdings snapshot.",
            "Macro transmission to a specific fund is qualitative only.",
        ],
        "what_would_change_assessment": [
            "Authorised issuer holdings linked to the vetted ETF universe.",
            "Verified prior-release context stored with source locators.",
            "Post-event official release compared against this frozen record.",
        ],
        "no_action_conclusion": (
            "Insufficient substantiated evidence to justify changing a diversified long-horizon "
            "allocation based on this calendar entry alone."
        ),
        "frozen_at_reference": datetime.now(tz=UTC).isoformat(),
    }
