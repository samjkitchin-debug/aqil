"""Parse one Eurostat JSON statistics response into EconomicObservation 1.0 rows."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from aqil_research.adapters.eurostat_unemployment.constants import (
    ACCESS_URL,
    ADAPTER_ID,
    ADAPTER_VERSION,
    ADJUSTMENT_LABEL,
    AGENCY_ID,
    DATASET_ID,
    DIMENSIONS,
    FREQUENCY_VALUE,
    GEO_CODE,
    GEOGRAPHY,
    PERIOD_KIND,
    PROVIDER_ID,
    RIGHTS_RECORD_ID,
    SEASONAL_VALUE,
    SOURCE_ID,
    SOURCE_NAME,
    UNIT_TEXT,
    VINTAGE_CLASS,
)
from aqil_research.adapters.eurostat_unemployment.stability import observation_id
from aqil_research.contracts.observation import (
    AvailabilityPrecision,
    EconomicObservation,
    Frequency,
    QualityStatus,
    SeasonalAdjustment,
    SeriesProvenance,
)

OBSERVATION_ADAPTER_VERSION = f"{ADAPTER_ID}:{ADAPTER_VERSION}"

MONTH_PERIOD = re.compile(r"^(\d{4})-(\d{2})$")

QUARTER_PERIOD = re.compile(r"^(\d{4})-Q([1-4])$")

_FREQUENCY = {
    "monthly": Frequency.MONTHLY,
    "quarterly": Frequency.QUARTERLY,
}

_SEASONAL = {
    "seasonally_adjusted": SeasonalAdjustment.SEASONALLY_ADJUSTED,
    "not_seasonally_adjusted": SeasonalAdjustment.NOT_SEASONALLY_ADJUSTED,
    "unknown": SeasonalAdjustment.UNKNOWN,
}


@dataclass(frozen=True, slots=True)
class EurostatParseResult:
    observations: tuple[EconomicObservation, ...]

    omitted_periods: tuple[str, ...]

    series_key: str

    compiler_sentence: str

    unit: str

    seasonal_adjustment: str

    frequency: str

    vintage_class: str


def parse_eurostat_json(text: str, *, retrieved_at: datetime) -> EurostatParseResult:
    """Map one filtered JSON series. Missing periods are omitted, not filled."""

    try:
        payload = json.loads(text, parse_float=Decimal, parse_int=Decimal)

    except json.JSONDecodeError as exc:
        raise ValueError("Eurostat JSON could not be read") from exc

    if not isinstance(payload, dict):
        raise ValueError("Eurostat JSON is not an object")

    if (
        payload.get("source") != SOURCE_NAME
        or (payload.get("extension") or {}).get("agencyId") != AGENCY_ID
    ):
        raise ValueError("refusing a response that is not from Eurostat agency ESTAT")

    dimension = payload.get("dimension")

    order = payload.get("id")

    size = payload.get("size")

    if not isinstance(dimension, dict) or not isinstance(order, list) or not isinstance(size, list):
        raise ValueError("Eurostat JSON has no series dimensions")

    if order[-1:] != ["time"]:
        raise ValueError("Eurostat time dimension is not last")

    if any(item != 1 for item in size[:-1]):
        raise ValueError("refusing a response that is not one series")

    for name, code, label in DIMENSIONS:
        _require_dimension(dimension, name, code, label)

    geo_label = _label(dimension, "geo", GEO_CODE)

    if "EU27" in GEO_CODE or "EU27" in geo_label:
        raise ValueError("refusing EU27; this series is not the euro area")

    time_index = ((dimension.get("time") or {}).get("category") or {}).get("index")

    if not isinstance(time_index, dict) or not time_index:
        raise ValueError("Eurostat JSON has no time index")

    values = payload.get("value")

    if not isinstance(values, dict):
        raise ValueError("Eurostat JSON has no values")

    observations: list[EconomicObservation] = []

    omitted: list[str] = []

    seen: dict[date, str] = {}

    for token, position in time_index.items():
        period_token = str(token)

        period_start = _period(period_token)

        if period_start is None:
            raise ValueError(f"unparseable period {period_token}")

        raw = values.get(str(position))

        if raw is None:
            omitted.append(period_token)

            continue

        if not isinstance(raw, Decimal) or not raw.is_finite():
            raise ValueError(f"{period_token}: non-numeric value")

        value_raw = format(raw, "f")

        previous = seen.get(period_start)

        if previous is not None:
            if Decimal(previous) != raw:
                raise ValueError(
                    f"{period_token}: more than one value; this file is not classified "
                    "as a vintage panel",
                )

            continue

        seen[period_start] = value_raw

        vintage = retrieved_at.date()

        observations.append(
            EconomicObservation(
                observation_id=observation_id(period_start, vintage),
                dataset_id=DATASET_ID,
                provider_id=PROVIDER_ID,
                source_id=SOURCE_ID,
                rights_record_id=RIGHTS_RECORD_ID,
                period_start=period_start,
                frequency=_FREQUENCY[FREQUENCY_VALUE],
                geography=GEOGRAPHY,
                unit=UNIT_TEXT,
                seasonal_adjustment=_SEASONAL[SEASONAL_VALUE],
                raw_value=value_raw,
                quality_status=QualityStatus.OBSERVED,
                series_provenance=SeriesProvenance.LATEST_REVISED,
                provider_vintage_date=vintage,
                source_release_at=retrieved_at,
                earliest_model_available_at=None,
                availability_precision=AvailabilityPrecision.UNKNOWN,
                retrieved_at=retrieved_at,
                first_seen_at=retrieved_at,
                source_locator=ACCESS_URL,
                adapter_version=OBSERVATION_ADAPTER_VERSION,
            ),
        )

    if not observations:
        raise ValueError("Eurostat JSON has no stored values")

    observations.sort(key=lambda item: item.period_start)

    return EurostatParseResult(
        observations=tuple(observations),
        omitted_periods=tuple(omitted),
        series_key=DATASET_ID,
        compiler_sentence=f"Eurostat agency {AGENCY_ID}. Geography {GEO_CODE}: {geo_label}.",
        unit=UNIT_TEXT,
        seasonal_adjustment=ADJUSTMENT_LABEL,
        frequency=FREQUENCY_VALUE,
        vintage_class=VINTAGE_CLASS,
    )


def _require_dimension(dimension: dict[str, object], name: str, code: str, label: str) -> None:

    actual_code = _index(dimension, name)

    actual_label = _label(dimension, name, code)

    if actual_code != {code: 0} or actual_label != label:
        raise ValueError(
            f"{name} is {actual_code} {actual_label or 'blank'}; refusing a series that is not "
            f"{code} ({label})",
        )


def _index(dimension: dict[str, object], name: str) -> dict[str, int]:

    category = _category(dimension, name)

    index = category.get("index")

    if not isinstance(index, dict):
        raise ValueError(f"{name} has no code index")

    return {str(key): int(value) for key, value in index.items()}


def _label(dimension: dict[str, object], name: str, code: str) -> str:

    category = _category(dimension, name)

    labels = category.get("label")

    if not isinstance(labels, dict):
        raise ValueError(f"{name} has no label")

    return str(labels.get(code) or "")


def _category(dimension: dict[str, object], name: str) -> dict[str, object]:

    spec = dimension.get(name)

    if not isinstance(spec, dict):
        raise ValueError(f"Eurostat JSON is missing {name}")

    category = spec.get("category")

    if not isinstance(category, dict):
        raise ValueError(f"{name} has no category")

    return category


def _period(token: str) -> date | None:

    if PERIOD_KIND == "month":
        match = MONTH_PERIOD.match(token)

        if match is None:
            return None

        year = int(match.group(1))

        month = int(match.group(2))

        if month < 1 or month > 12:
            return None

        return date(year, month, 1)

    match = QUARTER_PERIOD.match(token)

    if match is None:
        return None

    year = int(match.group(1))

    quarter = int(match.group(2))

    return date(year, (quarter - 1) * 3 + 1, 1)
