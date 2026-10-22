"""Parse confirmed BLS CPI-U all-items rows into EconomicObservation schema 1.0.

Binding comes from cu.series. Observations come from cu.data.1.AllItems.
Months without a finite non-zero number are omitted. They are not stored as
zero and they are not interpolated. A footnote on a real number stays the
current observed value. The file has no historical vintages, so rows are
latest_revised with availability_precision unknown.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from aqil_research.adapters.bls_cpi_series.stability import (
    CpiValuePoint,
    StableCpiPoint,
    StoredCpiPoint,
    stabilise_cpi_points,
)
from aqil_research.contracts.observation import (
    AvailabilityPrecision,
    EconomicObservation,
    Frequency,
    QualityStatus,
    SeasonalAdjustment,
    SeriesProvenance,
)

SERIES_ID = "CUSR0000SA0"
DATASET_ID = "bls.cu.CUSR0000SA0"
SOURCE_ID = "bls_cpi_u_all_items"
RIGHTS_RECORD_ID = SOURCE_ID
PROVIDER_ID = "bls"
GEOGRAPHY = "US"
UNIT = "1982-84=100"
SEASONAL_CODE = "S"
PERIODICITY_CODE = "R"
AREA_CODE = "0000"
ITEM_CODE = "SA0"
SERIES_TITLE = "All items in U.S. city average, all urban consumers, seasonally adjusted"
DATA_LOCATOR = "https://download.bls.gov/pub/time.series/cu/cu.data.1.AllItems"

MONTHLY_PERIOD = re.compile(r"^M(0[1-9]|1[0-2])$")
SERIES_COLUMNS = (
    "series_id",
    "area_code",
    "item_code",
    "seasonal",
    "periodicity_code",
    "base_code",
    "base_period",
    "series_title",
    "footnote_codes",
    "begin_year",
    "begin_period",
    "end_year",
    "end_period",
)
DATA_COLUMNS = ("series_id", "year", "period", "value", "footnote_codes")


@dataclass(frozen=True, slots=True)
class CpiSeriesBinding:
    """Identity fields read from one cu.series row."""

    series_id: str
    area_code: str
    item_code: str
    seasonal_code: str
    periodicity_code: str
    base_code: str
    base_period: str
    series_title: str


@dataclass(frozen=True, slots=True)
class OmittedCpiPeriod:
    period_label: str
    reason: str


@dataclass(frozen=True, slots=True)
class CpiParseResult:
    observations: tuple[EconomicObservation, ...]
    omitted_periods: tuple[OmittedCpiPeriod, ...]


def confirm_cpi_series(series_text: str) -> CpiSeriesBinding:
    """Bind CUSR0000SA0 only when the official series row matches the CU codes."""
    rows = _table(series_text, SERIES_COLUMNS, "cu.series")
    matches = [row for row in rows if row["series_id"] == SERIES_ID]
    if len(matches) != 1:
        raise ValueError(f"{SERIES_ID} was not confirmed in cu.series")
    row = matches[0]
    binding = CpiSeriesBinding(
        series_id=row["series_id"],
        area_code=row["area_code"],
        item_code=row["item_code"],
        seasonal_code=row["seasonal"],
        periodicity_code=row["periodicity_code"],
        base_code=row["base_code"],
        base_period=row["base_period"],
        series_title=row["series_title"],
    )
    _require_confirmed_binding(binding)
    return binding


def parse_cpi_data(
    data_text: str,
    *,
    binding: CpiSeriesBinding,
    adapter_version: str,
    retrieved_at: datetime,
    prior_points: tuple[StoredCpiPoint, ...] = (),
) -> CpiParseResult:
    """Map one all-items file to monthly observations for the confirmed series."""
    _require_confirmed_binding(binding)
    rows = _table(data_text, DATA_COLUMNS, "cu.data.1.AllItems")
    values, omitted = _select_monthly_values(rows)
    if not values:
        raise ValueError("no usable monthly CPI observations in the flat file")
    stable = stabilise_cpi_points(values, prior_points, retrieved_at)
    observations = tuple(_observation(point, adapter_version=adapter_version) for point in stable)
    return CpiParseResult(observations=observations, omitted_periods=tuple(omitted))


def _require_confirmed_binding(binding: CpiSeriesBinding) -> None:
    expected = {
        "series_id": SERIES_ID,
        "area_code": AREA_CODE,
        "item_code": ITEM_CODE,
        "seasonal_code": SEASONAL_CODE,
        "periodicity_code": PERIODICITY_CODE,
        "base_period": UNIT,
        "series_title": SERIES_TITLE,
    }
    actual = {
        "series_id": binding.series_id,
        "area_code": binding.area_code,
        "item_code": binding.item_code,
        "seasonal_code": binding.seasonal_code,
        "periodicity_code": binding.periodicity_code,
        "base_period": binding.base_period,
        "series_title": binding.series_title,
    }
    mismatched = [name for name, value in expected.items() if actual[name] != value]
    if mismatched or binding.base_code != "S":
        detail = ", ".join(mismatched) or "base_code"
        raise ValueError(f"cu.series no longer matches the bound CPI series ({detail})")


def _select_monthly_values(
    rows: list[dict[str, str]],
) -> tuple[tuple[CpiValuePoint, ...], list[OmittedCpiPeriod]]:
    omitted: list[OmittedCpiPeriod] = []
    by_period: dict[date, CpiValuePoint] = {}
    for row in rows:
        if row["series_id"] != SERIES_ID:
            continue
        label = _period_label(row["year"], row["period"])
        if not MONTHLY_PERIOD.match(row["period"]) or not row["year"].isdigit():
            omitted.append(OmittedCpiPeriod(label, "non-monthly period is omitted"))
            continue
        period_start = date(int(row["year"]), int(row["period"][1:]), 1)
        value = row["value"]
        footnote = row["footnote_codes"]
        if value == "":
            omitted.append(OmittedCpiPeriod(label, "missing value is omitted"))
            continue
        try:
            parsed = Decimal(value)
        except InvalidOperation:
            reason = (
                "unavailable value is omitted"
                if "X" in footnote or value == "-"
                else "missing value is omitted"
            )
            omitted.append(OmittedCpiPeriod(label, reason))
            continue
        if not parsed.is_finite():
            omitted.append(OmittedCpiPeriod(label, "missing value is omitted"))
            continue
        if parsed == 0:
            omitted.append(OmittedCpiPeriod(label, "zero is not stored"))
            continue
        if parsed < 0:
            raise ValueError(f"negative CPI index for {label}")
        point = CpiValuePoint(period_start=period_start, raw_value=value)
        existing = by_period.get(period_start)
        if existing is not None and not _same_text(existing.raw_value, point.raw_value):
            raise ValueError(f"contradictory CPI values for {label}")
        by_period[period_start] = point
    ordered = tuple(by_period[key] for key in sorted(by_period))
    return ordered, omitted


def _observation(point: StableCpiPoint, *, adapter_version: str) -> EconomicObservation:
    return EconomicObservation(
        observation_id=point.observation_id,
        dataset_id=DATASET_ID,
        provider_id=PROVIDER_ID,
        source_id=SOURCE_ID,
        rights_record_id=RIGHTS_RECORD_ID,
        period_start=point.period_start,
        frequency=Frequency.MONTHLY,
        geography=GEOGRAPHY,
        unit=UNIT,
        seasonal_adjustment=SeasonalAdjustment.SEASONALLY_ADJUSTED,
        raw_value=point.raw_value,
        quality_status=QualityStatus.OBSERVED,
        series_provenance=SeriesProvenance.LATEST_REVISED,
        provider_vintage_date=point.provider_vintage_date,
        source_release_at=point.source_release_at,
        earliest_model_available_at=None,
        availability_precision=AvailabilityPrecision.UNKNOWN,
        retrieved_at=point.retrieved_at,
        first_seen_at=point.retrieved_at,
        source_locator=DATA_LOCATOR,
        adapter_version=adapter_version,
    )


def _table(text: str, columns: tuple[str, ...], label: str) -> list[dict[str, str]]:
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        raise ValueError(f"{label} is empty")
    header = _cells(lines[0])
    if tuple(header) != columns:
        raise ValueError(f"{label} header does not match the CU flat file")
    rows: list[dict[str, str]] = []
    width = len(columns)
    for line in lines[1:]:
        cells = _cells(line)
        if len(cells) < width:
            cells = [*cells, *([""] * (width - len(cells)))]
        if len(cells) != width:
            raise ValueError(f"{label} row does not match the CU flat file")
        rows.append(dict(zip(columns, cells, strict=True)))
    return rows


def _cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.rstrip("\r").split("\t")]


def _period_label(year: str, period: str) -> str:
    if year.isdigit() and MONTHLY_PERIOD.match(period):
        return f"{year}-{period[1:]}"
    return f"{year or 'unknown'}-{period or 'unknown'}"


def _same_text(left: str, right: str) -> bool:
    try:
        return Decimal(left) == Decimal(right)
    except InvalidOperation:
        return left == right
