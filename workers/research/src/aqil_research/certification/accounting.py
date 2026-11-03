"""Independent replay of cash, units, wealth, and forgone value.

The replay does not call the simulator's reconciliation helpers. Terminal
wealth is cash plus held units marked at the final price. Forgone value is
the same final price times units that were sold. It is not added to wealth.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal

from aqil_research.long_horizon.simulator import CashFlow, Fill, ForgoneLot


class AccountingDefect(RuntimeError):
    """The events do not support the reported cash, units, or wealth."""


WEALTH_COMPONENTS = ("cash", "held_units_marked_at_the_final_price")
FORGONE_COMPONENT = "sold_units_marked_at_the_final_price"
EXACT_TOLERANCE = Decimal(0)


@dataclass(frozen=True)
class LedgerReconstruction:
    cash: Decimal
    units: dict[str, int]
    position_value: Decimal
    wealth: Decimal
    forgone_value: Decimal
    total_costs: Decimal
    total_contributions: Decimal

    @property
    def forgone_inside_terminal_wealth(self) -> bool:
        return False


def _require_identity(left: Decimal, right: Decimal, label: str) -> None:
    if left - right != EXACT_TOLERANCE:
        raise AccountingDefect(f"{label} differs by {left - right}")


def replay_ledger(
    flows: list[CashFlow],
    fills: list[Fill],
    lots: list[ForgoneLot],
    final_prices: dict[str, Decimal],
    *,
    opening_cash: Decimal = Decimal(0),
    cost_rate: Decimal | None = None,
) -> LedgerReconstruction:
    """Recompute the ending ledger from events. Tolerance is exact Decimal zero."""
    cash = opening_cash
    for flow in flows:
        if flow.kind not in {"contribution", "transfer", "interest"}:
            raise AccountingDefect(f"unexpected cash flow {flow.kind}")
        cash += flow.amount
    units: dict[str, int] = {}
    total_costs = Decimal(0)
    for fill in fills:
        if fill.units < 1 or isinstance(fill.units, bool):
            raise AccountingDefect("a fill must be a positive whole number of units")
        notional = fill.price * fill.units
        _require_identity(fill.notional, notional, "fill notional")
        if cost_rate is not None:
            _require_identity(fill.cost, fill.notional * cost_rate, "fill cost")
        if fill.cost < 0:
            raise AccountingDefect("a fill cost cannot be negative")
        total_costs += fill.cost
        held = units.get(fill.symbol, 0)
        if fill.side == "buy":
            cash -= fill.notional + fill.cost
            units[fill.symbol] = held + fill.units
        elif fill.side == "sell":
            if fill.units > held:
                raise AccountingDefect(f"sell exceeds held units of {fill.symbol}")
            cash += fill.notional - fill.cost
            remaining = held - fill.units
            if remaining == 0:
                units.pop(fill.symbol, None)
            else:
                units[fill.symbol] = remaining
        else:
            raise AccountingDefect(f"unexpected fill {fill.side}")
    sold: dict[str, int] = defaultdict(int)
    recorded: dict[str, int] = defaultdict(int)
    for fill in fills:
        if fill.side == "sell":
            sold[fill.symbol] += fill.units
    for lot in lots:
        recorded[lot.symbol] += lot.units
    if dict(sold) != dict(recorded):
        raise AccountingDefect("forgone lots do not match the units sold")
    if cash < 0:
        raise AccountingDefect("replayed cash is negative")
    position_value = Decimal(0)
    for symbol, held in units.items():
        price = final_prices.get(symbol)
        if price is None:
            raise AccountingDefect(f"no final price for held {symbol}")
        position_value += Decimal(held) * price
    forgone_value = Decimal(0)
    for lot in lots:
        price = final_prices.get(lot.symbol)
        if price is None:
            raise AccountingDefect(f"no final price for forgone {lot.symbol}")
        if lot.units < 1:
            raise AccountingDefect("a forgone lot must be a positive number of units")
        forgone_value += Decimal(lot.units) * price
    wealth = cash + position_value
    contributions = sum(
        (flow.amount for flow in flows if flow.kind == "contribution"),
        Decimal(0),
    )
    return LedgerReconstruction(
        cash=cash,
        units=units,
        position_value=position_value,
        wealth=wealth,
        forgone_value=forgone_value,
        total_costs=total_costs,
        total_contributions=contributions,
    )


def require_result_matches_replay(
    *,
    ending_cash: Decimal,
    ending_units: dict[str, int],
    terminal_wealth: Decimal,
    terminal_forgone_value: Decimal,
    total_costs: Decimal,
    reconstruction: LedgerReconstruction,
) -> None:
    """Fail if the simulator totals are not the replay totals."""
    _require_identity(reconstruction.cash, ending_cash, "cash")
    if reconstruction.units != ending_units:
        raise AccountingDefect("replayed units do not match the ending book")
    _require_identity(reconstruction.wealth, terminal_wealth, "terminal wealth")
    _require_identity(reconstruction.forgone_value, terminal_forgone_value, "forgone value")
    _require_identity(reconstruction.total_costs, total_costs, "costs")
    _require_identity(
        reconstruction.wealth,
        reconstruction.cash + reconstruction.position_value,
        "wealth components",
    )
    if FORGONE_COMPONENT in WEALTH_COMPONENTS:
        raise AccountingDefect("forgone value was classified as terminal wealth")
    if (
        reconstruction.forgone_value != 0
        and reconstruction.wealth
        == reconstruction.cash + reconstruction.position_value + reconstruction.forgone_value
    ):
        raise AccountingDefect("forgone value was included in terminal wealth")
