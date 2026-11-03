"""Portfolio accounting for category C research.

A passing synthetic example certifies the ledger. It does not support an
investment-alpha claim.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_DOWN, Decimal
from typing import Protocol

from aqil_research.long_horizon.money import decimal_text


class SimulatorError(RuntimeError):
    """The instruction is unsupported or the ledger does not reconcile."""


@dataclass(frozen=True)
class PriceBar:
    session: date
    price: Decimal
    currency: str


@dataclass(frozen=True)
class CashFlow:
    session: date
    amount: Decimal
    kind: str


@dataclass(frozen=True)
class Fill:
    session: date
    symbol: str
    side: str
    units: int
    price: Decimal
    notional: Decimal
    cost: Decimal


@dataclass(frozen=True)
class ForgoneLot:
    symbol: str
    units: int
    sale_session: date
    sale_price: Decimal


@dataclass(frozen=True)
class Decision:
    session: date
    action: str
    orders: tuple[tuple[str, str, int], ...]


@dataclass
class Book:
    cash: Decimal
    units: dict[str, int] = field(default_factory=dict)
    forgone: list[ForgoneLot] = field(default_factory=list)

    def units_of(self, symbol: str) -> int:
        return self.units.get(symbol, 0)


@dataclass(frozen=True)
class Snapshot:
    session: date
    cash: Decimal
    units: dict[str, int]
    wealth: Decimal
    forgone_value: Decimal
    contribution: Decimal


@dataclass(frozen=True)
class Reconciliation:
    cash_matches: bool
    units_match: bool
    wealth_matches: bool
    expected_cash: Decimal
    actual_cash: Decimal
    expected_units: dict[str, int]
    actual_units: dict[str, int]

    @property
    def matches(self) -> bool:
        return self.cash_matches and self.units_match and self.wealth_matches


@dataclass
class SimulationResult:
    policy_name: str
    snapshots: list[Snapshot]
    fills: list[Fill]
    cash_flows: list[CashFlow]
    decisions: list[Decision]
    forgone: list[ForgoneLot]
    reconciliation: Reconciliation
    terminal_wealth: Decimal
    total_contributions: Decimal
    total_costs: Decimal
    max_drawdown: Decimal | None

    @property
    def ending_cash(self) -> Decimal:
        if not self.snapshots:
            return Decimal(0)
        return self.snapshots[-1].cash

    @property
    def ending_units(self) -> dict[str, int]:
        if not self.snapshots:
            return {}
        return dict(self.snapshots[-1].units)

    @property
    def terminal_forgone_value(self) -> Decimal:
        if not self.snapshots:
            return Decimal(0)
        return self.snapshots[-1].forgone_value


class Policy(Protocol):
    name: str

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
        """Return (side, symbol, units) in execution order."""


def supports_investment_alpha(_result: SimulationResult) -> bool:
    """Synthetic and category C paths do not establish investment alpha."""
    return False


def whole_units_affordable(cash: Decimal, price: Decimal, cost_rate: Decimal) -> int:
    if price <= 0:
        raise SimulatorError("price must be positive")
    if cost_rate < 0:
        raise SimulatorError("cost rate cannot be negative")
    if cash <= 0:
        return 0
    outlay = price * (Decimal(1) + cost_rate)
    return int((cash / outlay).to_integral_value(rounding=ROUND_DOWN))


def prior_close(bars: dict[date, PriceBar], session: date) -> Decimal:
    """Last stored close strictly before the session.

    The same-session close is an execution price, not a lagged signal.
    """
    earlier = [item for item in bars if item < session]
    if not earlier:
        raise SimulatorError("no prior close; a same-session close is not a lagged signal")
    return bars[max(earlier)].price


def expected_cash_from_events(
    opening_cash: Decimal,
    flows: list[CashFlow],
    fills: list[Fill],
) -> Decimal:
    expected = opening_cash
    for flow in flows:
        if flow.kind not in {"contribution", "transfer", "interest"}:
            raise SimulatorError(f"unexpected cash flow {flow.kind}")
        expected += flow.amount
    for fill in fills:
        if fill.side == "buy":
            expected -= fill.notional + fill.cost
        elif fill.side == "sell":
            expected += fill.notional - fill.cost
        else:
            raise SimulatorError(f"unexpected fill {fill.side}")
    return expected


def expected_units_from_fills(fills: list[Fill]) -> dict[str, int]:
    units: dict[str, int] = {}
    for fill in fills:
        sign = 1 if fill.side == "buy" else -1
        units[fill.symbol] = units.get(fill.symbol, 0) + sign * fill.units
    return {symbol: held for symbol, held in units.items() if held != 0}


def _require_currency(bar: PriceBar, portfolio_currency: str, symbol: str) -> None:
    if bar.currency != portfolio_currency:
        raise SimulatorError(
            "currency conversion is unsupported for "
            f"{symbol} {bar.currency} into {portfolio_currency}"
        )


def _apply_buy(
    book: Book,
    *,
    session: date,
    symbol: str,
    units: int,
    price: Decimal,
    cost_rate: Decimal,
) -> Fill:
    if units < 1:
        raise SimulatorError("a buy must be a positive whole number of units")
    if price <= 0:
        raise SimulatorError("price must be positive")
    notional = price * units
    cost = notional * cost_rate
    outlay = notional + cost
    if outlay > book.cash:
        raise SimulatorError("cash cannot fund the buy and its explicit cost")
    book.cash -= outlay
    book.units[symbol] = book.units_of(symbol) + units
    return Fill(session, symbol, "buy", units, price, notional, cost)


def _apply_sell(
    book: Book,
    *,
    session: date,
    symbol: str,
    units: int,
    price: Decimal,
    cost_rate: Decimal,
) -> Fill:
    if units < 1:
        raise SimulatorError("a sale must be a positive whole number of units")
    held = book.units_of(symbol)
    if units > held:
        raise SimulatorError(f"cannot sell {units} {symbol}; held {held}")
    notional = price * units
    cost = notional * cost_rate
    book.cash += notional - cost
    remaining = held - units
    if remaining == 0:
        book.units.pop(symbol, None)
    else:
        book.units[symbol] = remaining
    book.forgone.append(ForgoneLot(symbol, units, session, price))
    return Fill(session, symbol, "sell", units, price, notional, cost)


def _marked_wealth(book: Book, prices: dict[str, PriceBar]) -> Decimal:
    total = book.cash
    for symbol, units in book.units.items():
        bar = prices.get(symbol)
        if bar is None:
            raise SimulatorError(f"no price for {symbol} on the valuation session")
        total += Decimal(units) * bar.price
    return total


def _forgone_value(lots: list[ForgoneLot], prices: dict[str, PriceBar]) -> Decimal:
    total = Decimal(0)
    for lot in lots:
        bar = prices.get(lot.symbol)
        if bar is None:
            raise SimulatorError(
                f"forgone path for {lot.symbol} has no price on the valuation session"
            )
        total += Decimal(lot.units) * bar.price
    return total


def _max_drawdown(wealths: list[Decimal]) -> Decimal | None:
    if not wealths:
        return None
    peak = wealths[0]
    worst = Decimal(0)
    for value in wealths:
        if value > peak:
            peak = value
        if peak > 0:
            drawdown = (peak - value) / peak
            if drawdown > worst:
                worst = drawdown
    return worst


def _decision_action(
    *,
    contributed: Decimal,
    is_rebalance: bool,
    orders: list[tuple[str, str, int]],
) -> str:
    if contributed > 0 and is_rebalance:
        return "contribute_and_rebalance"
    if contributed > 0:
        return "contribute"
    if is_rebalance:
        return "rebalance"
    if orders:
        return "trade"
    return "hold"


def simulate(
    *,
    policy: Policy,
    sessions: list[date],
    prices: dict[str, dict[date, PriceBar]],
    contributions: list[CashFlow],
    portfolio_currency: str,
    cost_rate: Decimal,
    cash_interest_rate: Decimal | None,
    opening_cash: Decimal = Decimal(0),
    transfers: list[CashFlow] | None = None,
    rebalance_sessions: set[date] | None = None,
    requires_distributions: bool = False,
) -> SimulationResult:
    if requires_distributions:
        raise SimulatorError("distributions are unsupported and are not invented")
    if cash_interest_rate is None:
        raise SimulatorError(
            "cash interest rate must be explicit; an unsupported rate is not invented"
        )
    if cost_rate < 0 or cash_interest_rate < 0:
        raise SimulatorError("rates cannot be negative")
    if not sessions:
        raise SimulatorError("a simulation needs at least one stored session")
    ordered = list(sessions)
    if ordered != sorted(set(ordered)):
        raise SimulatorError("sessions must be unique and in date order")

    contribution_on: dict[date, Decimal] = {}
    for item in contributions:
        if item.kind != "contribution":
            raise SimulatorError("contribution rows must use kind contribution")
        if item.session in contribution_on:
            raise SimulatorError("duplicate contribution session")
        if item.amount < 0:
            raise SimulatorError("a contribution cannot be negative; use a transfer")
        contribution_on[item.session] = item.amount
    if set(contribution_on) - set(ordered):
        raise SimulatorError("a contribution date has no stored session")

    transfer_on: dict[date, Decimal] = {}
    for item in transfers or []:
        if item.kind != "transfer":
            raise SimulatorError("transfer rows must use kind transfer")
        transfer_on[item.session] = transfer_on.get(item.session, Decimal(0)) + item.amount
    if set(transfer_on) - set(ordered):
        raise SimulatorError("a transfer date has no stored session")

    rebalance = rebalance_sessions or set()
    book = Book(cash=opening_cash)
    fills: list[Fill] = []
    flows: list[CashFlow] = []
    decisions: list[Decision] = []
    snapshots: list[Snapshot] = []

    for session in ordered:
        session_prices: dict[str, PriceBar] = {}
        for symbol, bars in prices.items():
            bar = bars.get(session)
            if bar is None:
                raise SimulatorError(
                    f"no stored price for {symbol} on {session.isoformat()}; "
                    "a missing session is not manufactured"
                )
            if bar.session != session:
                raise SimulatorError("price session does not match the valuation session")
            _require_currency(bar, portfolio_currency, symbol)
            session_prices[symbol] = bar

        interest = book.cash * cash_interest_rate
        if interest != 0:
            book.cash += interest
            flows.append(CashFlow(session, interest, "interest"))
        transfer = transfer_on.get(session, Decimal(0))
        if transfer != 0:
            if book.cash + transfer < 0:
                raise SimulatorError("a transfer cannot make cash negative")
            book.cash += transfer
            flows.append(CashFlow(session, transfer, "transfer"))
        contributed = contribution_on.get(session, Decimal(0))
        if contributed > 0:
            book.cash += contributed
            flows.append(CashFlow(session, contributed, "contribution"))

        view = Book(cash=book.cash, units=dict(book.units), forgone=list(book.forgone))
        requested = policy.orders(
            session=session,
            book=view,
            prices=session_prices,
            is_contribution=contributed > 0,
            is_rebalance=session in rebalance,
            cost_rate=cost_rate,
        )
        decisions.append(
            Decision(
                session=session,
                action=_decision_action(
                    contributed=contributed,
                    is_rebalance=session in rebalance,
                    orders=requested,
                ),
                orders=tuple(requested),
            )
        )
        for side, symbol, units in requested:
            if units < 1 or isinstance(units, bool):
                raise SimulatorError("orders use positive whole units")
            bar = session_prices.get(symbol)
            if bar is None:
                raise SimulatorError(f"no stored price for {symbol}")
            if side == "buy":
                fills.append(
                    _apply_buy(
                        book,
                        session=session,
                        symbol=symbol,
                        units=units,
                        price=bar.price,
                        cost_rate=cost_rate,
                    )
                )
            elif side == "sell":
                fills.append(
                    _apply_sell(
                        book,
                        session=session,
                        symbol=symbol,
                        units=units,
                        price=bar.price,
                        cost_rate=cost_rate,
                    )
                )
            else:
                raise SimulatorError(f"unsupported order side {side}")

        wealth = _marked_wealth(book, session_prices)
        forgone_value = _forgone_value(book.forgone, session_prices)
        snapshots.append(
            Snapshot(
                session=session,
                cash=book.cash,
                units={symbol: held for symbol, held in book.units.items() if held != 0},
                wealth=wealth,
                forgone_value=forgone_value,
                contribution=contributed,
            )
        )

    expected_cash = expected_cash_from_events(opening_cash, flows, fills)
    expected_units = expected_units_from_fills(fills)
    actual_units = {symbol: held for symbol, held in book.units.items() if held != 0}
    wealth_matches = True
    for snapshot in snapshots:
        marked = snapshot.cash
        for symbol, held in snapshot.units.items():
            marked += Decimal(held) * prices[symbol][snapshot.session].price
        if marked != snapshot.wealth:
            wealth_matches = False
        active = [lot for lot in book.forgone if lot.sale_session <= snapshot.session]
        forgone_marked = _forgone_value(
            active,
            {lot.symbol: prices[lot.symbol][snapshot.session] for lot in active},
        )
        if forgone_marked != snapshot.forgone_value:
            wealth_matches = False
    reconciliation = Reconciliation(
        cash_matches=expected_cash == book.cash,
        units_match=expected_units == actual_units,
        wealth_matches=wealth_matches,
        expected_cash=expected_cash,
        actual_cash=book.cash,
        expected_units=expected_units,
        actual_units=actual_units,
    )
    if not reconciliation.matches:
        raise SimulatorError(
            "cash, units, and terminal wealth do not reconcile: "
            f"expected cash {decimal_text(expected_cash)} "
            f"actual cash {decimal_text(book.cash)}"
        )
    return SimulationResult(
        policy_name=policy.name,
        snapshots=snapshots,
        fills=fills,
        cash_flows=flows,
        decisions=decisions,
        forgone=list(book.forgone),
        reconciliation=reconciliation,
        terminal_wealth=snapshots[-1].wealth,
        total_contributions=sum((item.amount for item in contributions), Decimal(0)),
        total_costs=sum((fill.cost for fill in fills), Decimal(0)),
        max_drawdown=_max_drawdown([item.wealth for item in snapshots]),
    )
