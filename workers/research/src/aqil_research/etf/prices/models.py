"""Normalised ETF prices. Close, NAV, bid, ask, last, and adjusted close stay distinct."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

PriceType = Literal["bid", "ask", "mid", "last", "close", "adjusted_close", "nav"]
DelayClass = Literal["realtime", "delayed", "end_of_day", "unknown"]
AdjustmentStatus = Literal["raw", "adjusted", "not_applicable"]
Quality = Literal["accepted", "stale", "disagreement", "rejected"]
QuoteUnit = str


class PriceObservation(BaseModel):
    """One stored price. The value is in quote_unit and is never rescaled here."""

    model_config = ConfigDict(extra="forbid")

    listing_key: str
    share_class_key: str | None = None
    session_date: date
    value: Decimal
    currency: str = Field(min_length=3, max_length=3)
    quote_unit: str = Field(min_length=3, max_length=3)
    price_type: PriceType
    observation_time: datetime
    retrieved_at: datetime
    delay_class: DelayClass
    adjustment_status: AdjustmentStatus
    adjustment_definition: str | None = None
    quality: Quality
    source_id: str = Field(min_length=1)
    source_locator: str = Field(min_length=1)
    revision: int = Field(ge=1)


class ProviderBar(BaseModel):
    """One provider row before it is accepted as a close or an adjusted close."""

    model_config = ConfigDict(extra="forbid")

    ticker: str
    mic: str
    session_date: date
    close: Decimal | None
    adjusted_close: Decimal | None
    currency: str | None
    quote_unit: str | None
    adjustment_definition: str | None
    observation_time: datetime | None
    volume: Decimal | None = None


class ProviderQuote(BaseModel):
    """A quote. It is not a close and it does not replace one."""

    model_config = ConfigDict(extra="forbid")

    ticker: str
    mic: str
    bid: Decimal | None
    ask: Decimal | None
    last: Decimal | None
    currency: str | None
    quote_unit: str | None
    delay_class: DelayClass
    observation_time: datetime | None


class AdapterCapabilities(BaseModel):
    """What one replaceable adapter claims. A claim is not a rights decision."""

    model_config = ConfigDict(extra="forbid")

    source_id: str
    daily_close: bool
    adjusted_close: bool
    quote: bool
    quote_entitlement: str
