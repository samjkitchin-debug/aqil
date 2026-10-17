"""Deterministic pre-event research assessments (no probability estimates)."""

from __future__ import annotations

from datetime import UTC, datetime


def build_macro_pre_event_scenario(
    *,
    event_payload: dict[str, object],
    macro_rationale: str,
) -> dict[str, object]:
    """Structured conditional scenario for a verified macro calendar event."""
    event_id = str(event_payload["event_id"])
    return {
        "schema_version": "1.0",
        "evidence_class": "research_assessment",
        "event_id": event_id,
        "headline": f"Pre-event assessment — {event_payload.get('title', event_id)}",
        "known_facts": [
            f"Event is scheduled per {event_payload.get('source_id', 'unknown source')}.",
            f"Source locator: {event_payload.get('source_locator', 'unknown')}.",
        ],
        "upside_case": (
            "If the release or decision is more growth-friendly than recent expectations, "
            "risk appetite may improve — without a verified ETF-level impact estimate."
        ),
        "downside_case": (
            "If the outcome signals tighter policy or weaker growth than expected, "
            "global equities may reprice — transmission to a diversified ETF is uncertain."
        ),
        "inconclusive": macro_rationale,
        "evidence_gaps": [
            "No verified analyst consensus ingested.",
            "No ETF-level numerical materiality without fresh holdings.",
        ],
        "no_action_conclusion": (
            "Insufficient substantiated evidence to justify changing a diversified long-horizon "
            "allocation based on this calendar entry alone."
        ),
        "frozen_at_reference": datetime.now(tz=UTC).isoformat(),
    }
