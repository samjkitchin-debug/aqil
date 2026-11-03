"""Known answers for the price-only baselines."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from aqil_research.certification.baselines import (
    BaselineError,
    CalendarRebalancePolicy,
    CashFlowOnlyPolicy,
    StaticMixPolicy,
    ThresholdRebalancePolicy,
    cash_flow_orders,
    equal_weights,
    rebalance_to_weights,
    static_slice_orders,
)
from aqil_research.long_horizon.policies import rebalance_to_equal_value
from aqil_research.long_horizon.simulator import Book, CashFlow, PriceBar, simulate

D1 = date(2020, 1, 2)
D2 = date(2020, 1, 3)


def _prices(rows: dict[str, list[tuple[date, str]]]) -> dict:
    books: dict = {}
    for symbol, series in rows.items():
        books[symbol] = {
            session: PriceBar(session, Decimal(price), "USD") for session, price in series
        }
    return books


def _run(policy, sessions, prices, contributions, rebalance=None, cost=Decimal(0)):
    return simulate(
        policy=policy,
        sessions=sessions,
        prices=prices,
        contributions=contributions,
        portfolio_currency="USD",
        cost_rate=cost,
        cash_interest_rate=Decimal(0),
        rebalance_sessions=set(rebalance or []),
    )


def test_static_equal_mix_leaves_the_unallocated_slice_in_cash() -> None:
    prices = _prices({"CSPX": [(D1, "10")], "VWRA": [(D1, "10")]})
    policy = StaticMixPolicy(equal_weights("VWRA", "CSPX"), name="static_equal")
    result = _run(
        policy,
        [D1],
        prices,
        [CashFlow(D1, Decimal("100"), "contribution")],
        cost=Decimal("0.1"),
    )
    assert result.ending_units == {"CSPX": 4, "VWRA": 4}
    assert result.ending_cash == Decimal("12")
    assert result.terminal_wealth == Decimal("92")
    assert result.total_costs == Decimal("8")
    assert all(fill.side == "buy" for fill in result.fills)
    assert policy.macro_intelligence is False


def test_static_cpx_overweight_is_not_macro_intelligence() -> None:
    prices = _prices({"CSPX": [(D1, "10")], "VWRA": [(D1, "10")]})
    weights = (("CSPX", Decimal("0.7")), ("VWRA", Decimal("0.3")))
    policy = StaticMixPolicy(weights, name="static_cpx_overweight")
    result = _run(policy, [D1], prices, [CashFlow(D1, Decimal("100"), "contribution")])
    assert result.ending_units == {"CSPX": 7, "VWRA": 3}
    assert result.ending_cash == Decimal(0)
    assert result.terminal_wealth == Decimal("100")
    with pytest.raises(BaselineError, match="not macroeconomic intelligence"):
        StaticMixPolicy(weights, name="rejected", macro_intelligence=True)


def test_static_slice_does_not_spend_another_names_residual() -> None:
    book = Book(cash=Decimal("100"))
    prices = {
        "CSPX": PriceBar(D1, Decimal("30"), "USD"),
        "VWRA": PriceBar(D1, Decimal("30"), "USD"),
    }
    orders = static_slice_orders(book, prices, equal_weights("CSPX", "VWRA"), Decimal(0))
    assert orders == [("buy", "CSPX", 1), ("buy", "VWRA", 1)]


def test_cash_flow_rebalance_matches_the_hand_account_and_never_sells() -> None:
    prices = _prices({"A": [(D1, "10")], "B": [(D1, "10")]})
    policy = CashFlowOnlyPolicy(equal_weights("A", "B"), name="cash_flow")
    result = _run(
        policy,
        [D1],
        prices,
        [CashFlow(D1, Decimal("100"), "contribution")],
        cost=Decimal("0.1"),
    )
    assert result.ending_units == {"A": 5, "B": 4}
    assert result.ending_cash == Decimal("1")
    assert result.terminal_wealth == Decimal("91")
    assert result.total_costs == Decimal("9")
    assert result.forgone == []
    assert result.terminal_forgone_value == Decimal(0)


def test_equal_weight_rebalance_matches_the_frozen_helper() -> None:
    book = Book(cash=Decimal(0), units={"CSPX": 1, "VWRA": 10})
    prices = {
        "CSPX": PriceBar(D1, Decimal("10"), "USD"),
        "VWRA": PriceBar(D1, Decimal("10"), "USD"),
    }
    weights = equal_weights("VWRA", "CSPX")
    assert rebalance_to_weights(book, prices, weights, Decimal(0)) == rebalance_to_equal_value(
        book,
        prices,
        ("VWRA", "CSPX"),
        Decimal(0),
    )


def test_threshold_rebalance_sells_only_outside_the_band() -> None:
    prices = _prices(
        {
            "A": [(D1, "10"), (D2, "30")],
            "B": [(D1, "10"), (D2, "10")],
        }
    )
    policy = ThresholdRebalancePolicy(
        equal_weights("A", "B"),
        Decimal("0.10"),
        name="threshold",
    )
    outside = _run(policy, [D1, D2], prices, [CashFlow(D1, Decimal("100"), "contribution")])
    assert outside.ending_units == {"A": 4, "B": 8}
    assert outside.ending_cash == Decimal(0)
    assert outside.terminal_wealth == Decimal("200")
    assert outside.terminal_forgone_value == Decimal("30")
    inside_prices = _prices({"A": [(D1, "10"), (D2, "10")], "B": [(D1, "10"), (D2, "10")]})
    inside = _run(
        policy,
        [D1, D2],
        inside_prices,
        [
            CashFlow(D1, Decimal("100"), "contribution"),
            CashFlow(D2, Decimal("20"), "contribution"),
        ],
    )
    assert inside.ending_units == {"A": 6, "B": 6}
    assert inside.ending_cash == Decimal(0)
    assert all(fill.side == "buy" for fill in inside.fills)


def test_calendar_rebalance_is_a_fixed_weight_rule_not_a_macro_signal() -> None:
    prices = _prices(
        {
            "A": [(D1, "10"), (D2, "30")],
            "B": [(D1, "10"), (D2, "10")],
        }
    )
    policy = CalendarRebalancePolicy(equal_weights("A", "B"), name="calendar_fixed_weight")
    result = _run(
        policy,
        [D1, D2],
        prices,
        [CashFlow(D1, Decimal("100"), "contribution")],
        rebalance={D2},
    )
    assert result.ending_units == {"A": 4, "B": 8}
    assert result.terminal_wealth == Decimal("200")
    assert result.terminal_forgone_value == Decimal("30")
    assert policy.macro_intelligence is False
    assert "macro" not in policy.name


def test_cash_flow_orders_stop_when_the_next_unit_would_cross_the_target() -> None:
    book = Book(cash=Decimal("25"))
    prices = {
        "A": PriceBar(D1, Decimal("10"), "USD"),
        "B": PriceBar(D1, Decimal("10"), "USD"),
    }
    orders = cash_flow_orders(book, prices, equal_weights("A", "B"), Decimal(0))
    assert orders == [("buy", "A", 1), ("buy", "B", 1)]
