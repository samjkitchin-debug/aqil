"""Checks for a supplied daily series. Missing history stays missing."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

TARGET_START = date(2016, 11, 3)
TARGET_END = date(2026, 11, 2)


class HistoryBar(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_date: date
    close: Decimal = Field(gt=0)
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    quote_unit: str = Field(pattern=r"^[A-Z]{3}$")
    price_type: str = Field(pattern="^(close|adjusted_close)$")
    completed_session: bool
    source_id: str = Field(min_length=1)


def history_import_refusal(*, source_id: str, retention_permitted: bool) -> str | None:
    """Refuse Saxo and any source whose retention right is not established."""

    if source_id.strip().lower().startswith("saxo"):
        return "Saxo history is not stored while retention rights are unresolved"
    if not retention_permitted:
        return "historical storage is refused until retention is permitted"
    return None


def history_findings(
    bars: tuple[HistoryBar, ...],
    *,
    expected_currency: str,
    inception: date | None,
) -> tuple[str, ...]:
    """Return quality findings. An empty series is a coverage gap, not a pass."""

    findings: list[str] = []
    if not bars:
        findings.append("no daily observations are stored")
        return tuple(findings)
    seen: set[date] = set()
    for bar in bars:
        if bar.session_date in seen:
            findings.append(f"duplicate session {bar.session_date.isoformat()}")
        seen.add(bar.session_date)
        if bar.currency != expected_currency or bar.quote_unit != expected_currency:
            findings.append(
                f"{bar.session_date.isoformat()} currency {bar.currency}/{bar.quote_unit} "
                f"does not match {expected_currency}"
            )
        if bar.quote_unit == "GBX" and expected_currency == "GBP":
            findings.append(f"{bar.session_date.isoformat()} is GBX and must not be read as GBP")
        if inception is not None and bar.session_date < inception:
            findings.append(f"{bar.session_date.isoformat()} is before inception")
        if bar.session_date < TARGET_START or bar.session_date > TARGET_END:
            findings.append(f"{bar.session_date.isoformat()} is outside the research window")
        if not bar.completed_session:
            findings.append(f"{bar.session_date.isoformat()} is not a completed session")
    ordered = sorted(bars, key=lambda bar: bar.session_date)
    for previous, current in zip(ordered, ordered[1:], strict=False):
        if previous.close > 0 and current.close / previous.close >= Decimal("2"):
            findings.append(
                f"{current.session_date.isoformat()} close doubles the previous close"
            )
    return tuple(findings)
