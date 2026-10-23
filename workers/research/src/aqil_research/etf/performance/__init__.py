"""ETF return windows.

Fund and benchmark series stay separate. A window is accepted only when a
cited value already exists. This module does not calculate a return or an
FX rate.
"""

from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, ValidationError

from aqil_research.etf.contracts import BenchmarkReturn, FundReturn

WINDOW_MONTHS: tuple[Literal[6, 12, 24], ...] = (6, 12, 24)

ReturnType = Literal["nav", "price", "total_return", "unknown"]
Reinvestment = Literal["reinvested", "not_reinvested", "unknown"]
ReturnConvention = Literal["price", "total_return", "net_total_return", "unknown"]


class SeriesRole(StrEnum):
    FUND = "fund"
    BENCHMARK = "benchmark"


class WindowResult(BaseModel):
    """One assessed window. A refusal carries no value."""

    model_config = ConfigDict(extra="forbid")

    series_role: SeriesRole
    months: Literal[6, 12, 24]
    accepted: bool
    reason: str
    value_text: str | None


def assess_fund_window(
    *,
    isin: str,
    inception: date | None,
    period_start: date,
    period_end: date,
    months: int,
    currency: str,
    return_type: ReturnType,
    reinvestment: Reinvestment,
    display_currency: str,
    fx_cited: bool,
    value_text: str | None,
    source_id: str | None,
    source_locator: str | None,
) -> WindowResult:
    """Accept a cited fund window, or refuse it without inventing a figure.

    The series role is always the fund. A missing inception, a period before
    inception, an unpublished month count, a missing citation, or a display
    currency with no cited FX rate is refused.
    """

    published = _published_months(months)
    if published is None:
        return _refused(SeriesRole.FUND, months, f"{months} months is not an accepted window")
    if inception is None:
        return _refused(SeriesRole.FUND, months, "share-class inception is unavailable")
    refused = _fx_or_citation_refusal(
        series_role=SeriesRole.FUND,
        months=published,
        currency=currency,
        display_currency=display_currency,
        fx_cited=fx_cited,
        value_text=value_text,
        source_id=source_id,
        source_locator=source_locator,
    )
    if refused is not None or value_text is None or source_id is None or source_locator is None:
        return refused or _refused(SeriesRole.FUND, months, "cited return is unavailable")
    try:
        cited = FundReturn(
            share_class_isin=isin,
            inception_date=inception,
            period_start=period_start,
            period_end=period_end,
            currency=currency,
            return_type=return_type,
            reinvestment=reinvestment,
            value_text=value_text,
            source_id=source_id,
            source_locator=source_locator,
        )
    except ValidationError as exc:
        return _refused(SeriesRole.FUND, months, _validation_reason(exc))
    return WindowResult(
        series_role=SeriesRole.FUND,
        months=published,
        accepted=True,
        reason=(
            "accepted fund series with return type "
            f"{cited.return_type} and reinvestment {cited.reinvestment}"
        ),
        value_text=cited.value_text,
    )


def assess_benchmark_window(
    *,
    benchmark_id: UUID,
    period_start: date,
    period_end: date,
    months: int,
    currency: str,
    return_convention: ReturnConvention,
    reinvestment: Reinvestment,
    display_currency: str,
    fx_cited: bool,
    value_text: str | None,
    source_id: str | None,
    source_locator: str | None,
) -> WindowResult:
    """Accept a cited benchmark window. This series is not the fund return.

    Price and total-return conventions stay distinct. Silent FX and a missing
    citation are refused. Share-class inception is not applied.
    """

    published = _published_months(months)
    if published is None:
        return _refused(
            SeriesRole.BENCHMARK,
            months,
            f"{months} months is not an accepted window",
        )
    refused = _fx_or_citation_refusal(
        series_role=SeriesRole.BENCHMARK,
        months=published,
        currency=currency,
        display_currency=display_currency,
        fx_cited=fx_cited,
        value_text=value_text,
        source_id=source_id,
        source_locator=source_locator,
    )
    if refused is not None or value_text is None or source_id is None or source_locator is None:
        return refused or _refused(SeriesRole.BENCHMARK, months, "cited return is unavailable")
    try:
        cited = BenchmarkReturn(
            benchmark_id=benchmark_id,
            period_start=period_start,
            period_end=period_end,
            currency=currency,
            return_convention=return_convention,
            reinvestment=reinvestment,
            value_text=value_text,
            source_id=source_id,
            source_locator=source_locator,
        )
    except ValidationError as exc:
        return _refused(SeriesRole.BENCHMARK, months, _validation_reason(exc))
    return WindowResult(
        series_role=SeriesRole.BENCHMARK,
        months=published,
        accepted=True,
        reason=(
            "accepted benchmark series with return convention "
            f"{cited.return_convention} and reinvestment {cited.reinvestment}"
        ),
        value_text=cited.value_text,
    )


def conventions_are_distinct(left: str, right: str) -> bool:
    """True when the two return conventions differ."""

    return left != right


def _published_months(months: int) -> Literal[6, 12, 24] | None:
    if months == 6 or months == 12 or months == 24:
        return months
    return None


def _fx_or_citation_refusal(
    *,
    series_role: SeriesRole,
    months: Literal[6, 12, 24],
    currency: str,
    display_currency: str,
    fx_cited: bool,
    value_text: str | None,
    source_id: str | None,
    source_locator: str | None,
) -> WindowResult | None:
    if display_currency != currency and not fx_cited:
        return _refused(series_role, months, "silent FX is refused")
    if value_text is None or source_id is None or source_locator is None:
        return _refused(series_role, months, "cited return is unavailable")
    return None


def _refused(series_role: SeriesRole, months: int, reason: str) -> WindowResult:
    published = _published_months(months)
    if published is None:
        # 3 and 36 are refused calls, not published windows. The result literal
        # cannot store them, and the caller still needs accepted=False.
        return WindowResult.model_construct(
            series_role=series_role,
            months=months,
            accepted=False,
            reason=reason,
            value_text=None,
        )
    return WindowResult(
        series_role=series_role,
        months=published,
        accepted=False,
        reason=reason,
        value_text=None,
    )


def _validation_reason(exc: ValidationError) -> str:
    parts: list[str] = []
    for err in exc.errors():
        message = str(err.get("msg", ""))
        prefix = "Value error, "
        if message.startswith(prefix):
            message = message.removeprefix(prefix)
        if message and message not in parts:
            parts.append(message)
    if not parts:
        return "cited return was refused"
    return "; ".join(parts)


__all__ = [
    "WINDOW_MONTHS",
    "SeriesRole",
    "WindowResult",
    "assess_benchmark_window",
    "assess_fund_window",
    "conventions_are_distinct",
]
