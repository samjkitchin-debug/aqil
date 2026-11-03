"""Price-only baselines. None of them is macroeconomic intelligence.

Split-adjusted closes are price returns. They are not certified total returns.
A static CSPX overweight is a structural mix. Currency conversion stays refused
because no foreign-exchange series is stored. Distributions are not invented.
"""

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

SPLIT_ADJUSTED_PRICE_RETURN = "split_adjusted_price_return"
NOT_CERTIFIED_TOTAL_RETURN = "not_certified_total_return"
HOLDINGS_OVERLAP_UNSUPPORTED = "unsupported_no_stored_holdings"


class BaselineError(SimulatorError):
    """A baseline instruction is not a lawful price-only rule."""


def price_observation_class(price_type: str, adjustment_status: str) -> str:
    """Name the stored close. A split adjustment is not a total-return certificate."""
    if price_type == "adjusted_close" and adjustment_status == "adjusted":
        return SPLIT_ADJUSTED_PRICE_RETURN
    raise BaselineError(
        "only a stored split-adjusted close is accepted, and it is not a certified total return"
    )


def holdings_overlap_diagnostic(holdings_line_count: int) -> str:
    """Constituent overlap needs stored holdings. An empty table is not a guess."""
    if holdings_line_count < 0:
        raise BaselineError("a holdings count cannot be negative")
    if holdings_line_count == 0:
        return HOLDINGS_OVERLAP_UNSUPPORTED
    raise BaselineError("stored holdings are not treated as a point-in-time overlap panel here")


def equal_weights(*symbols: str) -> tuple[tuple[str, Decimal], ...]:
    if len(symbols) < 1 or len(symbols) != len(set(symbols)):
        raise BaselineError("equal weights need distinct symbols")
    weight = Decimal(1) / Decimal(len(symbols))
    return tuple((symbol, weight) for symbol in sorted(symbols))


def _normalise_weights(
    weights: tuple[tuple[str, Decimal], ...],
) -> tuple[tuple[str, Decimal], ...]:
    if not weights:
        raise BaselineError("a mix needs a symbol")
    names = [symbol for symbol, _weight in weights]
    if len(names) != len(set(names)):
        raise BaselineError("duplicate symbol in weights")
    if any(weight <= 0 for _symbol, weight in weights):
        raise BaselineError("weights must be positive")
    total = sum((weight for _symbol, weight in weights), Decimal(0))
    if total != 1:
        raise BaselineError("weights must sum to 1")
    return tuple(sorted(weights, key=lambda item: item[0]))


def _refuse_macro_intelligence(enabled: bool) -> None:
    if enabled:
        raise BaselineError("this baseline is not macroeconomic intelligence")


def cash_flow_orders(
    book: Book,
    prices: dict[str, PriceBar],
    weights: tuple[tuple[str, Decimal], ...],
    cost_rate: Decimal,
) -> list[tuple[str, str, int]]:
    """Buy toward the targets with cash only. This path never sells."""
    ordered = _normalise_weights(weights)
    names = tuple(symbol for symbol, _weight in ordered)
    weight_of = dict(ordered)
    cash = book.cash
    units = {name: book.units_of(name) for name in names}
    price_of: dict[str, Decimal] = {}
    for name in names:
        bar = prices.get(name)
        if bar is None:
            raise BaselineError(f"no stored price for {name}")
        if bar.price <= 0:
            raise BaselineError("price must be positive")
        price_of[name] = bar.price
    position_value = sum((Decimal(units[name]) * price_of[name] for name in names), Decimal(0))
    total = position_value + cash
    target = {name: weight_of[name] * total for name in names}
    orders: list[tuple[str, str, int]] = []
    while True:
        choice: str | None = None
        choice_deficit = Decimal(0)
        for name in names:
            deficit = target[name] - Decimal(units[name]) * price_of[name]
            if deficit > choice_deficit:
                choice = name
                choice_deficit = deficit
        if choice is None:
            break
        buy_cap = int((choice_deficit / price_of[choice]).to_integral_value(rounding=ROUND_DOWN))
        affordable = whole_units_affordable(cash, price_of[choice], cost_rate)
        buy_units = min(buy_cap, affordable)
        if buy_units < 1:
            break
        notional = price_of[choice] * buy_units
        cash -= notional + notional * cost_rate
        units[choice] += buy_units
        orders.append(("buy", choice, buy_units))
    return orders


