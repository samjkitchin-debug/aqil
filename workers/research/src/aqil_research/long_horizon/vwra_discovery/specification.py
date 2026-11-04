"""Frozen VWRA discovery rules. This module does not read prices or write rows.

The literals below are the preregistration. A later change is a new version.
They are not retuned after a VWRA coefficient is seen.
"""

from __future__ import annotations

from datetime import date

from aqil_research.long_horizon.money import sha256_document

SPECIFICATION_ID = "VWRA-DISCOVERY-001"
SPECIFICATION_VERSION = 1
VWRA_FIRST_SESSION = date(2019, 7, 25)
PRIMARY_HORIZON = "6m"
PRIMARY_STEPS = 126
ADVANCE_MINIMUM = "0.10"
DECLINE_MAXIMUM = "-0.10"
PRE_EVENT_STEPS = (21, 63, 126, 252)
LOGISTIC_DECISION_POINTS = 60
LOGISTIC_NON_OVERLAPPING = 15
NON_OVERLAP_SESSION_GAP = 126
DRAWDOWN_SPLIT = "-0.10"
PUBLICATION_ALLOWED = False

FINDING_CLASSES = (
    "descriptive",
    "retrospective_exploratory",
    "inconclusive",
    "insufficient_sample",
    "rejected",
)
FORBIDDEN_PROMOTIONS = (
    "statistically_supported",
    "economically_useful",
    "forward_validated",
)
COMPARISON_FINDING = {
    "insufficient_data": "insufficient_sample",
    "no_incremental_information": "retrospective_exploratory",
    "rejected": "rejected",
    "inconclusive": "inconclusive",
}

PROTECTED_HYPOTHESES = frozenset({f"LH-H-{index:03d}" for index in range(1, 8)})
PROTECTED_EXPERIMENTS = frozenset({f"LH-E-{index:03d}" for index in range(1, 8)})
PROTECTED_EXECUTIONS = frozenset({f"LH-X-{index:03d}" for index in range(1, 8)})

SEQUENCE = {
    "sequence_id": "SEQ-INF-MOM-001",
    "inflation_dataset": "bls.cu.CUSR0000SA0",
    "inflation_feature": "bls.cu.CUSR0000SA0:year_on_year",
    "inflation_change": "negative",
    "inflation_unit": "atlas percent change, a ratio, not a percentage-point change",
    "follow_month_ends": (1, 2, 3),
    "momentum_feature": "trailing_return_63",
    "momentum_sign": "positive",
    "outcome_horizon": PRIMARY_HORIZON,
    "outcome_steps": PRIMARY_STEPS,
    "advance_minimum": ADVANCE_MINIMUM,
    "comparison": (
        "Cite the frozen ETF-PROT-001 conjunction floors. "
        "Do not replace those floors and do not retune them on VWRA."
    ),
}

