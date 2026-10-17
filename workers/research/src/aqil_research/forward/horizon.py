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
from aqil_research.forward.materiality import MaterialityInput, assess_materiality


def build_forward_horizon_bundle() -> dict[str, object]:
    generated_at = horizon_bundle_generated_at()
    instrument = vwra_instrument_payload()
    holdings = vwra_holdings_snapshot_payload()
    msft_event = msft_earnings_event_payload()
    fed_event = fed_fomc_event_payload()
    scenario = msft_scenario_payload()
    outcome = msft_outcome_payload()

    weight = Decimal("4.20")
    materiality = assess_materiality(
        MaterialityInput(
            weight_percentage=weight,
            holdings_completeness=str(holdings["completeness"]),
            snapshot_as_of=date.fromisoformat(str(holdings["as_of_date"])),
            reference_date=reference_horizon_date(),
            event_category="company_earnings",
        ),
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
        "holdings_as_of": holdings["as_of_date"],
        "completeness": holdings["completeness"],
        "top_holdings": top_holdings,
    }

    def _event_row(
        payload: dict[str, object], *, materiality_label: str, why: str
    ) -> dict[str, object]:
        scheduled = payload.get("scheduled_at")
        scheduled_date = str(scheduled)[:10] if scheduled else "unknown"
        return {
            "event_id": payload["event_id"],
            "title": payload["title"],
            "category": payload["category"],
            "subject_label": payload.get("subject_id"),
            "scheduled_date": scheduled_date,
            "scheduled_time": None,
            "timezone": payload.get("timezone"),
            "date_precision": payload["date_precision"],
            "materiality": materiality_label,
            "source_confidence": "fixture" if payload.get("is_fixture") else "verified_schedule",
            "why_it_matters": why,
            "etf_ids": [DEMO_ETF_ID] if payload["event_id"] == DEMO_EVENT_MSFT_EARNINGS else [],
            "is_fixture": bool(payload.get("is_fixture")),
        }

    events = [
        _event_row(
            msft_event,
            materiality_label=materiality.category,
            why=(
                f"Microsoft is a {weight}% weight in the dated VWRA holdings snapshot. "
                "Earnings may shift cloud-growth narrative for this ETF exposure."
            ),
        ),
        _event_row(
            fed_event,
            materiality_label="medium",
            why="US policy rates affect global discount rates for broad equity ETFs such as VWRA.",
        ),
    ]

    exposures = [
        {
            "event_id": DEMO_EVENT_MSFT_EARNINGS,
            "etf_id": DEMO_ETF_ID,
            "issuer_id": DEMO_ISSUER_MSFT,
            "weight_percentage": str(weight),
            "materiality": materiality.category,
            "snapshot_as_of": holdings["as_of_date"],
        },
    ]

    scenarios = [
        {
            "scenario_id": str(DEMO_SCENARIO_ID),
            "event_id": DEMO_EVENT_MSFT_EARNINGS,
            "frozen_at": "2026-01-20T12:00:00+00:00",
            "headline": str(scenario["headline"]),
            "upside_case": scenario["upside_case"],
            "downside_case": scenario["downside_case"],
            "evidence_gaps": scenario["evidence_gaps"],
        },
    ]

    outcomes = [
        {
            "outcome_id": str(DEMO_OUTCOME_ID),
            "event_id": DEMO_EVENT_MSFT_EARNINGS,
            "scenario_id": str(DEMO_SCENARIO_ID),
            "headline": str(outcome["reported_summary"]),
            "expectation_met": "partially_above_fixture_guidance",
            "surprise_assessment": outcome["surprise_assessment"],
        },
    ]

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
