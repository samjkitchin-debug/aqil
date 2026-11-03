"""Frozen ETF protocol and EVT-DEF-002 version 1.

Thresholds in these dictionaries are the preregistration. A later change is a
new version. This module does not read prices or write rows.
"""

from __future__ import annotations

from dataclasses import dataclass

from aqil_research.long_horizon.events.definition import EVENT_DEFINITION, event_definition_hash
from aqil_research.long_horizon.money import sha256_document
from aqil_research.long_horizon.state_atlas.specification import (
    EVT_DEFINITION_HASH,
    POINT_IN_TIME_DATASET,
    SESSION_STEPS,
)

PROTOCOL_ID = "ETF-PROT-001"
PROTOCOL_VERSION = 1
DEFINITION_ID = "EVT-DEF-002"
DEFINITION_VERSION = 1

VWRA_FIRST_SESSION = "2019-07-25"
PRIMARY_HORIZON = "6m"
PRIMARY_STEPS = 126
ADVANCE_MINIMUM = "0.10"
DECLINE_MAXIMUM = "-0.10"
PEER_TOLERANCE_DAYS = 5
DIAGNOSTIC_FDR = "0.05"
REQUIRED_INCREMENT = "0"

DOSSIER_IDS = ("LH-X-005", "LH-X-006", "LH-X-007")
PROTECTED_HYPOTHESES = frozenset({"LH-H-001", "LH-H-002", "LH-H-003", "LH-H-004"})
PROTECTED_EXPERIMENTS = frozenset({"LH-E-001", "LH-E-002", "LH-E-003", "LH-E-004"})
PROTECTED_EXECUTIONS = frozenset({"LH-X-001", "LH-X-002", "LH-X-003", "LH-X-004"})

FORBIDDEN_CLAIM_STATUSES = (
    "statistically_supported",
    "economically_useful",
    "forward_validated",
)
ALLOWED_PAIR_STATUSES = (
    "insufficient_data",
    "rejected",
    "no_incremental_information",
    "inconclusive",
)
SEARCH_REFUSALS = ("logistic", "probit", "regularized_search")
SEARCH_REFUSAL_REASON = "not_estimable_effective_sample"
ECONOMIC_TRANSFORMS = ("direction", "year_on_year", "acceleration")
SINGLE_OUTCOMES = ("advance", "decline")
PAIR_OUTCOMES = ("excess", "eimi_ahead")
HORIZONS = ("1m", "3m", "6m", "12m", "24m", "36m")
PRICE_FEATURES = (
    "trailing_return_63",
    "trailing_return_252",
    "drawdown_252",
    "volatility_63",
    "recovery_from_prior_trough_252",
)
BINARY_TRANSFORMS = {
    "trailing_return_63": "binary_at_least_0_05",
    "drawdown_252": "binary_drawdown_at_least_0_10",
}
PAIR_CONTROLS = (
    "relative_performance_vs_vwra_63",
    "relative_performance_vs_vwra_252",
)
PRIMARY_CONTROL = "relative_performance_vs_vwra_252"
LINKED_NOT_REDEFINED = (
    "persistent_bull",
    "drawdown_recovery",
    "failed_rally",
    "negative_market",
    "flat_market",
    "leadership_transition",
)


class ProtocolError(ValueError):
    """A frozen rule was asked to do something the protocol refuses."""


