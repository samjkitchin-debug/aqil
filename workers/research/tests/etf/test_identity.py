"""In-memory ETF identity slots stay unverified and carry one internal anchor."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from pydantic import ValidationError

from aqil_research.etf.contracts import IdentifierHistoryAppend
from aqil_research.etf.identity import (
    ANCHOR_ISIN,
    ANCHOR_SOURCE_ID,
    ANCHOR_SOURCE_LOCATOR,
    ANCHOR_TICKER,
    CandidateShareClass,
    anchor_identity,
    candidate_catalogue,
    ticker_change_keeps_share_class,
)

_RESEARCH_ROOT = Path(__file__).resolve().parents[2]
_IDENTITY_DIR = _RESEARCH_ROOT / "src" / "aqil_research" / "etf" / "identity"
_ISIN = re.compile(r"\b[A-Z]{2}[A-Z0-9]{9}[0-9]\b")
_BANNED_IMPORTS = (
    "httpx",
    "psycopg",
    "socket",
    "urllib",
    "requests",
    "sqlalchemy",
    "asyncpg",
    "supabase",
)


def test_catalogue_length_is_between_36_and_48() -> None:
    assert 36 <= len(candidate_catalogue()) <= 48


def test_every_row_evidence_status_is_unverified() -> None:
    assert {row.evidence_status for row in candidate_catalogue()} == {"unverified"}


def test_only_anchor_isin_and_ticker_are_present() -> None:
    rows = candidate_catalogue()
    isins = [row.isin for row in rows if row.isin is not None]
    tickers = [row.ticker for row in rows if row.ticker is not None]
    assert isins == [ANCHOR_ISIN]
    assert tickers == [ANCHOR_TICKER]
    assert ANCHOR_ISIN == "IE00BK5BQT80"
    assert ANCHOR_TICKER == "VWRA"
    anchor = anchor_identity()
    assert anchor in rows
    assert anchor.isin == ANCHOR_ISIN
    assert anchor.ticker == ANCHOR_TICKER
    stored = set()
    for path in _IDENTITY_DIR.glob("*.py"):
        stored.update(_ISIN.findall(path.read_text(encoding="utf-8")))
    assert stored == {ANCHOR_ISIN}


def test_anchor_unavailable_fields_include_product_facts() -> None:
    missing = set(anchor_identity().unavailable_fields)
    assert {
        "base_currency",
        "distribution_policy",
        "ter",
        "aum",
        "holdings",
        "spread",
        "fund_return",
    } <= missing


def test_ticker_change_keeps_share_class_without_a_new_isin() -> None:
    change = ticker_change_keeps_share_class()
    assert change.identifier_kind == "ticker"
    assert change.identifier_value == "VWRA-OLD"
    assert change.source_id == ANCHOR_SOURCE_ID
    assert "isin" not in IdentifierHistoryAppend.model_fields
    assert "isin" not in ticker_change_keeps_share_class.__annotations__


def test_no_network_and_no_database() -> None:
    for path in _IDENTITY_DIR.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        for name in _BANNED_IMPORTS:
            assert f"import {name}" not in text
            assert f"from {name}" not in text
        assert "EtfShareClass" not in text
    candidate_catalogue()
    anchor_identity()
    ticker_change_keeps_share_class()


def test_catalogue_covers_requested_exposure_slots() -> None:
    roles = [row.exposure_role for row in candidate_catalogue()]
    assert len(roles) == len(set(roles))
    text = "\n".join(roles)
    for label in (
        "Broad global equity",
        "Global developed equity",
        "Emerging equity",
        "US equity",
        "Europe equity",
        "Asia-Pacific developed equity",
        "Asia-Pacific emerging equity",
        "Investment-grade bond",
        "Government bond",
        "Inflation-linked bond",
        "Irish UCITS accumulating preference",
        "Irish UCITS distributing comparison",
        "US-domiciled comparison",
        "sector",
        "factor",
    ):
        assert label in text


def test_anchor_citation_is_the_internal_fixture() -> None:
    repo = _RESEARCH_ROOT.parents[1]
    fixture = (repo / ANCHOR_SOURCE_LOCATOR).read_text(encoding="utf-8")
    assert ANCHOR_ISIN in fixture
    assert ANCHOR_TICKER in fixture
    assert "legal_name" not in CandidateShareClass.model_fields


def test_candidate_rejects_invented_product_fields() -> None:
    with pytest.raises(ValidationError):
        CandidateShareClass(
            exposure_role="Broad global equity, Irish UCITS accumulating preference",
            evidence_status="unverified",
            unavailable_fields=anchor_identity().unavailable_fields,
            legal_name="not cited",
        )
