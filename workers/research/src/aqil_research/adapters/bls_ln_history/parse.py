"""Read LNS14000000 from the official LN flat files without a year window."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from aqil_research.adapters.bls_ln_history.constants import (
    ADAPTER_ID,
    ADAPTER_VERSION,
    DATA_URL,
    DATASET_ID,
    PERIODICITY_CODE,
    PROVIDER_ID,
    RIGHTS_RECORD_ID,
    SEASONAL_CODE,
    SERIES_ID,
    SERIES_TITLE,
    SOURCE_ID,
    UNIT,
)
from aqil_research.contracts.observation import (
    AvailabilityPrecision,
    EconomicObservation,
    Frequency,
    QualityStatus,
    SeasonalAdjustment,
    SeriesProvenance,
)

BLANK_VALUES = frozenset({"", "-", "."})


class LnHistoryError(ValueError):
    """The official LN files do not confirm the monthly unemployment rate."""


@dataclass(frozen=True, slots=True)
class LnBinding:
    begin: date
    end: date
    title: str


@dataclass(frozen=True, slots=True)
class LnMonth:
    period_start: date
    value: str


@dataclass(frozen=True, slots=True)
class LnExtract:
    rows: tuple[LnMonth, ...]
    omitted_periods: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class StoredLnPoint:
    period_start: date
    observation_id: str
    raw_value: str
    provider_vintage_date: date
    source_release_at: datetime | None
    retrieved_at: datetime
    first_seen_at: datetime


def confirm_unemployment_series(series_text: str) -> LnBinding:
    """Bind only the monthly seasonally adjusted unemployment rate."""
    rows = _rows(series_text, "ln.series")
    matches = [
        row
        for row in rows
        if row.get("series_id") == SERIES_ID and row.get("periodicity_code") == PERIODICITY_CODE
    ]
    if len(matches) != 1:
        raise LnHistoryError("ln.series does not contain one monthly LNS14000000 row")
    row = matches[0]
    if row.get("series_title") != SERIES_TITLE:
        raise LnHistoryError("ln.series title is not the seasonally adjusted unemployment rate")
    if row.get("seasonal") != SEASONAL_CODE:
        raise LnHistoryError("ln.series seasonal code is not S")
    begin = _period(row.get("begin_year", ""), row.get("begin_period", ""))
    end = _period(row.get("end_year", ""), row.get("end_period", ""))
    if begin is None or end is None or begin > end:
        raise LnHistoryError("ln.series begin and end are not monthly dates")
    return LnBinding(begin=begin, end=end, title=row["series_title"])


def extract_unemployment_months(data_text: str, binding: LnBinding) -> LnExtract:
    """Keep every monthly value the file prints. Do not apply a start year."""
    present: dict[date, str] = {}
    omitted: list[str] = []
    for row in _rows(data_text, "ln.data.1.AllData"):
        if row.get("series_id") != SERIES_ID:
            continue
        period = _period(row.get("year", ""), row.get("period", ""))
        if period is None:
            continue
        raw = row.get("value", "").strip()
        if raw in BLANK_VALUES:
            omitted.append(period.isoformat())
            continue
        try:
            number = Decimal(raw)
        except InvalidOperation as exc:
            raise LnHistoryError(f"{period.isoformat()} is not a decimal") from exc
        if not number.is_finite():
            raise LnHistoryError(f"{period.isoformat()} is not finite")
        if period in present and present[period] != raw:
            raise LnHistoryError(f"contradictory values for {period.isoformat()}")
        present[period] = raw
    cursor = binding.begin
    while cursor <= binding.end:
        if cursor not in present and cursor.isoformat() not in omitted:
            omitted.append(cursor.isoformat())
        cursor = _next_month(cursor)
    rows = tuple(LnMonth(period, present[period]) for period in sorted(present))
    if not rows:
        raise LnHistoryError("no usable monthly unemployment observations")
    return LnExtract(rows=rows, omitted_periods=tuple(sorted(set(omitted))))


def observations_from_months(
    extracted: LnExtract,
    *,
    prior_points: tuple[StoredLnPoint, ...],
    retrieved_at: datetime,
) -> tuple[EconomicObservation, ...]:
    """One latest-revised extract. An unchanged stored value keeps its first identity."""
    latest = _latest_by_period(prior_points)
    observations: list[EconomicObservation] = []
    for item in extracted.rows:
        existing = latest.get(item.period_start)
        if existing is not None and _same_value(existing.raw_value, item.value):
            release = existing.source_release_at or existing.retrieved_at
            observations.append(
                _observation(
                    item,
                    observation_id=existing.observation_id,
                    vintage=existing.provider_vintage_date,
                    retrieved_at=existing.retrieved_at,
                    first_seen_at=existing.first_seen_at,
                    source_release_at=release,
                ),
            )
            continue
        vintage = retrieved_at.date()
        observations.append(
            _observation(
                item,
                observation_id=_observation_id(item.period_start, vintage),
                vintage=vintage,
                retrieved_at=retrieved_at,
                first_seen_at=retrieved_at,
                source_release_at=retrieved_at,
            ),
        )
    return tuple(observations)


def _observation(
    item: LnMonth,
    *,
    observation_id: str,
    vintage: date,
    retrieved_at: datetime,
    first_seen_at: datetime,
    source_release_at: datetime,
) -> EconomicObservation:
    return EconomicObservation(
        observation_id=observation_id,
        dataset_id=DATASET_ID,
        provider_id=PROVIDER_ID,
        source_id=SOURCE_ID,
        rights_record_id=RIGHTS_RECORD_ID,
        period_start=item.period_start,
        frequency=Frequency.MONTHLY,
        geography="US",
        unit=UNIT,
        seasonal_adjustment=SeasonalAdjustment.SEASONALLY_ADJUSTED,
        raw_value=item.value,
        quality_status=QualityStatus.OBSERVED,
        series_provenance=SeriesProvenance.LATEST_REVISED,
        provider_vintage_date=vintage,
        source_release_at=source_release_at,
        availability_precision=AvailabilityPrecision.UNKNOWN,
        retrieved_at=retrieved_at,
        first_seen_at=first_seen_at,
        source_locator=f"{DATA_URL}#{SERIES_ID}",
        adapter_version=f"{ADAPTER_ID}:{ADAPTER_VERSION}",
    )


def _observation_id(period_start: date, vintage: date) -> str:
    material = f"{SERIES_ID}:{period_start.isoformat()}:{vintage.isoformat()}"
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()[:24]
    return f"ln-{period_start.strftime('%Y%m')}-{digest}"


def _rows(text: str, label: str) -> list[dict[str, str]]:
    lines = [line for line in text.lstrip("\ufeff").splitlines() if line.strip()]
    if len(lines) < 2:
        raise LnHistoryError(f"{label} has no data rows")
    header = [part.strip() for part in lines[0].split("\t")]
    rows: list[dict[str, str]] = []
    for line in lines[1:]:
        parts = [part.strip() for part in line.split("\t")]
        if len(parts) < len(header):
            parts.extend([""] * (len(header) - len(parts)))
        rows.append({header[index]: parts[index] for index in range(len(header))})
    return rows


def _period(year: str, period: str) -> date | None:
    if not year.isdigit() or len(period) != 3 or not period.startswith("M"):
        return None
    month_text = period[1:]
    if not month_text.isdigit():
        return None
    month = int(month_text)
    if month < 1 or month > 12:
        return None
    return date(int(year), month, 1)


def _next_month(day: date) -> date:
    if day.month == 12:
        return date(day.year + 1, 1, 1)
    return date(day.year, day.month + 1, 1)


def _latest_by_period(points: tuple[StoredLnPoint, ...]) -> dict[date, StoredLnPoint]:
    latest: dict[date, StoredLnPoint] = {}
    for point in points:
        current = latest.get(point.period_start)
        if current is None or (point.provider_vintage_date, point.retrieved_at) >= (
            current.provider_vintage_date,
            current.retrieved_at,
        ):
            latest[point.period_start] = point
    return latest


def _same_value(stored: str, incoming: str) -> bool:
    try:
        return Decimal(stored) == Decimal(incoming)
    except InvalidOperation:
        return stored == incoming
