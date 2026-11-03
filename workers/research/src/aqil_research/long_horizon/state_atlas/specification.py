"""Frozen historical-state atlas and the LH-H-004 sequence.

Thresholds in these dictionaries are the preregistration. A later change is a
new version. This module does not read prices or write rows.
"""

from __future__ import annotations

from aqil_research.long_horizon.money import sha256_document

SPECIFICATION_ID = "ATLAS-DEF-001"
SPECIFICATION_VERSION = 1

SEQUENCE_HYPOTHESIS_ID = "LH-H-004"
SEQUENCE_EXPERIMENT_ID = "LH-E-004"
SEQUENCE_EXECUTION_ID = "LH-X-004"
SEQUENCE_EVIDENCE_ID = "LH-V-004"
SEQUENCE_CLAIM_ID = "LH-C-004"

PROTECTED_HYPOTHESES = frozenset({"LH-H-001", "LH-H-002", "LH-H-003"})
PROTECTED_EXPERIMENTS = frozenset({"LH-E-001", "LH-E-002", "LH-E-003"})
PROTECTED_EXECUTIONS = frozenset({"LH-X-001", "LH-X-002", "LH-X-003"})

EVT_DEFINITION_ID = "EVT-DEF-001"
EVT_DEFINITION_VERSION = 1
EVT_DEFINITION_HASH = "3844aff160a7f6fac7fb4c966707a313b6e8c89f4bb04cee6a72cb4d97275114"

FORBIDDEN_CLAIM_STATUSES = (
    "statistically_supported",
    "economically_useful",
    "forward_validated",
)
ALLOWED_SEQUENCE_STATUSES = (
    "insufficient_data",
    "rejected",
    "no_incremental_information",
    "inconclusive",
)

POINT_IN_TIME_DATASET = "bea.vintage.real_gdp.pct_preceding"
CENSUS_METHOD_ID = "CENSUS_ADV_DURABLE_ORDERS"
ALFRED_DATASET = "fred.alfred.UNRATE"

SESSION_STEPS: dict[str, int] = {
    "1m": 21,
    "3m": 63,
    "6m": 126,
    "12m": 252,
    "24m": 504,
    "36m": 756,
}

