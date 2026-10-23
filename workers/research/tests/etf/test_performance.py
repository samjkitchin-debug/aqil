"""Window acceptance only. cited-fixture is not a market return."""

from __future__ import annotations

from datetime import date
from typing import Literal
from uuid import UUID

import pytest

from aqil_research.etf.performance import (
    WINDOW_MONTHS,
    SeriesRole,
    WindowResult,
    assess_benchmark_window,
    assess_fund_window,
    conventions_are_distinct,
)

# Shape only. This ISIN is not a verified fund, and the text is not a return.
ISIN = "IE00B0000009"
CITED = "cited-fixture"
SOURCE_ID = "fixture-source"
LOCATOR = "synthetic://aqil/etf/performance-window"
BENCHMARK_ID = UUID("88888888-8888-4888-8888-888888888888")
INCEPTION = date(2020, 1, 15)
PERIOD_START = date(2021, 1, 1)
PERIOD_END = date(2021, 12, 31)


def _assess_fund(
    *,
    months: int = 12,
    inception: date | None = INCEPTION,
    period_start: date = PERIOD_START,
    period_end: date = PERIOD_END,
    currency: str = "USD",
    display_currency: str = "USD",
    fx_cited: bool = False,
    value_text: str | None = CITED,
    source_id: str | None = SOURCE_ID,
    source_locator: str | None = LOCATOR,
    return_type: Literal["nav", "price", "total_return", "unknown"] = "total_return",
) -> WindowResult:
    return assess_fund_window(
        isin=ISIN,
        inception=inception,
        period_start=period_start,
        period_end=period_end,
        months=months,
        currency=currency,
        return_type=return_type,
        reinvestment="reinvested",
        display_currency=display_currency,
        fx_cited=fx_cited,
        value_text=value_text,
        source_id=source_id,
        source_locator=source_locator,
    )


def _assess_benchmark(
    *,
    months: int = 12,
    currency: str = "USD",
    display_currency: str = "USD",
    fx_cited: bool = False,
    value_text: str | None = CITED,
    source_id: str | None = SOURCE_ID,
    return_convention: Literal["price", "total_return", "net_total_return", "unknown"] = "price",
) -> WindowResult:
    return assess_benchmark_window(
        benchmark_id=BENCHMARK_ID,
        period_start=PERIOD_START,
        period_end=PERIOD_END,
        months=months,
        currency=currency,
        return_convention=return_convention,
        reinvestment="not_reinvested",
        display_currency=display_currency,
        fx_cited=fx_cited,
        value_text=value_text,
        source_id=source_id,
        source_locator=LOCATOR,
    )


def test_published_windows_are_six_twelve_and_twenty_four_months() -> None:
    assert WINDOW_MONTHS == (6, 12, 24)


@pytest.mark.parametrize("months", [6, 12, 24])
def test_published_month_counts_can_be_accepted(months: int) -> None:
    result = _assess_fund(months=months)
    assert result.accepted is True
    assert result.months == months
    assert result.series_role is SeriesRole.FUND
    assert result.value_text == CITED, "cited-fixture is not a market return"


@pytest.mark.parametrize("months", [3, 36])
def test_other_month_counts_are_refused(months: int) -> None:
    fund = _assess_fund(months=months)
    benchmark = _assess_benchmark(months=months)
    assert fund.accepted is False
    assert fund.value_text is None
    assert fund.series_role is SeriesRole.FUND
    assert benchmark.accepted is False
    assert benchmark.value_text is None
    assert benchmark.series_role is SeriesRole.BENCHMARK


def test_fund_window_without_inception_is_refused() -> None:
    result = _assess_fund(inception=None)
    assert result.accepted is False
    assert result.value_text is None
    assert result.series_role is SeriesRole.FUND
    assert "inception" in result.reason


def test_fund_window_before_inception_is_refused_by_fund_return() -> None:
    result = _assess_fund(
        inception=date(2020, 6, 1),
        period_start=date(2019, 1, 1),
        period_end=date(2019, 12, 31),
    )
    assert result.accepted is False
    assert result.value_text is None
    assert "fund return cannot start before share-class inception" in result.reason


def test_silent_fx_is_refused_for_a_fund_window() -> None:
    result = _assess_fund(currency="USD", display_currency="EUR", fx_cited=False)
    assert result.accepted is False
    assert result.value_text is None
    assert "silent FX" in result.reason
    assert result.series_role is SeriesRole.FUND


def test_cited_fx_accepts_the_fund_series() -> None:
    result = _assess_fund(currency="USD", display_currency="EUR", fx_cited=True)
    assert result.accepted is True
    assert result.series_role is SeriesRole.FUND
    assert result.value_text == CITED, "cited-fixture is not a market return"


def test_benchmark_window_stays_a_benchmark_series() -> None:
    price = _assess_benchmark(return_convention="price")
    total = _assess_benchmark(return_convention="total_return")
    assert price.accepted is True
    assert total.accepted is True
    assert price.series_role is SeriesRole.BENCHMARK
    assert total.series_role is SeriesRole.BENCHMARK
    assert price.value_text == CITED, "cited-fixture is not a market return"
    assert total.value_text == CITED, "cited-fixture is not a market return"
    assert "return convention price" in price.reason
    assert "return convention total_return" in total.reason
    assert price.reason != total.reason
    assert "fund" not in price.reason
    assert "fund" not in total.reason


def test_price_and_total_return_conventions_are_distinct() -> None:
    assert conventions_are_distinct("price", "total_return") is True
    assert conventions_are_distinct("total_return", "price") is True
    assert conventions_are_distinct("price", "price") is False
    price = _assess_fund(return_type="price")
    total = _assess_fund(return_type="total_return")
    assert price.reason != total.reason
    assert "return type price" in price.reason
    assert "return type total_return" in total.reason


def test_missing_value_text_is_refused_rather_than_filled() -> None:
    fund = _assess_fund(value_text=None)
    benchmark = _assess_benchmark(value_text=None)
    missing_source = _assess_fund(source_id=None)
    assert fund.accepted is False
    assert fund.value_text is None
    assert benchmark.accepted is False
    assert benchmark.value_text is None
    assert benchmark.series_role is SeriesRole.BENCHMARK
    assert missing_source.accepted is False
    assert missing_source.value_text is None
    assert not any(character.isdigit() for character in fund.reason)
    assert not any(character.isdigit() for character in benchmark.reason)
