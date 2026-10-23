"""Issuer cost facts. No figure is recorded until collection is permitted.

Issuer-reported TER is not total cost. There is no live spread. This module
does not collect, contact a provider, or derive a total cost.
"""

from __future__ import annotations

import re
from enum import StrEnum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

from aqil_research.etf.contracts import EtfShareClass
from aqil_research.etf.contracts.rights import (
    EtfRightsError,
    assert_automated_collection_allowed,
    load_etf_rights_fragment,
)

CostCode = Literal[
    "ter",
    "ongoing_charge",
    "tracking_difference",
    "aum",
    "bid_ask_spread",
    "total_cost",
]

_COST_CODES: tuple[CostCode, ...] = (
    "ter",
    "ongoing_charge",
    "tracking_difference",
    "aum",
    "bid_ask_spread",
    "total_cost",
)

_ISIN = re.compile(str(EtfShareClass.model_json_schema()["properties"]["isin"]["pattern"]))

_CAVEATS: dict[CostCode, str] = {
    "ter": "Issuer-reported TER is not total cost.",
    "ongoing_charge": (
        "Ongoing charge is unavailable because no ETF source permits automated collection."
    ),
    "tracking_difference": (
        "Tracking difference is unavailable because no ETF source permits automated collection."
    ),
    "aum": (
        "Assets under management are unavailable "
        "because no ETF source permits automated collection."
    ),
    "bid_ask_spread": "No live spread is collected.",
    "total_cost": "Total cost is not derived by adding a spread or inventing a figure.",
}


class CostAvailability(StrEnum):
    CITED = "cited"
    UNAVAILABLE = "unavailable"


class CostFact(BaseModel):
    """One cost code. An unavailable fact has no value and no source."""

    model_config = ConfigDict(extra="forbid")

    code: CostCode
    availability: CostAvailability
    value_text: str | None
    source_id: str | None
    source_locator: str | None
    caveat: str


def issuer_cost_facts(isin: str) -> tuple[CostFact, ...]:
    """Return the six cost codes as unavailable.

    No ETF fragment permits automated access, so no value or source is attached.
    A valid ISIN is not given a special figure.
    """
    if _ISIN.fullmatch(isin) is None:
        raise ValueError(f"{isin} is not a share-class ISIN")
    return tuple(
        CostFact(
            code=code,
            availability=CostAvailability.UNAVAILABLE,
            value_text=None,
            source_id=None,
            source_locator=None,
            caveat=_CAVEATS[code],
        )
        for code in _COST_CODES
    )


def costs_blocked_by_rights(fragment_path: Path) -> bool:
    """True when the fragment refuses automated collection."""
    record = load_etf_rights_fragment(fragment_path)
    try:
        assert_automated_collection_allowed(record)
    except EtfRightsError:
        return True
    return False
