"""Point-in-time and latest-revised series selection."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from aqil_research.contracts.observation import (
    AnalysisMode,
    EconomicObservation,
    Frequency,
    QualityStatus,
    SeriesProvenance,
    model_available_at,
)


class AsOfSelectionError(Exception):
    """Raised when an as-of view cannot be built."""


def select_as_of_series(
    observations: tuple[EconomicObservation, ...],
    dataset_id: str,
    decision_at: datetime,
    mode: AnalysisMode,
) -> dict[date, EconomicObservation]:
    """One observation per period for the requested analysis mode."""
    if decision_at.tzinfo is None:
        raise AsOfSelectionError("decision_at must be timezone-aware (UTC)")
    decision = decision_at.astimezone(UTC)
    rows = [row for row in observations if row.dataset_id == dataset_id]
    if mode == AnalysisMode.LATEST_REVISED:
        return _latest_revised_per_period(rows)
    return _point_in_time_per_period(rows, decision)


def _latest_revised_per_period(
    rows: list[EconomicObservation],
) -> dict[date, EconomicObservation]:
    by_period: dict[date, EconomicObservation] = {}
    for row in rows:
        if row.quality_status in {
            QualityStatus.RETRACTED,
            QualityStatus.MISSING,
            QualityStatus.CONTESTED,
        }:
            continue
        if row.series_provenance not in {
            SeriesProvenance.LATEST_REVISED,
            SeriesProvenance.AQIL_ARCHIVED,
            SeriesProvenance.PROVIDER_VINTAGE,
        }:
            continue
        current = by_period.get(row.period_start)
        if current is None or (row.provider_vintage_date, row.retrieved_at) >= (
            current.provider_vintage_date,
            current.retrieved_at,
        ):
            by_period[row.period_start] = row
    return by_period


def _point_in_time_per_period(
    rows: list[EconomicObservation],
    decision_at: datetime,
) -> dict[date, EconomicObservation]:
    eligible: list[EconomicObservation] = []
    for row in rows:
        if row.series_provenance == SeriesProvenance.LATEST_REVISED:
            continue
        if row.quality_status in {
            QualityStatus.RETRACTED,
            QualityStatus.MISSING,
            QualityStatus.CONTESTED,
        }:
            continue
        available = model_available_at(row)
        if available is None:
            continue
        if available > decision_at:
            continue
        eligible.append(row)

    by_period: dict[date, list[EconomicObservation]] = {}
    for row in eligible:
        by_period.setdefault(row.period_start, []).append(row)

    selected: dict[date, EconomicObservation] = {}
    for period, candidates in by_period.items():
        candidates.sort(key=lambda row: row.provider_vintage_date, reverse=True)
        selected[period] = candidates[0]
    return selected


def monthly_decimal_series(
    by_period: dict[date, EconomicObservation],
) -> dict[date, Decimal]:
    """Extract monthly values; raises if frequency or gaps are wrong for callers."""
    series: dict[date, Decimal] = {}
    for period, row in by_period.items():
        if row.frequency != Frequency.MONTHLY:
            raise AsOfSelectionError(f"expected monthly frequency for {period}")
        series[period] = row.decimal_value()
    return series
