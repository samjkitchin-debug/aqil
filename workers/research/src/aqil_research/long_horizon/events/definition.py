"""Frozen event-identification and pilot specifications.

Thresholds in these dictionaries are the preregistration. A later change is a
new version. This module does not read prices.
"""

from __future__ import annotations

from aqil_research.long_horizon.money import sha256_document

DEFINITION_ID = "EVT-DEF-001"
DEFINITION_VERSION = 1

PILOT_HYPOTHESIS_ID = "LH-H-002"
PILOT_EXPERIMENT_ID = "LH-E-002"
PILOT_EXECUTION_ID = "LH-X-002"
PILOT_EVIDENCE_ID = "LH-V-002"
PILOT_CLAIM_ID = "LH-C-002"

MACRO_HYPOTHESIS_ID = "LH-H-003"
MACRO_EXPERIMENT_ID = "LH-E-003"
MACRO_EXECUTION_ID = "LH-X-003"
MACRO_EVIDENCE_ID = "LH-V-003"
MACRO_CLAIM_ID = "LH-C-003"

PROTECTED_HYPOTHESES = frozenset({"LH-H-001"})
PROTECTED_EXPERIMENTS = frozenset({"LH-E-001"})
PROTECTED_EXECUTIONS = frozenset({"LH-X-001"})

VWRA_FIRST_SESSION = "2019-07-25"
FORBIDDEN_CLAIM_STATUSES = (
    "statistically_supported",
    "economically_useful",
    "forward_validated",
)

EVENT_DEFINITION: dict[str, object] = {
    "schema_version": "1.0",
    "definition_id": DEFINITION_ID,
    "version": DEFINITION_VERSION,
    "price_type": "adjusted_close",
    "adjustment_status": "adjusted",
    "total_return_events": "blocked",
    "total_return_block_reason": (
        "Stored series are split-adjusted closes. Distributions are not stored. "
        "A split-adjusted close is not relabelled as a total return."
    ),
    "session_clock": (
        "Horizons labelled 1m, 3m, 6m, 12m, 24m, and 36m are stored-session "
        "steps of 21, 63, 126, 252, 504, and 756. They are not calendar months. "
        "A missing session is not filled."
    ),
    "session_steps": {
        "1m": 21,
        "3m": 63,
        "6m": 126,
        "12m": 252,
        "24m": 504,
        "36m": 756,
    },
    "vwra_first_stored_session": VWRA_FIRST_SESSION,
    "vwra_rule": ("A VWRA session before 2019-07-25 is refused. No earlier price is manufactured."),
    "currency_rule": (
        "Each event stays in the stored listing currency. quote_unit must equal "
        "that currency. No foreign-exchange conversion is applied."
    ),
    "label_rule": (
        "An event label may use later stored closes to describe an episode. "
        "usable_as_investment_signal is false on every catalogue row. The eventual "
        "bottom, the rally start, and the forward return are not decision inputs."
    ),
    "catalogue_rule": (
        "Sustained advances and sideways-then-advance episodes keep the earliest "
        "qualifying window and resume at its end session. Interiors do not overlap. "
        "The shared endpoint may be the next start. Qualifying overlapping windows "
        "are counted and are not each given an event id. Negative, flat, and "
        "relative-outperformance rows use a fixed grid, not a search for the "
        "strongest window."
    ),
    "sustained_advance": {
        "1m": {
            "steps": 21,
            "minimum_return": "0.05",
            "maximum_drawdown": "0.08",
            "minimum_up_session_fraction": "0.55",
        },
        "3m": {
            "steps": 63,
            "minimum_return": "0.10",
            "maximum_drawdown": "0.10",
            "minimum_up_session_fraction": "0.55",
        },
        "6m": {
            "steps": 126,
            "minimum_return": "0.15",
            "maximum_drawdown": "0.12",
            "minimum_up_session_fraction": "0.55",
        },
        "12m": {
            "steps": 252,
            "minimum_return": "0.20",
            "maximum_drawdown": "0.15",
            "minimum_up_session_fraction": "0.55",
        },
        "24m": {
            "steps": 504,
            "minimum_return": "0.30",
            "maximum_drawdown": "0.20",
            "minimum_up_session_fraction": "0.55",
        },
        "36m": {
            "steps": 756,
            "minimum_return": "0.40",
            "maximum_drawdown": "0.20",
            "minimum_up_session_fraction": "0.55",
        },
    },
    "persistent_bull": {
        "minimum_rise": "0.20",
        "confirming_decline": "0.20",
        "minimum_session_steps": 126,
        "terminal_upswing_without_confirmation": "censored_not_an_event",
    },
    "early_bull": {
        "session_steps": 63,
        "requires_persistent_bull": True,
        "uses_later_prices": True,
    },
    "drawdown_recovery": {
        "minimum_decline": "0.15",
        "recovery_rule": "first later close at or above the peak close that started the drawdown",
        "open_drawdown": "censored_not_a_recovery",
    },
    "early_recovery": {
        "session_steps": 63,
        "retracement": "0.50",
        "must_finish_before_the_full_recovery": True,
        "uses_later_prices": True,
    },
    "sideways_then_advance": {
        "sideways_steps": 126,
        "maximum_absolute_return": "0.08",
        "maximum_range_over_start": "0.12",
        "maximum_drawdown": "0.10",
        "advance_steps": 63,
        "minimum_advance_return": "0.10",
    },
    "relative_outperformance": {
        "steps": 252,
        "grid": "fixed_step_equal_to_the_horizon",
        "minimum_excess_over_peer_median": "0.10",
        "minimum_peers": 3,
        "peer_tolerance_days": 5,
        "same_currency_only": True,
        "peer_currency": "USD",
        "cross_currency": "blocked_no_foreign_exchange_conversion",
    },
    "leadership_transition": {
        "steps": 252,
        "grid": "last_stored_usd_session_of_each_calendar_month",
        "minimum_excess_over_previous_leader": "0.05",
        "minimum_eligible_symbols": 3,
        "tie_break": "alphabetical_ticker",
        "peer_tolerance_days": 5,
        "peer_currency": "USD",
        "cross_currency": "blocked_no_foreign_exchange_conversion",
        "observable_at_the_event_date": True,
        "usable_as_investment_signal": False,
    },
    "failed_rally": {
        "attempt_rise": "0.08",
        "failure_decline_from_attempt_peak": "0.08",
        "not_failed_if_rise_reaches": "0.15",
        "confirmation_close_at_or_below_trough": True,
        "uses_later_prices": True,
    },
    "negative_market": {
        "steps": 126,
        "grid": "fixed_from_the_first_session",
        "classification_order": "flat_before_negative",
        "negative_if_return_below": "0",
    },
    "flat_market": {
        "steps": 126,
        "grid": "fixed_from_the_first_session",
        "absolute_return_at_most": "0.03",
        "priority_over_negative": True,
    },
    "rally_despite_deterioration": {
        "status": "blocked",
        "reason": (
            "No registered deterioration rule has an original vintage. "
            "Latest-revised macro observations are not used to label a rally. "
            "bea.vintage.real_gdp.pct_preceding does not unlock a method."
        ),
    },
    "blocked_families": ["total_return_advance", "rally_despite_deterioration"],
    "publication_allowed": False,
    "not_a_rewrite_of": [
        "docs/research/macro-etf/COVERAGE_MATRIX.csv",
        "LH-H-001",
        "LH-E-001",
        "LH-X-001",
        "the version 1 catalogue of 309 signals and 618 scenarios",
    ],
}


