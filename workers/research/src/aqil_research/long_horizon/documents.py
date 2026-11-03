"""Canonical pilot artifact. The hash covers the path, not a separate narrative."""

from __future__ import annotations

from decimal import Decimal

from aqil_research.long_horizon.money import decimal_text
from aqil_research.long_horizon.simulator import SimulationResult


def _decimal_or_none(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return decimal_text(value)


def simulation_document(result: SimulationResult) -> dict[str, object]:
    return {
        "policy_name": result.policy_name,
        "terminal_wealth": decimal_text(result.terminal_wealth),
        "ending_cash": decimal_text(result.ending_cash),
        "ending_units": result.ending_units,
        "total_contributions": decimal_text(result.total_contributions),
        "total_costs": decimal_text(result.total_costs),
        "terminal_forgone_value": decimal_text(result.terminal_forgone_value),
        "max_drawdown": _decimal_or_none(result.max_drawdown),
        "decisions": [
            {
                "session": item.session.isoformat(),
                "action": item.action,
                "orders": [
                    {"side": side, "symbol": symbol, "units": units}
                    for side, symbol, units in item.orders
                ],
            }
            for item in result.decisions
        ],
        "fills": [
            {
                "session": fill.session.isoformat(),
                "symbol": fill.symbol,
                "side": fill.side,
                "units": fill.units,
                "price": decimal_text(fill.price),
                "notional": decimal_text(fill.notional),
                "cost": decimal_text(fill.cost),
            }
            for fill in result.fills
        ],
        "cash_flows": [
            {
                "session": flow.session.isoformat(),
                "amount": decimal_text(flow.amount),
                "kind": flow.kind,
            }
            for flow in result.cash_flows
        ],
        "snapshots": [
            {
                "session": snapshot.session.isoformat(),
                "cash": decimal_text(snapshot.cash),
                "units": snapshot.units,
                "wealth": decimal_text(snapshot.wealth),
                "forgone_value": decimal_text(snapshot.forgone_value),
                "contribution": decimal_text(snapshot.contribution),
            }
            for snapshot in result.snapshots
        ],
        "forgone": [
            {
                "symbol": lot.symbol,
                "units": lot.units,
                "sale_session": lot.sale_session.isoformat(),
                "sale_price": decimal_text(lot.sale_price),
            }
            for lot in result.forgone
        ],
    }


def pilot_artifact(
    *,
    specification_hash: str,
    price_series_sha256: str,
    status: str,
    passive: SimulationResult,
    alternative: SimulationResult,
) -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "experiment_id": "LH-E-001",
        "specification_hash": specification_hash,
        "price_series_sha256": price_series_sha256,
        "status": status,
        "certification_only": True,
        "supports_investment_alpha": False,
        "passive": simulation_document(passive),
        "alternative": simulation_document(alternative),
    }