ATLAS_SPECIFICATION: dict[str, object] = {
    "schema_version": "1.0",
    "specification_id": SPECIFICATION_ID,
    "version": SPECIFICATION_VERSION,
    "publication_allowed": False,
    "event_definition_id": EVT_DEFINITION_ID,
    "event_definition_version": EVT_DEFINITION_VERSION,
    "event_definition_hash": EVT_DEFINITION_HASH,
    "price_type": "adjusted_close",
    "adjustment_status": "adjusted",
    "price_label": (
        "A stored adjusted close stays a split-adjusted close. It is not relabelled "
        "as a total return."
    ),
    "total_return": "blocked",
    "distributions": "blocked",
    "surprise": "blocked_no_consensus",
    "full_sample_standardisation": "refused",
    "anchor_kinds": ["listing_month_end", "bea_gdp_release"],
    "absent_anchor_kinds": ["market_transition", "daily_unchanged_macro_print"],
    "insufficient_lookback": "marks the feature insufficient and keeps the anchor",
    "session_clock": (
        "Horizons labelled 1m, 3m, 6m, 12m, 24m, and 36m are stored-session steps "
        "of 21, 63, 126, 252, 504, and 756. They are not calendar months. A missing "
        "session is not filled. An incomplete forward horizon is censored."
    ),
    "session_steps": SESSION_STEPS,
    "peer_tolerance_days": 5,
    "peer_currency": "USD",
    "relative_performance": (
        "Relative performance versus VWRA uses US-dollar listings only and the "
        "existing five-day peer-date tolerance. EUNA stays blocked because "
        "fx_observations is empty. No other cross-currency excess is calculated."
    ),
    "euna_relative_performance": "blocked_no_foreign_exchange",
    "retrospective_clock": "retrospective_latest_revised_release_lag_unknown",
    "retrospective_usable_as_decision_input": False,
    "point_in_time_dataset": POINT_IN_TIME_DATASET,
    "point_in_time_rule": (
        "Only bea.vintage.real_gdp.pct_preceding may be a point-in-time observation. "
        "A vintage is eligible when its printed release date is on or before the "
        "anchor session. A row without a release date is not used. The latest "
        "eligible vintage is kept for each quarter. This does not make any "
        "registered method point-in-time."
    ),
    "period_bound": {
        "stored_period_end": "used when the column is present",
        "monthly_if_period_end_null": "last calendar day of the period_start month",
        "quarterly_if_period_end_null": "last calendar day of the period_start quarter",
        "weekly_if_period_end_null": "period_start, the stored week-ending day",
        "daily_if_period_end_null": "period_start",
        "annual_if_period_end_null": "31 December of the period_start year",
        "release_date_is_not_invented": True,
    },
    "economic_features": [
        "level",
        "direction",
        "difference",
        "percent_change",
        "year_on_year",
        "acceleration",
        "persistence",
        "trailing_percentile",
        "trailing_standardisation",
    ],
    "trailing_observation_counts": {
        "daily": 252,
        "weekly": 52,
        "monthly": 36,
        "quarterly": 20,
        "annual": 10,
    },
    "year_on_year_steps": {"monthly": 12, "quarterly": 4, "weekly": 52},
    "year_on_year_unsupported_frequencies": ["daily", "annual"],
    "year_on_year_gap_rule": (
        "The earlier observation must sit the exact number of periods back on the "
        "frequency grid. A missing period is not filled."
    ),
    "percent_change_rule": (
        "current divided by the previous value, minus one; zero base is insufficient"
    ),
    "acceleration_rule": (
        "Economic acceleration is the change in that percent change. Market "
        "acceleration is the change in the same-horizon trailing return versus "
        "the trailing return one horizon earlier."
    ),
    "standardisation_rule": (
        "Trailing mean and sample standard deviation use only the trailing window "
        "already inside the anchor sample. A full-sample z-score is refused."
    ),
    "market_features": [
        "split_adjusted_close",
        "trailing_return",
        "trailing_return_acceleration",
        "drawdown",
        "recovery_from_prior_trough",
        "volatility",
        "relative_performance_vs_vwra",
    ],
    "drawdown_rule": (
        "Inside the trailing window, drawdown is the anchor close divided by the "
        "highest close, minus one. Recovery uses the earliest peak and the lowest "
        "close after that peak. The peak being the anchor close leaves recovery "
        "insufficient."
    ),
    "volatility_rule": (
        "sample standard deviation of simple session returns inside the trailing window"
    ),
    "families_linked_not_redefined": [
        "sustained_advance",
        "relative_outperformance",
        "persistent_bull",
        "drawdown_recovery",
        "early_recovery",
        "failed_rally",
        "negative_market",
        "flat_market",
        "leadership_transition",
    ],
    "absent_from_version_1": [
        "volatility_transition",
        "failed_recovery",
        "trend_reversal",
    ],
    "methodology_inventory": (
        "All 26 registrations are listed with class, inputs, and output definition. "
        "The replay status is not_historically_replayed or unavailable_input. No "
        "historical output series is manufactured from a research_runs row."
    ),
    "unavailable_dimensions": [
        "surprise",
        "euna_relative_performance",
        "total_return",
        "distributions",
        "fx_observations",
        "inrg_prices",
        CENSUS_METHOD_ID,
        ALFRED_DATASET,
        "full_sample_z_score",
        "volatility_transition",
        "failed_recovery",
        "trend_reversal",
    ],
}