def _mapping(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ProtocolError("the mirrored event rule is not an object")
    return value


def _negative(magnitude: object) -> str:
    text = str(magnitude)
    if text.startswith("-") or text == "":
        raise ProtocolError("a mirrored magnitude is already signed")
    return f"-{text}"


def _decline_rules() -> dict[str, object]:
    advance = _mapping(EVENT_DEFINITION["sustained_advance"])
    mirrored: dict[str, object] = {}
    for horizon, raw in advance.items():
        rule = _mapping(raw)
        mirrored[str(horizon)] = {
            "steps": rule["steps"],
            "maximum_return": _negative(rule["minimum_return"]),
            "maximum_rally": rule["maximum_drawdown"],
            "minimum_down_session_fraction": rule["minimum_up_session_fraction"],
        }
    return mirrored


def _bear_rule() -> dict[str, object]:
    bull = _mapping(EVENT_DEFINITION["persistent_bull"])
    return {
        "minimum_decline": bull["minimum_rise"],
        "confirming_rally": bull["confirming_decline"],
        "minimum_session_steps": bull["minimum_session_steps"],
        "terminal_downswing_without_confirmation": "censored_not_an_event",
    }


def _failed_recovery_rule() -> dict[str, object]:
    recovery = _mapping(EVENT_DEFINITION["drawdown_recovery"])
    early = _mapping(EVENT_DEFINITION["early_recovery"])
    return {
        "minimum_decline": recovery["minimum_decline"],
        "retracement": early["retracement"],
        "returns_to_the_trough_before_the_old_peak": True,
        "open_path": "censored_not_an_event",
    }


_BEAR = _bear_rule()
_RECOVERY = _failed_recovery_rule()

EVENT_DEFINITION_V2: dict[str, object] = {
    "schema_version": "1.0",
    "definition_id": DEFINITION_ID,
    "version": DEFINITION_VERSION,
    "mirrors": "EVT-DEF-001 version 1",
    "does_not_edit": "EVT-DEF-001",
    "event_definition_hash_v1": EVT_DEFINITION_HASH,
    "price_type": "adjusted_close",
    "adjustment_status": "adjusted",
    "total_return_events": "blocked",
    "price_label": (
        "A stored adjusted close stays a split-adjusted close. It is not relabelled "
        "as a total return."
    ),
    "session_steps": dict(SESSION_STEPS),
    "vwra_first_stored_session": VWRA_FIRST_SESSION,
    "vwra_rule": "A VWRA session before 2019-07-25 is refused. No earlier price is manufactured.",
    "families": {
        "sustained_decline": _decline_rules(),
        "persistent_bear": _BEAR,
        "failed_recovery": _RECOVERY,
        "trend_reversal": {
            "trailing_steps": SESSION_STEPS["12m"],
            "horizon_label": "12m",
            "confirmation": "the next month-end still holds the new sign",
            "zero_is_not_a_sign": True,
            "historically_observable_at_event_date": False,
            "reason": "The confirmation uses a later close.",
        },
        "volatility_transition": {
            "volatility_steps": SESSION_STEPS["3m"],
            "median_sessions": SESSION_STEPS["12m"],
            "median": "trailing_not_full_sample",
            "cross": "strict sign change of volatility minus that trailing median",
            "historically_observable_at_event_date": True,
        },
    },
    "linked_not_redefined": list(LINKED_NOT_REDEFINED),
    "catalogue_scope": "every listing that has stored adjusted closes",
    "publication_allowed": False,
}


def _hypothesis(
    hypothesis_id: str,
    proposition: str,
    target: list[str],
) -> dict[str, object]:
    return {
        "hypothesis_id": hypothesis_id,
        "version": 1,
        "proposition": proposition,
        "economic_rationale": (
            "A long-term buyer can observe trailing price state and stored economic "
            "features at a month-end. The question is whether those features rank "
            "with later session-step results. No cause is claimed. Latest-revised "
            "figures are not treated as known on the anchor date."
        ),
        "expected_mechanism": "No causal mechanism is claimed.",
        "expected_direction": (
            "No sign is required for the Spearman battery. The new price conjunction "
            "must beat each of its legs by more than zero or its status is "
            "no_incremental_information."
        ),
        "horizon": (
            "Month-end anchors and the six stored session steps 21, 63, 126, 252, "
            "504, and 756. The primary labels use 126 sessions. The other horizons "
            "are secondary trials. The whole stored history is inspected."
        ),
        "falsification_criteria": (
            "The conjunction is insufficient when the frozen count floors are missed, "
            "no_incremental_information when it does not beat each leg, and rejected "
            "when it beats the legs but misses the base rate or precedes at least "
            "70 percent of primary advances. Otherwise inconclusive. Statistical "
            "support, economic usefulness, and forward validation are forbidden. "
            "The Benjamini-Hochberg diagnostic cannot promote a claim."
        ),
        "alternative_explanations": [
            "Month-end outcomes overlap, so the months are not independent trials.",
            "The series are split-adjusted closes, not total returns.",
            "Latest-revised economic features can use information published later.",
            "The stored universe was selected in 2026, so closed funds are absent.",
            "A short overlapping sample can manufacture precision if a saturated model is fit.",
        ],
        "relevant_indicators": [],
        "relevant_methodologies": [],
        "target_instruments": target,
        "initial_status": "proposed",
        "catalogue_signal_id": None,
    }


HYPOTHESES: dict[str, dict[str, object]] = {
    "LH-H-005": _hypothesis(
        "LH-H-005",
        (
            "On VWRA month-ends on or after 2019-07-25, the frozen predictors in "
            "ETF-PROT-001 rank with the later advance and decline labels. The "
            "conjunction of a 252-session drawdown of at least 0.10 and volatility "
            "above VWRA's own trailing median beats each leg on the primary advance "
            "label by more than zero, or the pair status is no_incremental_information. "
            "Category B. Not an allocation rule."
        ),
        ["VWRA"],
    ),
    "LH-H-006": _hypothesis(
        "LH-H-006",
        (
            "On EIMI month-ends in its own stored history, the same frozen predictors "
            "and the same thresholds rank with the later advance and decline labels. "
            "The same drawdown-and-volatility conjunction is applied unchanged. "
            "Category B. Not an allocation rule."
        ),
        ["EIMI"],
    ),
    "LH-H-007": _hypothesis(
        "LH-H-007",
        (
            "On matched US-dollar month-ends within five days, the same predictors "
            "rank with the session-step excess of EIMI minus VWRA and with EIMI "
            "ahead. EIMI is an emerging-market overweight relative to VWRA, not a "
            "separate diversifier. Relative outperformance is not a positive absolute "
            "return. The price-only control is the stored relative performance versus "
            "VWRA. An allocation policy requires a point-in-time input, an uninspected "
            "evaluation period, and incremental information over that control."
        ),
        ["EIMI", "VWRA"],
    ),
}

DOSSIERS: tuple[dict[str, object], ...] = (
    {
        "hypothesis_id": "LH-H-005",
        "experiment_id": "LH-E-005",
        "execution_id": "LH-X-005",
        "evidence_id": "LH-V-005",
        "claim_id": "LH-C-005",
        "symbol": "VWRA",
        "kind": "single",
        "dependency_ids": ("LH-D-015", "LH-D-016", "LH-D-017", "LH-D-018"),
    },
    {
        "hypothesis_id": "LH-H-006",
        "experiment_id": "LH-E-006",
        "execution_id": "LH-X-006",
        "evidence_id": "LH-V-006",
        "claim_id": "LH-C-006",
        "symbol": "EIMI",
        "kind": "single",
        "dependency_ids": ("LH-D-019", "LH-D-020", "LH-D-021", "LH-D-022"),
    },
    {
        "hypothesis_id": "LH-H-007",
        "experiment_id": "LH-E-007",
        "execution_id": "LH-X-007",
        "evidence_id": "LH-V-007",
        "claim_id": "LH-C-007",
        "symbol": "EIMI-VWRA",
        "kind": "pair",
        "dependency_ids": ("LH-D-023", "LH-D-024", "LH-D-025", "LH-D-026"),
    },
)

PROTOCOL: dict[str, object] = {
    "schema_version": "1.0",
    "protocol_id": PROTOCOL_ID,
    "version": PROTOCOL_VERSION,
    "publication_allowed": False,
    "event_definition_v2": EVENT_DEFINITION_V2,
    "atlas_specification_id": "ATLAS-DEF-001",
    "event_definition_v1": "EVT-DEF-001",
    "session_steps": dict(SESSION_STEPS),
    "primary_horizon": PRIMARY_HORIZON,
    "advance_minimum_return": ADVANCE_MINIMUM,
    "decline_maximum_return": DECLINE_MAXIMUM,
    "secondary_horizons_use_the_same_cuts": True,
    "non_event_month_ends_stay_in_the_denominator": True,
    "incomplete_horizons": "censored",
    "price_features": list(PRICE_FEATURES),
    "binary_transforms": dict(BINARY_TRANSFORMS),
    "binary_thresholds": {
        "trailing_return_63": "0.05",
        "drawdown_252_magnitude": "0.10",
    },
    "volatility_has_no_new_cut": True,
    "economic_transforms": list(ECONOMIC_TRANSFORMS),
    "economic_clock": "retrospective_latest_revised_release_lag_unknown",
    "economic_usable_as_decision_input": False,
    "point_in_time_dataset": POINT_IN_TIME_DATASET,
    "point_in_time_is_not_a_method_replay": True,
    "pair_controls": list(PAIR_CONTROLS),
    "primary_price_only_control": PRIMARY_CONTROL,
    "peer_tolerance_days": PEER_TOLERANCE_DAYS,
    "peer_currency": "USD",
    "euna_relative_result": "blocked_no_foreign_exchange",
    "inrg_prices": "absent",
    "relative_classes": [
        "eimi_ahead_both_positive",
        "eimi_positive_vwra_negative",
        "both_negative_eimi_declines_less",
        "vwra_ahead",
        "no_sign",
    ],
    "search_refusals": list(SEARCH_REFUSALS),
    "search_refusal_reason": SEARCH_REFUSAL_REASON,
    "methods": "one refusal row each, not a fitted association",
    "cited_not_refitted": ["LH-E-002", "LH-E-004"],
    "conjunction": {
        "drawdown_feature": "drawdown_252",
        "drawdown_magnitude": "0.10",
        "volatility_feature": "volatility_63",
        "volatility_median_sessions": SESSION_STEPS["12m"],
        "outcome": "advance",
        "horizon": PRIMARY_HORIZON,
        "required_increment": REQUIRED_INCREMENT,
        "comparison": "strictly_greater_than_each_leg",
        "minimum_eligible": 12,
        "minimum_pair": 3,
        "minimum_each_leg": 3,
        "minimum_advances": 3,
        "rejected_if_event_share_at_least": "0.70",
        "count_floors_cited_from": ["LH-H-002", "LH-H-004"],
        "symbols": ["VWRA", "EIMI"],
    },
    "multiple_comparison": {
        "recorded_trial_count": True,
        "benjamini_hochberg_horizon": PRIMARY_HORIZON,
        "benjamini_hochberg_statistic": "spearman",
        "q": DIAGNOSTIC_FDR,
        "cannot_promote": True,
    },
    "promotion_rule": {
        "requires_point_in_time_input": True,
        "requires_uninspected_evaluation_period": True,
        "requires_incremental_information_over_price_only_control": True,
        "this_history_is_inspected": True,
        "expected_registry_result": "no_policy_registered",
    },
    "allowed_pair_statuses": list(ALLOWED_PAIR_STATUSES),
    "forbidden_claim_statuses": list(FORBIDDEN_CLAIM_STATUSES),
    "minimum_complete_observations": 3,
    "portfolio_simulation": "blocked",
    "catalogue_scenarios_executed": 0,
    "hypotheses": {key: value["proposition"] for key, value in HYPOTHESES.items()},
    "dossiers": [
        {key: list(value) if isinstance(value, tuple) else value for key, value in row.items()}
        for row in DOSSIERS
    ],
}


@dataclass(frozen=True)
class TrialKey:
    dossier_id: str
    symbol: str
    feature: str
    transform: str
    horizon_label: str
    outcome: str
    statistic: str
    eligibility: str
    kind: str

    def identity(self) -> str:
        return "|".join(
            (
                self.dossier_id,
                self.symbol,
                self.feature,
                self.transform,
                self.horizon_label,
                self.outcome,
                self.statistic,
            )
        )


def threshold_table(symbol: str) -> dict[str, object]:
    """One threshold table. VWRA and EIMI do not receive private cuts."""
    if symbol not in {"VWRA", "EIMI", "EIMI-VWRA"}:
        raise ProtocolError("this protocol is not open for that symbol")
    table = PROTOCOL["binary_thresholds"]
    if not isinstance(table, dict):
        raise ProtocolError("the threshold table is missing")
    return table


def _eligibility(dataset_id: str) -> str:
    if dataset_id == POINT_IN_TIME_DATASET:
        return "point_in_time_indicator"
    return "category_b_retrospective"


def _append_score_keys(
    rows: list[TrialKey],
    *,
    dossier_id: str,
    symbol: str,
    feature: str,
    eligibility: str,
    outcomes: tuple[str, ...],
    binary_transform: str | None,
) -> None:
    for horizon in HORIZONS:
        for outcome in outcomes:
            rows.append(
                TrialKey(
                    dossier_id,
                    symbol,
                    feature,
                    "continuous",
                    horizon,
                    outcome,
                    "spearman",
                    eligibility,
                    "score",
                )
            )
            if binary_transform is None:
                continue
            if outcome == "excess":
                continue
            rows.append(
                TrialKey(
                    dossier_id,
                    symbol,
                    feature,
                    binary_transform,
                    horizon,
                    outcome,
                    "conditional_frequency",
                    eligibility,
                    "score",
                )
            )


def declare_trials(
    economic_datasets: tuple[str, ...] | list[str],
    method_ids: tuple[str, ...] | list[str],
) -> tuple[TrialKey, ...]:
    """The grid is fixed by this function. Callers do not add cells later."""
    datasets = tuple(sorted(set(economic_datasets)))
    methods = tuple(sorted(set(method_ids)))
    rows: list[TrialKey] = []
    for dossier in DOSSIERS:
        dossier_id = str(dossier["execution_id"])
        symbol = str(dossier["symbol"])
        kind = str(dossier["kind"])
        outcomes = PAIR_OUTCOMES if kind == "pair" else SINGLE_OUTCOMES
        features = list(PRICE_FEATURES)
        if kind == "pair":
            features.extend(PAIR_CONTROLS)
        for feature in features:
            _append_score_keys(
                rows,
                dossier_id=dossier_id,
                symbol=symbol,
                feature=feature,
                eligibility="category_c_price_only",
                outcomes=outcomes,
                binary_transform=BINARY_TRANSFORMS.get(feature),
            )
        for dataset_id in datasets:
            for transform_name in ECONOMIC_TRANSFORMS:
                _append_score_keys(
                    rows,
                    dossier_id=dossier_id,
                    symbol=symbol,
                    feature=f"{dataset_id}:{transform_name}",
                    eligibility=_eligibility(dataset_id),
                    outcomes=outcomes,
                    binary_transform=None,
                )
        for method_id in methods:
            rows.append(
                TrialKey(
                    dossier_id,
                    symbol,
                    method_id,
                    "inventory",
                    "not_applicable",
                    "not_applicable",
                    "not_fitted",
                    "not_a_method_replay",
                    "method_refusal",
                )
            )
        for name in SEARCH_REFUSALS:
            rows.append(
                TrialKey(
                    dossier_id,
                    symbol,
                    name,
                    "search",
                    "not_applicable",
                    "not_applicable",
                    "not_fitted",
                    "not_estimable",
                    "search_refusal",
                )
            )
        if kind == "single":
            for cited in ("LH-E-002", "LH-E-004"):
                rows.append(
                    TrialKey(
                        dossier_id,
                        symbol,
                        cited,
                        "cited",
                        PRIMARY_HORIZON,
                        "advance",
                        "not_reestimated",
                        "category_c_price_only",
                        "citation",
                    )
                )
            rows.append(
                TrialKey(
                    dossier_id,
                    symbol,
                    "drawdown_252_and_volatility_63",
                    "conjunction",
                    PRIMARY_HORIZON,
                    "advance",
                    "incremental_contrast",
                    "category_c_price_only",
                    "conjunction",
                )
            )
    identities = [row.identity() for row in rows]
    if len(identities) != len(set(identities)):
        raise ProtocolError("the declared grid has a duplicate trial")
    return tuple(rows)


def protocol_hash() -> str:
    return sha256_document(PROTOCOL)


def event_definition_v2_hash() -> str:
    return sha256_document(EVENT_DEFINITION_V2)


def assert_v1_hash_unchanged() -> None:
    if event_definition_hash() != EVT_DEFINITION_HASH:
        raise ProtocolError("EVT-DEF-001 hash changed")


def assert_status_allowed(status: str) -> None:
    if status in FORBIDDEN_CLAIM_STATUSES:
        raise ProtocolError("this protocol cannot promote that status")
    if status not in ALLOWED_PAIR_STATUSES and status != "no_policy_registered":
        raise ProtocolError("the status is not one of the predetermined statuses")
