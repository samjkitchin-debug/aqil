"""Read-only reconstruction of LH-X-001 and the price-only baselines.

The test skips when the local databases are down. It does not reset them.
"""

from __future__ import annotations

from datetime import date
from decimal import ROUND_HALF_UP, Decimal

import psycopg
import pytest

from aqil_research.certification.accounting import replay_ledger, require_result_matches_replay
from aqil_research.certification.baselines import (
    SPLIT_ADJUSTED_PRICE_RETURN,
    CalendarRebalancePolicy,
    CashFlowOnlyPolicy,
    StaticMixPolicy,
    ThresholdRebalancePolicy,
    equal_weights,
    holdings_overlap_diagnostic,
    price_observation_class,
)
from aqil_research.certification.traceability import (
    classify_progress,
    shared_rows_are_independent,
)
from aqil_research.certification.vintage_gate import GDP_SERIES, load_registered_assessment
from aqil_research.long_horizon.pilot import (
    LOCAL_ETF_URL,
    LOCAL_RESEARCH_URL,
    load_listing_prices,
    run_frozen_comparison,
)
from aqil_research.long_horizon.policies import ImmediateSingleAssetPolicy
from aqil_research.long_horizon.reproduce import reproduce
from aqil_research.long_horizon.simulator import simulate
from aqil_research.long_horizon.spec import PILOT_COST_RATE, PILOT_INTEREST_RATE
from aqil_research.long_horizon.status import FORBIDDEN_FOR_CATEGORY_C, assign_category_c_status

LISTING = date(2019, 7, 25)
FINAL = date(2026, 11, 2)
VWRA_FINAL = Decimal("189.7")
CSPX_FINAL = Decimal("823.57")


def _research():
    try:
        connection = psycopg.connect(LOCAL_RESEARCH_URL, connect_timeout=3)
    except psycopg.OperationalError:
        pytest.skip("local research database is unavailable")
    return connection


def _replay(result, final_prices: dict[str, Decimal]):
    reconstruction = replay_ledger(
        result.cash_flows,
        result.fills,
        result.forgone,
        final_prices,
        cost_rate=Decimal(PILOT_COST_RATE),
    )
    require_result_matches_replay(
        ending_cash=result.ending_cash,
        ending_units=result.ending_units,
        terminal_wealth=result.terminal_wealth,
        terminal_forgone_value=result.terminal_forgone_value,
        total_costs=result.total_costs,
        reconstruction=reconstruction,
    )
    return reconstruction


