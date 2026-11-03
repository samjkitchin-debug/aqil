"""LH-H-004 sequence. Conditions do not read a later close."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from aqil_research.long_horizon.events.pilot_rule import month_end_indices
from aqil_research.long_horizon.money import decimal_text
from aqil_research.long_horizon.state_atlas.features import trough_after_peak
from aqil_research.long_horizon.state_atlas.specification import (
    ALLOWED_SEQUENCE_STATUSES,
    FORBIDDEN_CLAIM_STATUSES,
    SEQUENCE_EXPERIMENT,
    assert_sequence_status_allowed,
)


class SequenceRuleError(ValueError):
    """The frozen sequence was asked to read ahead or to promote a status."""


def _experiment() -> dict[str, object]:
    return SEQUENCE_EXPERIMENT


def _leg(name: str) -> dict[str, object]:
    raw = _experiment()[name]
    assert isinstance(raw, dict)
    return raw


def _status_rule() -> dict[str, object]:
    raw = _experiment()["status_rule"]
    assert isinstance(raw, dict)
    return raw


def _add_months(year: int, month: int, delta: int) -> tuple[int, int]:
    index = year * 12 + (month - 1) + delta
    return index // 12, index % 12 + 1


def condition_a(closes: Sequence[Decimal], index: int) -> bool:
    """True only from closes at or before index."""
    rule = _leg("condition_a")
    lookback = int(rule["lookback_steps"])
    found = trough_after_peak(closes, index, lookback)
    if found is None:
        return False
    peak, trough = found
    decline = trough / peak - 1
    distance = closes[index] / trough - 1
    return decline <= -Decimal(str(rule["minimum_decline"])) and distance <= Decimal(
        str(rule["maximum_distance_above_trough"])
    )


def condition_b_alone(closes: Sequence[Decimal], index: int) -> bool:
    rule = _leg("condition_b_alone")
    lookback = int(rule["lookback_steps"])
    momentum = int(rule["momentum_steps"])
    if index < momentum:
        return False
    found = trough_after_peak(closes, index, lookback)
    if found is None:
        return False
    _peak, trough = found
    trailing = closes[index] / closes[index - momentum] - 1
    distance = closes[index] / trough - 1
    return trailing >= Decimal(str(rule["minimum_return"])) and distance >= Decimal(
        str(rule["minimum_distance_above_own_trough"])
    )


def condition_b_after_a(closes: Sequence[Decimal], index: int, trough_at_a: Decimal) -> bool:
    rule = _leg("condition_b_after_a")
    momentum = int(rule["lookback_steps"])
    if index < momentum or trough_at_a <= 0:
        return False
    trailing = closes[index] / closes[index - momentum] - 1
    distance = closes[index] / trough_at_a - 1
    return trailing >= Decimal(str(rule["minimum_return"])) and distance >= Decimal(
        str(rule["minimum_distance_above_a_trough"])
    )


def _advance(closes: Sequence[Decimal], index: int) -> tuple[bool, Decimal]:
    label = _leg("outcome_label")
    steps = int(label["steps"])
    if index + steps >= len(closes):
        raise SequenceRuleError("the outcome label is not available")
    forward = closes[index + steps] / closes[index] - 1
    return forward >= Decimal(str(label["minimum_return"])), forward


@dataclass(frozen=True)
class SequenceDecision:
    symbol: str
    decision_date: date
    decision_index: int
    condition_a: bool
    condition_b_alone: bool
    prior_a: bool
    sequence: bool
    outcome_advance: bool
    forward_price_return: str
    selected_on_future_return: bool = False


@dataclass(frozen=True)
class SymbolSequence:
    symbol: str
    eligible: int
    sequence: int
    sequence_and_advance: int
    control: int
    control_and_advance: int
    component: int
    advances: int

    def qualifies(self) -> bool:
        rule = _status_rule()
        return (
            self.eligible >= int(rule["minimum_eligible_per_symbol"])
            and self.sequence >= int(rule["minimum_sequence_per_symbol"])
            and self.control >= int(rule["minimum_control_per_symbol"])
            and self.advances >= int(rule["minimum_advances_per_symbol"])
        )

    def sequence_frequency(self) -> Decimal:
        return Decimal(self.sequence_and_advance) / Decimal(self.sequence)

    def control_frequency(self) -> Decimal:
        return Decimal(self.control_and_advance) / Decimal(self.control)

    def incremental(self) -> Decimal:
        return self.sequence_frequency() - self.control_frequency()

    def base_rate(self) -> Decimal:
        return Decimal(self.advances) / Decimal(self.eligible)

    def sequence_lift(self) -> Decimal:
        return self.sequence_frequency() - self.base_rate()

    def event_share(self) -> Decimal:
        return Decimal(self.sequence_and_advance) / Decimal(self.advances)


def evaluate_listing(
    symbol: str,
    dates: Sequence[date],
    closes: Sequence[Decimal],
) -> list[SequenceDecision]:
    if len(dates) != len(closes):
        raise SequenceRuleError("dates and closes differ in length")
    label = _leg("outcome_label")
    near = _leg("condition_a")
    steps = int(label["steps"])
    lookback = int(near["lookback_steps"])
    ends = month_end_indices(dates)
    by_month = {(dates[index].year, dates[index].month): index for index in ends}
    later = _leg("condition_b_after_a")["later_month_ends"]
    assert isinstance(later, list)
    rows: list[SequenceDecision] = []
    for index in ends:
        if index < lookback or index + steps >= len(closes):
            continue
        history = closes[: index + 1]
        near_trough = condition_a(history, index)
        bounce = condition_b_alone(history, index)
        prior: list[int] = []
        year, month = dates[index].year, dates[index].month
        for delta in later:
            key = _add_months(year, month, -int(delta))
            prior_index = by_month.get(key)
            if prior_index is None or prior_index >= index:
                continue
            if condition_a(closes[: prior_index + 1], prior_index):
                prior.append(prior_index)
        sequence = False
        if prior:
            latest = max(prior)
            found = trough_after_peak(closes[: latest + 1], latest, lookback)
            if found is not None:
                sequence = condition_b_after_a(history, index, found[1])
        advance, forward = _advance(closes, index)
        rows.append(
            SequenceDecision(
                symbol=symbol,
                decision_date=dates[index],
                decision_index=index,
                condition_a=near_trough,
                condition_b_alone=bounce,
                prior_a=bool(prior),
                sequence=sequence,
                outcome_advance=advance,
                forward_price_return=decimal_text(forward),
                selected_on_future_return=False,
            )
        )
    return rows


def summarise(rows: Sequence[SequenceDecision]) -> SymbolSequence:
    if not rows:
        raise SequenceRuleError("a symbol summary needs the eligible rows")
    symbol = rows[0].symbol
    return SymbolSequence(
        symbol=symbol,
        eligible=len(rows),
        sequence=sum(1 for row in rows if row.sequence),
        sequence_and_advance=sum(1 for row in rows if row.sequence and row.outcome_advance),
        control=sum(1 for row in rows if row.condition_b_alone and not row.prior_a),
        control_and_advance=sum(
            1 for row in rows if row.condition_b_alone and not row.prior_a and row.outcome_advance
        ),
        component=sum(1 for row in rows if row.condition_b_alone),
        advances=sum(1 for row in rows if row.outcome_advance),
    )


def median(values: Sequence[Decimal]) -> Decimal:
    ordered = sorted(values)
    count = len(ordered)
    if count == 0:
        raise SequenceRuleError("median is undefined")
    mid = count // 2
    if count % 2 == 1:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / Decimal(2)


def assign_sequence_status(symbols: Sequence[SymbolSequence]) -> tuple[str, tuple[str, ...]]:
    rule = _status_rule()
    qualifying = [item for item in symbols if item.qualifies()]
    if len(qualifying) < int(rule["minimum_qualifying_symbols"]):
        status = "insufficient_data"
        reasons = ("fewer than five symbols meet the minimum counts",)
    else:
        incremental = median([item.incremental() for item in qualifying])
        floor = Decimal(str(rule["minimum_median_incremental_difference"]))
        if incremental <= floor:
            status = "no_incremental_information"
            reasons = ("the median incremental difference is not greater than zero",)
        else:
            lift = median([item.sequence_lift() for item in qualifying])
            share = median([item.event_share() for item in qualifying])
            share_cap = Decimal(str(rule["rejected_if_median_event_share_at_least"]))
            reasons_list: list[str] = []
            if lift <= 0:
                reasons_list.append("the sequence does not beat the eligible-month base rate")
            if share >= share_cap:
                reasons_list.append("the sequence precedes most labelled advances")
            if reasons_list:
                status = "rejected"
                reasons = tuple(reasons_list)
            else:
                status = "inconclusive"
                reasons = (
                    "the descriptive checks do not reject the sequence on this inspected window",
                )
    if status in FORBIDDEN_CLAIM_STATUSES or status not in ALLOWED_SEQUENCE_STATUSES:
        raise SequenceRuleError("category C cannot promote this status")
    assert_sequence_status_allowed(status)
    return status, reasons


def reconcile_checksum(existing: str | None, recomputed: str) -> str:
    """Second pass inserts nothing when the checksum already matches."""
    if existing is None:
        return "insert"
    if existing != recomputed:
        raise SequenceRuleError("stored checksum differs and was not overwritten")
    return "unchanged"