def static_slice_orders(
    book: Book,
    prices: dict[str, PriceBar],
    weights: tuple[tuple[str, Decimal], ...],
    cost_rate: Decimal,
) -> list[tuple[str, str, int]]:
    """Split this contribution by weight. Residual cash is not reallocated."""
    ordered = _normalise_weights(weights)
    budget = book.cash
    orders: list[tuple[str, str, int]] = []
    for symbol, weight in ordered:
        bar = prices.get(symbol)
        if bar is None:
            raise BaselineError(f"no stored price for {symbol}")
        allocation = budget * weight
        units = whole_units_affordable(allocation, bar.price, cost_rate)
        if units >= 1:
            orders.append(("buy", symbol, units))
    return orders


def rebalance_to_weights(
    book: Book,
    prices: dict[str, PriceBar],
    weights: tuple[tuple[str, Decimal], ...],
    cost_rate: Decimal,
) -> list[tuple[str, str, int]]:
    """Sell overweight names, then buy underweight names. Cash is outside the target.

    Equal weights use the same target as the frozen equal-value helper: half of
    position value, with sells and buys in ticker order.
    """
    ordered = _normalise_weights(weights)
    names = tuple(symbol for symbol, _weight in ordered)
    weight_of = dict(ordered)
    cash = book.cash
    units = {name: book.units_of(name) for name in names}
    price_of: dict[str, Decimal] = {}
    for name in names:
        bar = prices.get(name)
        if bar is None:
            raise BaselineError(f"no stored price for {name}")
        price_of[name] = bar.price
    position_value = sum((Decimal(units[name]) * price_of[name] for name in names), Decimal(0))
    orders: list[tuple[str, str, int]] = []
    for name in names:
        held = units[name]
        excess = Decimal(held) * price_of[name] - weight_of[name] * position_value
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
        deficit = weight_of[name] * position_value - Decimal(held) * price_of[name]
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


def _project(
    book: Book, orders: list[tuple[str, str, int]], prices: dict[str, PriceBar], cost_rate: Decimal
) -> Book:
    cash = book.cash
    units = dict(book.units)
    for side, symbol, quantity in orders:
        price = prices[symbol].price
        notional = price * quantity
        cost = notional * cost_rate
        if side == "buy":
            cash -= notional + cost
            units[symbol] = units.get(symbol, 0) + quantity
        elif side == "sell":
            cash += notional - cost
            remaining = units.get(symbol, 0) - quantity
            if remaining <= 0:
                units.pop(symbol, None)
            else:
                units[symbol] = remaining
        else:
            raise BaselineError(f"unsupported order side {side}")
    return Book(cash=cash, units=units)


def _position_value(book: Book, prices: dict[str, PriceBar], names: tuple[str, ...]) -> Decimal:
    total = Decimal(0)
    for name in names:
        bar = prices.get(name)
        if bar is None:
            raise BaselineError(f"no stored price for {name}")
        total += Decimal(book.units_of(name)) * bar.price
    return total


def drift_exceeds(
    book: Book,
    prices: dict[str, PriceBar],
    weights: tuple[tuple[str, Decimal], ...],
    threshold: Decimal,
) -> bool:
    ordered = _normalise_weights(weights)
    names = tuple(symbol for symbol, _weight in ordered)
    weight_of = dict(ordered)
    position_value = _position_value(book, prices, names)
    if position_value == 0:
        return False
    for name, target in weight_of.items():
        current = Decimal(book.units_of(name)) * prices[name].price / position_value
        if abs(current - target) > threshold:
            return True
    return False