PILOT_HYPOTHESIS: dict[str, object] = {
    "hypothesis_id": PILOT_HYPOTHESIS_ID,
    "version": 1,
    "proposition": (
        "On the last stored session of each calendar month, the conjunction of "
        "an already completed 10 percent drawdown and a 63-session price rise of "
        "at least 5 percent is followed, over the next 126 stored sessions, by a "
        "price rise of at least 10 percent more often than on the other eligible "
        "month-ends, and that conjunction occurs on fewer than 40 percent of "
        "eligible month-ends. Both legs use only closes on or before the decision "
        "session. The later rise is a label. This is category C. It is not one of "
        "the 618 catalogue scenarios, not a macroeconomic claim, and not an "
        "allocation rule."
    ),
    "economic_rationale": (
        "A long-term buyer can observe a decline that has already occurred and a "
        "partial retracement that has already occurred, together with recent "
        "price momentum. The question is whether that conjunction is uncommon in "
        "ordinary months and whether the labelled advance is more frequent after "
        "it. No cause is claimed. Comparison months are the other eligible "
        "month-ends on the same grid. They are not chosen for their later returns."
    ),
    "expected_mechanism": "No causal mechanism is claimed.",
    "expected_direction": (
        "Median conditional frequency exceeds the median base rate, the median "
        "condition frequency is below 40 percent, and the median share of labelled "
        "advances preceded by the condition is below 70 percent."
    ),
    "horizon": (
        "Eligible month-end sessions with 252 prior stored sessions and 126 later "
        "stored sessions. The whole eligible history is inspected. It is not an "
        "untouched holdout."
    ),
    "falsification_criteria": (
        "Insufficient when fewer than five symbols have at least 12 eligible "
        "months, 3 condition months, and 3 labelled advances. Rejected when the "
        "median lift is not positive, or the median condition frequency is at "
        "least 40 percent, or the condition precedes at least 70 percent of "
        "labelled advances. Otherwise inconclusive. Statistical support, economic "
        "usefulness, and forward validation are forbidden."
    ),
    "alternative_explanations": [
        "Month-end outcomes overlap, so the months are not independent trials.",
        "Listings share a common equity path.",
        "The series are split-adjusted closes, not total returns.",
        "The retracement and the 63-session momentum can describe one price path.",
        "The stored universe was selected in 2026, so closed funds are absent.",
        "A positive lift on this single inspected window can be chance.",
    ],
    "relevant_indicators": [],
    "relevant_methodologies": [],
    "target_instruments": ["every stored adjusted-close listing, read at execution"],
    "initial_status": "proposed",
    "catalogue_signal_id": None,
}