# Economically named pairs. Dataset ids are the stored series, not a search.
INTERSECTION_PAIRS = (
    {
        "pair_id": "labour_inflation",
        "left_feature": "method:LABOUR_MARKET_CONDITIONS:unemployment_change_percentage_points",
        "left_sign": "positive",
        "left_unit": "percentage_points",
        "right_feature": "bls.cu.CUSR0000SA0:year_on_year",
        "right_sign": "positive",
        "right_unit": "ratio",
    },
    {
        "pair_id": "growth_inflation",
        "left_feature": "fed.g17.IP.B50001.S:year_on_year",
        "left_sign": "positive",
        "left_unit": "ratio",
        "right_feature": "bls.cu.CUSR0000SA0:year_on_year",
        "right_sign": "positive",
        "right_unit": "ratio",
    },
    {
        "pair_id": "growth_credit",
        "left_feature": "fed.g17.IP.B50001.S:year_on_year",
        "left_sign": "positive",
        "left_unit": "ratio",
        "right_feature": "fed.sloos.SUBLPDCILS_N.Q:level",
        "right_sign": "positive",
        "right_unit": "percent_net_tightening",
    },
    {
        "pair_id": "credit_rates",
        "left_feature": "fed.sloos.SUBLPDCILS_N.Q:level",
        "left_sign": "positive",
        "left_unit": "percent_net_tightening",
        "right_feature": "fed.h15.RIFSPFF_N.M:difference",
        "right_sign": "positive",
        "right_unit": "percentage_points",
    },
    {
        "pair_id": "policy_yield_curve",
        "left_feature": "fed.h15.RIFSPFF_N.M:difference",
        "left_sign": "positive",
        "left_unit": "percentage_points",
        "right_feature": "method:ESTRELLA_MISHKIN_TERM_SPREAD:spread",
        "right_sign": "negative",
        "right_unit": "percentage_points",
    },
    {
        "pair_id": "liquidity_activity",
        "left_feature": "bis.ws_gli.Q.USD.3P.N.A.I.B.USD:percent_change",
        "left_sign": "positive",
        "left_unit": "ratio",
        "right_feature": "fed.g17.IP.B50001.S:year_on_year",
        "right_sign": "positive",
        "right_unit": "ratio",
    },
    {
        "pair_id": "growth_momentum",
        "left_feature": "fed.g17.IP.B50001.S:year_on_year",
        "left_sign": "positive",
        "left_unit": "ratio",
        "right_feature": "trailing_return_63",
        "right_sign": "positive",
        "right_unit": "ratio",
    },
    {
        "pair_id": "inflation_drawdown",
        "left_feature": "bls.cu.CUSR0000SA0:year_on_year",
        "left_sign": "positive",
        "left_unit": "ratio",
        "right_feature": "drawdown_252",
        "right_sign": "drawdown_0_10",
        "right_unit": "ratio",
    },
)

EPISODE_GROUP = {
    "sustained_advance": "advances",
    "sideways_then_advance": "advances",
    "negative_market": "declines",
    "sustained_decline": "declines",
    "early_bull": "bulls",
    "persistent_bull": "bulls",
    "persistent_bear": "bears",
    "drawdown_recovery": "recoveries",
    "early_recovery": "recoveries",
    "failed_rally": "failed_recoveries",
    "failed_recovery": "failed_recoveries",
    "trend_reversal": "reversals",
    "volatility_transition": "volatility_transitions",
    "flat_market": "stagnation",
}

ROLE_CLASS = {
    "supporting_indicator": "indicator",
    "executable_historical_methodology": "methodology",
    "diagnostic": "diagnostic",
    "unavailable": "unavailable",
}

CONFIRMATION_DELAY_METHODS = frozenset(
    {
        "EX_POST_REAL_FUNDS_RATE",
        "CONSTANT_MATURITY_SPREAD_RECESSION_PROBIT",
    }
)
PHASE_CODE = {"expansion": "1", "contraction": "-1"}
NOT_A_MONTHLY_STATE = (
    "LEAD_LAG_CROSS_CORRELATION",
    "ENGLE_GRANGER_COINTEGRATION",
    "CUSUM_RECURSIVE_RESIDUALS",
    "IP_GROWTH_CUSUM",
    "INFLATION_AUTOREGRESSION",
    "CPI_U_INFLATION_AUTREGRESSION",
    "AUTOREGRESSIVE_BENCHMARK",
)
RATE_DATASETS = (
    "bls.ln.LNS14000000",
    "fed.h15.RIFSPFF_N.M",
    "fed.h15.RIFLGFCY10_N.M",
    "fed.h15.RIFLGFCM03_N.M",
    "fed.sloos.SUBLPDCILS_N.Q",
)
CENSUS_DATASET = "census.m3.adv.MDM.NO"
REPRODUCTION_COMMAND = "uv run python -m aqil_research.long_horizon.vwra_discovery"
ATLAS_ID = "ATLAS-DEF-001"
EVENT_DEFINITIONS = ("EVT-DEF-001", "EVT-DEF-002")


