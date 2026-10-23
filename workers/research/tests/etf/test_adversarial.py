"""Adversarial checks for ETF identity, rights, and return windows.

These tests do not invent a verified catalogue or a holdings file.
Uniqueness of a share-class ISIN is a database rule on instruments.share_classes.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from uuid import UUID

import pytest
from aqil_research.etf.fundamentals import issuer_cost_facts
from aqil_research.etf.holdings import coverage_for_record, top_ten_overlap
from aqil_research.etf.identity import (
    ANCHOR_ISIN,
    anchor_identity,
    candidate_catalogue,
    ticker_change_keeps_share_class,
)
from aqil_research.etf.performance import (
    WINDOW_MONTHS,
    assess_benchmark_window,
    assess_fund_window,
    conventions_are_distinct,
)
from aqil_research.etf.vetting import EvidenceInput, assess_anchor, assess_quality

from aqil_research.etf.contracts import (
    BenchmarkReturn,
    EtfRightsError,
    EtfShareClass,
    assert_automated_collection_allowed,
    load_etf_rights_fragment,
)
from aqil_research.sources.rights import load_source_rights

REPO_ROOT = Path(__file__).resolve().parents[4]
FRAGMENTS = REPO_ROOT / "docs" / "sources" / "etf" / "fragments"
SOURCE_RIGHTS = REPO_ROOT / "docs" / "sources" / "SOURCE_RIGHTS.csv"
SHAPE_ISIN = "IE00B0000009"
BENCHMARK_ID = UUID("11111111-1111-4111-8111-111111111111")


def _shape_share_class() -> EtfShareClass:
    """Shape example only. IE00B0000009 is not a real fund."""
    return EtfShareClass(
        isin=SHAPE_ISIN,
        base_currency="USD",
        distribution_policy="unknown",
        hedge_status="unknown",
        inception_date=None,
        evidence_status="unverified",
        benchmark_id=None,
        listings=[],
    )


def test_duplicate_isin_uniqueness_is_enforced_in_instruments_share_classes() -> None:
    """Two Python objects can share an ISIN. That does not satisfy the database rule."""
    catalogue = candidate_catalogue()
    assert sum(row.isin == ANCHOR_ISIN for row in catalogue) == 1
    assert [row.isin for row in catalogue if row.isin is not None] == [ANCHOR_ISIN]

    left = _shape_share_class()
    right = _shape_share_class()
    assert left is not right
    assert left.isin == right.isin == SHAPE_ISIN


def test_ticker_change_does_not_add_a_share_class() -> None:
    history = ticker_change_keeps_share_class()
    assert history.identifier_kind == "ticker"
    assert history.identifier_value == "VWRA-OLD"
    assert anchor_identity().isin == ANCHOR_ISIN
    non_null_isins = [row.isin for row in candidate_catalogue() if row.isin is not None]
    assert non_null_isins == [ANCHOR_ISIN]


def test_price_and_total_return_indexes_stay_distinct() -> None:
    assert conventions_are_distinct("price", "total_return") is True
    assert 6 in WINDOW_MONTHS
    price = BenchmarkReturn(
        benchmark_id=BENCHMARK_ID,
        period_start=date(2024, 1, 1),
        period_end=date(2024, 6, 30),
        currency="USD",
        return_convention="price",
        reinvestment="unknown",
        value_text="not-a-market-return",
        source_id="test",
        source_locator="test",
    )
    total_return = BenchmarkReturn(
        benchmark_id=BENCHMARK_ID,
        period_start=date(2024, 1, 1),
        period_end=date(2024, 6, 30),
        currency="USD",
        return_convention="total_return",
        reinvestment="unknown",
        value_text="not-a-market-return",
        source_id="test",
        source_locator="test",
    )
    assert price.return_convention != total_return.return_convention
    assert conventions_are_distinct(price.return_convention, total_return.return_convention)
    for convention in (price.return_convention, total_return.return_convention):
        window = assess_benchmark_window(
            benchmark_id=BENCHMARK_ID,
            period_start=date(2024, 1, 1),
            period_end=date(2024, 6, 30),
            months=6,
            currency="USD",
            return_convention=convention,
            reinvestment="unknown",
            display_currency="USD",
            fx_cited=False,
            value_text="not-a-market-return",
            source_id="test",
            source_locator="test",
        )
        assert window.series_role == "benchmark"


def test_restricted_sources_block_collection_holdings_and_ter() -> None:
    paths = sorted(FRAGMENTS.glob("*.csv"))
    assert paths, "ETF rights fragments are missing"
    for path in paths:
        record = load_etf_rights_fragment(path)
        with pytest.raises(EtfRightsError):
            assert_automated_collection_allowed(record)

    records = load_source_rights(SOURCE_RIGHTS)
    by_id = {record.source_id: record for record in records}
    for source_id in ("vanguard_uk_vwra_holdings", "ishares_ucits_holdings"):
        coverage = coverage_for_record(by_id[source_id])
        assert coverage.status == "insufficient_coverage"
        assert coverage.line_count == 0

    ter = next(fact for fact in issuer_cost_facts(ANCHOR_ISIN) if fact.code == "ter")
    assert ter.availability != "cited"
    assert ter.value_text is None


def test_partial_holdings_and_pre_inception_window_are_refused() -> None:
    overlap = top_ten_overlap(left_line_count=10, right_line_count=10, rights_cleared=False)
    assert overlap["label"] == "partial"
    assert overlap["computed"] is False

    evidence = EvidenceInput(
        isin=ANCHOR_ISIN,
        identity_cited=False,
        structure_cited=False,
        cost_cited=False,
        benchmark_cited=False,
        holdings_rights="prohibited",
        scale_cited=False,
        performance_cited=False,
    )
    assert assess_quality(evidence).eligibility == "UNKNOWN"
    assert assess_anchor()[0].eligibility == "UNKNOWN"

    window = assess_fund_window(
        isin=ANCHOR_ISIN,
        inception=date(2020, 1, 1),
        period_start=date(2019, 1, 1),
        period_end=date(2019, 6, 30),
        months=6,
        currency="USD",
        return_type="total_return",
        reinvestment="unknown",
        display_currency="USD",
        fx_cited=False,
        value_text=None,
        source_id=None,
        source_locator=None,
    )
    assert window.accepted is False


def test_silent_fx_after_inception_is_refused() -> None:
    assert 6 in WINDOW_MONTHS
    window = assess_fund_window(
        isin=ANCHOR_ISIN,
        inception=date(2020, 1, 1),
        period_start=date(2024, 1, 1),
        period_end=date(2024, 6, 30),
        months=6,
        currency="USD",
        return_type="total_return",
        reinvestment="unknown",
        display_currency="SGD",
        fx_cited=False,
        value_text="not-a-market-return",
        source_id="test",
        source_locator="test",
    )
    assert window.accepted is False
    assert "silent FX" in window.reason
