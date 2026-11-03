"""Preregistered month-end intersection. The condition cannot read later closes."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from aqil_research.long_horizon.events.definition import (
    FORBIDDEN_CLAIM_STATUSES,
    FROZEN_PILOT_INTERSECTION,
)
from aqil_research.long_horizon.money import decimal_text


class PilotRuleError(ValueError):
    """The frozen rule was asked to promote a forbidden status or to read ahead."""


def _rule() -> dict[str, object]:
    return FROZEN_PILOT_INTERSECTION


def _intersection() -> dict[str, object]:
    raw = _rule()["intersection"]
    assert isinstance(raw, dict)
    return raw


def _leg(name: str) -> dict[str, object]:
    legs = _intersection()["legs"]
    assert isinstance(legs, list)
    for leg in legs:
        assert isinstance(leg, dict)
        if leg["name"] == name:
            return leg
    raise PilotRuleError(name)


def _status_rule() -> dict[str, object]:
    raw = _rule()["status_rule"]
    assert isinstance(raw, dict)
    return raw


def month_end_indices(dates: Sequence[date]) -> list[int]:
    last: dict[tuple[int, int], int] = {}
    for index, session in enumerate(dates):
        last[(session.year, session.month)] = index
    return [last[key] for key in sorted(last)]


def condition_at(closes: Sequence[Decimal], index: int) -> bool:
    """True only from closes at or before index. Later slots are not read."""
    drawdown = _leg("completed_drawdown")
    momentum = _leg("price_momentum")
    lookback = int(drawdown["lookback_steps"])
    momentum_steps = int(momentum["lookback_steps"])
    if index < lookback or index < momentum_steps:
        raise PilotRuleError("the condition lookback is not available")
    if index >= len(closes):
        raise PilotRuleError("the decision session is outside the series")
    history = closes[: index + 1]
    window = history[index - lookback : index + 1]
    peak_price = max(window)
    peak_offset = window.index(peak_price)
    if peak_offset == len(window) - 1:
        return False
    trough_price = min(window[peak_offset + 1 :])
    depth = trough_price / peak_price - 1
    recovery = history[index] / trough_price - 1
    trailing = history[index] / history[index - momentum_steps] - 1
    return (
        depth <= -Decimal(str(drawdown["minimum_decline"]))
        and recovery >= Decimal(str(drawdown["minimum_retracement_from_trough"]))
        and trailing >= Decimal(str(momentum["minimum_return"]))
    )


def outcome_at(closes: Sequence[Decimal], index: int) -> tuple[bool, Decimal]:
    label = _rule()["outcome_label"]
    assert isinstance(label, dict)
    steps = int(label["steps"])
    if index + steps >= len(closes):
        raise PilotRuleError("the outcome label is not available")
    forward = closes[index + steps] / closes[index] - 1
    return forward >= Decimal(str(label["minimum_return"])), forward


@dataclass(frozen=True)
class DecisionRow:
    symbol: str
    decision_date: date
    decision_index: int
    condition_met: bool
    outcome_advance: bool
    forward_price_return: str
    selected_on_future_return: bool = False


@dataclass(frozen=True)
class SymbolFrequency:
    symbol: str
    eligible: int
    condition: int
    event: int
    condition_and_event: int

    def qualifies(self) -> bool:
        rule = _status_rule()
        return (
            self.eligible >= int(rule["minimum_eligible_per_symbol"])
            and self.condition >= int(rule["minimum_condition_per_symbol"])
            and self.event >= int(rule["minimum_events_per_symbol"])
        )

    def base_rate(self) -> Decimal:
        return Decimal(self.event) / Decimal(self.eligible)

    def conditional_frequency(self) -> Decimal:
        return Decimal(self.condition_and_event) / Decimal(self.condition)

    def condition_frequency(self) -> Decimal:
        return Decimal(self.condition) / Decimal(self.eligible)

    def event_share(self) -> Decimal:
        return Decimal(self.condition_and_event) / Decimal(self.event)

    def lift(self) -> Decimal:
        return self.conditional_frequency() - self.base_rate()


def evaluate_listing(
    symbol: str,
    dates: Sequence[date],
    closes: Sequence[Decimal],
) -> list[DecisionRow]:
    label = _rule()["outcome_label"]
    drawdown = _leg("completed_drawdown")
    assert isinstance(label, dict)
    steps = int(label["steps"])
    lookback = int(drawdown["lookback_steps"])
    rows: list[DecisionRow] = []
    for index in month_end_indices(dates):
        if index < lookback or index + steps >= len(closes):
            continue
        met = condition_at(closes, index)
        advance, forward = outcome_at(closes, index)
        rows.append(
            DecisionRow(
                symbol=symbol,
                decision_date=dates[index],
                decision_index=index,
                condition_met=met,
                outcome_advance=advance,
                forward_price_return=decimal_text(forward),
                selected_on_future_return=False,
            )
        )
    return rows


def summarise(rows: Sequence[DecisionRow]) -> SymbolFrequency:
    if not rows:
        raise PilotRuleError("a symbol summary needs the eligible rows")
    symbol = rows[0].symbol
    return SymbolFrequency(
        symbol=symbol,
        eligible=len(rows),
        condition=sum(1 for row in rows if row.condition_met),
        event=sum(1 for row in rows if row.outcome_advance),
        condition_and_event=sum(1 for row in rows if row.condition_met and row.outcome_advance),
    )


def median(values: Sequence[Decimal]) -> Decimal:
    ordered = sorted(values)
    count = len(ordered)
    if count == 0:
        raise PilotRuleError("median is undefined")
    mid = count // 2
    if count % 2 == 1:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / Decimal(2)


def assign_pilot_status(
    symbols: Sequence[SymbolFrequency],
) -> tuple[str, tuple[str, ...]]:
    rule = _status_rule()
    qualifying = [item for item in symbols if item.qualifies()]
    if len(qualifying) < int(rule["minimum_qualifying_symbols"]):
        status = "insufficient_data"
        reasons = ("fewer than five symbols meet the minimum counts",)
    else:
        lift = median([item.lift() for item in qualifying])
        frequency = median([item.condition_frequency() for item in qualifying])
        share = median([item.event_share() for item in qualifying])
        common = Decimal(str(rule["common_if_median_condition_frequency_at_least"]))
        accompanies = Decimal(str(rule["accompanies_advances_if_median_event_share_at_least"]))
        reasons_list: list[str] = []
        if lift <= 0:
            reasons_list.append("median lift is not positive")
        if frequency >= common:
            reasons_list.append("the condition is common in ordinary eligible months")
        if share >= accompanies:
            reasons_list.append("the condition accompanies most labelled advances")
        if reasons_list:
            status = "rejected"
            reasons = tuple(reasons_list)
        else:
            status = "inconclusive"
            reasons = ("the descriptive checks do not reject the conjunction on this window",)
    if status in FORBIDDEN_CLAIM_STATUSES:
        raise PilotRuleError("category C cannot promote this status")
    return status, reasons


def describe_pilot(symbols: Sequence[SymbolFrequency]) -> dict[str, object]:
    """Status, reasons, and medians from the frozen rule."""
    status, reasons = assign_pilot_status(symbols)
    qualifying = [item for item in symbols if item.qualifies()]
    minimum = int(_status_rule()["minimum_qualifying_symbols"])
    if len(qualifying) < minimum:
        medians = {
            "lift": "not_defined",
            "condition_frequency": "not_defined",
            "event_share": "not_defined",
        }
    else:
        medians = {
            "lift": decimal_text(median([item.lift() for item in qualifying])),
            "condition_frequency": decimal_text(
                median([item.condition_frequency() for item in qualifying])
            ),
            "event_share": decimal_text(median([item.event_share() for item in qualifying])),
        }
    return {
        "status": status,
        "reasons": list(reasons),
        "medians": medians,
        "qualifying_symbols": len(qualifying),
        "pooled": pooled_counts(symbols),
    }


def pooled_counts(symbols: Sequence[SymbolFrequency]) -> dict[str, int]:
    return {
        "eligible": sum(item.eligible for item in symbols),
        "condition": sum(item.condition for item in symbols),
        "event": sum(item.event for item in symbols),
        "condition_and_event": sum(item.condition_and_event for item in symbols),
        "false_positives": sum(item.condition - item.condition_and_event for item in symbols),
        "false_negatives": sum(item.event - item.condition_and_event for item in symbols),
        "condition_false": sum(item.eligible - item.condition for item in symbols),
        "outcome_false": sum(item.eligible - item.event for item in symbols),
    }