SEQUENCE_HYPOTHESIS: dict[str, object] = {
    "hypothesis_id": SEQUENCE_HYPOTHESIS_ID,
    "version": 1,
    "proposition": (
        "On the last stored session of a calendar month, a 252-session peak-to-trough "
        "decline of at least 10 percent, with the decision close still within 2 percent "
        "of that trough, followed one to three calendar months later by a 63-session "
        "rise of at least 5 percent and a close at least 5 percent above that earlier "
        "trough, precedes the existing 126-session labelled advance of at least 10 "
        "percent more often than month-ends where the standalone bounce is true and "
        "the earlier condition did not occur. The median incremental difference must "
        "be greater than zero. Otherwise the status is no_incremental_information. "
        "This is category C. It is not one of the 618 catalogue scenarios, it does "
        "not call the portfolio simulator, and it is not an allocation rule."
    ),
    "economic_rationale": (
        "A long-term buyer can see a decline that is still near its trough, and "
        "can later see a bounce from that trough. The question is whether the "
        "sequence adds anything to the bounce on its own. No cause is claimed. "
        "LH-X-002 is cited and is not re-estimated. Comparison month-ends are not "
        "chosen for their later returns."
    ),
    "expected_mechanism": "No causal mechanism is claimed.",
    "expected_direction": (
        "The median frequency of the labelled advance after the sequence exceeds "
        "the median frequency after the standalone bounce without the earlier "
        "condition, by more than zero."
    ),
    "horizon": (
        "Eligible month-end sessions with 252 prior stored sessions and 126 later "
        "stored sessions. The whole eligible history is inspected. It is not an "
        "untouched holdout."
    ),
    "falsification_criteria": (
        "Insufficient when fewer than five symbols have at least 12 eligible "
        "months, 3 sequence months, 3 standalone-bounce months without the earlier "
        "condition, and 3 labelled advances. no_incremental_information when the "
        "median incremental difference is not greater than zero. Rejected when "
        "that difference is greater than zero but the sequence does not beat the "
        "eligible-month base rate, or it precedes at least 70 percent of labelled "
        "advances. Otherwise inconclusive. Statistical support, economic usefulness, "
        "and forward validation are forbidden."
    ),
    "alternative_explanations": [
        "Month-end outcomes overlap, so the months are not independent trials.",
        "Listings share a common equity path.",
        "The series are split-adjusted closes, not total returns.",
        "The sequence and the standalone bounce can describe one price path.",
        "The stored universe was selected in 2026, so closed funds are absent.",
        "A positive difference on this single inspected window can be chance.",
    ],
    "relevant_indicators": [],
    "relevant_methodologies": [],
    "target_instruments": ["every stored adjusted-close listing, read at execution"],
    "initial_status": "proposed",
    "catalogue_signal_id": None,
}


