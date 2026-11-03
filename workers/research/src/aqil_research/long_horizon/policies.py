"""Frozen pilot policies. Orders are whole units. Costs stay explicit."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_DOWN, Decimal

from aqil_research.long_horizon.simulator import (
    Book,
    PriceBar,
    SimulatorError,
    whole_units_affordable,
)


def rebalance_to_equal_value(
    book: Book,
    prices: dict[str, PriceBar],
    symbols: tuple[str, str],
    cost_rate: Decimal,
) -> list[tuple[str, str, int]]:
    """Sell the overweight name, then buy the underweight name.

    Target value is half of the position value before the rebalance. Cash is
    not part of that target. Sells and buys run in ticker order. A sale records
    a forgone lot in the engine, which is outside portfolio wealth.
    """
    names = tuple(sorted(symbols))
    if len(names) != 2 or len(set(names)) != 2:
        raise SimulatorError("equal-value rebalance needs two distinct symbols")
    cash = book.cash
    units = {name: book.units_of(name) for name in names}
    price_of: dict[str, Decimal] = {}
    for name in names:
        bar = prices.get(name)
        if bar is None:
            raise SimulatorError(f"no stored price for {name}")
        price_of[name] = bar.price
    position_value = sum(
        (Decimal(units[name]) * price_of[name] for name in names),
        Decimal(0),
    )
    target = position_value / 2
    orders: list[tuple[str, str, int]] = []
    for name in names:
        held = units[name]
        excess = Decimal(held) * price_of[name] - target
        if excess <= 0 or held <= 0:
            continue
        sell_units = min(
            held,
            int((excess / price_of[name]).to_integral_value(rounding=ROUND_DOWN)),
        )
        if sell_units < 1:
            continue
        notional = price_of[name] * sell_units
        cash += notional - notional * cost_rate
        units[name] = held - sell_units
        orders.append(("sell", name, sell_units))
    for name in names:
        held = units[name]
        deficit = target - Decimal(held) * price_of[name]
        if deficit <= 0:
            continue
        buy_cap = int((deficit / price_of[name]).to_integral_value(rounding=ROUND_DOWN))
        affordable = whole_units_affordable(cash, price_of[name], cost_rate)
        buy_units = min(buy_cap, affordable)
        if buy_units < 1:
            continue
        notional = price_of[name] * buy_units
        cash -= notional + notional * cost_rate
        units[name] = held + buy_units
        orders.append(("buy", name, buy_units))
    return orders


@dataclass(frozen=True)
class ImmediateSingleAssetPolicy:
    """Invest available cash into one symbol on contribution sessions."""

    symbol: str
    name: str = "immediate_vwra"

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
        del session, is_rebalance
        if not is_contribution:
            return []
        bar = prices.get(self.symbol)
        if bar is None:
            raise SimulatorError(f"no stored price for {self.symbol}")
        units = whole_units_affordable(book.cash, bar.price, cost_rate)
        if units < 1:
            return []
        return [("buy", self.symbol, units)]


@dataclass(frozen=True)
class OddEvenJanuaryPolicy:
    """Odd months buy VWRA, even months buy CSPX, January rebalances.

    The month rule uses the session's calendar month. January is odd, so the
    January contribution buys VWRA before the equal-value rebalance.
    """

    odd_month_symbol: str = "VWRA"
    even_month_symbol: str = "CSPX"
    name: str = "odd_month_vwra_even_month_cspx_january_equal_value_rebalance"

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
            symbol = self.odd_month_symbol if session.month % 2 == 1 else self.even_month_symbol
            bar = prices.get(symbol)
            if bar is None:
                raise SimulatorError(f"no stored price for {symbol}")
            units = whole_units_affordable(projected.cash, bar.price, cost_rate)
            if units >= 1:
                orders.append(("buy", symbol, units))
                projected.cash -= bar.price * units * (Decimal(1) + cost_rate)
                projected.units[symbol] = projected.units_of(symbol) + units
        if is_rebalance:
            orders.extend(
                rebalance_to_equal_value(
                    projected,
                    prices,
                    (self.odd_month_symbol, self.even_month_symbol),
                    cost_rate,
                )
            )
        return orders
