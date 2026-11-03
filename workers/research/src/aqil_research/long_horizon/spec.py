"""Frozen category C pilot. The historical run must use this object unchanged."""

from __future__ import annotations

from aqil_research.long_horizon.money import sha256_document

HYPOTHESIS_ID = "LH-H-001"
EXPERIMENT_ID = "LH-E-001"
EXECUTION_ID = "LH-X-001"
EVIDENCE_ID = "LH-V-001"
CLAIM_ID = "LH-C-001"
REGISTER_ID = "long-horizon-catalogue-v1"
REGISTER_VERSION = 1
METHODOLOGY_VERSION = "long-horizon-simulator-1"
PILOT_CONTRIBUTION = "1000"
PILOT_COST_RATE = "0.001"
PILOT_INTEREST_RATE = "0"

HYPOTHESIS = {
    "hypothesis_id": HYPOTHESIS_ID,
    "version": 1,
    "proposition": (
        "Investing 1000 US dollars into CSPX in even calendar months and into "
        "VWRA in odd calendar months, then rebalancing those two positions to "
        "equal market value on each January contribution session, produces "
        "greater after-cost terminal wealth than investing every one of those "
        "contributions immediately into VWRA. Costs are 10 basis points of "
        "notional. Units are whole units and residual cash is kept. The prices "
        "are the stored listing-currency split-adjusted closes. This statement "
        "is category C and is not a macroeconomic claim."
    ),
    "economic_rationale": (
        "The comparison is a price-only accounting contrast between immediate "
        "investment in one stored global equity listing and a calendar split "
        "across two stored US-dollar equity listings. It asks whether terminal "
        "wealth differs under matched contributions. It does not identify a "
        "macroeconomic mechanism."
    ),
    "expected_mechanism": "No causal mechanism is claimed.",
    "expected_direction": "alternative terminal wealth greater than the passive terminal wealth",
    "horizon": "the full overlap of stored VWRA and CSPX split-adjusted closes",
    "falsification_criteria": (
        "On this single frozen window, the inequality is rejected when both "
        "ledgers reconcile and the alternative terminal wealth is less than or "
        "equal to the passive terminal wealth. A greater alternative terminal "
        "wealth does not accept the inequality."
    ),
    "alternative_explanations": [
        "The two policies share one price path and one contribution calendar.",
        "Whole-unit residual cash can change the invested amount.",
        "The stored series is split-adjusted and is not a total-return index.",
        "A January rebalance sells units whose later path is forgone wealth.",
    ],
    "relevant_indicators": [],
    "relevant_methodologies": [METHODOLOGY_VERSION],
    "target_instruments": ["VWRA", "CSPX"],
    "initial_status": "proposed",
}

FROZEN_PILOT_SPECIFICATION = {
    "schema_version": "1.0",
    "experiment_id": EXPERIMENT_ID,
    "version": 1,
    "category": "C",
    "category_label": "price_only_simulator_research",
    "not_macroeconomic_investment_intelligence": True,
    "hypothesis_id": HYPOTHESIS_ID,
    "hypothesis_version": 1,
    "research_question": (
        "On the stored common sessions, does the registered price-only policy "
        "end with greater terminal wealth than investing each matched "
        "contribution immediately into VWRA?"
    ),
    "independent_variables": [
        "calendar month parity of the contribution session",
        "January equal-value rebalance",
    ],
    "dependent_variables": ["terminal wealth after explicit costs"],
    "historical_data_requirements": [
        "stored listing-currency split-adjusted closes for VWRA and CSPX",
        "no manufactured session before the first stored close",
        "no foreign-exchange conversion",
    ],
    "input_transformations": ["none"],
    "point_in_time_assumptions": [
        "No macroeconomic series is an input.",
        "The execution price is the stored close of that session.",
        "That close is an accounting price, not a signal taken from a later session.",
        "A lagged signal, if one were used, would have to be a prior stored close.",
        "bea.vintage.real_gdp.pct_preceding is not an input.",
    ],
    "methodology_version": METHODOLOGY_VERSION,
    "statistical_tests": ["none; one path is not a sample"],
    "portfolio_decision_policy": ("odd_month_vwra_even_month_cspx_january_equal_value_rebalance"),
    "baseline_strategy": "immediate_vwra",
    "etf_universe": ["VWRA", "CSPX"],
    "investability_rules": [
        "whole units only",
        "trade only on a stored session for that symbol",
        "refuse a currency conversion",
        "do not invent a distribution or a corporate action",
    ],
    "simulation_window_rule": ("intersection of stored VWRA and CSPX adjusted_close sessions"),
    "starting_capital": "0",
    "contribution_amount": PILOT_CONTRIBUTION,
    "contribution_schedule": ("1000 USD on the first common stored session of each calendar month"),
    "transaction_cost_rate": PILOT_COST_RATE,
    "cash_interest_rate": PILOT_INTEREST_RATE,
    "distributions": "unsupported_not_invented",
    "corporate_actions": "not_applied_prices_are_already_split_adjusted",
    "currency_conversion": "refused",
    "risk_constraints": ["no leverage", "no short sale", "no fractional unit"],
    "training_window": "none",
    "validation_window": "none",
    "holdout_window": "none; the single full overlap is the only window",
    "acceptance_criteria": {
        "insufficient_data_if": "either ledger fails to reconcile",
        "rejected_if": (
            "both ledgers reconcile and alternative terminal wealth is less "
            "than or equal to passive terminal wealth"
        ),
        "inconclusive_if": ("both ledgers reconcile and alternative terminal wealth is greater"),
        "forbidden_statuses": [
            "statistically_supported",
            "economically_useful",
            "forward_validated",
        ],
    },
    "multiple_testing": (
        "One preregistered comparison. The two paths share inputs and overlap "
        "in time, so they are not independent confirmations."
    ),
    "macro_vintage_ids": [],
    "publication_allowed": False,
    "next_eligible_session_rule": (
        "A printed release date whose clock time is unknown is not eligible on "
        "that date. The first eligible session is the next stored session "
        "strictly after the printed date. A missing session is not filled. "
        "Midnight UTC on source_release_at is an identity anchor, not an "
        "observed publication time. This experiment does not use a "
        "macroeconomic release, so the rule is not applied to a decision."
    ),
}


def frozen_specification_hash() -> str:
    return sha256_document(FROZEN_PILOT_SPECIFICATION)
