"""Frozen CNDX and VWRA comparison. This module does not read prices or write rows.

The literals below are the preregistration. They are the EIMI and VWRA thresholds.
They are not chosen from a CNDX coefficient.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from aqil_research.long_horizon.etf_protocol.specification import (
    PEER_TOLERANCE_DAYS,
    PRIMARY_CONTROL,
)
from aqil_research.long_horizon.money import sha256_document
from aqil_research.long_horizon.spec import (
    PILOT_CONTRIBUTION,
    PILOT_COST_RATE,
    PILOT_INTEREST_RATE,
)
from aqil_research.long_horizon.state_atlas.specification import SESSION_STEPS
from aqil_research.long_horizon.vwra_discovery.comparison import (
    PRICE_CONTROL,
    REAL_GDP_FEATURE,
    UNEMPLOYMENT_FEATURE,
    assert_not_promoted,
)
from aqil_research.long_horizon.vwra_discovery.specification import (
    ADVANCE_MINIMUM,
    DECLINE_MAXIMUM,
    INTERSECTION_PAIRS,
    LOGISTIC_DECISION_POINTS,
    LOGISTIC_NON_OVERLAPPING,
    NON_OVERLAP_SESSION_GAP,
    SEQUENCE,
    VWRA_FIRST_SESSION,
)

SPECIFICATION_ID = "CNDX-VWRA-COMPARISON-001"
SPECIFICATION_VERSION = 1
PUBLICATION_ALLOWED = False
PEER = "CNDX"
CONTROL = "VWRA"
PAIR = "CNDX-VWRA"
MATCHED_NOT_BEFORE = VWRA_FIRST_SESSION
TOLERANCE_DAYS = PEER_TOLERANCE_DAYS
DIVERGENCE_STEPS = 126
DIVERGENCE_EXCESS = "0.10"
PRIMARY_STEPS = 126
RELATIVE_CONTROL = f"{PEER}:{PRIMARY_CONTROL}"
MOMENTUM_STEPS = 252
MOMENTUM_BASELINE = CONTROL
STATIC_MIX = "equal_cash_vwra_cndx_january_equal_value"
THRESHOLD_BAND = "0.10"
REPRODUCTION_COMMAND = "uv run python -m aqil_research.long_horizon.vwra_discovery.cndx"
STORED_METHOD_SPECIFICATION = "VWRA-DISCOVERY-001"
PROTECTED_THROUGH = 18

EXCLUSIVE_CLASSES = (
    "cndx_ahead_both_positive",
    "cndx_positive_vwra_negative",
    "both_negative_cndx_declines_less",
    "vwra_ahead",
    "no_sign",
)
EXCLUSIVE_RENAME = {
    "eimi_ahead_both_positive": "cndx_ahead_both_positive",
    "eimi_positive_vwra_negative": "cndx_positive_vwra_negative",
    "both_negative_eimi_declines_less": "both_negative_cndx_declines_less",
    "vwra_ahead": "vwra_ahead",
    "no_sign": "no_sign",
}
CASE_CLASSES = (
    "cndx_ahead",
    "vwra_ahead",
    "both_advance",
    "both_decline",
    "cndx_up_vwra_down",
    "cndx_down_vwra_up",
    "leadership_reversal",
    "approximately_neutral",
)
CASE_STATE_FEATURES = (
    ("unemployment_year_on_year", UNEMPLOYMENT_FEATURE),
    ("cpi_year_on_year", "bls.cu.CUSR0000SA0:year_on_year"),
    ("industrial_production_year_on_year", "fed.g17.IP.B50001.S:year_on_year"),
    ("term_spread", "method:ESTRELLA_MISHKIN_TERM_SPREAD:spread"),
    ("credit_standards", "fed.sloos.SUBLPDCILS_N.Q:level"),
)
FINDING_CLASSES = (
    "descriptive",
    "retrospective_exploratory",
    "inconclusive",
    "insufficient_sample",
    "rejected",
    "no_incremental_information",
)
FORBIDDEN_PROMOTIONS = (
    "statistically_supported",
    "economically_useful",
    "forward_validated",
)
IMPLEMENTED_PORTFOLIO_PATHS = (
    "immediate_vwra",
    "immediate_cndx",
    STATIC_MIX,
    "contribution_to_higher_trailing_return_252",
    "calendar_fixed_weight",
    "threshold_fixed_weight",
    "cash_flow_only_equal_weight",
)
BLOCKED_PORTFOLIO_PATHS = ("bounded_vwra_to_cndx_rotation",)

HYPOTHESES: tuple[dict[str, object], ...] = (
    {
        "hypothesis_id": "LH-H-019",
        "experiment_id": "LH-E-019",
        "execution_id": "LH-X-019",
        "evidence_id": "LH-V-019",
        "claim_id": "LH-C-019",
        "category": "B",
        "category_label": "retrospective_economic_research",
        "proposition": (
            "The 26 registered methods already stored under VWRA-DISCOVERY-001 have "
            "a retrospective coverage census. Component counts are not distinct dates. "
            "Point-in-time methodology output remains zero. The census is not a "
            "CNDX score and not an allocation."
        ),
        "economic_rationale": (
            "The census reads the stored points and does not delete them. "
            "It does not replay a method."
        ),
        "expected_mechanism": (
            "Each method keeps its stored version, class, and failure. Census methods "
            "stay unavailable. Inflation autoregression stays the stored failure."
        ),
        "expected_direction": "not prejudged",
        "horizon": "the stored output dates of each registered method",
        "falsification_criteria": (
            "A point-in-time methodology output, a deleted point, or a retuned "
            "threshold fails this census."
        ),
        "alternative_explanations": [
            "Several components can share one date.",
            "A full-sample smoother describes the past without having been known then.",
        ],
        "relevant_indicators": ["registered method outputs"],
        "relevant_methodologies": ["default_method_registry", STORED_METHOD_SPECIFICATION],
        "target_instruments": [],
    },
    {
        "hypothesis_id": "LH-H-020",
        "experiment_id": "LH-E-020",
        "execution_id": "LH-X-020",
        "evidence_id": "LH-V-020",
        "claim_id": "LH-C-020",
        "category": "B",
        "category_label": "retrospective_economic_research",
        "proposition": (
            "On CNDX month-ends, stored atlas features and reconstructed method output "
            "have a descriptive association with the later 126-session return. An advance "
            "is a stored return of at least 0.10. A decline is a stored return of at most "
            "-0.10. Logistic and probit are fit only when the frozen floors of 60 decision "
            "points and 15 non-overlapping 126-session keeps are both met."
        ),
        "economic_rationale": (
            "The battery is the VWRA discovery battery with the symbol changed to CNDX. "
            "The thresholds are not retuned."
        ),
        "expected_mechanism": (
            "Spearman and Pearson use the anchor set. A missing forward session is censored. "
            "No later close is filled. Sessions before the first stored CNDX session are refused."
        ),
        "expected_direction": "not prejudged",
        "horizon": "126 sessions after the CNDX month-end",
        "falsification_criteria": (
            "A future return is not a state. A missed floor stores "
            "not_estimable_effective_sample and still stores the descriptive rows. "
            "The result is not an allocation."
        ),
        "alternative_explanations": [
            "Overlapping month-ends repeat one episode.",
            "Latest-revised features were not known on the anchor date.",
        ],
        "relevant_indicators": ["atlas features", "reconstructed method output"],
        "relevant_methodologies": ["ATLAS-DEF-001", "VWRA-DISCOVERY-001"],
        "target_instruments": [PEER],
    },
    {
        "hypothesis_id": "LH-H-021",
        "experiment_id": "LH-E-021",
        "execution_id": "LH-X-021",
        "evidence_id": "LH-V-021",
        "claim_id": "LH-C-021",
        "category": "B",
        "category_label": "retrospective_economic_research",
        "proposition": (
            "The same eight economically named pairs are scored on CNDX when both "
            "series are stored. A missing input is a refusal. Shared inputs are not "
            "independent confirmation."
        ),
        "economic_rationale": (
            "The pairs stay labour and inflation, growth and inflation, growth and credit, "
            "credit and rates, policy and the yield curve, liquidity and activity, "
            "growth and momentum, and inflation and drawdown."
        ),
        "expected_mechanism": "Each pair uses the sign or drawdown rule already frozen.",
        "expected_direction": "not prejudged",
        "horizon": "126 sessions after the CNDX month-end",
        "falsification_criteria": (
            "An absent input is refused. No substitute series is introduced."
        ),
        "alternative_explanations": [
            "The two legs can move together because they share a business-cycle factor.",
        ],
        "relevant_indicators": ["the eight named pairs"],
        "relevant_methodologies": ["ATLAS-DEF-001"],
        "target_instruments": [PEER],
    },
    {
        "hypothesis_id": "LH-H-022",
        "experiment_id": "LH-E-022",
        "execution_id": "LH-X-022",
        "evidence_id": "LH-V-022",
        "claim_id": "LH-C-022",
        "category": "B",
        "category_label": "retrospective_economic_research",
        "proposition": (
            "The stored sequence is a negative change in year-on-year CPI inflation, "
            "followed within one to three month-ends by a strictly positive 63-session "
            "trailing return, compared with each component against the later 126-session "
            "advance. The stored sign is positive, which the frozen function treats as "
            "greater than zero. The separate ETF-PROT-001 binary of 0.05 is not substituted."
        ),
        "economic_rationale": (
            "The sequence is SEQ-INF-MOM-001. Substituting 0.05 would retune the stored rule."
        ),
        "expected_mechanism": (
            "The comparison uses the frozen ETF-PROT-001 conjunction floors. "
            "It cannot assign a forbidden promotion."
        ),
        "expected_direction": "not prejudged",
        "horizon": "confirmation inside one to three month-ends, outcome 126 sessions later",
        "falsification_criteria": (
            "The frozen conjunction rule assigns insufficient_sample, "
            "retrospective_exploratory, rejected, or inconclusive."
        ),
        "alternative_explanations": [
            "Momentum alone can match the sequence.",
            "Month-ends inside one episode are not independent trials.",
        ],
        "relevant_indicators": ["CPI year-on-year", "trailing_return_63"],
        "relevant_methodologies": ["ETF-PROT-001", "VWRA-DISCOVERY-001"],
        "target_instruments": [PEER],
    },
    {
        "hypothesis_id": "LH-H-023",
        "experiment_id": "LH-E-023",
        "execution_id": "LH-X-023",
        "evidence_id": "LH-V-023",
        "claim_id": "LH-C-023",
        "category": "B",
        "category_label": "retrospective_economic_research",
        "proposition": (
            "On matched month-ends at or after the later of the two first stored sessions, "
            "within five calendar days, the outcome is the CNDX session-step return minus "
            "the VWRA session-step return. The same economic and methodology states are "
            "applied to both returns and to the excess. Unemployment year-on-year and "
            "real-GDP trailing standardisation are remeasured on that matched sample. "
            "A predeclared price control accounts for common equity exposure. The excess "
            "model is not chosen by comparing two absolute models."
        ),
        "economic_rationale": (
            "CNDX and VWRA are separate US-dollar London listings. The excess is not an "
            "independent diversifier and not a total return. Relative outperformance is "
            "not a positive absolute return."
        ),
        "expected_mechanism": (
            "A missing session is censored. No foreign-exchange rate is invented. "
            "Associations differ when the Spearman coefficients have opposite signs. "
            "An excess partial survives VWRA trailing 252-session return only when its "
            "absolute partial Spearman is strictly greater than the absolute Spearman of "
            "the price-only relative-performance control. Otherwise the relative result "
            "is structural exposure or price momentum, not macroeconomic information."
        ),
        "expected_direction": "not prejudged",
        "horizon": "21, 63, 126, 252, 504, and 756 stored sessions",
        "falsification_criteria": (
            "A state after the earlier anchor is dropped. A Benjamini-Hochberg flag "
            "cannot promote a claim. Currency intersections stay blocked while "
            "fx_observations is empty."
        ),
        "alternative_explanations": [
            "The 2019 to 2026 overlap has already been inspected by the VWRA and EIMI programmes.",
            "Common equity exposure or price momentum can produce the excess association.",
        ],
        "relevant_indicators": [
            UNEMPLOYMENT_FEATURE,
            REAL_GDP_FEATURE,
            PRICE_CONTROL,
            RELATIVE_CONTROL,
        ],
        "relevant_methodologies": ["ETF-PROT-001", "ATLAS-DEF-001"],
        "target_instruments": [PEER, CONTROL],
    },
    {
        "hypothesis_id": "LH-H-024",
        "experiment_id": "LH-E-024",
        "execution_id": "LH-X-024",
        "evidence_id": "LH-V-024",
        "claim_id": "LH-C-024",
        "category": "B",
        "category_label": "retrospective_economic_research",
        "proposition": (
            "Matched 126-session episodes are counted for CNDX ahead, VWRA ahead, "
            "both advance, both decline, CNDX up and VWRA down, CNDX down and VWRA up, "
            "leadership reversal, and approximately neutral. The divergence magnitude is "
            "0.10 excess over 126 sessions, the same magnitude frozen before any CNDX score. "
            "Classes may overlap. Each class stores counts and the pre-event states."
        ),
        "economic_rationale": (
            "EVT-DEF-001 relative outperformance uses a 252-session peer median and "
            "three peers. That object is not edited. The pairwise rule is the same 0.10 magnitude."
        ),
        "expected_mechanism": (
            "CNDX ahead is excess of at least 0.10. VWRA ahead is excess of at most -0.10. "
            "Both advance and both decline use the 0.10 absolute thresholds. "
            "CNDX up and VWRA down, and the reverse, use strict signs "
            "and are not the 0.10 classes. "
            "The five exclusive classes at zero are a separate partition."
        ),
        "expected_direction": "not prejudged",
        "horizon": "126 sessions",
        "falsification_criteria": (
            "A class without a count is not a case. A narrative without a number is not stored."
        ),
        "alternative_explanations": [
            "A small day gap inside the five-day tolerance is still one matched month.",
        ],
        "relevant_indicators": [name for name, _feature in CASE_STATE_FEATURES],
        "relevant_methodologies": ["EVT-DEF-001"],
        "target_instruments": [PEER, CONTROL],
    },
    {
        "hypothesis_id": "LH-H-025",
        "experiment_id": "LH-E-025",
        "execution_id": "LH-X-025",
        "evidence_id": "LH-V-025",
        "claim_id": "LH-C-025",
        "category": "C",
        "category_label": "price_only_simulator_research",
        "proposition": (
            "On the stored common sessions from the later of the two first stored sessions, "
            "with the category C contribution of 1000 US dollars, a cost rate of 0.001, and "
            "a cash interest rate of 0, immediate VWRA, immediate CNDX, one static equal-cash "
            "mix, one price-only 252-session relative-momentum rule, and the simulator paths "
            "that already exist for calendar rebalancing, threshold rebalancing, and "
            "cash-flow-only allocation have reconciled price-return terminal wealth. "
            "A bounded VWRA-to-CNDX rotation is not implemented. A higher terminal wealth "
            "is not economically useful or forward-validated. The path is not a total return "
            "and not an SGD investor return."
        ),
        "economic_rationale": (
            "The simulator already accounts for whole units and explicit costs. "
            "It does not invent a distribution, a fund expense, or a currency conversion."
        ),
        "expected_mechanism": "No macroeconomic state enters the orders.",
        "expected_direction": "not prejudged",
        "horizon": "the common stored sessions from the later listing start",
        "falsification_criteria": (
            "The category C rule leaves a greater alternative inconclusive and rejects "
            "an alternative that is not greater. A path that would need a manufactured "
            "session, a total return, or a foreign-exchange rate is blocked and stores "
            "no wealth."
        ),
        "alternative_explanations": [
            "Split-adjusted closes omit distributions.",
            "Whole-unit residual cash changes the invested amount.",
            "A January rebalance records forgone units outside terminal wealth.",
        ],
        "relevant_indicators": [],
        "relevant_methodologies": ["long-horizon-simulator-1"],
        "target_instruments": [CONTROL, PEER],
    },
)

DEPENDENCIES: tuple[dict[str, object], ...] = (
    {
        "dependency_id": "LH-D-044",
        "experiment_id": "LH-E-019",
        "relation": "shares_methodology",
        "right_kind": "methodology",
        "right_id": STORED_METHOD_SPECIFICATION,
        "instrument_id": None,
        "methodology_id": STORED_METHOD_SPECIFICATION,
        "period_start": None,
        "detail": "The census reads stored method points. This is not independent confirmation.",
    },
    {
        "dependency_id": "LH-D-045",
        "experiment_id": "LH-E-020",
        "relation": "shares_instrument",
        "right_kind": "instrument",
        "right_id": PEER,
        "instrument_id": PEER,
        "methodology_id": None,
        "period_start": None,
        "detail": "The CNDX battery uses CNDX month-ends. This is not independent confirmation.",
    },
    {
        "dependency_id": "LH-D-046",
        "experiment_id": "LH-E-020",
        "relation": "shares_methodology",
        "right_kind": "methodology",
        "right_id": "ATLAS-DEF-001",
        "instrument_id": None,
        "methodology_id": "ATLAS-DEF-001",
        "period_start": None,
        "detail": "The battery reads stored atlas features. This is not independent confirmation.",
    },
    {
        "dependency_id": "LH-D-047",
        "experiment_id": "LH-E-021",
        "relation": "shares_methodology",
        "right_kind": "methodology",
        "right_id": "ATLAS-DEF-001",
        "instrument_id": None,
        "methodology_id": "ATLAS-DEF-001",
        "period_start": None,
        "detail": "The eight pairs are unchanged. This is not independent confirmation.",
    },
    {
        "dependency_id": "LH-D-048",
        "experiment_id": "LH-E-022",
        "relation": "overlaps_period",
        "right_kind": "experiment",
        "right_id": "LH-E-020",
        "instrument_id": None,
        "methodology_id": None,
        "period_start": None,
        "detail": (
            "The sequence uses the same CNDX month-ends as LH-E-020. "
            "The overlap is not independent confirmation."
        ),
    },
    {
        "dependency_id": "LH-D-049",
        "experiment_id": "LH-E-023",
        "relation": "shares_instrument",
        "right_kind": "instrument",
        "right_id": PEER,
        "instrument_id": PEER,
        "methodology_id": None,
        "period_start": MATCHED_NOT_BEFORE.isoformat(),
        "detail": "The matched sample includes CNDX. This is not independent confirmation.",
    },
    {
        "dependency_id": "LH-D-050",
        "experiment_id": "LH-E-023",
        "relation": "shares_instrument",
        "right_kind": "instrument",
        "right_id": CONTROL,
        "instrument_id": CONTROL,
        "methodology_id": None,
        "period_start": MATCHED_NOT_BEFORE.isoformat(),
        "detail": "The matched sample includes VWRA. This is not independent confirmation.",
    },
    {
        "dependency_id": "LH-D-051",
        "experiment_id": "LH-E-023",
        "relation": "overlaps_period",
        "right_kind": "experiment",
        "right_id": "LH-E-016",
        "instrument_id": None,
        "methodology_id": None,
        "period_start": MATCHED_NOT_BEFORE.isoformat(),
        "detail": (
            "The matched window overlaps the inspected VWRA discovery and the EIMI comparison. "
            "It is not an untouched holdout and not independent confirmation."
        ),
    },
    {
        "dependency_id": "LH-D-052",
        "experiment_id": "LH-E-023",
        "relation": "matched_control",
        "right_kind": "methodology",
        "right_id": "ETF-PROT-001",
        "instrument_id": None,
        "methodology_id": "ETF-PROT-001",
        "period_start": MATCHED_NOT_BEFORE.isoformat(),
        "detail": (
            "The price control is the stored VWRA trailing 252-session return and the "
            "stored CNDX relative-performance feature. This is not independent confirmation."
        ),
    },
    {
        "dependency_id": "LH-D-053",
        "experiment_id": "LH-E-024",
        "relation": "shares_methodology",
        "right_kind": "methodology",
        "right_id": "EVT-DEF-001",
        "instrument_id": None,
        "methodology_id": "EVT-DEF-001",
        "period_start": None,
        "detail": (
            "EVT-DEF-001 is not edited. The pairwise 0.10 excess over 126 sessions "
            "uses the magnitude already frozen. This is not independent confirmation."
        ),
    },
    {
        "dependency_id": "LH-D-054",
        "experiment_id": "LH-E-025",
        "relation": "same_contribution_schedule",
        "right_kind": "experiment",
        "right_id": "LH-E-018",
        "instrument_id": CONTROL,
        "methodology_id": None,
        "period_start": MATCHED_NOT_BEFORE.isoformat(),
        "detail": (
            "Contributions, the cost rate, cash interest, and the later-listing start follow "
            "LH-E-018 where the simulator can represent a second US-dollar listing. "
            "This is not independent confirmation. LH-X-001 and LH-X-018 are not rewritten."
        ),
    },
)


def specification_document() -> dict[str, object]:
    """The hashed preregistration. It has no CNDX coefficient and no wealth number."""
    return {
        "specification_id": SPECIFICATION_ID,
        "version": SPECIFICATION_VERSION,
        "publication_allowed": PUBLICATION_ALLOWED,
        "not_macroeconomic_investment_intelligence": True,
        "peer": PEER,
        "control": CONTROL,
        "pair": PAIR,
        "matched_not_before_rule": (
            "The later of the two first stored sessions. VWRA's first stored session "
            "is 2019-07-25. A CNDX session before the first stored CNDX session is refused."
        ),
        "matched_not_before": MATCHED_NOT_BEFORE.isoformat(),
        "tolerance_days": TOLERANCE_DAYS,
        "tolerance_tie": "closest calendar-day gap, then the earlier CNDX session",
        "anchor_order": "VWRA month-ends in date order, each CNDX anchor used once",
        "session_steps": dict(SESSION_STEPS),
        "advance_minimum": ADVANCE_MINIMUM,
        "decline_maximum": DECLINE_MAXIMUM,
        "primary_steps": PRIMARY_STEPS,
        "divergence_steps": DIVERGENCE_STEPS,
        "divergence_excess": DIVERGENCE_EXCESS,
        "divergence_source": (
            "The pairwise rule is excess of at least 0.10 over 126 sessions, the same "
            "magnitude frozen for EIMI before any score. EVT-DEF-001 and EVT-DEF-002 "
            "are not edited."
        ),
        "exclusive_classes": list(EXCLUSIVE_CLASSES),
        "exclusive_rename": EXCLUSIVE_RENAME,
        "exclusive_class_rule": (
            "relative_class from ETF-PROT-001, boundaries at zero, labels renamed for CNDX"
        ),
        "relative_outperformance_is_not_an_advance": True,
        "case_classes": list(CASE_CLASSES),
        "case_class_rules": {
            "cndx_ahead": "excess at least 0.10 over 126 sessions",
            "vwra_ahead": "excess at most -0.10 over 126 sessions",
            "both_advance": "each leg at least 0.10",
            "both_decline": "each leg at most -0.10",
            "cndx_up_vwra_down": "CNDX return strictly positive and VWRA return strictly negative",
            "cndx_down_vwra_up": "CNDX return strictly negative and VWRA return strictly positive",
            "leadership_reversal": (
                "previous and current excess have opposite strict signs and the current "
                "absolute excess is at least 0.10"
            ),
            "approximately_neutral": "absolute 126-session excess strictly below 0.10",
        },
        "classes_may_overlap": True,
        "unemployment_feature": UNEMPLOYMENT_FEATURE,
        "real_gdp_feature": REAL_GDP_FEATURE,
        "association_differs_when": "Spearman coefficients have opposite strict signs",
        "price_control": PRICE_CONTROL,
        "relative_control": RELATIVE_CONTROL,
        "excess_survives_price_control_when": (
            "The absolute partial Spearman of the excess after VWRA:trailing_return_252 "
            "is strictly greater than the absolute Spearman of "
            "CNDX:relative_performance_vs_vwra_252 against the same excess. "
            "If neither unemployment nor real GDP survives, the relative result is "
            "structural exposure or price momentum, not macroeconomic information."
        ),
        "partial_association": (
            "Pearson of residuals after a linear projection on the control, and Spearman "
            "of rank residuals after the same projection. Both controls are scored. "
            "Neither is selected after the coefficient is seen."
        ),
        "sequence": {
            key: list(value) if isinstance(value, tuple) else value
            for key, value in SEQUENCE.items()
        },
        "sequence_implementation": (
            "sequence_flags treats momentum as strictly greater than zero. "
            "The ETF-PROT-001 binary threshold of 0.05 for trailing_return_63 is a "
            "different object and is not applied to this sequence."
        ),
        "logistic_decision_points": LOGISTIC_DECISION_POINTS,
        "logistic_non_overlapping": LOGISTIC_NON_OVERLAPPING,
        "non_overlap_session_gap": NON_OVERLAP_SESSION_GAP,
        "intersection_pairs": [dict(row) for row in INTERSECTION_PAIRS],
        "fx_intersections": "blocked_no_foreign_exchange",
        "price_type": "adjusted_close",
        "price_label": (
            "split-adjusted close, not a distribution-adjusted total return, "
            "not issuer NAV, not the Nasdaq-100 index, and not an SGD investor return"
        ),
        "forward_fill": "refused",
        "total_return": "not_represented",
        "portfolio": {
            "contribution_amount": PILOT_CONTRIBUTION,
            "transaction_cost_rate": PILOT_COST_RATE,
            "cash_interest_rate": PILOT_INTEREST_RATE,
            "start_rule": "no earlier than both instruments' first stored sessions",
            "contribution_schedule": (
                "1000 USD on the first common stored session of each calendar month"
            ),
            "paths": list(IMPLEMENTED_PORTFOLIO_PATHS),
            "blocked_paths": list(BLOCKED_PORTFOLIO_PATHS),
            "blocked_reason": (
                "No stored policy sells VWRA to buy CNDX, or the reverse, under a bound. "
                "Relative momentum does not sell. The rotation is not implemented."
            ),
            "static_mix": (
                "On a contribution, each name is bought with whole units up to half of "
                "the cash then available, CNDX then VWRA. January contribution sessions "
                "then rebalance to equal market value with the existing simulator rule."
            ),
            "calendar_rebalance": (
                "CalendarRebalancePolicy with equal weights, rebalance sessions limited "
                "to January contribution sessions. The policy already exists."
            ),
            "threshold_rebalance": (
                "ThresholdRebalancePolicy with equal weights and a band of 0.10. "
                "The band is the existing certification band and is not fit to CNDX."
            ),
            "cash_flow_only": (
                "CashFlowOnlyPolicy with equal weights. New cash buys the underweight name. "
                "No sale is made."
            ),
            "momentum_rule": (
                "On a contribution, compare 252-session simple returns using closes "
                "strictly before the session. The higher return receives the contribution. "
                "A tie, or a missing lookback on either name, buys VWRA. No sale is made. "
                "No macroeconomic state is read. The same-session close is not a signal."
            ),
            "macro_states_in_simulator": False,
            "catalogue_scenarios_executed": 0,
            "higher_terminal_wealth": "inconclusive_not_economically_useful",
        },
        "finding_classes": list(FINDING_CLASSES),
        "forbidden_promotions": list(FORBIDDEN_PROMOTIONS),
        "hypotheses": [dict(row) for row in HYPOTHESES],
        "dependencies": [dict(row) for row in DEPENDENCIES],
        "point_in_time_eligible": [],
        "independently_validated": [],
        "inspected_history_is_not_a_holdout": True,
        "earlier_programmes_in_the_multiple_testing_note": [
            "VWRA-DISCOVERY-001",
            "EIMI-VWRA-COMPARISON-001",
        ],
    }


def specification_hash() -> str:
    return sha256_document(specification_document())


def excess_survives_price_control(
    partial: Decimal | None,
    control_spearman: Decimal | None,
) -> bool:
    """Predeclared survival rule. A missing coefficient does not survive."""
    if partial is None or control_spearman is None:
        return False
    return abs(partial) > abs(control_spearman)


def relative_classification(unemployment_survives: bool, gdp_survives: bool) -> str:
    """Structural exposure when neither named excess partial beats the price control."""
    if unemployment_survives or gdp_survives:
        return "excess_partial_survives_price_control"
    return "structural_exposure_or_price_momentum"


def assert_not_promoted_status(status: str) -> None:
    assert_not_promoted(status)
    if status in FORBIDDEN_PROMOTIONS:
        raise ValueError(status)


def matched_floor(cndx_first: date, vwra_first: date) -> date:
    """The later listing start. Earlier sessions are not manufactured."""
    return max(cndx_first, vwra_first)


def refuse_before_listing(session: date, first: date, symbol: str) -> None:
    """A session before the first stored close is not filled in."""
    if session < first:
        raise ValueError(
            f"{symbol} {session.isoformat()} is before the first stored session {first.isoformat()}"
        )
