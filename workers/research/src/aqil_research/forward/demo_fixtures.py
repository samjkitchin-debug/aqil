"""Synthetic demonstration fixtures — clearly labelled, offline reproducible."""

from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import UUID

DEMO_ETF_ID = "etf:vanguard:ftse-all-world:vwra:lse:gbp:acc"
DEMO_ISSUER_MSFT = "issuer:microsoft:msft:nasdaq"
DEMO_EVENT_MSFT_EARNINGS = "event:fixture:msft:fy26q2:earnings"
DEMO_SCENARIO_ID = UUID("aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee")
DEMO_OUTCOME_ID = UUID("bbbbbbbb-cccc-4ddd-8eee-ffffffffffff")
FED_EVENT_FOMC = "event:verified:fed:fomc:2025-09-17"


def vwra_instrument_payload() -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "etf_id": DEMO_ETF_ID,
        "legal_name": "Vanguard FTSE All-World UCITS ETF",
        "ticker": "VWRA",
        "exchange": "LSE",
        "isin": "IE00BK5BQT80",
        "fund_provider": "Vanguard Group",
        "domicile": "IE",
        "share_class": "Accumulating",
        "distribution_policy": "accumulating",
        "benchmark": "FTSE All-World Index",
        "source_id": "fixture_vwra_identity_v1",
        "source_locator": "synthetic://aqil/demo/vwra-identity",
        "verification_date": "2026-10-01",
        "research_status": "fixture_verified_identity",
        "evidence_class": "verified_instrument_identity",
        "caveat": ("Instrument identity only. This record does not verify holdings weights."),
    }


def vwra_holdings_snapshot_payload() -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "etf_id": DEMO_ETF_ID,
        "as_of_date": "2025-06-30",
        "source_publication_date": "2025-07-15",
        "completeness": "top_holdings_partial",
        "source_id": "fixture_vwra_holdings_v1",
        "source_locator": "synthetic://aqil/demo/vwra-holdings-2025-06-30",
        "evidence_class": "synthetic_demonstration",
        "licence_evidence": (
            "Synthetic weights for engineering demonstration only — not provider data."
        ),
        "currency": "USD",
        "lines": [
            {
                "line_id": "line:msft",
                "holding_name": "Microsoft Corp",
                "issuer_id": DEMO_ISSUER_MSFT,
                "weight_percentage": "4.20",
                "category": "equity",
            },
            {
                "line_id": "line:aapl",
                "holding_name": "Apple Inc",
                "issuer_id": "issuer:apple:aapl:nasdaq",
                "weight_percentage": "3.80",
                "category": "equity",
            },
            {
                "line_id": "line:cash",
                "holding_name": "Cash and equivalents (residual)",
                "issuer_id": None,
                "weight_percentage": "1.50",
                "category": "cash",
            },
        ],
        "residual_weight_percentage": "91.50",
        "caveat": (
            "Synthetic demonstration weights. The VWRA ISIN is not evidence that "
            "these weights are Vanguard holdings."
        ),
    }


def msft_earnings_event_payload() -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "event_id": DEMO_EVENT_MSFT_EARNINGS,
        "category": "company_earnings",
        "subject_type": "company",
        "subject_id": DEMO_ISSUER_MSFT,
        "title": "Microsoft Corp — Q2 FY2026 earnings release (fixture)",
        "scheduled_at": "2026-01-28T21:00:00+00:00",
        "timezone": "America/New_York",
        "date_precision": "estimated",
        "status": "scheduled",
        "source_id": "fixture_msft_ir_calendar_v1",
        "source_locator": "synthetic://aqil/demo/msft-earnings-2026-01",
        "expected_information": "Quarterly revenue, operating income, Azure growth commentary.",
        "caveat": "Synthetic schedule for demonstration; not sourced from live IR feeds.",
        "evidence_class": "synthetic_demonstration",
        "is_fixture": True,
    }


def fed_fomc_event_payload() -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "event_id": FED_EVENT_FOMC,
        "category": "central_bank_meeting",
        "subject_type": "macro",
        "subject_id": "economy:us",
        "title": "FOMC meeting — federal funds rate decision",
        "scheduled_at": "2025-09-17T18:00:00+00:00",
        "timezone": "America/New_York",
        "date_precision": "confirmed",
        "status": "scheduled",
        "source_id": "federal_reserve_fomc_calendar",
        "source_locator": "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm",
        "expected_information": "Policy statement and SEP materials when published.",
        "evidence_class": "verified_schedule",
        "is_fixture": False,
        "caveat": (
            "Scheduled date is cited from the Federal Reserve FOMC calendar. "
            "That citation does not assess materiality or market impact."
        ),
    }


def msft_expectation_payload() -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "event_id": DEMO_EVENT_MSFT_EARNINGS,
        "expectation_kind": "company_guidance_reference",
        "label": "Prior company guidance (fixture)",
        "narrative": (
            "Demonstration assumes management previously guided Azure growth in the mid-30% range. "
            "This is synthetic context for offline replay — not live consensus data."
        ),
        "evidence_class": "synthetic_demonstration",
        "source_id": "fixture_msft_expectation_v1",
        "is_fixture": True,
    }


def msft_scenario_payload() -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "event_id": DEMO_EVENT_MSFT_EARNINGS,
        "headline": "Azure trajectory vs prior guidance (fixture scenario)",
        "known_facts": [
            (
                "A synthetic demonstration snapshot assigns Microsoft a weight in VWRA "
                "as of 2025-06-30. That weight is not a Vanguard holdings file."
            ),
            "Earnings date is estimated, not confirmed.",
        ],
        "exposed_etf_ids": [DEMO_ETF_ID],
        "upside_case": (
            "If reported Azure growth materially exceeds prior published guidance, "
            "operating momentum may be stronger than the market assumed — though ETF "
            "price reaction also depends on broader index moves and other holdings."
        ),
        "downside_case": (
            "If cloud growth decelerates versus guidance, Microsoft may weigh on VWRA more than "
            "lower-weight peers, without implying a single-stock return forecast for the ETF."
        ),
        "inconclusive": "Market-implied expectations are not assessed in this demonstration.",
        "evidence_gaps": [
            "No live analyst consensus ingested.",
            "Holdings snapshot is partial and dated.",
        ],
        "evidence_class": "synthetic_demonstration",
        "is_fixture": True,
    }


def msft_outcome_payload() -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "event_id": DEMO_EVENT_MSFT_EARNINGS,
        "scenario_id": str(DEMO_SCENARIO_ID),
        "reported_summary": "Azure growth reported at 38% year over year (fixture outcome).",
        "source_id": "fixture_msft_earnings_release_v1",
        "source_locator": "synthetic://aqil/demo/msft-outcome",
        "expectation_comparison": (
            "Outcome modestly above the synthetic mid-30% guidance reference — "
            "classified as a mild upside versus the demonstration expectation, "
            "not an investment recommendation."
        ),
        "surprise_assessment": "small_positive_vs_fixture_guidance",
        "market_response_assessed": False,
        "evidence_class": "synthetic_demonstration",
        "is_fixture": True,
    }


def horizon_bundle_generated_at() -> datetime:
    return datetime(2026, 10, 17, 10, 0, tzinfo=UTC)


def reference_horizon_date() -> date:
    return date(2026, 10, 17)


__all__ = [
    "reference_horizon_date",
]