HYPOTHESES: tuple[dict[str, object], ...] = (
    {
        "hypothesis_id": "LH-H-008",
        "experiment_id": "LH-E-008",
        "execution_id": "LH-X-008",
        "evidence_id": "LH-V-008",
        "claim_id": "LH-C-008",
        "proposition": (
            "Replaying the registered methods on stored latest-revised inputs produces "
            "retrospective numerical timelines where those inputs exist. The timelines "
            "are not point-in-time and they are not investment signals."
        ),
        "economic_rationale": (
            "A registered equation can be replayed on the stored sample. A missing "
            "point-in-time vintage does not delete a replay that uses latest-revised inputs."
        ),
        "expected_mechanism": (
            "Each method returns the number its existing equation already defines. "
            "The equation is not widened and another series is not substituted."
        ),
        "expected_direction": "not prejudged",
        "horizon": "the stored history of each required series",
        "falsification_criteria": (
            "A method whose required series has no stored rows stays unavailable. "
            "A failed calculation stores the failure reason and no empty success. "
            "No timeline is marked point-in-time or usable as a decision input."
        ),
        "alternative_explanations": [
            "A full-sample smoother describes the past without having been known at the time.",
            "A latest-revised print differs from the first release.",
        ],
        "relevant_indicators": ["registered method outputs"],
        "relevant_methodologies": ["default_method_registry"],
        "target_instruments": [],
    },
    {
        "hypothesis_id": "LH-H-009",
        "experiment_id": "LH-E-009",
        "execution_id": "LH-X-009",
        "evidence_id": "LH-V-009",
        "claim_id": "LH-C-009",
        "proposition": (
            "On VWRA month-ends on or after 2019-07-25, stored atlas features and "
            "reconstructed method output have a descriptive rank association with the "
            "later 126-session return. An advance is a stored return of at least 0.10. "
            "A decline is a stored return of at most -0.10. Overlapping month-ends are "
            "not independent trials."
        ),
        "economic_rationale": (
            "The association uses the frozen outcome already stored on the atlas. "
            "It does not recompute the return from a different price."
        ),
        "expected_mechanism": (
            "Spearman is computed on the anchor set. Pearson is computed only when both "
            "series are numeric. Logistic and probit are estimated only when the frozen "
            "effective-sample rule is met."
        ),
        "expected_direction": "not prejudged",
        "horizon": "126 sessions after the month-end anchor",
        "falsification_criteria": (
            "A future return is not readable as a state. Logistic output is "
            "not_estimable_effective_sample when the frozen floors are not met, and the "
            "descriptive counts are still stored. The result is not an allocation rule."
        ),
        "alternative_explanations": [
            "Overlapping month-ends repeat the same episode.",
            "A latest-revised feature was not known on the anchor date.",
        ],
        "relevant_indicators": ["atlas features", "reconstructed method output"],
        "relevant_methodologies": ["ATLAS-DEF-001", "EVT-DEF-001", "EVT-DEF-002"],
        "target_instruments": ["VWRA"],
    },
    {
        "hypothesis_id": "LH-H-010",
        "experiment_id": "LH-E-010",
        "execution_id": "LH-X-010",
        "evidence_id": "LH-V-010",
        "claim_id": "LH-C-010",
        "proposition": (
            "The eight named pairs have a descriptive association with the same advance "
            "and decline labels when both series are stored. A missing input is a refusal. "
            "Methods that share inputs are not independent confirmations."
        ),
        "economic_rationale": (
            "The pairs are labour and inflation, growth and inflation, growth and credit, "
            "credit and rates, policy and the yield curve, liquidity and activity, "
            "growth and momentum, and inflation and drawdown."
        ),
        "expected_mechanism": (
            "Each pair uses the sign or drawdown rule frozen before the score. "
            "No other pair is searched."
        ),
        "expected_direction": "not prejudged",
        "horizon": "126 sessions after the month-end anchor",
        "falsification_criteria": (
            "A pair with an absent input is refused and is not filled with another series. "
            "Shared inputs stay independent_confirmation false."
        ),
        "alternative_explanations": [
            "The two legs can move together because they share a business-cycle factor.",
        ],
        "relevant_indicators": ["the eight named pairs"],
        "relevant_methodologies": ["ATLAS-DEF-001"],
        "target_instruments": ["VWRA"],
    },
    {
        "hypothesis_id": "LH-H-011",
        "experiment_id": "LH-E-011",
        "execution_id": "LH-X-011",
        "evidence_id": "LH-V-011",
        "claim_id": "LH-C-011",
        "proposition": (
            "Year-on-year CPI inflation that is lower than at the previous month-end, "
            "followed within one to three month-ends by a positive 63-session trailing "
            "return, is compared with each component against the later 126-session advance. "
            "The thresholds are not retuned. The comparison is not an executable strategy."
        ),
        "economic_rationale": (
            "The sequence asks whether the conjunction adds anything beyond either leg "
            "under the frozen ETF-PROT-001 conjunction floors."
        ),
        "expected_mechanism": (
            "Inflation deceleration is a negative change in the atlas year-on-year ratio. "
            "It is not a percentage-point change. The advance label is the later outcome."
        ),
        "expected_direction": "not prejudged",
        "horizon": "confirmation inside one to three month-ends, outcome 126 sessions later",
        "falsification_criteria": (
            "The frozen conjunction rule assigns insufficient_sample, "
            "retrospective_exploratory, rejected, or inconclusive. It cannot assign "
            "statistically_supported, economically_useful, or forward_validated."
        ),
        "alternative_explanations": [
            "Momentum alone can match the sequence because the inflation leg adds no increment.",
            "The month-ends inside one episode are not independent trials.",
        ],
        "relevant_indicators": ["CPI year-on-year", "trailing_return_63"],
        "relevant_methodologies": ["ETF-PROT-001", "ATLAS-DEF-001"],
        "target_instruments": ["VWRA"],
    },
)