@dataclass(frozen=True)
class StaticMixPolicy:
    """Invest each contribution in fixed weights. No sales and no macro signal."""

    weights: tuple[tuple[str, Decimal], ...]
    name: str
    macro_intelligence: bool = False

    def __post_init__(self) -> None:
        _refuse_macro_intelligence(self.macro_intelligence)
        object.__setattr__(self, "weights", _normalise_weights(self.weights))

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
        return static_slice_orders(book, prices, self.weights, cost_rate)


@dataclass(frozen=True)
class CashFlowOnlyPolicy:
    """Use new cash to buy the underweight name. Never sell."""

    weights: tuple[tuple[str, Decimal], ...]
    name: str = "cash_flow_only_rebalance"
    macro_intelligence: bool = False

    def __post_init__(self) -> None:
        _refuse_macro_intelligence(self.macro_intelligence)
        object.__setattr__(self, "weights", _normalise_weights(self.weights))

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
        return cash_flow_orders(book, prices, self.weights, cost_rate)


@dataclass(frozen=True)
class CalendarRebalancePolicy:
    """Deploy contributions by cash flow, and rebalance positions on designated sessions.

    This is a fixed-weight accounting rule. It is not the registered odd-month
    calendar split, and it is not macroeconomic intelligence.
    """

    weights: tuple[tuple[str, Decimal], ...]
    name: str = "calendar_fixed_weight_rebalance"
    macro_intelligence: bool = False

    def __post_init__(self) -> None:
        _refuse_macro_intelligence(self.macro_intelligence)
        object.__setattr__(self, "weights", _normalise_weights(self.weights))

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
        del session
        orders: list[tuple[str, str, int]] = []
        projected = Book(cash=book.cash, units=dict(book.units))
        if is_contribution:
            buys = cash_flow_orders(projected, prices, self.weights, cost_rate)
            orders.extend(buys)
            projected = _project(projected, buys, prices, cost_rate)
        if is_rebalance:
            orders.extend(rebalance_to_weights(projected, prices, self.weights, cost_rate))
        return orders


@dataclass(frozen=True)
class ThresholdRebalancePolicy:
    """Rebalance when a position weight differs from its target by more than the band.

    Cash inside the band is deployed only on a contribution, and only by buying.
    """

    weights: tuple[tuple[str, Decimal], ...]
    threshold: Decimal
    name: str = "threshold_fixed_weight_rebalance"
    macro_intelligence: bool = False

    def __post_init__(self) -> None:
        _refuse_macro_intelligence(self.macro_intelligence)
        object.__setattr__(self, "weights", _normalise_weights(self.weights))
        if self.threshold <= 0:
            raise BaselineError("a threshold band must be positive")

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
        if drift_exceeds(book, prices, self.weights, self.threshold):
            return rebalance_to_weights(book, prices, self.weights, cost_rate)
        if is_contribution:
            return cash_flow_orders(book, prices, self.weights, cost_rate)
        return []


def common_sessions(prices: dict[str, dict[date, PriceBar]]) -> list[date]:
    """Stored overlap, starting at the later listing. No session is manufactured."""
    if not prices:
        raise BaselineError("a window needs stored prices")
    sessions = sorted(set.intersection(*(set(bars) for bars in prices.values())))
    if not sessions:
        raise BaselineError("the listings have no common stored session")
    later_listing = max(min(bars) for bars in prices.values())
    if sessions[0] != later_listing:
        raise BaselineError("the window does not start at the later listing")
    if any(session < later_listing for session in sessions):
        raise BaselineError("refusing a session before the later listing")
    return sessions


def ending_weights(
    cash: Decimal,
    units: dict[str, int],
    final_prices: dict[str, Decimal],
) -> dict[str, Decimal]:
    """Share of terminal wealth in cash and in each held listing."""
    position_value = sum(
        (Decimal(held) * final_prices[symbol] for symbol, held in units.items()),
        Decimal(0),
    )
    wealth = cash + position_value
    if wealth == 0:
        raise BaselineError("ending weights are undefined at zero wealth")
    weights = {
        symbol: Decimal(held) * final_prices[symbol] / wealth for symbol, held in units.items()
    }
    weights["cash"] = cash / wealth
    return weights
