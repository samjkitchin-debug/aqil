"""ETF read contract V1. Answers come from stored rows. Missing stays missing."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from aqil_research.etf.prices.models import PriceObservation


class ApprovalRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: str
    actor: str
    rationale: str
    recorded_at: datetime


class EligibilityRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: str
    conditions: str
    recorded_at: datetime


class HoldingLine(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    weight: Decimal | None = None


class AdjustedCloseSeries(BaseModel):
    """A split-adjusted series. It is not a raw close and not a total return."""

    model_config = ConfigDict(extra="forbid")

    currency: str | None = None
    first_date: date | None = None
    last_date: date | None = None
    count: int = 0


class EtfReadModel(BaseModel):
    """One share class as the web loader may show it. No recommendation is included."""

    model_config = ConfigDict(extra="forbid")

    isin: str | None
    cited: bool
    listings: tuple[str, ...] = ()
    eligibility: tuple[EligibilityRow, ...] = ()
    approvals: tuple[ApprovalRow, ...] = ()
    latest_close: PriceObservation | None = None
    historical_closes: tuple[PriceObservation, ...] = ()
    latest_adjusted_close: PriceObservation | None = None
    historical_adjusted_closes: tuple[PriceObservation, ...] = ()
    adjusted_close_series: AdjustedCloseSeries = Field(default_factory=AdjustedCloseSeries)
    latest_nav: PriceObservation | None = None
    fx_lineage: str
    holdings_completeness: str
    holdings_lines: tuple[HoldingLine, ...] = ()
    overlap_label: str
    overlap_reason: str
    shared_holding_count: int | None = None
    sources: tuple[str, ...] = Field(default_factory=tuple)


def build_read_model(
    *,
    isin: str | None,
    cited: bool,
    listings: tuple[str, ...],
    eligibility: tuple[EligibilityRow, ...],
    approvals: tuple[ApprovalRow, ...],
    prices: tuple[PriceObservation, ...],
    fx_reason: str,
    holdings_completeness: str,
    holdings_lines: tuple[HoldingLine, ...] = (),
    other_lines: tuple[HoldingLine, ...] = (),
    as_of: date | None = None,
) -> EtfReadModel:
    """Assemble stored facts. Eligibility is not copied into approvals."""

    closes = _typed(prices, "close", as_of)
    adjusted = _typed(prices, "adjusted_close", as_of)
    navs = _typed(prices, "nav", as_of)
    overlap_count, overlap_reason = _overlap(
        holdings_completeness,
        holdings_lines,
        other_lines,
    )
    source_ids = tuple(dict.fromkeys(row.source_id for row in prices))
    return EtfReadModel(
        isin=isin,
        cited=cited,
        listings=listings,
        eligibility=eligibility,
        approvals=approvals,
        latest_close=closes[-1] if closes else None,
        historical_closes=closes,
        latest_adjusted_close=adjusted[-1] if adjusted else None,
        historical_adjusted_closes=adjusted,
        adjusted_close_series=_adjusted_series(adjusted),
        latest_nav=navs[-1] if navs else None,
        fx_lineage=fx_reason,
        holdings_completeness=holdings_completeness,
        holdings_lines=holdings_lines,
        overlap_label="partial" if overlap_count is not None else "unavailable",
        overlap_reason=overlap_reason,
        shared_holding_count=overlap_count,
        sources=source_ids,
    )


def _adjusted_series(rows: tuple[PriceObservation, ...]) -> AdjustedCloseSeries:
    if not rows:
        return AdjustedCloseSeries()
    currencies = {row.currency for row in rows}
    return AdjustedCloseSeries(
        currency=rows[-1].currency if len(currencies) == 1 else None,
        first_date=rows[0].session_date,
        last_date=rows[-1].session_date,
        count=len(rows),
    )


def _typed(
    prices: tuple[PriceObservation, ...],
    price_type: str,
    as_of: date | None,
) -> tuple[PriceObservation, ...]:
    rows = [row for row in prices if row.price_type == price_type and row.quality != "rejected"]
    if as_of is not None:
        rows = [row for row in rows if row.session_date <= as_of]
    rows.sort(key=lambda row: (row.session_date, row.revision))
    return tuple(rows)


def _overlap(
    completeness: str,
    left: tuple[HoldingLine, ...],
    right: tuple[HoldingLine, ...],
) -> tuple[int | None, str]:
    if completeness != "full" or not left or not right:
        return None, (
            "Overlap is unavailable. Top-ten holdings stay partial, and missing "
            "holdings are not treated as an empty portfolio."
        )
    shared = {line.name.casefold() for line in left} & {line.name.casefold() for line in right}
    return len(shared), "Overlap counts only names present in both stored full snapshots."
