"""Frozen EIMI and VWRA comparison. This module does not read prices or write rows.

The literals below are the preregistration. A later change is a new version.
They are not chosen from an EIMI coefficient.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from aqil_research.long_horizon.etf_protocol.rules import relative_class
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
from aqil_research.long_horizon.status import assign_category_c_status
from aqil_research.long_horizon.vwra_discovery.specification import (
    ADVANCE_MINIMUM,
    COMPARISON_FINDING,
    DECLINE_MAXIMUM,
    INTERSECTION_PAIRS,
    LOGISTIC_DECISION_POINTS,
    LOGISTIC_NON_OVERLAPPING,
    NON_OVERLAP_SESSION_GAP,
    SEQUENCE,
    VWRA_FIRST_SESSION,
)

SPECIFICATION_ID = "EIMI-VWRA-COMPARISON-001"
SPECIFICATION_VERSION = 1
PUBLICATION_ALLOWED = False
MATCHED_NOT_BEFORE = VWRA_FIRST_SESSION
TOLERANCE_DAYS = PEER_TOLERANCE_DAYS
DIVERGENCE_STEPS = 126
DIVERGENCE_EXCESS = "0.10"
PRIMARY_STEPS = 126
UNEMPLOYMENT_FEATURE = "bls.ln.LNS14000000:year_on_year"
REAL_GDP_FEATURE = "bea.nipa.T10106.A191RX:trailing_standardisation"
PRICE_CONTROL = "VWRA:trailing_return_252"
RELATIVE_CONTROL = f"EIMI:{PRIMARY_CONTROL}"
MOMENTUM_STEPS = 252
MOMENTUM_BASELINE = "VWRA"
STATIC_MIX = "equal_cash_vwra_eimi_january_equal_value"
REPRODUCTION_COMMAND = "uv run python -m aqil_research.long_horizon.vwra_discovery.compare"
STORED_METHOD_SPECIFICATION = "VWRA-DISCOVERY-001"
EXCLUSIVE_CLASSES = (
    "eimi_ahead_both_positive",
    "eimi_positive_vwra_negative",
    "both_negative_eimi_declines_less",
    "vwra_ahead",
    "no_sign",
)
CASE_CLASSES = (
    "eimi_ahead",
    "vwra_ahead",
    "both_advance",
    "both_decline",
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
PROTECTED_THROUGH = 11

HYPOTHESES: tuple[dict[str, object], ...] = (
    {
        "hypothesis_id": "LH-H-012",
        "experiment_id": "LH-E-012",
        "execution_id": "LH-X-012",
        "evidence_id": "LH-V-012",
        "claim_id": "LH-C-012",
        "category": "B",
        "category_label": "retrospective_economic_research",
        "proposition": (
            "The 26 registered methods already stored under VWRA-DISCOVERY-001 have "
            "a retrospective coverage census. Component counts are not distinct dates. "
            "Point-in-time methodology output remains zero. The census is not an "
            "EIMI score and not an allocation."
        ),
        "economic_rationale": (
            "A sample-end diagnostic and a monthly timeline answer different questions. "
            "The census reads the stored points and does not delete them."
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
        "hypothesis_id": "LH-H-013",
        "experiment_id": "LH-E-013",
        "execution_id": "LH-X-013",
        "evidence_id": "LH-V-013",
        "claim_id": "LH-C-013",
        "category": "B",
        "category_label": "retrospective_economic_research",
        "proposition": (
            "On EIMI month-ends, stored atlas features and reconstructed method output "
            "have a descriptive association with the later 126-session return. An advance "
            "is a stored return of at least 0.10. A decline is a stored return of at most "
            "-0.10. Logistic and probit are fit only when the frozen floors of 60 decision "
            "points and 15 non-overlapping 126-session keeps are both met."
        ),
        "economic_rationale": (
            "The battery is the VWRA discovery battery with the symbol changed to EIMI. "
            "The thresholds are not retuned."
        ),
        "expected_mechanism": (
            "Spearman and Pearson use the anchor set. A missing forward session is censored. "
            "No later close is filled."
        ),
        "expected_direction": "not prejudged",
        "horizon": "126 sessions after the EIMI month-end",
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
        "target_instruments": ["EIMI"],
    },
    {
        "hypothesis_id": "LH-H-014",
        "experiment_id": "LH-E-014",
        "execution_id": "LH-X-014",
        "evidence_id": "LH-V-014",
        "claim_id": "LH-C-014",
        "category": "B",
        "category_label": "retrospective_economic_research",
        "proposition": (
            "The same eight economically named pairs are scored on EIMI when both "
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
        "horizon": "126 sessions after the EIMI month-end",
        "falsification_criteria": (
            "An absent input is refused. No substitute series is introduced."
        ),
        "alternative_explanations": [
            "The two legs can move together because they share a business-cycle factor.",
        ],
        "relevant_indicators": ["the eight named pairs"],
        "relevant_methodologies": ["ATLAS-DEF-001"],
        "target_instruments": ["EIMI"],
    },
    {
        "hypothesis_id": "LH-H-015",
        "experiment_id": "LH-E-015",
        "execution_id": "LH-X-015",
        "evidence_id": "LH-V-015",
        "claim_id": "LH-C-015",
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
            "The sequence is SEQ-INF-MOM-001. Substituting 0.05 would retune the stored VWRA rule."
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
        "target_instruments": ["EIMI"],
    },
    {
        "hypothesis_id": "LH-H-016",
        "experiment_id": "LH-E-016",
        "execution_id": "LH-X-016",
        "evidence_id": "LH-V-016",
        "claim_id": "LH-C-016",
        "category": "B",
        "category_label": "retrospective_economic_research",
        "proposition": (
            "On matched month-ends at or after 2019-07-25, within five calendar days, "
            "the outcome is the EIMI session-step return minus the VWRA session-step "
            "return. The same economic and methodology states are applied to both "
            "returns and to the excess. Unemployment year-on-year and real-GDP trailing "
            "standardisation are remeasured on that matched sample. A predeclared price "
            "control accounts for common equity exposure. The excess model is not chosen "
            "by comparing two absolute models."
        ),
        "economic_rationale": (
            "EIMI is an emerging-market overweight relative to VWRA, not an independent "
            "diversifier. Both listings are US-dollar London lines. Relative "
            "outperformance is not a positive absolute return."
        ),
        "expected_mechanism": (
            "A missing session is censored. No foreign-exchange rate is invented. "
            "Associations differ when the Spearman coefficients have opposite signs."
        ),
        "expected_direction": "not prejudged",
        "horizon": "21, 63, 126, 252, 504, and 756 stored sessions",
        "falsification_criteria": (
            "A state after the earlier anchor is dropped. A Benjamini-Hochberg flag "
            "cannot promote a claim. Currency intersections stay blocked while "
            "fx_observations is empty."
        ),
        "alternative_explanations": [
            "The overlap has already been inspected and is not an untouched holdout.",
            "Common equity exposure can produce a similar absolute association.",
        ],
        "relevant_indicators": [
            UNEMPLOYMENT_FEATURE,
            REAL_GDP_FEATURE,
            PRICE_CONTROL,
            RELATIVE_CONTROL,
        ],
        "relevant_methodologies": ["ETF-PROT-001", "ATLAS-DEF-001"],
        "target_instruments": ["EIMI", "VWRA"],
    },
    {
        "hypothesis_id": "LH-H-017",
        "experiment_id": "LH-E-017",
        "execution_id": "LH-X-017",
        "evidence_id": "LH-V-017",
        "claim_id": "LH-C-017",
        "category": "B",
        "category_label": "retrospective_economic_research",
        "proposition": (
            "Matched 126-session episodes are counted for EIMI ahead, VWRA ahead, "
            "both advance, both decline, leadership reversal, and approximately neutral. "
            "The new divergence magnitude is 0.10 excess over 126 sessions, mirrored "
            "from the existing 0.10 magnitude before any score. Non-divergent anchors "
            "stay in the neutral class. Each class stores counts and the pre-event states."
        ),
        "economic_rationale": (
            "EVT-DEF-001 relative outperformance uses a 252-session peer median and "
            "three peers. That object is not edited. The pairwise rule is the mirror."
        ),
        "expected_mechanism": (
            "Classes may overlap. The five exclusive classes at zero are a separate "
            "partition and are not these episode labels."
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
        "target_instruments": ["EIMI", "VWRA"],
    },
    {
        "hypothesis_id": "LH-H-018",
        "experiment_id": "LH-E-018",
        "execution_id": "LH-X-018",
        "evidence_id": "LH-V-018",
        "claim_id": "LH-C-018",
        "category": "C",
        "category_label": "price_only_simulator_research",
        "proposition": (
            "On the stored common sessions from 2019-07-25, with the category C "
            "contribution of 1000 US dollars, a cost rate of 0.001, and a cash interest "
            "rate of 0, immediate VWRA, immediate EIMI, one static equal-cash mix, and "
            "one price-only 252-session relative-momentum rule have reconciled price-return "
            "terminal wealth. A higher terminal wealth is not economically useful or "
            "forward-validated. The path is not a total return and not an SGD investor return."
        ),
        "economic_rationale": (
            "The simulator already accounts for whole units and explicit costs. "
            "It does not invent a distribution, a fund expense, or a currency conversion."
        ),
        "expected_mechanism": "No macroeconomic state enters the orders.",
        "expected_direction": "not prejudged",
        "horizon": "the common stored sessions from the category C start date",
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
        "target_instruments": ["VWRA", "EIMI"],
    },
)

DEPENDENCIES: tuple[dict[str, object], ...] = (
    {
        "dependency_id": "LH-D-033",
        "experiment_id": "LH-E-012",
        "relation": "shares_methodology",
        "right_kind": "methodology",
        "right_id": STORED_METHOD_SPECIFICATION,
        "instrument_id": None,
        "methodology_id": STORED_METHOD_SPECIFICATION,
        "period_start": None,
        "detail": "The census reads stored method points. This is not independent confirmation.",
    },
    {
        "dependency_id": "LH-D-034",
        "experiment_id": "LH-E-013",
        "relation": "shares_instrument",
        "right_kind": "instrument",
        "right_id": "EIMI",
        "instrument_id": "EIMI",
        "methodology_id": None,
        "period_start": "2016-11-03",
        "detail": "The EIMI battery uses EIMI month-ends. This is not independent confirmation.",
    },
    {
        "dependency_id": "LH-D-035",
        "experiment_id": "LH-E-013",
        "relation": "shares_methodology",
        "right_kind": "methodology",
        "right_id": "ATLAS-DEF-001",
        "instrument_id": None,
        "methodology_id": "ATLAS-DEF-001",
        "period_start": None,
        "detail": "The battery reads stored atlas features. This is not independent confirmation.",
    },
    {
        "dependency_id": "LH-D-036",
        "experiment_id": "LH-E-014",
        "relation": "shares_methodology",
        "right_kind": "methodology",
        "right_id": "ATLAS-DEF-001",
        "instrument_id": None,
        "methodology_id": "ATLAS-DEF-001",
        "period_start": None,
        "detail": "The eight pairs are unchanged. This is not independent confirmation.",
    },
    {
        "dependency_id": "LH-D-037",
        "experiment_id": "LH-E-015",
        "relation": "overlaps_period",
        "right_kind": "experiment",
        "right_id": "LH-E-013",
        "instrument_id": None,
        "methodology_id": None,
        "period_start": "2016-11-30",
        "detail": (
            "The sequence uses the same EIMI month-ends as LH-E-013. "
            "The overlap is not independent confirmation."
        ),
    },
    {
        "dependency_id": "LH-D-038",
        "experiment_id": "LH-E-016",
        "relation": "shares_instrument",
        "right_kind": "instrument",
        "right_id": "EIMI",
        "instrument_id": "EIMI",
        "methodology_id": None,
        "period_start": MATCHED_NOT_BEFORE.isoformat(),
        "detail": "The matched sample includes EIMI. This is not independent confirmation.",
    },
    {
        "dependency_id": "LH-D-039",
        "experiment_id": "LH-E-016",
        "relation": "shares_instrument",
        "right_kind": "instrument",
        "right_id": "VWRA",
        "instrument_id": "VWRA",
        "methodology_id": None,
        "period_start": MATCHED_NOT_BEFORE.isoformat(),
        "detail": "The matched sample includes VWRA. This is not independent confirmation.",
    },
    {
        "dependency_id": "LH-D-040",
        "experiment_id": "LH-E-016",
        "relation": "overlaps_period",
        "right_kind": "experiment",
        "right_id": "LH-E-009",
        "instrument_id": None,
        "methodology_id": None,
        "period_start": MATCHED_NOT_BEFORE.isoformat(),
        "detail": (
            "The matched window overlaps the inspected VWRA discovery. "
            "It is not an untouched holdout and not independent confirmation."
        ),
    },
    {
        "dependency_id": "LH-D-041",
        "experiment_id": "LH-E-016",
        "relation": "matched_control",
        "right_kind": "methodology",
        "right_id": "ETF-PROT-001",
        "instrument_id": None,
        "methodology_id": "ETF-PROT-001",
        "period_start": MATCHED_NOT_BEFORE.isoformat(),
        "detail": (
            "The price control is the stored VWRA trailing 252-session return and the "
            "stored relative-performance feature. This is not independent confirmation."
        ),
    },
    {
        "dependency_id": "LH-D-042",
        "experiment_id": "LH-E-017",
        "relation": "shares_methodology",
        "right_kind": "methodology",
        "right_id": "EVT-DEF-001",
        "instrument_id": None,
        "methodology_id": "EVT-DEF-001",
        "period_start": None,
        "detail": (
            "EVT-DEF-001 is not edited. The pairwise 0.10 excess over 126 sessions "
            "mirrors an existing magnitude. This is not independent confirmation."
        ),
    },
    {
        "dependency_id": "LH-D-043",
        "experiment_id": "LH-E-018",
        "relation": "same_contribution_schedule",
        "right_kind": "experiment",
        "right_id": "LH-E-001",
        "instrument_id": "VWRA",
        "methodology_id": None,
        "period_start": MATCHED_NOT_BEFORE.isoformat(),
        "detail": (
            "Contributions, the start date, and the fee convention follow LH-E-001 "
            "where the simulator can represent a second US-dollar listing. "
            "This is not independent confirmation. LH-X-001 is not rewritten."
        ),
    },
)


def specification_document() -> dict[str, object]:
    """The hashed preregistration. It has no EIMI coefficient and no wealth number."""
    return {
        "specification_id": SPECIFICATION_ID,
        "version": SPECIFICATION_VERSION,
        "publication_allowed": PUBLICATION_ALLOWED,
        "not_macroeconomic_investment_intelligence": True,
        "matched_not_before": MATCHED_NOT_BEFORE.isoformat(),
        "tolerance_days": TOLERANCE_DAYS,
        "tolerance_tie": "closest calendar-day gap, then the earlier EIMI session",
        "anchor_order": "VWRA month-ends in date order, each EIMI anchor used once",
        "session_steps": dict(SESSION_STEPS),
        "advance_minimum": ADVANCE_MINIMUM,
        "decline_maximum": DECLINE_MAXIMUM,
        "primary_steps": PRIMARY_STEPS,
        "divergence_steps": DIVERGENCE_STEPS,
        "divergence_excess": DIVERGENCE_EXCESS,
        "divergence_source": (
            "EVT-DEF-001 relative outperformance already uses a 0.10 excess magnitude "
            "over 252 sessions against a peer median. This pairwise rule mirrors 0.10 "
            "and applies it to the 126-session EIMI minus VWRA return. EVT-DEF-001 "
            "and EVT-DEF-002 are not edited."
        ),
        "exclusive_classes": list(EXCLUSIVE_CLASSES),
        "exclusive_class_rule": "relative_class from ETF-PROT-001, boundaries at zero",
        "relative_outperformance_is_not_an_advance": True,
        "case_classes": list(CASE_CLASSES),
        "case_state_features": [
            {"name": name, "feature_id": feature_id} for name, feature_id in CASE_STATE_FEATURES
        ],
        "leadership_reversal": (
            "The previous matched excess and the current excess have opposite strict "
            "signs, and the current absolute excess is at least 0.10. A missing previous "
            "excess is not a reversal."
        ),
        "approximately_neutral": "absolute 126-session excess strictly below 0.10",
        "non_divergent_anchors_are_kept": True,
        "unemployment_feature": UNEMPLOYMENT_FEATURE,
        "real_gdp_feature": REAL_GDP_FEATURE,
        "association_differs_when": "Spearman coefficients have opposite strict signs",
        "price_control": PRICE_CONTROL,
        "relative_control": RELATIVE_CONTROL,
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
        "sequence_on_the_matched_sample": (
            "Inflation is the shared CPI year-on-year print on or before the earlier "
            "anchor. EIMI is scored with EIMI trailing_return_63. VWRA is scored with "
            "VWRA trailing_return_63. The excess uses EIMI trailing_return_63 as the "
            "momentum leg. A price leg in one of the eight pairs, trailing_return_63 "
            "or drawdown_252, uses the EIMI value when the outcome is the excess and "
            "the VWRA value when the outcome is the VWRA return. Relative momentum "
            "remains the separate stored control."
        ),
        "logistic_decision_points": LOGISTIC_DECISION_POINTS,
        "logistic_non_overlapping": LOGISTIC_NON_OVERLAPPING,
        "non_overlap_session_gap": NON_OVERLAP_SESSION_GAP,
        "intersection_pairs": [dict(row) for row in INTERSECTION_PAIRS],
        "fx_intersections": "blocked_no_foreign_exchange",
        "price_type": "adjusted_close",
        "price_label": "split-adjusted close, not a total return and not an SGD return",
        "forward_fill": "refused",
        "portfolio": {
            "contribution_amount": PILOT_CONTRIBUTION,
            "transaction_cost_rate": PILOT_COST_RATE,
            "cash_interest_rate": PILOT_INTEREST_RATE,
            "start_date": MATCHED_NOT_BEFORE.isoformat(),
            "contribution_schedule": (
                "1000 USD on the first common stored session of each calendar month"
            ),
            "paths": [
                "immediate_vwra",
                "immediate_eimi",
                STATIC_MIX,
                "contribution_to_higher_trailing_return_252",
            ],
            "static_mix": (
                "On a contribution, each name is bought with whole units up to half of "
                "the cash then available, EIMI then VWRA. January contribution sessions "
                "then rebalance to equal market value with the existing simulator rule."
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
        "comparison_finding": COMPARISON_FINDING,
        "hypotheses": [dict(row) for row in HYPOTHESES],
        "dependencies": [dict(row) for row in DEPENDENCIES],
        "point_in_time_eligible": [],
        "independently_validated": [],
        "inspected_history_is_not_a_holdout": True,
    }


def specification_hash() -> str:
    return sha256_document(specification_document())


def assert_not_promoted(status: str) -> None:
    if status in FORBIDDEN_PROMOTIONS:
        raise ValueError(f"{status} is not allowed")


def mapped_status(comparison_status: str) -> str:
    """Store a comparison status in a finding class the registry already allows."""
    if comparison_status in FINDING_CLASSES and comparison_status != "no_incremental_information":
        return comparison_status
    mapped = COMPARISON_FINDING[comparison_status]
    assert_not_promoted(mapped)
    return mapped


def exclusive_class(eimi_return: Decimal, vwra_return: Decimal) -> str:
    """The frozen five-class partition. Boundaries stay at zero."""
    label = relative_class(eimi_return, vwra_return)
    if label not in EXCLUSIVE_CLASSES:
        raise ValueError(f"unexpected relative class {label}")
    return label


def excess_return(eimi_return: Decimal | None, vwra_return: Decimal | None) -> Decimal | None:
    """Censor a missing leg. Do not fill it with zero."""
    if eimi_return is None or vwra_return is None:
        return None
    return eimi_return - vwra_return


def is_advance(value: Decimal) -> bool:
    return value >= Decimal(ADVANCE_MINIMUM)


def is_decline(value: Decimal) -> bool:
    return value <= Decimal(DECLINE_MAXIMUM)


def divergent_eimi(excess: Decimal) -> bool:
    return excess >= Decimal(DIVERGENCE_EXCESS)


def divergent_vwra(excess: Decimal) -> bool:
    return excess <= -Decimal(DIVERGENCE_EXCESS)


def approximately_neutral(excess: Decimal) -> bool:
    return abs(excess) < Decimal(DIVERGENCE_EXCESS)


def leadership_reversal(previous: Decimal | None, current: Decimal | None) -> bool:
    """Opposite strict signs, and the current excess meets the frozen magnitude."""
    if previous is None or current is None or previous == 0 or current == 0:
        return False
    if abs(current) < Decimal(DIVERGENCE_EXCESS):
        return False
    return (previous > 0) != (current > 0)


def association_relation(left: Decimal | None, right: Decimal | None) -> str:
    """Predeclared comparison of two Spearman coefficients. A null is not a difference."""
    if left is None or right is None:
        return "not_comparable"
    if left == 0 or right == 0:
        return "zero_coefficient"
    if (left > 0) != (right > 0):
        return "signs_differ"
    return "signs_agree"


def match_month_ends(
    vwra_anchors: tuple[tuple[str, date], ...],
    eimi_anchors: tuple[tuple[str, date], ...],
) -> tuple[tuple[str, date, str, date, int], ...]:
    """Pair month-ends inside the frozen tolerance. Dates before 2019-07-25 are excluded."""
    unused = set(range(len(eimi_anchors)))
    paired: list[tuple[str, date, str, date, int]] = []
    for vwra_id, vwra_day in vwra_anchors:
        if vwra_day < MATCHED_NOT_BEFORE:
            continue
        candidates: list[tuple[int, date, int]] = []
        for index in unused:
            eimi_id, eimi_day = eimi_anchors[index]
            del eimi_id
            if eimi_day < MATCHED_NOT_BEFORE:
                continue
            gap = abs((vwra_day - eimi_day).days)
            if gap <= TOLERANCE_DAYS:
                candidates.append((gap, eimi_day, index))
        if not candidates:
            continue
        candidates.sort()
        _gap, _day, chosen = candidates[0]
        unused.remove(chosen)
        eimi_id, eimi_day = eimi_anchors[chosen]
        paired.append((vwra_id, vwra_day, eimi_id, eimi_day, candidates[0][0]))
    return tuple(paired)


def shared_date(vwra_day: date, eimi_day: date) -> date:
    """The earlier session. A state after this date is not used for the pair."""
    if vwra_day <= eimi_day:
        return vwra_day
    return eimi_day


def portfolio_claim_status(
    *,
    reconciled: bool,
    passive_terminal: Decimal,
    alternatives: dict[str, Decimal],
) -> str:
    """Apply the category C rule to each alternative. A greater path stays inconclusive."""
    if not reconciled or not alternatives:
        return "insufficient_data"
    statuses = [
        assign_category_c_status(
            reconciled=True,
            alternative_terminal=value,
            passive_terminal=passive_terminal,
        )
        for value in alternatives.values()
    ]
    if "inconclusive" in statuses:
        status = "inconclusive"
    else:
        status = "rejected"
    assert_not_promoted(status)
    return status


def portfolio_statement(status: str, wealth: dict[str, str]) -> str:
    parts = ", ".join(f"{name} {value}" for name, value in sorted(wealth.items()))
    return (
        f"The price-only comparison is {status}. Terminal wealth values are {parts}. "
        "These are split-adjusted US-dollar price paths with the category C cost rate. "
        "They are not total returns, not SGD investor returns, not economically useful, "
        "and not forward-validated."
    )
