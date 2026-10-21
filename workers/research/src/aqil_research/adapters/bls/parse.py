"""Parse BLS Public API JSON into canonical observations."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from aqil_research.contracts.observation import (
    AvailabilityPrecision,
    EconomicObservation,
    Frequency,
    QualityStatus,
    SeasonalAdjustment,
    SeriesProvenance,
)

SERIES_ID = "LNS14000000"
DATASET_ID = "bls.ln.LNS14000000"
SOURCE_ID = "bls_cps_unemployment_rate"
RIGHTS_RECORD_ID = "bls_cps_unemployment_rate"
PROVIDER_ID = "bls"

MONTH_PERIOD = re.compile(r"^M(0[1-9]|1[0-2])$")


@dataclass(frozen=True, slots=True)
class BlsParseResult:
    observations: tuple[EconomicObservation, ...]
    warnings: tuple[str, ...]
    missing_months: tuple[str, ...]
    unavailable_months: tuple[str, ...] = ()


def parse_bls_payload(
    payload: dict[str, object],
    *,
    adapter_version: str,
    retrieved_at: datetime,
    collection_vintage_date: date,
    start_year: int | None = None,
    end_year: int | None = None,
) -> BlsParseResult:
    """Map BLS API results to latest-revised observations for one collection snapshot."""
    results = payload.get("Results")
    if not isinstance(results, dict):
        raise ValueError("Results object missing from BLS payload")
    series_list = results.get("series")
    if not isinstance(series_list, list) or not series_list:
        raise ValueError("no series returned")

    warnings: list[str] = []
    observations: list[EconomicObservation] = []
    missing: list[str] = []
    unavailable: list[str] = []

    for series in series_list:
        if not isinstance(series, dict):
            raise ValueError("series entry is not an object")
        series_id = str(series.get("seriesID", ""))
        if series_id != SERIES_ID:
            raise ValueError(f"unexpected series id {series_id}")
        data = series.get("data")
        if not isinstance(data, list):
            raise ValueError("series data is not a list")
        for point in data:
            if not isinstance(point, dict):
                raise ValueError("observation point is not an object")
            obs, warning = _point_to_observation(
                point,
                adapter_version=adapter_version,
                retrieved_at=retrieved_at,
                collection_vintage_date=collection_vintage_date,
            )
            if obs is None:
                if warning and warning.startswith("officially unavailable "):
                    unavailable.append(warning.removeprefix("officially unavailable "))
                elif warning and warning.startswith("skipped non-monthly "):
                    warnings.append(warning)
                elif warning:
                    missing.append(warning)
                continue
            if warning:
                warnings.append(warning)
            observations.append(obs)

    if not observations:
        raise ValueError("no usable monthly observations in BLS payload")

    deduped = _dedupe_by_period(observations, warnings)
    if start_year is not None and end_year is not None:
        observed = {row.period_start for row in deduped}
        unavailable_dates = {date.fromisoformat(label) for label in unavailable}
        for month_start in _required_months(start_year, end_year, retrieved_at):
            if month_start in observed or month_start in unavailable_dates:
                continue
            missing.append(f"absent period {month_start.isoformat()}")
    return BlsParseResult(
        observations=tuple(deduped),
        warnings=tuple(warnings),
        missing_months=tuple(missing),
        unavailable_months=tuple(unavailable),
    )


def _officially_unavailable(point: dict[str, object]) -> bool:
    """BLS marks a real month with '-' and a footnote when the figure was not published."""
    notes = point.get("footnotes")
    if not isinstance(notes, list):
        return False
    for note in notes:
        if not isinstance(note, dict):
            continue
        if str(note.get("code", "")).strip() == "9":
            return True
        if "unavailable" in str(note.get("text", "")).lower():
            return True
    return False


def _required_months(start_year: int, end_year: int, retrieved_at: datetime) -> list[date]:
    """Months in the request that should already have been released.

    The Employment Situation for a month is published during the following month.
    The current calendar month is not required. An earlier month that is absent
    from the payload is a gap.
    """
    latest_due = _previous_month(retrieved_at.date())
    last = min(latest_due, date(end_year, 12, 1))
    cursor = date(start_year, 1, 1)
    months: list[date] = []
    while cursor <= last:
        months.append(cursor)
        cursor = _next_month(cursor)
    return months


def _previous_month(day: date) -> date:
    if day.month == 1:
        return date(day.year - 1, 12, 1)
    return date(day.year, day.month - 1, 1)


def _next_month(day: date) -> date:
    if day.month == 12:
        return date(day.year + 1, 1, 1)
    return date(day.year, day.month + 1, 1)


def _point_to_observation(
    point: dict[str, object],
    *,
    adapter_version: str,
    retrieved_at: datetime,
    collection_vintage_date: date,
) -> tuple[EconomicObservation | None, str | None]:
    year = str(point.get("year", ""))
    period = str(point.get("period", ""))
    if not year.isdigit() or not MONTH_PERIOD.match(period):
        return None, f"skipped non-monthly period {year}-{period}"
    month = int(period[1:])
    period_start = date(int(year), month, 1)
    raw = str(point.get("value", "")).strip()
    if raw in {"", "-"}:
        if _officially_unavailable(point):
            return None, f"officially unavailable {period_start.isoformat()}"
        return None, f"missing value for {period_start.isoformat()}"
    try:
        decimal_value = Decimal(raw)
    except InvalidOperation:
        return None, f"non-numeric value for {period_start.isoformat()}"
    if not decimal_value.is_finite():
        return None, f"non-finite value for {period_start.isoformat()}"
    if decimal_value < Decimal("0") or decimal_value > Decimal("30"):
        return None, f"implausible unemployment rate {raw} for {period_start.isoformat()}"

    observation_id = _observation_id(period_start, collection_vintage_date, raw)
    return (
        EconomicObservation(
            observation_id=observation_id,
            dataset_id=DATASET_ID,
            provider_id=PROVIDER_ID,
            source_id=SOURCE_ID,
            rights_record_id=RIGHTS_RECORD_ID,
            period_start=period_start,
            frequency=Frequency.MONTHLY,
            geography="US",
            unit="percent",
            seasonal_adjustment=SeasonalAdjustment.SEASONALLY_ADJUSTED,
            raw_value=str(decimal_value),
            quality_status=QualityStatus.OBSERVED,
            series_provenance=SeriesProvenance.LATEST_REVISED,
            provider_vintage_date=collection_vintage_date,
            availability_precision=AvailabilityPrecision.UNKNOWN,
            retrieved_at=retrieved_at,
            first_seen_at=retrieved_at,
            source_locator=f"bls:series:{SERIES_ID}",
            adapter_version=adapter_version,
        ),
        None,
    )


def _observation_id(period_start: date, vintage: date, raw_value: str) -> str:
    material = f"{DATASET_ID}|{period_start.isoformat()}|{vintage.isoformat()}|{raw_value}"
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()[:24]
    return f"bls-{period_start.year:04d}{period_start.month:02d}-{digest}"


def _dedupe_by_period(
    rows: list[EconomicObservation],
    warnings: list[str],
) -> list[EconomicObservation]:
    by_period: dict[date, EconomicObservation] = {}
    for row in rows:
        existing = by_period.get(row.period_start)
        if existing is None:
            by_period[row.period_start] = row
            continue
        if existing.raw_value != row.raw_value:
            raise ValueError(
                f"contradictory values for period {row.period_start.isoformat()} "
                f"in one provider response",
            )
        by_period[row.period_start] = row
    return [by_period[key] for key in sorted(by_period)]
