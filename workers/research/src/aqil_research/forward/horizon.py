"""Build forward horizon presentation bundle."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from aqil_research.forward.demo_fixtures import (
    DEMO_ETF_ID,
    DEMO_EVENT_MSFT_EARNINGS,
    DEMO_ISSUER_MSFT,
    DEMO_OUTCOME_ID,
    DEMO_SCENARIO_ID,
    fed_fomc_event_payload,
    horizon_bundle_generated_at,
    msft_earnings_event_payload,
    msft_outcome_payload,
    msft_scenario_payload,
    reference_horizon_date,
    vwra_holdings_snapshot_payload,
    vwra_instrument_payload,
)
from aqil_research.forward.materiality import assess_event_materiality


def build_forward_horizon_bundle() -> dict[str, object]:
    """Offline bundle. The persisted path loads the frozen scenario from PostgreSQL."""
    scenario = msft_scenario_payload()
    outcome = msft_outcome_payload()
    return assemble_forward_horizon(
        instrument=vwra_instrument_payload(),
        holdings=vwra_holdings_snapshot_payload(),
        msft_event=msft_earnings_event_payload(),
        fed_event=fed_fomc_event_payload(),
        scenario_id=str(DEMO_SCENARIO_ID),
        scenario_frozen_at="2026-01-20T12:00:00+00:00",
        scenario=scenario,
        outcome_id=str(DEMO_OUTCOME_ID),
        outcome=outcome,
        scenario_source="fixture",
    )


def assemble_forward_horizon(
    *,
    instrument: dict[str, object],
    holdings: dict[str, object],
    msft_event: dict[str, object],
    fed_event: dict[str, object],
    scenario_id: str,
    scenario_frozen_at: str,
    scenario: dict[str, object],
    outcome_id: str | None,
    outcome: dict[str, object] | None,
    scenario_source: str,
) -> dict[str, object]:
    generated_at = horizon_bundle_generated_at()
    weight = Decimal("4.20")
    materiality = assess_event_materiality(
        weight_percentage=weight,
        holdings_completeness=str(holdings["completeness"]),
        snapshot_as_of=date.fromisoformat(str(holdings["as_of_date"])),
        reference_date=reference_horizon_date(),
        event_category="company_earnings",
    )
    fed_materiality = assess_event_materiality(
        weight_percentage=None,
        holdings_completeness=None,
        snapshot_as_of=None,
        reference_date=reference_horizon_date(),
        event_category="central_bank_meeting",
    )

    top_holdings = []
    for line in holdings.get("lines", []):
        if not isinstance(line, dict) or line.get("category") == "cash":
            continue
        top_holdings.append(
            {
                "name": line["holding_name"],
                "issuer_id": line.get("issuer_id"),
                "weight_percentage": str(line["weight_percentage"]),
            },
        )

    etf_summary = {
        "etf_id": DEMO_ETF_ID,
        "legal_name": instrument["legal_name"],
        "ticker": instrument["ticker"],
        "exchange": instrument["exchange"],
        "isin": instrument["isin"],
        "identity_evidence": "verified_instrument_identity",
        "holdings_as_of": holdings["as_of_date"],
        "completeness": holdings["completeness"],
        "holdings_evidence": "synthetic_demonstration",
        "holdings_caveat": (
            "The ISIN identifies the share class. Weights are synthetic demonstration data, "
            "not fund-provider holdings."
        ),
        "top_holdings": top_holdings,
    }

    def _event_row(
        payload: dict[str, object],
        *,
        materiality_label: str,
        materiality_basis: str,
        why: str,
    ) -> dict[str, object]:
        scheduled = payload.get("scheduled_at")
        scheduled_date = str(scheduled)[:10] if scheduled else "unknown"
        evidence = str(payload.get("evidence_class"))
        return {
            "event_id": payload["event_id"],
            "title": payload["title"],
            "category": payload["category"],
            "subject_label": payload.get("subject_id"),
            "scheduled_date": scheduled_date,
            "scheduled_time": None,
            "timezone": payload.get("timezone"),
            "date_precision": payload["date_precision"],
            "schedule_evidence": evidence,
            "materiality": materiality_label,
            "materiality_basis": materiality_basis,
            "interpretation_status": "unverified",
            "source_confidence": evidence,
            "why_it_matters": why,
            "etf_ids": [DEMO_ETF_ID] if payload["event_id"] == DEMO_EVENT_MSFT_EARNINGS else [],
            "is_fixture": bool(payload.get("is_fixture")),
        }

    events = [
        _event_row(
            msft_event,
            materiality_label=materiality.category,
            materiality_basis="calculated",
            why=(
                f"A synthetic demonstration snapshot shows Microsoft at {weight}%. "
                "Materiality is calculated from that demonstration weight. "
                "It is not a verified fund-provider holding."
            ),
        ),
        _event_row(
            fed_event,
            materiality_label=fed_materiality.category,
            materiality_basis="insufficient_evidence",
            why=(
                "The meeting date is cited from the Federal Reserve FOMC calendar. "
                "No holdings weight is linked, so materiality is not assessed. "
                "Any view of market impact is an unverified interpretation."
            ),
        ),
    ]

    exposures = [
        {
            "event_id": DEMO_EVENT_MSFT_EARNINGS,
            "etf_id": DEMO_ETF_ID,
            "issuer_id": DEMO_ISSUER_MSFT,
            "weight_percentage": str(weight),
            "weight_evidence": "synthetic_demonstration",
            "materiality": materiality.category,
            "materiality_evidence": "calculated",
            "snapshot_as_of": holdings["as_of_date"],
        },
    ]

    scenarios = [
        {
            "scenario_id": scenario_id,
            "event_id": str(scenario["event_id"]),
            "frozen_at": scenario_frozen_at,
            "headline": str(scenario["headline"]),
            "upside_case": scenario["upside_case"],
            "downside_case": scenario["downside_case"],
            "evidence_gaps": scenario["evidence_gaps"],
            "evidence_class": "synthetic_demonstration",
            "record_source": scenario_source,
        },
    ]

    outcomes: list[dict[str, object]] = []
    if outcome is not None and outcome_id is not None:
        outcomes.append(
            {
                "outcome_id": outcome_id,
                "event_id": str(outcome["event_id"]),
                "scenario_id": str(outcome["scenario_id"]),
                "headline": str(outcome["reported_summary"]),
                "expectation_met": "partially_above_fixture_guidance",
                "surprise_assessment": outcome["surprise_assessment"],
                "evidence_class": "synthetic_demonstration",
            },
        )

    return {
        "schema_version": "1.0",
        "generated_at": generated_at.isoformat(),
        "data_mode": "mixed",
        "etfs": [etf_summary],
        "events": events,
        "exposures": exposures,
        "scenarios": scenarios,
        "outcomes": outcomes,
    }
