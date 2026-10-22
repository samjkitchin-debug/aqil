"""Keep an unchanged CPI value on its original row.

The CU flat file is one latest-revised extract. It does not carry a historical
vintage for each month. Aqil reuses the first stored identity when the finite
decimal is unchanged, and opens a new identity only when the value changes.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from aqil_research.contracts.observation import EconomicObservation

SERIES_ID = "CUSR0000SA0"


@dataclass(frozen=True, slots=True)
class CpiValuePoint:
    period_start: date
    raw_value: str


@dataclass(frozen=True, slots=True)
class StoredCpiPoint:
    period_start: date
    observation_id: str
    raw_value: str
    provider_vintage_date: date
    source_release_at: datetime | None
    retrieved_at: datetime


@dataclass(frozen=True, slots=True)
class StableCpiPoint:
    period_start: date
    raw_value: str
    observation_id: str
    provider_vintage_date: date
    source_release_at: datetime
    retrieved_at: datetime


def cpi_observation_id(period_start: date, vintage: date, disambiguator: str = "") -> str:
    """Stable id for one month and collection date. A disambiguator separates a same-day change."""
    key = f"{SERIES_ID}:{period_start.isoformat()}:{vintage.isoformat()}"
    if disambiguator:
        key = f"{key}:{disambiguator}"
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]
    return f"cpi-{period_start.strftime('%Y%m')}-{digest}"


def points_from_observations(
    observations: tuple[EconomicObservation, ...],
) -> tuple[StoredCpiPoint, ...]:
    """Copy stored identity fields so a later read of the same file can reuse them."""
    return tuple(
        StoredCpiPoint(
            period_start=row.period_start,
            observation_id=row.observation_id,
            raw_value=row.raw_value,
            provider_vintage_date=row.provider_vintage_date,
            source_release_at=row.source_release_at,
            retrieved_at=row.retrieved_at,
        )
        for row in observations
    )


def stabilise_cpi_points(
    points: tuple[CpiValuePoint, ...],
    prior_points: tuple[StoredCpiPoint, ...],
    retrieved_at: datetime,
) -> tuple[StableCpiPoint, ...]:
    """Attach a stable identity to each monthly value before it becomes an observation."""
    latest = _latest_by_period(prior_points)
    used_ids = {point.observation_id for point in prior_points}
    stable: list[StableCpiPoint] = []
    for point in points:
        existing = latest.get(point.period_start)
        if existing is not None and _same_value(existing.raw_value, point.raw_value):
            release = existing.source_release_at or existing.retrieved_at
            stable.append(
                StableCpiPoint(
                    period_start=point.period_start,
                    raw_value=existing.raw_value,
                    observation_id=existing.observation_id,
                    provider_vintage_date=existing.provider_vintage_date,
                    source_release_at=release,
                    retrieved_at=existing.retrieved_at,
                ),
            )
            continue
        vintage = retrieved_at.date()
        observation_id = cpi_observation_id(point.period_start, vintage)
        if observation_id in used_ids:
            observation_id = cpi_observation_id(
                point.period_start,
                vintage,
                f"{point.raw_value}:{retrieved_at.isoformat()}",
            )
        used_ids.add(observation_id)
        stable.append(
            StableCpiPoint(
                period_start=point.period_start,
                raw_value=point.raw_value,
                observation_id=observation_id,
                provider_vintage_date=vintage,
                source_release_at=retrieved_at,
                retrieved_at=retrieved_at,
            ),
        )
    return tuple(stable)


def _latest_by_period(
    points: tuple[StoredCpiPoint, ...],
) -> dict[date, StoredCpiPoint]:
    latest: dict[date, StoredCpiPoint] = {}
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