def test_lh_x_001_reconstructs_and_forgone_value_is_outside_wealth() -> None:
    try:
        etf = psycopg.connect(LOCAL_ETF_URL, connect_timeout=3)
    except psycopg.OperationalError:
        pytest.skip("local ETF database is unavailable")
    with etf:
        etf.read_only = True
        prices, _combined, _symbols = load_listing_prices(etf)
        fx_rows = etf.execute("select count(*) from instruments.fx_observations").fetchone()[0]
        holdings = etf.execute("select count(*) from instruments.holdings_lines").fetchone()[0]
        fund_returns = etf.execute("select count(*) from instruments.fund_returns").fetchone()[0]
    assert fx_rows == 0
    assert holdings == 0
    assert fund_returns == 0
    assert holdings_overlap_diagnostic(holdings) == "unsupported_no_stored_holdings"
    assert price_observation_class("adjusted_close", "adjusted") == SPLIT_ADJUSTED_PRICE_RETURN
    assert min(prices["VWRA"]) == LISTING
    assert FINAL in prices["VWRA"]
    assert prices["VWRA"][FINAL].price == VWRA_FINAL
    assert prices["CSPX"][FINAL].price == CSPX_FINAL

    sessions, contributions, passive, alternative, status = run_frozen_comparison(prices)
    assert sessions[0] == LISTING
    assert sessions[-1] == FINAL
    assert len(sessions) == 1838
    assert len(contributions) == 89
    assert sum(item.amount for item in contributions) == Decimal("89000")
    assert contributions[0].session == LISTING
    assert contributions[-1].session == FINAL
    assert status == "inconclusive"
    assert status not in FORBIDDEN_FOR_CATEGORY_C

    final_prices = {"VWRA": VWRA_FINAL, "CSPX": CSPX_FINAL}
    passive_replay = _replay(passive, final_prices)
    alternative_replay = _replay(alternative, final_prices)
    assert passive.terminal_wealth == Decimal("150430.016335996")
    assert passive.ending_cash == Decimal("187.616335996")
    assert passive.ending_units == {"VWRA": 792}
    assert passive.total_costs == Decimal("88.723660004")
    assert passive.terminal_forgone_value == Decimal(0)
    assert alternative.terminal_wealth == Decimal("155534.402817166")
    assert alternative.ending_cash == Decimal("27.192817166")
    assert alternative.ending_units == {"VWRA": 416, "CSPX": 93}
    assert alternative.total_costs == Decimal("100.672404834")
    assert alternative_replay.forgone_value == Decimal("8726.2")
    sold_vwra = sum(lot.units for lot in alternative.forgone)
    assert sold_vwra == 46
    assert {lot.symbol for lot in alternative.forgone} == {"VWRA"}
    assert Decimal(sold_vwra) * VWRA_FINAL == Decimal("8726.2")
    assert alternative.terminal_wealth == (
        alternative.ending_cash + Decimal(416) * VWRA_FINAL + Decimal(93) * CSPX_FINAL
    )
    wealth_gap = alternative.terminal_wealth - passive.terminal_wealth
    assert wealth_gap == Decimal("5104.386481170")
    assert wealth_gap != alternative.terminal_forgone_value
    assert passive.terminal_wealth.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) == Decimal(
        "150430.02"
    )
    assert alternative.terminal_wealth.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) == Decimal(
        "155534.40"
    )
    assert alternative.terminal_forgone_value.quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    ) == Decimal("8726.20")
    assert passive_replay.forgone_inside_terminal_wealth is False

    first = alternative.fills[0]
    assert first.session == LISTING
    assert first.symbol == "VWRA"
    assert first.side == "buy"
    assert first.units == 12
    assert first.price == Decimal("79.925003")
    assert first.notional == Decimal("959.100036")
    assert first.cost == Decimal("0.959100036")
    assert Decimal("1000") - first.notional - first.cost == Decimal("39.940863964")
    january = next(
        fill
        for fill in alternative.fills
        if fill.session == date(2020, 1, 2) and fill.side == "sell"
    )
    assert january.symbol == "VWRA"
    assert january.units == 9
    assert january.price == Decimal("86.695")
    assert january.notional == Decimal("780.255")
    assert january.cost == Decimal("0.780255")

    with _research() as research:
        research.read_only = True
        evidence = research.execute(
            """
            select body->'alternative'->>'terminal_forgone_value',
                   body->'alternative'->>'terminal_wealth',
                   body->'passive'->>'terminal_wealth',
                   publication_allowed
            from research.evidence_records
            where evidence_id = 'LH-V-001'
            """
        ).fetchone()
        assert evidence == ("8726.2", "155534.402817166", "150430.016335996", False)
        published = research.execute(
            "select count(*) from research.research_runs where publication_allowed"
        ).fetchone()
        assert published[0] == 0


def test_price_only_baselines_use_the_same_schedule_and_are_not_macro() -> None:
    try:
        etf = psycopg.connect(LOCAL_ETF_URL, connect_timeout=3)
    except psycopg.OperationalError:
        pytest.skip("local ETF database is unavailable")
    with etf:
        etf.read_only = True
        prices, _combined, _symbols = load_listing_prices(etf)
    sessions, contributions, passive, _alternative, _status = run_frozen_comparison(prices)
    final_prices = {
        "VWRA": prices["VWRA"][sessions[-1]].price,
        "CSPX": prices["CSPX"][sessions[-1]].price,
    }
    january = {item.session for item in contributions if item.session.month == 1}
    weights = equal_weights("VWRA", "CSPX")
    policies = [
        ImmediateSingleAssetPolicy("CSPX", name="immediate_cpx"),
        StaticMixPolicy(weights, name="static_equal_vwra_cpx"),
        StaticMixPolicy(
            (("CSPX", Decimal("0.7")), ("VWRA", Decimal("0.3"))),
            name="static_cpx_overweight",
        ),
        CalendarRebalancePolicy(weights, name="calendar_fixed_weight"),
        ThresholdRebalancePolicy(weights, Decimal("0.10"), name="threshold_fixed_weight"),
        CashFlowOnlyPolicy(weights, name="cash_flow_only_equal_weight"),
    ]
    shared = dict(
        sessions=sessions,
        prices=prices,
        contributions=contributions,
        portfolio_currency="USD",
        cost_rate=Decimal(PILOT_COST_RATE),
        cash_interest_rate=Decimal(PILOT_INTEREST_RATE),
    )
    for policy in policies:
        assert getattr(policy, "macro_intelligence", False) is False
        rebalance = january if policy.name == "calendar_fixed_weight" else set()
        result = simulate(policy=policy, rebalance_sessions=rebalance, **shared)
        _replay(result, final_prices)
        assert result.total_contributions == passive.total_contributions == Decimal("89000")
        status = assign_category_c_status(
            reconciled=result.reconciliation.matches and passive.reconciliation.matches,
            alternative_terminal=result.terminal_wealth,
            passive_terminal=passive.terminal_wealth,
        )
        assert status not in FORBIDDEN_FOR_CATEGORY_C
        if result.terminal_wealth > passive.terminal_wealth:
            assert status == "inconclusive"
        if policy.name in {
            "static_equal_vwra_cpx",
            "static_cpx_overweight",
            "cash_flow_only_equal_weight",
        }:
            assert all(fill.side == "buy" for fill in result.fills)
            assert result.terminal_forgone_value == Decimal(0)
        if policy.name == "immediate_cpx":
            assert set(result.ending_units) == {"CSPX"}


