"""Synthetic ledgers with known cash, units, wealth, and forgone value."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from aqil_research.certification.accounting import (
    EXACT_TOLERANCE,
    WEALTH_COMPONENTS,
    replay_ledger,
    require_result_matches_replay,
)
from aqil_research.certification.baselines import (
    SPLIT_ADJUSTED_PRICE_RETURN,
    common_sessions,
    holdings_overlap_diagnostic,
    price_observation_class,
)
from aqil_research.long_horizon.eligibility import next_eligible_session
from aqil_research.long_horizon.policies import ImmediateSingleAssetPolicy
from aqil_research.long_horizon.simulator import (
    CashFlow,
    PriceBar,
    SimulatorError,
    prior_close,
    simulate,
)
from aqil_research.long_horizon.status import FORBIDDEN_FOR_CATEGORY_C, assign_category_c_status

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


def test_one_complete_trade_history_matches_hand_accounting() -> None:
    prices = _bars(
        {
            "A": [(D1, "10"), (D2, "12")],
            "B": [(D1, "10"), (D2, "10")],
        }
    )
    result = simulate(
        policy=Scripted({D1: [("buy", "A", 10)], D2: [("sell", "A", 4), ("buy", "B", 2)]}),
        sessions=[D1, D2],
        prices=prices,
        contributions=[CashFlow(D1, Decimal("110"), "contribution")],
        portfolio_currency="USD",
        cost_rate=Decimal("0.1"),
        cash_interest_rate=Decimal(0),
    )
    replay = replay_ledger(
        result.cash_flows,
        result.fills,
        result.forgone,
        {"A": Decimal("12"), "B": Decimal("10")},
        cost_rate=Decimal("0.1"),
    )
    require_result_matches_replay(
        ending_cash=result.ending_cash,
        ending_units=result.ending_units,
        terminal_wealth=result.terminal_wealth,
        terminal_forgone_value=result.terminal_forgone_value,
        total_costs=result.total_costs,
        reconstruction=replay,
    )
    assert result.ending_units == {"A": 6, "B": 2}
    assert result.ending_cash == Decimal("21.2")
    assert result.terminal_wealth == Decimal("113.2")
    assert result.terminal_forgone_value == Decimal("48")
    assert result.total_costs == Decimal("16.8")
    assert result.total_contributions == Decimal("110")
    assert replay.forgone_inside_terminal_wealth is False
    assert "sold_units_marked_at_the_final_price" not in WEALTH_COMPONENTS
    assert result.terminal_wealth + result.terminal_forgone_value == Decimal("161.2")
    assert result.terminal_wealth - replay.wealth == EXACT_TOLERANCE


def test_drawdown_is_the_peak_to_trough_fraction() -> None:
    prices = _bars({"VWRA": [(D1, "10"), (D2, "5"), (D3, "8")]})
    result = simulate(
        policy=ImmediateSingleAssetPolicy("VWRA"),
        sessions=[D1, D2, D3],
        prices=prices,
        contributions=[CashFlow(D1, Decimal("100"), "contribution")],
        portfolio_currency="USD",
        cost_rate=Decimal(0),
        cash_interest_rate=Decimal(0),
    )
    assert result.terminal_wealth == Decimal("80")
    assert result.max_drawdown == Decimal("0.5")


def test_cash_opportunity_cost_is_only_the_explicit_interest() -> None:
    shared = dict(
        policy=Scripted({}),
        sessions=[D1],
        prices={},
        contributions=[],
        portfolio_currency="USD",
        cost_rate=Decimal(0),
        opening_cash=Decimal("100"),
    )
    with_interest = simulate(cash_interest_rate=Decimal("0.1"), **shared)
    without = simulate(cash_interest_rate=Decimal(0), **shared)
    assert with_interest.terminal_wealth - without.terminal_wealth == Decimal("10")
    assert with_interest.cash_flows[0].kind == "interest"


def test_missing_price_currency_distribution_and_interest_fail_closed() -> None:
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
    with pytest.raises(SimulatorError, match="currency conversion is unsupported"):
        simulate(
            policy=ImmediateSingleAssetPolicy("EUNA"),
            sessions=[D1],
            prices=_bars({"EUNA": [(D1, "10")]}, currency="EUR"),
            contributions=[CashFlow(D1, Decimal("20"), "contribution")],
            portfolio_currency="USD",
            cost_rate=Decimal(0),
            cash_interest_rate=Decimal(0),
        )
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


def test_a_single_currency_book_can_be_marked_in_that_currency() -> None:
    result = simulate(
        policy=ImmediateSingleAssetPolicy("EUNA", name="eur_book"),
        sessions=[D1],
        prices=_bars({"EUNA": [(D1, "10")]}, currency="EUR"),
        contributions=[CashFlow(D1, Decimal("25"), "contribution")],
        portfolio_currency="EUR",
        cost_rate=Decimal(0),
        cash_interest_rate=Decimal(0),
    )
    assert result.ending_units == {"EUNA": 2}
    assert result.ending_cash == Decimal("5")
    assert result.terminal_wealth == Decimal("25")


def test_replay_is_deterministic_and_a_printed_date_waits_for_the_next_session() -> None:
    prices = _bars({"VWRA": [(D1, "10"), (D2, "11")]})
    shared = dict(
        policy=ImmediateSingleAssetPolicy("VWRA"),
        sessions=[D1, D2],
        prices=prices,
        contributions=[CashFlow(D1, Decimal("30"), "contribution")],
        portfolio_currency="USD",
        cost_rate=Decimal("0.001"),
        cash_interest_rate=Decimal(0),
    )
    first = simulate(**shared)
    second = simulate(**shared)
    assert first.terminal_wealth == second.terminal_wealth
    assert [(fill.session, fill.units, fill.cost) for fill in first.fills] == [
        (fill.session, fill.units, fill.cost) for fill in second.fills
    ]
    assert next_eligible_session(D1, [D1, D2]) == D2
    assert next_eligible_session(D2, [D1, D2]) is None
    bars = {D1: PriceBar(D1, Decimal("10"), "USD"), D2: PriceBar(D2, Decimal("11"), "USD")}
    assert prior_close(bars, D2) == Decimal("10")


def test_window_starts_at_the_later_listing_and_prices_are_not_total_return() -> None:
    earlier = date(2016, 11, 3)
    listing = date(2019, 7, 25)
    prices = _bars(
        {
            "CSPX": [(earlier, "10"), (listing, "11")],
            "VWRA": [(listing, "12")],
        }
    )
    assert common_sessions(prices) == [listing]
    assert price_observation_class("adjusted_close", "adjusted") == SPLIT_ADJUSTED_PRICE_RETURN
    with pytest.raises(Exception, match="not a certified total return"):
        price_observation_class("close", "raw")
    assert holdings_overlap_diagnostic(0) == "unsupported_no_stored_holdings"
    with pytest.raises(Exception, match="not treated as a point-in-time"):
        holdings_overlap_diagnostic(3)


def test_a_larger_terminal_wealth_stays_inconclusive() -> None:
    status = assign_category_c_status(
        reconciled=True,
        alternative_terminal=Decimal("2"),
        passive_terminal=Decimal("1"),
    )
    assert status == "inconclusive"
    assert status not in FORBIDDEN_FOR_CATEGORY_C
