"""In-memory exposure slots for a Singapore-based long-horizon investor.

An exposure role is a shortlist label. It is not a cited domicile, distribution
policy, hedge status, currency, or issuer product. Irish UCITS accumulating is
the preferred label. Distributing and US-domiciled rows are comparison slots.

The only stored identifiers are the internal fixture anchor. That fixture is
not a permitted issuer source. Evidence stays unverified. No TER, AUM,
holding, spread, NAV, return, legal name, or inception date is copied.
"""

from __future__ import annotations

from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator

from aqil_research.etf.contracts import IdentifierHistoryAppend

ANCHOR_ISIN = "IE00BK5BQT80"
ANCHOR_TICKER = "VWRA"
ANCHOR_SOURCE_ID = "aqil_internal_forward_fixture"
ANCHOR_SOURCE_LOCATOR = "apps/web/fixtures/forward-horizon.v1.json"

_ANCHOR_ROLE = "Broad global equity, Irish UCITS accumulating preference"

_UNAVAILABLE_FIELDS = (
    "base_currency",
    "distribution_policy",
    "hedge_status",
    "inception_date",
    "mic",
    "trading_currency",
    "legal_name",
    "domicile",
    "ter",
    "aum",
    "holdings",
    "spread",
    "nav",
    "fund_return",
    "benchmark_return",
)

_EQUITY_FAMILIES = (
    "Broad global equity",
    "Global developed equity",
    "Emerging equity",
    "US equity",
    "Europe equity",
    "Asia-Pacific developed equity",
    "Asia-Pacific emerging equity",
)

_BOND_FAMILIES = (
    "Investment-grade bond",
    "Government bond",
    "Inflation-linked bond",
)

_WRAPPERS = (
    "Irish UCITS accumulating preference",
    "Irish UCITS distributing comparison",
    "US-domiciled comparison",
)

_HEDGED_BOND_WRAPPER = "Irish UCITS accumulating currency-hedged comparison"

_SECTOR_AND_FACTOR_ROLES = (
    "Broad technology sector equity, Irish UCITS accumulating comparison",
    "Broad healthcare sector equity, Irish UCITS accumulating comparison",
    "Broad financials sector equity, Irish UCITS accumulating comparison",
    "Quality factor equity, Irish UCITS accumulating comparison",
    "Value factor equity, Irish UCITS accumulating comparison",
    "Minimum-volatility factor equity, Irish UCITS accumulating comparison",
)


class CandidateShareClass(BaseModel):
    """One exposure slot. Identifiers stay empty unless they are the anchor."""

    model_config = ConfigDict(extra="forbid")

    exposure_role: str
    evidence_status: Literal["unverified"]
    isin: str | None = None
    ticker: str | None = None
    unavailable_fields: tuple[str, ...]

    @model_validator(mode="after")
    def only_the_internal_anchor_has_identifiers(self) -> CandidateShareClass:
        if self.isin is None and self.ticker is None:
            return self
        if self.isin != ANCHOR_ISIN or self.ticker != ANCHOR_TICKER:
            raise ValueError("only the internal fixture anchor may carry an identifier")
        return self


def _roles() -> tuple[str, ...]:
    roles = [f"{family}, {wrapper}" for family in _EQUITY_FAMILIES for wrapper in _WRAPPERS]
    for family in _BOND_FAMILIES:
        roles.extend(f"{family}, {wrapper}" for wrapper in _WRAPPERS)
        roles.append(f"{family}, {_HEDGED_BOND_WRAPPER}")
    roles.extend(_SECTOR_AND_FACTOR_ROLES)
    if len(roles) != len(set(roles)):
        raise RuntimeError("exposure roles must be unique")
    if _ANCHOR_ROLE not in roles:
        raise RuntimeError("the preferred broad global equity slot is missing")
    if not 36 <= len(roles) <= 48:
        raise RuntimeError("candidate catalogue must hold 36 to 48 exposure slots")
    return tuple(roles)


def _row(role: str) -> CandidateShareClass:
    if role == _ANCHOR_ROLE:
        return CandidateShareClass(
            exposure_role=role,
            evidence_status="unverified",
            isin=ANCHOR_ISIN,
            ticker=ANCHOR_TICKER,
            unavailable_fields=_UNAVAILABLE_FIELDS,
        )
    return CandidateShareClass(
        exposure_role=role,
        evidence_status="unverified",
        unavailable_fields=_UNAVAILABLE_FIELDS,
    )


_CATALOGUE = tuple(_row(role) for role in _roles())


def candidate_catalogue() -> tuple[CandidateShareClass, ...]:
    """Return the exposure slots. Every row is unverified."""
    return _CATALOGUE


def anchor_identity() -> CandidateShareClass:
    """Return the catalogue row that stores the internal fixture anchor.

    The ISIN and ticker are the pair already cited at ``ANCHOR_SOURCE_LOCATOR``.
    That file is an internal fixture, not a permitted issuer source.
    ``evidence_status`` stays unverified. Legal name, domicile, accumulating
    flag, exchange, currency, benchmark, and holdings from the fixture are not
    copied into this row. Those fields stay on ``unavailable_fields``.
    """
    found = tuple(row for row in _CATALOGUE if row.isin == ANCHOR_ISIN)
    if len(found) != 1 or found[0].ticker != ANCHOR_TICKER:
        raise RuntimeError("anchor identifiers must appear on exactly one catalogue row")
    return found[0]


def ticker_change_keeps_share_class() -> IdentifierHistoryAppend:
    """Append an example ticker on one example share-class id.

    ``VWRA-OLD`` is an example value, not a cited historical ticker. The
    share-class id, effective date, and source locator are examples too.
    ``ANCHOR_SOURCE_ID`` is only the history example source label. This is
    not a verified market fact. A ticker change is identifier history: it
    does not construct another share class and it does not require a new ISIN.
    """
    return IdentifierHistoryAppend(
        share_class_id=UUID("00000000-0000-4000-8000-000000000001"),
        identifier_kind="ticker",
        identifier_value="VWRA-OLD",
        effective_on=date(2000, 1, 1),
        source_id=ANCHOR_SOURCE_ID,
        source_locator="example:not-a-cited-historical-ticker",
    )
