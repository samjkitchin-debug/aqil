"""Contribution paths. Cash earns nothing because no cash rate is stored."""

from __future__ import annotations

import statistics
from datetime import date
from decimal import Decimal

from aqil_research.discovery.calendar import add_months
from aqil_research.discovery.pairs import AlignedPair, first_on_or_after


def adverse_flags(signals: list[float], rule: str, minimum_history: int = 36) -> list[bool]:
    """True when the predeclared rule retains that contribution as cash.

    A median uses only earlier signals. Until that history exists, the contribution stays in cash.
    """
    history: list[float] = []
    flags: list[bool] = []
    for value in signals:
        if rule == "positive":
            flags.append(value > 0)
        elif rule == "negative":
            flags.append(value < 0)
        elif rule == "above_past_median":
            if len(history) < minimum_history:
                flags.append(True)
            else:
                flags.append(value > statistics.median(history))
        else:
            raise ValueError(f"unknown adverse rule: {rule}")
        history.append(value)
    return flags


def _grow(notional: float, entry_price: float, end_price: float, cost_bps: float) -> float:
    cost = cost_bps / 10_000
    return notional * (1.0 - cost) * end_price / entry_price


def terminal_wealth(
    pairs: tuple[AlignedPair, ...] | list[AlignedPair],
    invested: list[bool],
    prices: dict[date, Decimal],
    end: date,
    cost_bps: float,
) -> float:
    """Sum of contribution values at one stored end date. Uninvested cash stays at notional 1."""
    if end not in prices:
        raise ValueError("the end date is not a stored session")
    end_price = float(prices[end])
    wealth = 0.0
    for pair, flag in zip(pairs, invested, strict=True):
        if not flag:
            wealth += 1.0
            continue
        wealth += _grow(1.0, float(prices[pair.entry]), end_price, cost_bps)
    return wealth


def invest_at_once_flags(count: int) -> list[bool]:
    return [True] * count


def quarterly_flags(pairs: tuple[AlignedPair, ...] | list[AlignedPair]) -> list[bool]:
    return [pair.decision.month in {3, 6, 9, 12} for pair in pairs]


def momentum_flags(
    pairs: tuple[AlignedPair, ...] | list[AlignedPair],
    sessions: tuple[date, ...],
    prices: dict[date, Decimal],
) -> list[bool]:
    """Invest when the price return over the prior 12 calendar months is positive.

    The look-back ends on the last stored session strictly before the entry.
    """
    flags: list[bool] = []
    for pair in pairs:
        prior_sessions = [session for session in sessions if session < pair.entry]
        if not prior_sessions:
            flags.append(False)
            continue
        end = prior_sessions[-1]
        start = first_on_or_after(sessions, add_months(end, -12))
        if start is None or start >= end or start not in prices or end not in prices:
            flags.append(False)
            continue
        flags.append(prices[end] > prices[start] and prices[start] > 0)
    return flags


def beats_immediate(
    pairs: list[AlignedPair],
    signal_invested: list[bool],
    prices: dict[date, Decimal],
    end: date,
    cost_bps: tuple[float, ...] = (0, 10),
) -> bool:
    """True only when the signal path is ahead of immediate investment at every stated cost."""
    immediate = invest_at_once_flags(len(pairs))
    for cost in cost_bps:
        signal_wealth = terminal_wealth(pairs, signal_invested, prices, end, cost)
        immediate_wealth = terminal_wealth(pairs, immediate, prices, end, cost)
        if signal_wealth <= immediate_wealth:
            return False
    return True
