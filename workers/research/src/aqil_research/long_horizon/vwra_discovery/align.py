"""Matched dates, excess returns, and predeclared partial associations.

These functions do not read a database and do not invent a foreign-exchange rate.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from aqil_research.long_horizon.etf_protocol.rules import _pearson, _ranks
from aqil_research.long_horizon.money import decimal_text
from aqil_research.long_horizon.vwra_discovery.comparison import (
    PRICE_CONTROL,
    RELATIVE_CONTROL,
    shared_date,
)
from aqil_research.long_horizon.vwra_discovery.guards import assert_state_feature, latest_period
from aqil_research.long_horizon.vwra_discovery.statistics import Association, linear_association


def assert_no_fx(rate: object) -> None:
    """A currency conversion is refused. An empty rate is not a rate of one."""
    if rate is not None:
        raise ValueError("fx_observations does not supply a conversion for this comparison")


def state_on_or_before(feature_id: str, period_end: date, anchor: date, value: str) -> str | None:
    """Drop a later period. The value is not carried forward and an outcome is not a state."""
    assert_state_feature(feature_id)
    chosen = latest_period((period_end,), anchor)
    if chosen is None:
        return None
    return value


def pair_shared_date(vwra_day: date, eimi_day: date) -> date:
    return shared_date(vwra_day, eimi_day)


def usable_symbol_state(anchor_day: date, shared: date) -> bool:
    """A listing's own state is usable only when that listing's anchor is not later."""
    return anchor_day <= shared


MARKET_PREFIXES = (
    "trailing_return_",
    "drawdown_",
    "volatility_",
    "recovery_",
    "relative_performance_",
    "downside_volatility_",
    "trend_persistence_",
)


def is_market_feature(feature_id: str) -> bool:
    return feature_id.startswith(MARKET_PREFIXES)


def market_values(anchor_day: date, shared: date, features: dict[str, str]) -> dict[str, str]:
    """Price features of a later anchor are not a state at the earlier shared date."""
    if not usable_symbol_state(anchor_day, shared):
        return {}
    return {
        feature_id: value for feature_id, value in features.items() if is_market_feature(feature_id)
    }


def refuse_fx_count(count: int) -> None:
    """Stop when a rate exists. An empty table is not a rate of one."""
    if count != 0:
        raise ValueError("fx_observations is not empty; no conversion is calculated")
    assert_no_fx(None)


def linear_residuals(target: list[Decimal], control: list[Decimal]) -> list[Decimal] | None:
    """Residuals of target after a linear projection on control. No filled gap."""
    count = len(target)
    if count != len(control) or count < 3:
        return None
    mean_control = sum(control, Decimal(0)) / Decimal(count)
    mean_target = sum(target, Decimal(0)) / Decimal(count)
    variance = sum((item - mean_control) ** 2 for item in control)
    if variance == 0:
        return None
    covariance = sum(
        (left - mean_control) * (right - mean_target)
        for left, right in zip(control, target, strict=True)
    )
    slope = covariance / variance
    intercept = mean_target - slope * mean_control
    return [right - (intercept + slope * left) for left, right in zip(control, target, strict=True)]


def partial_linear(
    target: list[Decimal], feature: list[Decimal], control: list[Decimal]
) -> Association:
    """Pearson after removing a linear price control. The control is not a macro cut."""
    detail = f"n={len(target)}. Partial Pearson uses a predeclared price control."
    left = linear_residuals(feature, control)
    right = linear_residuals(target, control)
    if left is None or right is None:
        return Association(None, "insufficient_effective_sample", None, len(target), detail)
    score = linear_association(list(zip(left, right, strict=True)))
    return Association(
        score.result_text, score.refusal_reason, score.p_value_text, len(target), detail
    )


def partial_rank(
    target: list[Decimal], feature: list[Decimal], control: list[Decimal]
) -> Association:
    """Spearman of rank residuals. Ranks use the same average-tie rule as the protocol."""
    detail = f"n={len(target)}. Partial Spearman uses rank residuals of a predeclared control."
    if len(target) < 3:
        return Association(None, "insufficient_effective_sample", None, len(target), detail)
    left = linear_residuals(_ranks(feature), _ranks(control))
    right = linear_residuals(_ranks(target), _ranks(control))
    if left is None or right is None:
        return Association(None, "insufficient_effective_sample", None, len(target), detail)
    rho = _pearson(left, right)
    if rho is None:
        return Association(None, "variance is zero", None, len(target), detail)
    return Association(decimal_text(rho), None, None, len(target), detail)


def control_feature_id(kind: str) -> str:
    if kind == "trailing_return_252":
        return PRICE_CONTROL
    if kind == "relative_performance":
        return RELATIVE_CONTROL
    raise ValueError(f"unknown price control {kind}")
