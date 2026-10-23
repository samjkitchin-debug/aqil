"""ETF issuer costs stay unavailable until a source permits collection."""

from __future__ import annotations

from pathlib import Path

import pytest

from aqil_research.etf.fundamentals import (
    CostAvailability,
    costs_blocked_by_rights,
    issuer_cost_facts,
)
from aqil_research.sources.rights import RightsDecision, load_source_rights

REPO_ROOT = Path(__file__).resolve().parents[4]
FRAGMENTS = REPO_ROOT / "docs" / "sources" / "etf" / "fragments"
REGISTER = REPO_ROOT / "docs" / "sources" / "SOURCE_RIGHTS.csv"

_COST_CODES = (
    "ter",
    "ongoing_charge",
    "tracking_difference",
    "aum",
    "bid_ask_spread",
    "total_cost",
)


def test_vwra_isin_returns_six_unavailable_facts() -> None:
    facts = issuer_cost_facts("IE00BK5BQT80")
    assert tuple(fact.code for fact in facts) == _COST_CODES
    for fact in facts:
        assert fact.availability is CostAvailability.UNAVAILABLE
        assert fact.value_text is None
        assert fact.source_id is None
        assert fact.source_locator is None
        assert fact.caveat


def test_ter_caveat_states_it_is_not_total_cost() -> None:
    facts = issuer_cost_facts("IE00BK5BQT80")
    ter = next(fact for fact in facts if fact.code == "ter")
    assert "TER is not total cost" in ter.caveat


def test_spread_caveat_states_there_is_no_live_spread() -> None:
    facts = issuer_cost_facts("IE00BK5BQT80")
    spread = next(fact for fact in facts if fact.code == "bid_ask_spread")
    assert "no live spread" in spread.caveat.lower()


@pytest.mark.parametrize("isin", ["VWRA", "ie00bk5bqt80", ""])
def test_bad_isin_raises_value_error(isin: str) -> None:
    with pytest.raises(ValueError):
        issuer_cost_facts(isin)


def test_every_etf_fragment_blocks_cost_collection() -> None:
    paths = sorted(path for path in FRAGMENTS.iterdir() if path.is_file())
    assert paths, "ETF rights fragments are missing"
    for path in paths:
        assert costs_blocked_by_rights(path) is True


def test_holdings_sources_are_not_permitted_for_automated_access() -> None:
    records = {record.source_id: record for record in load_source_rights(REGISTER)}
    for source_id in ("vanguard_uk_vwra_holdings", "ishares_ucits_holdings"):
        assert records[source_id].automated_access != RightsDecision.PERMITTED