DEPENDENCIES: tuple[dict[str, object], ...] = (
    {
        "dependency_id": "LH-D-027",
        "experiment_id": "LH-E-008",
        "relation": "shares_methodology",
        "right_kind": "methodology",
        "right_id": ATLAS_ID,
        "instrument_id": None,
        "methodology_id": ATLAS_ID,
        "period_start": None,
        "detail": (
            "Method timelines are joined onto the stored atlas anchors. "
            "This is not independent confirmation."
        ),
    },
    {
        "dependency_id": "LH-D-028",
        "experiment_id": "LH-E-009",
        "relation": "shares_instrument",
        "right_kind": "instrument",
        "right_id": "VWRA",
        "instrument_id": "VWRA",
        "methodology_id": None,
        "period_start": VWRA_FIRST_SESSION.isoformat(),
        "detail": "The univariate sample is VWRA. This is not independent confirmation.",
    },
    {
        "dependency_id": "LH-D-029",
        "experiment_id": "LH-E-009",
        "relation": "shares_methodology",
        "right_kind": "methodology",
        "right_id": "EVT-DEF-001",
        "instrument_id": None,
        "methodology_id": "EVT-DEF-001",
        "period_start": None,
        "detail": "The casebook reuses EVT-DEF-001. This is not independent confirmation.",
    },
    {
        "dependency_id": "LH-D-030",
        "experiment_id": "LH-E-009",
        "relation": "shares_methodology",
        "right_kind": "methodology",
        "right_id": "EVT-DEF-002",
        "instrument_id": None,
        "methodology_id": "EVT-DEF-002",
        "period_start": None,
        "detail": "The casebook reuses EVT-DEF-002. This is not independent confirmation.",
    },
    {
        "dependency_id": "LH-D-031",
        "experiment_id": "LH-E-010",
        "relation": "shares_methodology",
        "right_kind": "methodology",
        "right_id": ATLAS_ID,
        "instrument_id": None,
        "methodology_id": ATLAS_ID,
        "period_start": None,
        "detail": "The pairs read stored atlas features. This is not independent confirmation.",
    },
    {
        "dependency_id": "LH-D-032",
        "experiment_id": "LH-E-011",
        "relation": "overlaps_period",
        "right_kind": "experiment",
        "right_id": "LH-E-009",
        "instrument_id": None,
        "methodology_id": None,
        "period_start": VWRA_FIRST_SESSION.isoformat(),
        "detail": (
            "The sequence uses the same VWRA month-ends as LH-E-009. "
            "The overlap is not independent confirmation."
        ),
    },
)


def method_finding(numeric_methods: int) -> str:
    """A timeline with a stored number is descriptive. It is not a promotion."""
    if numeric_methods > 0:
        return "descriptive"
    return "insufficient_sample"


