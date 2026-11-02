"""Market, NAV, and total-return calculations stay separate.

No return is produced before inception. A distributing class does not get a
total return from price changes alone. An accumulating class does not have a
dividend added on top of an adjusted close. Benchmark series are not accepted
by these functions.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict

DistributionPolicy = Literal["accumulating", "distributing", "unknown"]
SeriesKind = Literal["market", "nav"]


class ReturnResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    series_kind: SeriesKind | Literal["total_return"]
    accepted: bool
    reason: str
    value: Decimal | None


def simple_return(
    *,
    series_kind: SeriesKind,
    start_value: Decimal,
    end_value: Decimal,
    start_unit: str,
    end_unit: str,
    inception: date | None,
    period_start: date,
) -> ReturnResult:
    """Price or NAV return. Units that differ are refused, including GBX and GBP."""

    if inception is None:
        return _refused(series_kind, "share-class inception is unavailable")
    if period_start < inception:
        return _refused(series_kind, "no fund return before inception")
    if start_unit.strip().upper() != end_unit.strip().upper():
        return _refused(series_kind, "GBX and GBP stay distinct; differing quote units are refused")
    if start_value <= 0 or end_value < 0:
        return _refused(
            series_kind, "a non-positive start value or a negative end value is refused"
        )
    return ReturnResult(
        series_kind=series_kind,
        accepted=True,
        reason=f"accepted {series_kind} return in {start_unit.strip().upper()}",
        value=(end_value / start_value) - Decimal(1),
    )


def total_return(
    *,
    distribution_policy: DistributionPolicy,
    start_value: Decimal,
    end_value: Decimal,
    start_unit: str,
    end_unit: str,
    dividend: Decimal | None,
    uses_adjusted_close: bool,
    inception: date | None,
    period_start: date,
) -> ReturnResult:
    """Total return is calculated on its own. It is not a renamed market return."""

    if inception is None or period_start < inception:
        return _refused("total_return", "no fund return before inception")
    if start_unit.strip().upper() != end_unit.strip().upper():
        return _refused(
            "total_return", "GBX and GBP stay distinct; differing quote units are refused"
        )
    if distribution_policy == "distributing" and dividend is None:
        return _refused(
            "total_return",
            "no total return from price changes alone for a distributing class",
        )
    if distribution_policy == "accumulating" and uses_adjusted_close and dividend is not None:
        return _refused(
            "total_return",
            "an accumulating class does not add a dividend on top of an adjusted close",
        )
    if distribution_policy == "unknown":
        return _refused("total_return", "distribution policy is unknown")
    if start_value <= 0 or end_value < 0:
        return _refused(
            "total_return", "a non-positive start value or a negative end value is refused"
        )
    if distribution_policy == "distributing":
        if dividend is None or dividend < 0 or uses_adjusted_close:
            return _refused("total_return", "a dividend is not added to an adjusted close")
        return ReturnResult(
            series_kind="total_return",
            accepted=True,
            reason="accepted distributing total return from price plus dividend",
            value=((end_value + dividend) / start_value) - Decimal(1),
        )
    if dividend is not None:
        return _refused(
            "total_return",
            "an accumulating class does not add a dividend on top of an adjusted close",
        )
    return ReturnResult(
        series_kind="total_return",
        accepted=True,
        reason="accepted accumulating total return without a second dividend",
        value=(end_value / start_value) - Decimal(1),
    )


def _refused(series_kind: SeriesKind | Literal["total_return"], reason: str) -> ReturnResult:
    return ReturnResult(series_kind=series_kind, accepted=False, reason=reason, value=None)
