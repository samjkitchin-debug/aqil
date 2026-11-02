"""Frozen ETF universe V1. The artifact is checked. No price is stored."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from aqil_research.etf.history.manifest import dataset_manifest
from aqil_research.etf.history.quality import HistoryBar, history_findings, history_import_refusal
from aqil_research.etf.register.universe import (
    RegisterError,
    listing_is_forbidden_substitute,
    load_universe_v1,
)


def test_frozen_register_counts_and_listing_locks() -> None:
    rows = load_universe_v1()
    assert len(rows) == 20
    assert sum(1 for row in rows if row.investment_approved) == 18
    by_symbol = {row.research_symbol: row for row in rows}
    assert by_symbol["VWRA"].isin == "IE00BK5BQT80"
    assert by_symbol["VWRA"].mic == "XLON"
    assert by_symbol["VWRA"].listing_currency == "USD"
    assert by_symbol["ICHN"].mic == "XAMS"
    assert by_symbol["EUNA"].mic == "XETR"
    assert by_symbol["EUNA"].listing_currency == "EUR"
    assert by_symbol["INRG"].investment_approved is False
    assert by_symbol["INRG"].distribution_policy == "Distributing"
    assert by_symbol["SMH"].isin == "IE00BMC38736"


def test_forbidden_listing_substitutes() -> None:
    assert listing_is_forbidden_substitute(research_symbol="VWRA", ticker="VWCE", mic="XETR")
    assert listing_is_forbidden_substitute(research_symbol="VWRA", ticker="VWRP", mic="XLON")
    assert listing_is_forbidden_substitute(research_symbol="CNDX", ticker="CNDX", mic="XTSE")
    assert listing_is_forbidden_substitute(research_symbol="ICHN", ticker="ICHN", mic="XLON")
    assert listing_is_forbidden_substitute(research_symbol="SPEQ", ticker="SPEX", mic="XLON")
    assert listing_is_forbidden_substitute(research_symbol="IJPA", ticker="SJPA", mic="XLON")
    assert listing_is_forbidden_substitute(research_symbol="SMH", ticker="SMH", mic="ARCX")
    assert not listing_is_forbidden_substitute(research_symbol="VWRA", ticker="VWRA", mic="XLON")


def test_register_refuses_a_changed_version(tmp_path) -> None:
    source = {
        "version": "other",
        "decision_date": "2026-11-03",
        "instruments": [],
    }
    path = tmp_path / "register.json"
    path.write_text(__import__("json").dumps(source), encoding="utf-8")
    with pytest.raises(RegisterError):
        load_universe_v1(path)


def test_saxo_history_is_not_stored_and_quality_flags_gaps() -> None:
    assert history_import_refusal(source_id="saxo_live_chart", retention_permitted=True)
    assert history_import_refusal(source_id="eodhd", retention_permitted=False)
    assert history_import_refusal(source_id="eodhd", retention_permitted=True) is None
    assert history_findings((), expected_currency="USD", inception=date(2019, 7, 23)) == (
        "no daily observations are stored",
    )
    findings = history_findings(
        (
            HistoryBar(
                session_date=date(2019, 7, 22),
                close=Decimal("50"),
                currency="USD",
                quote_unit="USD",
                price_type="close",
                completed_session=True,
                source_id="fixture",
            ),
            HistoryBar(
                session_date=date(2026, 11, 2),
                close=Decimal("100"),
                currency="GBX",
                quote_unit="GBX",
                price_type="close",
                completed_session=False,
                source_id="fixture",
            ),
        ),
        expected_currency="USD",
        inception=date(2019, 7, 23),
    )
    assert any("before inception" in item for item in findings)
    assert any("GBX" in item or "currency" in item for item in findings)
    assert any("not a completed session" in item for item in findings)


def test_manifest_records_zero_prices_and_survivorship() -> None:
    manifest = dataset_manifest(load_universe_v1())
    assert manifest["dataset_id"] == "aqil-etf-history-v1-2026-11"
    assert manifest["stored_price_observations"] == 0
    assert manifest["saxo_persistence"] == "refused"
    assert manifest["approved_count"] == 18
    assert "survivorship" in str(manifest["survivorship"]).lower() or "founder-selected" in str(
        manifest["survivorship"]
    )