def univariate_finding(executed_descriptive: int) -> str:
    if executed_descriptive > 0:
        return "descriptive"
    return "insufficient_sample"


def intersection_finding(estimated_pairs: int) -> str:
    if estimated_pairs > 0:
        return "descriptive"
    return "insufficient_sample"


def sequence_finding(comparison_status: str) -> str:
    return COMPARISON_FINDING[comparison_status]


def assert_vwra_session(session: date) -> None:
    """VWRA history starts on the listing date. Earlier sessions are refused."""
    if session < VWRA_FIRST_SESSION:
        raise ValueError(
            f"{session.isoformat()} is before VWRA listing {VWRA_FIRST_SESSION.isoformat()}"
        )


def join_allowed(period_end: date, anchor: date) -> bool:
    """A later period is not a state at this anchor."""
    return period_end <= anchor


def percent_change_ratio(current: str, previous: str) -> str:
    """Ratio change. This is not a percentage-point difference."""
    from decimal import Decimal

    from aqil_research.long_horizon.money import decimal_text

    latest = Decimal(current)
    earlier = Decimal(previous)
    if earlier == 0:
        raise ValueError("percent change is undefined when the earlier level is zero")
    return decimal_text(latest / earlier - 1)


def specification_document() -> dict[str, object]:
    """The hashed preregistration. It has no VWRA coefficient."""
    return {
        "specification_id": SPECIFICATION_ID,
        "version": SPECIFICATION_VERSION,
        "publication_allowed": PUBLICATION_ALLOWED,
        "vwra_first_session": VWRA_FIRST_SESSION.isoformat(),
        "advance_minimum": ADVANCE_MINIMUM,
        "decline_maximum": DECLINE_MAXIMUM,
        "primary_steps": PRIMARY_STEPS,
        "pre_event_steps": list(PRE_EVENT_STEPS),
        "logistic_decision_points": LOGISTIC_DECISION_POINTS,
        "logistic_non_overlapping": LOGISTIC_NON_OVERLAPPING,
        "non_overlap_session_gap": NON_OVERLAP_SESSION_GAP,
        "drawdown_split": DRAWDOWN_SPLIT,
        "finding_classes": list(FINDING_CLASSES),
        "forbidden_promotions": list(FORBIDDEN_PROMOTIONS),
        "comparison_finding": COMPARISON_FINDING,
        "sequence": {
            key: list(value) if isinstance(value, tuple) else value
            for key, value in SEQUENCE.items()
        },
        "intersection_pairs": [dict(row) for row in INTERSECTION_PAIRS],
        "episode_group": EPISODE_GROUP,
        "confirmation_delay_methods": sorted(CONFIRMATION_DELAY_METHODS),
        "phase_code": PHASE_CODE,
        "not_a_monthly_state": list(NOT_A_MONTHLY_STATE),
        "rate_datasets": list(RATE_DATASETS),
        "census_dataset": CENSUS_DATASET,
        "hypotheses": [dict(row) for row in HYPOTHESES],
        "dependencies": [dict(row) for row in DEPENDENCIES],
        "join_rule": (
            "Join a reconstructed point when its period end is on or before the "
            "anchor. A confirmation-delay method uses the later observation as "
            "that period end. Label the join retrospective. usable_as_decision_input "
            "stays false. A forward return is not copied onto the anchor."
        ),
        "percent_change_rule": (
            "A percent change is current divided by previous, minus one. "
            "A percentage-point change is a difference of levels that are already percents."
        ),
        "downside_volatility_rule": (
            "Sample standard deviation of strictly negative simple session returns "
            "inside the same trailing window as stored volatility. Fewer than two "
            "negative returns is insufficient. No later close is used and no gap is filled."
        ),
        "trend_persistence_rule": (
            "The atlas persistence run, applied to closes inside the trailing window "
            "on or before the anchor. It counts the current run of close-to-close signs."
        ),
        "portfolio_simulation": "not_called",
        "eimi_scoring": "not_started",
        "catalogue_scenarios_executed": 0,
        "point_in_time_eligible": [],
        "independently_validated": [],
    }


def specification_hash() -> str:
    return sha256_document(specification_document())
