"""Price-only paths. Macro states are not inputs. Costs stay the category C rate."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_DOWN, Decimal

from aqil_research.long_horizon.policies import rebalance_to_equal_value
from aqil_research.long_horizon.simulator import (
    Book,
    PriceBar,
    SimulatorError,
    whole_units_affordable,
)
from aqil_research.long_horizon.vwra_discovery.comparison import MOMENTUM_BASELINE, MOMENTUM_STEPS


def trailing_return_before(
    bars: dict[date, PriceBar],
    session: date,
    steps: int = MOMENTUM_STEPS,
) -> Decimal | None:
    """Simple return ending at the last close strictly before the session."""
    earlier = sorted(day for day in bars if day < session)
    if len(earlier) <= steps:
        return None
    start = bars[earlier[-1 - steps]].price
    end = bars[earlier[-1]].price
    if start <= 0 or end <= 0:
        return None
    return end / start - Decimal(1)


@dataclass
class EqualCashMixPolicy:
    """Split each contribution in cash, then rebalance to equal value in January."""

    name: str = "equal_cash_vwra_eimi_january_equal_value"
    symbols: tuple[str, str] = ("EIMI", "VWRA")

    def orders(
        self,
        *,
        session: date,
        book: Book,
        prices: dict[str, PriceBar],
        is_contribution: bool,
        is_rebalance: bool,
        cost_rate: Decimal,
    ) -> list[tuple[str, str, int]]:
        orders: list[tuple[str, str, int]] = []
        projected = Book(cash=book.cash, units=dict(book.units))
        if is_contribution:
            target = projected.cash / Decimal(2)
            for symbol in self.symbols:
                bar = prices.get(symbol)
                if bar is None:
                    raise SimulatorError(f"no stored price for {symbol}")
                cap = int((target / bar.price).to_integral_value(rounding=ROUND_DOWN))
                affordable = whole_units_affordable(projected.cash, bar.price, cost_rate)
                units = min(cap, affordable)
                if units < 1:
                    continue
                orders.append(("buy", symbol, units))
                projected.cash -= bar.price * units * (Decimal(1) + cost_rate)
                projected.units[symbol] = projected.units_of(symbol) + units
        if is_rebalance:
            orders.extend(rebalance_to_equal_value(projected, prices, self.symbols, cost_rate))
        return orders


@dataclass
class RelativeMomentumPolicy:
    """Give the contribution to the higher prior 252-session return.

    A tie or a missing lookback buys VWRA. No holding is sold. The same-session
    close is an execution price and is not the signal.
    """

    prices: dict[str, dict[date, PriceBar]]
    name: str = "contribution_to_higher_trailing_return_252"
    steps: int = MOMENTUM_STEPS
    baseline: str = MOMENTUM_BASELINE
    fallbacks: int = 0
    ties: int = 0
    choices: list[str] = field(default_factory=list)

    def orders(
        self,
        *,
        session: date,
        book: Book,
        prices: dict[str, PriceBar],
        is_contribution: bool,
        is_rebalance: bool,
        cost_rate: Decimal,
    ) -> list[tuple[str, str, int]]:
        del is_rebalance
        if not is_contribution:
            return []
        returns = {
            symbol: trailing_return_before(self.prices[symbol], session, self.steps)
            for symbol in ("EIMI", "VWRA")
        }
        eimi = returns["EIMI"]
        vwra = returns["VWRA"]
        if eimi is None or vwra is None:
            chosen = self.baseline
            self.fallbacks += 1
        elif eimi == vwra:
            chosen = self.baseline
            self.ties += 1
        elif eimi > vwra:
            chosen = "EIMI"
        else:
            chosen = "VWRA"
        self.choices.append(chosen)
        bar = prices.get(chosen)
        if bar is None:
            raise SimulatorError(f"no stored price for {chosen}")
        units = whole_units_affordable(book.cash, bar.price, cost_rate)
        if units < 1:
            return []
        return [("buy", chosen, units)]