FROZEN_PILOT_INTERSECTION: dict[str, object] = {
    "schema_version": "1.0",
    "experiment_id": PILOT_EXPERIMENT_ID,
    "version": 1,
    "category": "C",
    "category_label": "price_only_simulator_research",
    "not_macroeconomic_investment_intelligence": True,
    "hypothesis_id": PILOT_HYPOTHESIS_ID,
    "hypothesis_version": 1,
    "event_definition_id": DEFINITION_ID,
    "event_definition_version": DEFINITION_VERSION,
    "research_question": (
        "On eligible month-ends, does the preregistered price-only conjunction "
        "precede a labelled 126-session advance more often than the base rate, "
        "without being common in ordinary months?"
    ),
    "intersection": {
        "operator": "logical_and",
        "composite_score": "none",
        "weights": "none",
        "legs": [
            {
                "name": "completed_drawdown",
                "lookback_steps": 252,
                "minimum_decline": "0.10",
                "minimum_retracement_from_trough": "0.05",
                "peak_tie_break": "earliest_close_in_the_lookback",
                "observable_from": "closes on or before the decision session",
            },
            {
                "name": "price_momentum",
                "lookback_steps": 63,
                "minimum_return": "0.05",
                "observable_from": "closes on or before the decision session",
            },
        ],
    },
    "outcome_label": {
        "steps": 126,
        "minimum_return": "0.10",
        "uses_later_prices": True,
        "known_at_the_decision": False,
        "not_the_inventory_sustained_advance_filter": True,
    },
    "decision_grid": "last stored session of each calendar month, per listing",
    "eligibility": (
        "The decision index has 252 prior sessions and 126 later sessions. "
        "A month without that span is excluded. Exclusion uses availability, "
        "not the sign of the later return."
    ),
    "comparison_periods": (
        "Every eligible month-end is retained. Condition-false months are the "
        "controls. selected_on_future_return is false."
    ),
    "status_rule": {
        "minimum_qualifying_symbols": 5,
        "minimum_eligible_per_symbol": 12,
        "minimum_condition_per_symbol": 3,
        "minimum_events_per_symbol": 3,
        "common_if_median_condition_frequency_at_least": "0.40",
        "accompanies_advances_if_median_event_share_at_least": "0.70",
        "insufficient_data_if": "fewer than five symbols meet the minimum counts",
        "rejected_if": (
            "median lift is not positive, or the condition is common, or the "
            "condition accompanies most labelled advances"
        ),
        "inconclusive_if": "none of the rejection conditions hold",
        "forbidden_statuses": list(FORBIDDEN_CLAIM_STATUSES),
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
        "This experiment does not call the portfolio simulator. A larger "
        "alternative terminal wealth would be inconclusive under the LH-E-001 "
        "rule, and this specification has no path to an allocation. A later "
        "portfolio test would be a new experiment id. LH-X-001 is not reopened."
    ),
    "methodology_version": "outcome-event-identification-1",
    "statistical_tests": ["none; overlapping month-ends are not a sample of independent trials"],
    "portfolio_decision_policy": "none_frequency_study_only",
    "baseline_strategy": "eligible_month_end_base_rate",
    "starting_capital": "not_applicable",
    "contribution_amount": "not_applicable",
    "contribution_schedule": "not_applicable_no_portfolio_path",
    "simulation_window_rule": "eligible month-ends on stored adjusted closes",
    "investability_rules": [
        "no order is generated",
        "no currency conversion",
        "no manufactured session",
        "no distribution is invented",
    ],
    "independent_variables": [
        "completed drawdown of at least 10 percent with a 5 percent retracement",
        "63-session price return of at least 5 percent",
    ],
    "dependent_variables": ["126-session labelled advance of at least 10 percent"],
    "historical_data_requirements": [
        "stored split-adjusted closes",
        "no foreign-exchange rate",
        "no total-return index",
    ],
    "input_transformations": ["none"],
    "point_in_time_assumptions": [
        "The condition reads closes on or before the decision session.",
        "The outcome label reads the close 126 sessions later and is not a signal.",
        "No macroeconomic series is an input.",
        "bea.vintage.real_gdp.pct_preceding is not an input.",
    ],
    "macro_vintage_ids": [],
    "multiple_testing": (
        "One preregistered intersection. Inventory families are descriptive "
        "counts, not additional tested hypotheses."
    ),
    "publication_allowed": False,
}


