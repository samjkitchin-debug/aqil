"""ETF share-class contract v1.

Field names follow docs/schemas/etf_share_class.v1.json, mirrored under
packages/contracts/schemas/. Base currency, listing trading currency, hedge
status, and distribution policy stay separate. This module does not collect.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

SHARE_CLASS_SCHEMA_FILE = "etf_share_class.v1.json"

DistributionPolicy = Literal["accumulating", "distributing", "unknown"]
HedgeStatus = Literal["hedged", "unhedged", "unknown"]
EvidenceStatus = Literal["unverified", "cited", "unavailable", "insufficient"]
ReturnType = Literal["nav", "price", "total_return", "unknown"]
Reinvestment = Literal["reinvested", "not_reinvested", "unknown"]
ReturnConvention = Literal["price", "total_return", "net_total_return", "unknown"]
IdentifierKind = Literal["ticker", "isin", "mic"]


def share_class_schema_path() -> Path:
    """Authoritative JSON Schema. The packages/contracts copy must stay identical."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "docs" / "schemas" / SHARE_CLASS_SCHEMA_FILE
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(SHARE_CLASS_SCHEMA_FILE)


def share_class_field_names() -> tuple[str, ...]:
    """Required share-class payload names, in schema order."""
    document = json.loads(share_class_schema_path().read_text(encoding="utf-8"))
    required = document["required"]
    if not isinstance(required, list) or not all(isinstance(name, str) for name in required):
        raise ValueError("ETF share class schema required list is not a list of names")
    return tuple(required)


class Listing(BaseModel):
    """One exchange line. Trading currency belongs here, not on the share class."""

    model_config = ConfigDict(extra="forbid")

    mic: str = Field(pattern=r"^[A-Z0-9]{4}$")
    trading_currency: str = Field(pattern=r"^[A-Z]{3}$")
    ticker: str = Field(min_length=1)


class EtfShareClass(BaseModel):
    """One ISIN. A ticker change is identifier history, not a new share class."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    isin: str = Field(pattern=r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")
    base_currency: str = Field(pattern=r"^[A-Z]{3}$")
    distribution_policy: DistributionPolicy
    hedge_status: HedgeStatus
    inception_date: date | None
    evidence_status: EvidenceStatus
    benchmark_id: UUID | None
    listings: list[Listing]


class IdentifierHistoryAppend(BaseModel):
    """Append a ticker, ISIN, or MIC observation for an existing share class.

    Callers must not insert a second share class because a ticker changed.
    """

    model_config = ConfigDict(extra="forbid")

    share_class_id: UUID
    identifier_kind: IdentifierKind
    identifier_value: str = Field(min_length=1)
    effective_on: date
    source_id: str = Field(min_length=1)
    source_locator: str = Field(min_length=1)


class FundReturn(BaseModel):
    """A share-class fund return. Refused when it starts before inception."""

    model_config = ConfigDict(extra="forbid")

    share_class_isin: str = Field(pattern=r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")
    inception_date: date
    period_start: date
    period_end: date
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    return_type: ReturnType
    reinvestment: Reinvestment
    value_text: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    source_locator: str = Field(min_length=1)

    @model_validator(mode="after")
    def not_before_inception(self) -> FundReturn:
        if self.period_end < self.period_start:
            raise ValueError("fund return period ends before it starts")
        if self.period_start < self.inception_date or self.period_end < self.inception_date:
            raise ValueError("fund return cannot start before share-class inception")
        return self


class BenchmarkReturn(BaseModel):
    """A benchmark series. It has no share class and is not the fund's own return."""

    model_config = ConfigDict(extra="forbid")

    benchmark_id: UUID
    period_start: date
    period_end: date
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    return_convention: ReturnConvention
    reinvestment: Reinvestment
    value_text: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    source_locator: str = Field(min_length=1)

    @model_validator(mode="after")
    def period_is_ordered(self) -> BenchmarkReturn:
        if self.period_end < self.period_start:
            raise ValueError("benchmark return period ends before it starts")
        return self