SEQUENCE_EXPERIMENT: dict[str, object] = {
    "schema_version": "1.0",
    "experiment_id": SEQUENCE_EXPERIMENT_ID,
    "version": 1,
    "category": "C",
    "category_label": "price_only_simulator_research",
    "not_macroeconomic_investment_intelligence": True,
    "hypothesis_id": SEQUENCE_HYPOTHESIS_ID,
    "hypothesis_version": 1,
    "atlas_specification_id": SPECIFICATION_ID,
    "atlas_specification_version": SPECIFICATION_VERSION,
    "event_definition_id": EVT_DEFINITION_ID,
    "event_definition_version": EVT_DEFINITION_VERSION,
    "research_question": (
        "After a month-end still near a 10 percent peak-to-trough decline, does "
        "a bounce one to three calendar months later precede the existing "
        "126-session labelled advance more often than the bounce without that "
        "earlier condition?"
    ),
    "condition_a": {
        "name": "near_trough",
        "lookback_steps": 252,
        "minimum_decline": "0.10",
        "maximum_distance_above_trough": "0.02",
        "peak_tie_break": "earliest_close_in_the_lookback",
        "observable_from": "closes on or before the decision session",
    },
    "condition_b_after_a": {
        "name": "bounce_from_earlier_trough",
        "later_month_ends": [1, 2, 3],
        "which_earlier_a": "latest month-end in that span where condition A is true",
        "lookback_steps": 63,
        "minimum_return": "0.05",
        "minimum_distance_above_a_trough": "0.05",
        "observable_from": (
            "closes on or before the later decision session, plus the trough "
            "price already fixed at A"
        ),
    },
    "condition_b_alone": {
        "name": "standalone_bounce",
        "lookback_steps": 252,
        "momentum_steps": 63,
        "minimum_return": "0.05",
        "minimum_distance_above_own_trough": "0.05",
        "observable_from": "closes on or before the decision session",
    },
    "primary_control": (
        "Month-ends where the standalone bounce is true and condition A did not "
        "occur on any of the prior three month-ends."
    ),
    "component_control": (
        "The standalone bounce on its own. LH-X-002 is cited and is not re-estimated."
    ),
    "outcome_label": {
        "steps": 126,
        "minimum_return": "0.10",
        "uses_later_prices": True,
        "known_at_the_decision": False,
        "same_label_as": "LH-E-002 outcome_label",
        "not_a_state_input": True,
    },
    "decision_grid": "last stored session of each calendar month, per listing",
    "eligibility": (
        "The decision index has 252 prior sessions and 126 later sessions. "
        "A month without that span is excluded from the score. Exclusion uses "
        "availability, not the sign of the later return. The atlas anchor remains."
    ),
    "status_rule": {
        "minimum_qualifying_symbols": 5,
        "minimum_eligible_per_symbol": 12,
        "minimum_sequence_per_symbol": 3,
        "minimum_control_per_symbol": 3,
        "minimum_advances_per_symbol": 3,
        "minimum_median_incremental_difference": "0",
        "incremental_comparison": "strictly_greater",
        "rejected_if_median_event_share_at_least": "0.70",
        "insufficient_data_if": "fewer than five symbols meet the minimum counts",
        "no_incremental_information_if": (
            "the median frequency after the sequence is not greater than the "
            "median frequency after the primary control"
        ),
        "rejected_if": (
            "the incremental difference is greater than zero, and either the "
            "sequence does not beat the eligible-month base rate or it precedes "
            "at least 70 percent of labelled advances"
        ),
        "inconclusive_if": "none of those conditions hold",
        "forbidden_statuses": list(FORBIDDEN_CLAIM_STATUSES),
        "allowed_statuses": list(ALLOWED_SEQUENCE_STATUSES),
        "median": (
            "odd count uses the middle value; even count uses the mean of the two middle values"
        ),
    },
    "holdout_window": (
        "none. The eligible month-ends are the only sample. That sample is "
        "inspected by this experiment. It is not an untouched holdout."
    ),
    "training_window": "none",
    "validation_window": "none separate from the inspected eligible history",
    "portfolio_comparison": "blocked",
    "portfolio_block_reason": (
        "This experiment does not call the portfolio simulator. The 618 catalogue "
        "scenarios stay unexecuted. A later portfolio test would be a new experiment id."
    ),
    "methodology_version": "historical-state-atlas-1",
    "statistical_tests": [
        "none; overlapping month-ends are not a sample of independent trials"
    ],
    "portfolio_decision_policy": "none_frequency_study_only",
    "baseline_strategy": "standalone_bounce_without_prior_near_trough",
    "etf_universe": ["every stored adjusted-close listing"],
    "starting_capital": "not_applicable",
    "contribution_amount": "not_applicable",
    "contribution_schedule": "not_applicable_no_portfolio_path",
    "transaction_cost_rate": "not_applicable",
    "cash_interest_rate": "not_applicable",
    "distributions": "blocked_not_stored",
    "corporate_actions": "split adjustment is already in the stored close and is not relabelled",
    "currency_conversion": "none",
    "risk_constraints": ["no order is generated"],
    "simulation_window_rule": "eligible month-ends on stored adjusted closes",
    "investability_rules": [
        "no order is generated",
        "no currency conversion",
        "no manufactured session",
        "no distribution is invented",
    ],
    "independent_variables": [
        (
            "252-session peak-to-trough decline of at least 10 percent with the close "
            "within 2 percent of that trough"
        ),
        (
            "one to three calendar months later, a 63-session return of at least 5 percent "
            "and a close at least 5 percent above that trough"
        ),
    ],
    "dependent_variables": ["126-session labelled advance of at least 10 percent"],
    "historical_data_requirements": [
        "stored split-adjusted closes",
        "no foreign-exchange rate",
        "no total-return index",
        "no macroeconomic series",
    ],
    "input_transformations": ["none"],
    "point_in_time_assumptions": [
        "Conditions A and B read closes on or before the decision session.",
        "The trough used by the later month was fixed at the earlier month.",
        "The outcome label reads the close 126 sessions later and is not a state.",
        "No macroeconomic series is an input.",
        "bea.vintage.real_gdp.pct_preceding is not an input.",
    ],
    "macro_vintage_ids": [],
    "multiple_testing": (
        "One preregistered sequence. LH-X-002 remains the stored conjunction and "
        "is not a second test. Inventory families are descriptive counts."
    ),
    "acceptance_criteria": {
        "insufficient_data_if": "fewer than five symbols meet the minimum counts",
        "rejected_if": (
            "the incremental difference is positive and the sequence fails the "
            "base-rate or event-share check"
        ),
        "inconclusive_if": (
            "the incremental difference is positive and the rejection checks do not fire"
        ),
        "forbidden_statuses": list(FORBIDDEN_CLAIM_STATUSES),
    },
    "next_eligible_session_rule": "not_applicable_no_order",
    "publication_allowed": False,
    "cited_execution": "LH-X-002",
    "cited_execution_is_not_reestimated": True,
}


def atlas_specification_hash() -> str:
    return sha256_document(ATLAS_SPECIFICATION)


def sequence_experiment_hash() -> str:
    return sha256_document(SEQUENCE_EXPERIMENT)


def assert_sequence_status_allowed(status: str) -> None:
    if status in FORBIDDEN_CLAIM_STATUSES:
        raise ValueError("category C cannot promote this status")
    if status not in ALLOWED_SEQUENCE_STATUSES:
        raise ValueError("the sequence status is not one of the predetermined statuses")
