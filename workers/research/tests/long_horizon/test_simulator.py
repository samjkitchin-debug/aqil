"""Synthetic ledger cases with known cash, units, and terminal wealth."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from aqil_research.long_horizon.policies import (
    ImmediateSingleAssetPolicy,
    OddEvenJanuaryPolicy,
)
from aqil_research.long_horizon.simulator import (
    CashFlow,
    PriceBar,
    SimulatorError,
    prior_close,
    simulate,
    supports_investment_alpha,
)
from aqil_research.long_horizon.status import assign_category_c_status

D1 = date(2020, 1, 2)
D2 = date(2020, 1, 3)
D3 = date(2020, 1, 6)


class Scripted:
    name = "scripted"

    def __init__(self, plan: dict[date, list[tuple[str, str, int]]]) -> None:
        self.plan = plan

    def orders(self, *, session: date, book, prices, is_contribution, is_rebalance, cost_rate):
        del book, prices, is_contribution, is_rebalance, cost_rate
        return list(self.plan.get(session, []))


def _bars(series: dict[str, list[tuple[date, str]]], currency: str = "USD") -> dict:
    books: dict = {}
    for symbol, rows in series.items():
        books[symbol] = {
            session: PriceBar(session, Decimal(price), currency) for session, price in rows
        }
    return books


def test_residual_cash_and_whole_units() -> None:
    prices = _bars({"VWRA": [(D1, "10")]})
    result = simulate(
        policy=Scripted({D1: [("buy", "VWRA", 2)]}),
        sessions=[D1],
        prices=prices,
        contributions=[CashFlow(D1, Decimal("25"), "contribution")],
        portfolio_currency="USD",
        cost_rate=Decimal(0),
        cash_interest_rate=Decimal(0),
    )
    assert result.ending_units == {"VWRA": 2}
    assert result.ending_cash == Decimal("5")
    assert result.terminal_wealth == Decimal("25")
    assert result.reconciliation.matches


def test_explicit_cost_on_buy() -> None:
    prices = _bars({"VWRA": [(D1, "10")]})
    result = simulate(
        policy=ImmediateSingleAssetPolicy("VWRA"),
        sessions=[D1],
        prices=prices,
        contributions=[CashFlow(D1, Decimal("100"), "contribution")],
        portfolio_currency="USD",
        cost_rate=Decimal("0.1"),
        cash_interest_rate=Decimal(0),
    )
    # Unit outlay is 11. Nine units cost 99. Residual cash is 1.
    assert result.ending_units == {"VWRA": 9}
    assert result.ending_cash == Decimal("1")
    assert result.total_costs == Decimal("9")
    assert result.terminal_wealth == Decimal("91")


def test_sale_keeps_the_forgone_path_of_the_sold_asset() -> None:
    prices = _bars(
        {
            "A": [(D1, "10"), (D2, "20"), (D3, "30")],
            "B": [(D1, "10"), (D2, "10"), (D3, "10")],
        }
    )
    result = simulate(
        policy=Scripted(
            {
                D1: [("buy", "A", 10)],
                D2: [("sell", "A", 10), ("buy", "B", 16)],
            }
        ),
        sessions=[D1, D2, D3],
        prices=prices,
        contributions=[CashFlow(D1, Decimal("110"), "contribution")],
        portfolio_currency="USD",
        cost_rate=Decimal("0.1"),
        cash_interest_rate=Decimal(0),
    )
    assert result.ending_units == {"B": 16}
    assert result.ending_cash == Decimal("4")
    assert result.terminal_wealth == Decimal("164")
    assert result.terminal_forgone_value == Decimal("300")
    assert result.total_costs == Decimal("46")
    assert result.forgone[0].symbol == "A"
    assert result.forgone[0].units == 10
    assert result.terminal_wealth + result.terminal_forgone_value != result.terminal_wealth
    assert supports_investment_alpha(result) is False


def test_cash_interest_is_explicit_and_applied_before_the_contribution() -> None:
    prices = _bars({"VWRA": [(D1, "10")]})
    result = simulate(
        policy=ImmediateSingleAssetPolicy("VWRA"),
        sessions=[D1],
        prices=prices,
        contributions=[CashFlow(D1, Decimal("20"), "contribution")],
        portfolio_currency="USD",
        cost_rate=Decimal(0),
        cash_interest_rate=Decimal("0.1"),
        opening_cash=Decimal("100"),
    )
    # Interest on 100 is 10. Cash is then 130, which buys 13 units.
    assert result.ending_units == {"VWRA": 13}
    assert result.ending_cash == Decimal(0)
    assert result.terminal_wealth == Decimal("130")
    assert result.cash_flows[0].kind == "interest"
    assert result.cash_flows[0].amount == Decimal("10")


def test_transfer_cannot_overdraw_cash() -> None:
    prices = _bars({"VWRA": [(D1, "10")]})
    with pytest.raises(SimulatorError, match="cannot make cash negative"):
        simulate(
            policy=ImmediateSingleAssetPolicy("VWRA"),
            sessions=[D1],
            prices=prices,
            contributions=[],
            portfolio_currency="USD",
            cost_rate=Decimal(0),
            cash_interest_rate=Decimal(0),
            opening_cash=Decimal("4"),
            transfers=[CashFlow(D1, Decimal("-5"), "transfer")],
        )


def test_external_transfer_is_in_the_cash_identity() -> None:
    prices = _bars({"VWRA": [(D1, "10")]})
    result = simulate(
        policy=Scripted({}),
        sessions=[D1],
        prices=prices,
        contributions=[CashFlow(D1, Decimal("15"), "contribution")],
        portfolio_currency="USD",
        cost_rate=Decimal(0),
        cash_interest_rate=Decimal(0),
        opening_cash=Decimal("10"),
        transfers=[CashFlow(D1, Decimal("5"), "transfer")],
    )
    assert result.ending_cash == Decimal("30")
    assert result.ending_units == {}
    assert result.terminal_wealth == Decimal("30")


def test_currency_conversion_is_refused() -> None:
    prices = _bars({"EUNA": [(D1, "10")]}, currency="EUR")
    with pytest.raises(SimulatorError, match="currency conversion is unsupported"):
        simulate(
            policy=ImmediateSingleAssetPolicy("EUNA", name="eur"),
            sessions=[D1],
            prices=prices,
            contributions=[CashFlow(D1, Decimal("100"), "contribution")],
            portfolio_currency="USD",
            cost_rate=Decimal(0),
            cash_interest_rate=Decimal(0),
        )


def test_missing_session_is_not_manufactured() -> None:
    prices = _bars({"VWRA": [(D1, "10")]})
    with pytest.raises(SimulatorError, match="not manufactured"):
        simulate(
            policy=ImmediateSingleAssetPolicy("VWRA"),
            sessions=[D1, D2],
            prices=prices,
            contributions=[],
            portfolio_currency="USD",
            cost_rate=Decimal(0),
            cash_interest_rate=Decimal(0),
        )


def test_distributions_and_unspecified_interest_are_refused() -> None:
    prices = _bars({"VWRA": [(D1, "10")]})
    with pytest.raises(SimulatorError, match="distributions are unsupported"):
        simulate(
            policy=ImmediateSingleAssetPolicy("VWRA"),
            sessions=[D1],
            prices=prices,
            contributions=[],
            portfolio_currency="USD",
            cost_rate=Decimal(0),
            cash_interest_rate=Decimal(0),
            requires_distributions=True,
        )
    with pytest.raises(SimulatorError, match="cash interest rate must be explicit"):
        simulate(
            policy=ImmediateSingleAssetPolicy("VWRA"),
            sessions=[D1],
            prices=prices,
            contributions=[],
            portfolio_currency="USD",
            cost_rate=Decimal(0),
            cash_interest_rate=None,
        )


def test_prior_close_does_not_read_the_execution_session() -> None:
    bars = {
        D1: PriceBar(D1, Decimal("10"), "USD"),
        D2: PriceBar(D2, Decimal("7"), "USD"),
        D3: PriceBar(D3, Decimal("11"), "USD"),
    }
    assert prior_close(bars, D3) == Decimal("7")
    with pytest.raises(SimulatorError, match="not a lagged signal"):
        prior_close(bars, D1)


def test_january_rebalance_matches_hand_accounting_and_rejects_the_inequality() -> None:
    july = date(2019, 7, 25)
    august = date(2019, 8, 1)
    january = date(2020, 1, 2)
    sessions = [july, august, january]
    prices = _bars(
        {
            "VWRA": [(july, "10"), (august, "10"), (january, "30")],
            "CSPX": [(july, "10"), (august, "10"), (january, "10")],
        }
    )
    contributions = [CashFlow(session, Decimal("100"), "contribution") for session in sessions]
    common = dict(
        sessions=sessions,
        prices=prices,
        contributions=contributions,
        portfolio_currency="USD",
        cost_rate=Decimal(0),
        cash_interest_rate=Decimal(0),
        rebalance_sessions={january},
    )
    passive = simulate(policy=ImmediateSingleAssetPolicy("VWRA"), **common)
    alternative = simulate(policy=OddEvenJanuaryPolicy(), **common)
    assert passive.ending_units == {"VWRA": 23}
    assert passive.ending_cash == Decimal("10")
    assert passive.terminal_wealth == Decimal("700")
    assert alternative.ending_units == {"VWRA": 9, "CSPX": 23}
    assert alternative.ending_cash == Decimal(0)
    assert alternative.terminal_wealth == Decimal("500")
    assert alternative.terminal_forgone_value == Decimal("120")
    assert passive.total_contributions == alternative.total_contributions
    assert [item.session for item in passive.decisions] == sessions
    status = assign_category_c_status(
        reconciled=alternative.reconciliation.matches and passive.reconciliation.matches,
        alternative_terminal=alternative.terminal_wealth,
        passive_terminal=passive.terminal_wealth,
    )
    assert status == "rejected"
    assert supports_investment_alpha(alternative) is False


def test_a_larger_synthetic_terminal_wealth_stays_inconclusive() -> None:
    status = assign_category_c_status(
        reconciled=True,
        alternative_terminal=Decimal("2"),
        passive_terminal=Decimal("1"),
    )
    assert status == "inconclusive"