MACRO_HYPOTHESIS: dict[str, object] = {
    "hypothesis_id": MACRO_HYPOTHESIS_ID,
    "version": 1,
    "proposition": (
        "Improving industrial production, declining consumer-price inflation, "
        "and positive equity-price momentum were jointly present before "
        "sustained equity advances. This statement is retrospective. It is not "
        "estimated and it is not a portfolio rule."
    ),
    "economic_rationale": (
        "The outcome-first brief names this conjunction as an example to test, "
        "not as a finding. Latest-revised production and inflation are not a "
        "decision clock. No registered method has an original vintage. The real "
        "GDP growth vintage does not supply one. No composite score and no "
        "weights are defined."
    ),
    "expected_mechanism": "Not estimated.",
    "expected_direction": "Not estimated.",
    "horizon": "Not estimated. No lookback values are read.",
    "falsification_criteria": (
        "This version is blocked before estimation. A test would be a new "
        "hypothesis version with a vintage that covers the method's own inputs. "
        "This row is not revised into that test."
    ),
    "alternative_explanations": [
        "Latest-revised series are revised after the months they describe.",
        "Production and inflation can move together without identifying a purchase date.",
        "Equity momentum alone can accompany most advances.",
    ],
    "relevant_indicators": ["fed.g17.IP.B50001.S", "bls.cu.CUSR0000SA0"],
    "relevant_methodologies": [],
    "target_instruments": [],
    "initial_status": "retrospective_only",
    "catalogue_signal_id": None,
}


FROZEN_MACRO_INTERSECTION: dict[str, object] = {
    "schema_version": "1.0",
    "experiment_id": MACRO_EXPERIMENT_ID,
    "version": 1,
    "category": "B",
    "category_label": "retrospective_economic_research",
    "hypothesis_id": MACRO_HYPOTHESIS_ID,
    "hypothesis_version": 1,
    "estimated": False,
    "values_read": False,
    "research_question": (
        "Did improving industrial production, declining inflation, and positive "
        "equity momentum jointly precede sustained advances in a way that could "
        "be decided at the time?"
    ),
    "intersection": {
        "operator": "not_estimated",
        "composite_score": "none",
        "weights": "none",
        "legs": [
            "fed.g17.IP.B50001.S direction, not read",
            "bls.cu.CUSR0000SA0 direction, not read",
            "equity price momentum, not joined",
        ],
    },
    "block_reason": (
        "Both macro legs are stored as latest_revised. No registered method "
        "accepts them as an original vintage. bea.vintage.real_gdp.pct_preceding "
        "is not an input and does not unlock this intersection. ALFRED is not "
        "stored. No portfolio path is run."
    ),
    "portfolio_comparison": "blocked",
    "methodology_version": "none_blocked_before_estimation",
    "statistical_tests": ["none"],
    "portfolio_decision_policy": "none",
    "baseline_strategy": "not_run",
    "starting_capital": "not_applicable",
    "contribution_amount": "not_applicable",
    "contribution_schedule": "not_applicable",
    "simulation_window_rule": "not_run",
    "investability_rules": ["no order is generated"],
    "holdout_window": "not applicable; the intersection was not estimated",
    "macro_vintage_ids": [],
    "publication_allowed": False,
    "not_an_investment_claim": True,
}


def event_definition_hash() -> str:
    return sha256_document(EVENT_DEFINITION)


def pilot_intersection_hash() -> str:
    return sha256_document(FROZEN_PILOT_INTERSECTION)


def macro_intersection_hash() -> str:
    return sha256_document(FROZEN_MACRO_INTERSECTION)
