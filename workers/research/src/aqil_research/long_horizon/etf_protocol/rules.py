"""Frozen arithmetic for ETF-PROT-001.

Callers pass closes and stored values. This module does not read a database
and does not fit a logistic, probit, or regularized model.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from scipy.stats import t as student_t

from aqil_research.long_horizon.etf_protocol.specification import (
    ADVANCE_MINIMUM,
    ALLOWED_PAIR_STATUSES,
    DECLINE_MAXIMUM,
    FORBIDDEN_CLAIM_STATUSES,
    PRIMARY_HORIZON,
    PROTOCOL,
    SEARCH_REFUSAL_REASON,
    VWRA_FIRST_SESSION,
    ProtocolError,
    TrialKey,
)
from aqil_research.long_horizon.money import decimal_text
from aqil_research.long_horizon.state_atlas.features import (
    drawdown,
    recovery_from_prior_trough,
    trailing_return,
    volatility,
)


@dataclass(frozen=True)
class Score:
    effect: str | None
    result: str | None
    refusal: str | None
    p_value: str | None = None


def assert_session_allowed(symbol: str, session: date) -> None:
    first = date.fromisoformat(VWRA_FIRST_SESSION)
    if symbol == "VWRA" and session < first:
        raise ProtocolError("A VWRA session before 2019-07-25 is refused")


def _history(closes: Sequence[Decimal], index: int) -> Sequence[Decimal]:
    if index < 0 or index >= len(closes):
        raise ProtocolError("the anchor index is outside the series")
    return closes[: index + 1]


def predictor_value(closes: Sequence[Decimal], index: int, feature: str) -> Decimal | None:
    """A predictor uses closes on or before index. A later close is not read."""
    _history(closes, index)
    if feature.startswith("trailing_return_"):
        steps = int(feature.removeprefix("trailing_return_"))
        found = trailing_return(closes, index, steps)
    elif feature.startswith("drawdown_"):
        steps = int(feature.removeprefix("drawdown_"))
        found = drawdown(closes, index, steps)
    elif feature.startswith("volatility_"):
        steps = int(feature.removeprefix("volatility_"))
        found = volatility(closes, index, steps)
    elif feature.startswith("recovery_from_prior_trough_"):
        steps = int(feature.removeprefix("recovery_from_prior_trough_"))
        found = recovery_from_prior_trough(closes, index, steps)
    else:
        raise ProtocolError(f"{feature} is not a frozen price predictor")
    if found.value is None:
        return None
    return Decimal(found.value)


def _median(values: Sequence[Decimal]) -> Decimal:
    ordered = sorted(values)
    count = len(ordered)
    if count == 0:
        raise ProtocolError("median is undefined for an empty list")
    middle = count // 2
    if count % 2 == 1:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / Decimal(2)


def trailing_volatility_median(closes: Sequence[Decimal], index: int) -> Decimal | None:
    """Median of volatility_63 over the trailing 252 sessions, including index."""
    rule = PROTOCOL["conjunction"]
    if not isinstance(rule, dict):
        raise ProtocolError("the conjunction rule is missing")
    window = int(rule["volatility_median_sessions"])
    if index + 1 < window:
        return None
    start = index - window + 1
    values: list[Decimal] = []
    for cursor in range(start, index + 1):
        value = predictor_value(closes, cursor, "volatility_63")
        if value is None:
            return None
        values.append(value)
    if len(values) != window:
        return None
    return _median(values)


def binary_flag(feature: str, value: Decimal | None) -> bool | None:
    if value is None:
        return None
    thresholds = PROTOCOL["binary_thresholds"]
    if not isinstance(thresholds, dict):
        raise ProtocolError("the threshold table is missing")
    if feature == "trailing_return_63":
        return value >= Decimal(str(thresholds["trailing_return_63"]))
    if feature == "drawdown_252":
        return value <= -Decimal(str(thresholds["drawdown_252_magnitude"]))
    return None


def outcome_flag(outcome: str, value: Decimal | None) -> bool | None:
    if value is None:
        return None
    if outcome == "advance":
        return value >= Decimal(ADVANCE_MINIMUM)
    if outcome == "decline":
        return value <= Decimal(DECLINE_MAXIMUM)
    if outcome == "eimi_ahead":
        return value > 0
    raise ProtocolError(f"{outcome} is not a binary label")


def relative_class(eimi_return: Decimal, vwra_return: Decimal) -> str:
    """Five exclusive classes. A tie or a zero that fits none of them is no sign."""
    eimi_ahead_both = eimi_return > 0 and vwra_return > 0 and eimi_return > vwra_return
    if eimi_ahead_both:
        return "eimi_ahead_both_positive"
    if eimi_return > 0 and vwra_return < 0:
        return "eimi_positive_vwra_negative"
    both_negative = eimi_return < 0 and vwra_return < 0 and eimi_return > vwra_return
    if both_negative:
        return "both_negative_eimi_declines_less"
    if vwra_return > eimi_return and eimi_return != 0 and vwra_return != 0:
        return "vwra_ahead"
    return "no_sign"


def _ranks(values: Sequence[Decimal]) -> list[Decimal]:
    order = sorted(range(len(values)), key=lambda index: (values[index], index))
    ranks = [Decimal(0)] * len(values)
    cursor = 0
    while cursor < len(values):
        end = cursor
        while end + 1 < len(values) and values[order[end + 1]] == values[order[cursor]]:
            end += 1
        average = (Decimal(cursor + 1) + Decimal(end + 1)) / Decimal(2)
        for position in range(cursor, end + 1):
            ranks[order[position]] = average
        cursor = end + 1
    return ranks


def _pearson(left: Sequence[Decimal], right: Sequence[Decimal]) -> Decimal | None:
    count = len(left)
    if count != len(right) or count < 3:
        return None
    mean_left = sum(left, Decimal(0)) / Decimal(count)
    mean_right = sum(right, Decimal(0)) / Decimal(count)
    covariance = sum((x - mean_left) * (y - mean_right) for x, y in zip(left, right, strict=True))
    var_left = sum((item - mean_left) ** 2 for item in left)
    var_right = sum((item - mean_right) ** 2 for item in right)
    if var_left == 0 or var_right == 0:
        return None
    return covariance / (var_left.sqrt() * var_right.sqrt())


def _p_value(rho: Decimal, count: int) -> str:
    if abs(rho) >= 1:
        return "0"
    ratio = Decimal(1) - rho**2
    if ratio <= 0 or count <= 2:
        return "0"
    statistic = float(rho * (Decimal(count - 2) / ratio).sqrt())
    probability = float(student_t.sf(abs(statistic), count - 2) * 2)
    if probability < 0:
        probability = 0.0
    if probability > 1:
        probability = 1.0
    return format(probability, ".6e")


def spearman(pairs: Sequence[tuple[Decimal, Decimal]]) -> Score:
    minimum = int(PROTOCOL["minimum_complete_observations"])
    if len(pairs) < minimum:
        return Score(None, None, "insufficient_effective_sample")
    left = _ranks([item[0] for item in pairs])
    right = _ranks([item[1] for item in pairs])
    rho = _pearson(left, right)
    if rho is None:
        return Score(None, None, "insufficient_effective_sample")
    return Score(decimal_text(rho), decimal_text(rho), None, _p_value(rho, len(pairs)))


def conditional_frequency(flags: Sequence[bool], outcomes: Sequence[bool]) -> Score:
    if len(flags) != len(outcomes):
        raise ProtocolError("the conditional contrast is not aligned")
    if len(flags) < int(PROTOCOL["minimum_complete_observations"]):
        return Score(None, None, "insufficient_effective_sample")
    true_rows = [outcome for flag, outcome in zip(flags, outcomes, strict=True) if flag]
    false_rows = [outcome for flag, outcome in zip(flags, outcomes, strict=True) if not flag]
    if not true_rows or not false_rows:
        return Score(None, None, "insufficient_effective_sample")
    true_rate = Decimal(sum(true_rows)) / Decimal(len(true_rows))
    false_rate = Decimal(sum(false_rows)) / Decimal(len(false_rows))
    difference = true_rate - false_rate
    text = decimal_text(difference)
    return Score(text, text, None)


def benjamini_hochberg(p_values: Sequence[str], q: str | None = None) -> tuple[bool, ...]:
    """A diagnostic. The caller must not change a claim status from these flags."""
    diagnostic = PROTOCOL["multiple_comparison"]
    if not isinstance(diagnostic, dict):
        raise ProtocolError("the multiple-comparison rule is missing")
    level = Decimal(q or str(diagnostic["q"]))
    count = len(p_values)
    if count == 0:
        return ()
    numbered = sorted(
        ((Decimal(value), index) for index, value in enumerate(p_values)),
        key=lambda item: (item[0], item[1]),
    )
    cutoff = -1
    for rank, (probability, _index) in enumerate(numbered, start=1):
        if probability <= (Decimal(rank) / Decimal(count)) * level:
            cutoff = rank
    flags = [False] * count
    if cutoff > 0:
        for rank, (_probability, index) in enumerate(numbered, start=1):
            if rank <= cutoff:
                flags[index] = True
    return tuple(flags)


def conjunction_status(
    *,
    eligible: int,
    pair_count: int,
    pair_advances: int,
    drawdown_count: int,
    drawdown_advances: int,
    volatility_count: int,
    volatility_advances: int,
    advances: int,
) -> str:
    rule = PROTOCOL["conjunction"]
    if not isinstance(rule, dict):
        raise ProtocolError("the conjunction rule is missing")
    floors_met = (
        eligible >= int(rule["minimum_eligible"])
        and pair_count >= int(rule["minimum_pair"])
        and drawdown_count >= int(rule["minimum_each_leg"])
        and volatility_count >= int(rule["minimum_each_leg"])
        and advances >= int(rule["minimum_advances"])
    )
    if not floors_met:
        return "insufficient_data"
    pair_rate = Decimal(pair_advances) / Decimal(pair_count)
    drawdown_rate = Decimal(drawdown_advances) / Decimal(drawdown_count)
    volatility_rate = Decimal(volatility_advances) / Decimal(volatility_count)
    increment = Decimal(str(rule["required_increment"]))
    beats_drawdown = pair_rate - drawdown_rate > increment
    beats_volatility = pair_rate - volatility_rate > increment
    if not (beats_drawdown and beats_volatility):
        return "no_incremental_information"
    base_rate = Decimal(advances) / Decimal(eligible)
    event_share = Decimal(pair_advances) / Decimal(advances)
    share_cap = Decimal(str(rule["rejected_if_event_share_at_least"]))
    if pair_rate <= base_rate or event_share >= share_cap:
        return "rejected"
    return "inconclusive"


def control_increment_status(
    *,
    control_estimated: bool,
    any_candidate_beats_control: bool,
    any_candidate_estimated: bool,
) -> str:
    if not control_estimated or not any_candidate_estimated:
        return "insufficient_data"
    if any_candidate_beats_control:
        return "inconclusive"
    return "no_incremental_information"


def promotion_decision(
    *,
    point_in_time: bool,
    uninspected_evaluation: bool,
    incremental_information: bool,
) -> str:
    if point_in_time and uninspected_evaluation and incremental_information:
        return "policy_registered"
    return "no_policy_registered"


def method_refusal(replay_status: str) -> Score:
    if replay_status not in {"not_historically_replayed", "unavailable_input"}:
        raise ProtocolError("a method row must be a refusal, not a fitted output")
    return Score(None, None, replay_status)


def search_refusal() -> Score:
    return Score(None, None, SEARCH_REFUSAL_REASON)


def rows_to_insert(declared: Sequence[TrialKey], existing: set[str]) -> tuple[TrialKey, ...]:
    return tuple(row for row in declared if row.identity() not in existing)


def assert_effect_null(score: Score) -> None:
    if score.effect is not None or score.result is not None:
        raise ProtocolError("a refusal row has an effect")


def assert_pair_status(status: str) -> None:
    if status in FORBIDDEN_CLAIM_STATUSES or status not in ALLOWED_PAIR_STATUSES:
        raise ProtocolError("the pair status is not allowed")


def primary_horizon() -> str:
    return PRIMARY_HORIZON