def test_progress_dependencies_and_vintage_gate_match_the_preserved_database() -> None:
    with _research() as research:
        research.read_only = True
        description = research.execute("select * from research.long_horizon_progress")
        row = dict(
            zip(
                (item.name for item in description.description), description.fetchone(), strict=True
            )
        )
        links = research.execute(
            """
            select dependency_id, relation, independent_confirmation
            from research.research_dependencies
            order by dependency_id
            """
        ).fetchall()
        simulations = research.execute(
            """
            select execution_id
            from research.experiment_executions
            where state = 'succeeded'
              and coalesce(configuration->>'portfolio_path', '') <> 'not_called'
              and coalesce(configuration->>'portfolio_simulator', '') <> 'not_called'
              and coalesce(configuration->>'portfolio_comparison', '') <> 'blocked'
              and coalesce(configuration->>'portfolio_simulation', '') <> 'not_called'
            order by execution_id
            """
        ).fetchall()
    counts = classify_progress(row)
    # LH-X-001 is the category C pilot. LH-X-018 is the later price-only
    # EIMI comparison. Dossier executions stay out of this count.
    assert counts["registered_scenarios"] == 618
    assert counts["registered_signals"] == 309
    assert [item[0] for item in simulations] == ["LH-X-001", "LH-X-018"]
    assert counts["portfolio_simulations"] == 2
    assert counts["point_in_time_results"] == 0
    assert counts["scientifically_validated_findings"] == 0
    assert counts["scientifically_supported_conclusions"] == 0
    assert counts["candidate_rows_marked_as_results"] == 0
    assert counts["registered_comparisons"] == (
        counts["executed_comparisons"] + counts["refused_comparisons"]
    )
    assert row["succeeded_executions"] > row["portfolio_simulations"]
    assert row["blocked_executions"] == 1
    assert row["claims_statistically_supported"] == 0
    assert row["claims_economically_useful"] == 0
    assert row["claims_forward_validated"] == 0
    assert row["executions_published"] == 0
    dependency_ids = [item[0] for item in links]
    assert dependency_ids[:26] == [f"LH-D-{index:03d}" for index in range(1, 27)]
    assert dependency_ids[26:] == [
        f"LH-D-{index:03d}" for index in range(27, 27 + len(dependency_ids) - 26)
    ]
    assert (
        shared_rows_are_independent(
            [
                {"relation": relation, "independent_confirmation": flag}
                for _dependency_id, relation, flag in links
            ]
        )
        is False
    )
    assessment = load_registered_assessment()
    assert assessment.method_count == 26
    assert assessment.eligible_method_ids == ()
    assert assessment.gate6_allowed is False
    assert assessment.gdp_is_required_by_any_method is False
    assert assessment.alfred_historical_archiving == "prohibited"
    assert assessment.blocker is not None
    assert GDP_SERIES in assessment.blocker
    assert "fred.alfred.UNRATE" in assessment.blocker
    reproduced = reproduce()
    assert reproduced["status"] == "inconclusive"
    assert reproduced["execution_id"] == "LH-X-001"
