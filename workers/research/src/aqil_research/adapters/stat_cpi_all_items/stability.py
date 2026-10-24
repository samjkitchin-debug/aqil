"""Keep an unchanged CPI reference value on its first stored row.

The CSV is one latest-revised series. It does not carry a historical vintage
for each month. An unchanged finite decimal keeps the first observation id,
provider vintage date, and release identity. A changed value is a new row.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from aqil_research.adapters.stat_cpi_all_items.constants import ITEM_CODE
from aqil_research.contracts.observation import EconomicObservation


@dataclass(frozen=True, slots=True)
class StoredStatCpiPoint:
    period_start: date
    observation_id: str
    raw_value: str
    provider_vintage_date: date
    source_release_at: datetime | None
    retrieved_at: datetime
    first_seen_at: datetime


def observation_id(period_start: date, vintage: date, disambiguator: str = "") -> str:
    """Stable id for one period and vintage. A disambiguator separates a same-day change."""
    key = f"{ITEM_CODE}:{period_start.isoformat()}:{vintage.isoformat()}"
    if disambiguator:
        key = f"{key}:{disambiguator}"
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]
    return f"stat-cpi-{period_start.strftime('%Y%m')}-{digest}"


def stabilise_stat_cpi_observations(
    observations: tuple[EconomicObservation, ...],
    prior_points: tuple[StoredStatCpiPoint, ...],
    retrieved_at: datetime,
) -> tuple[EconomicObservation, ...]:
    """Reuse the stored identity when the finite decimal is unchanged."""
    latest = _latest_by_period(prior_points)
    used_ids = {point.observation_id for point in prior_points}
    stabilised: list[EconomicObservation] = []
    for observation in observations:
        existing = latest.get(observation.period_start)
        if existing is not None and _same_value(existing.raw_value, observation.raw_value):
            stabilised.append(
                observation.model_copy(
                    update={
                        "observation_id": existing.observation_id,
                        "raw_value": existing.raw_value,
                        "provider_vintage_date": existing.provider_vintage_date,
                        "source_release_at": existing.source_release_at,
                        "retrieved_at": existing.retrieved_at,
                        "first_seen_at": existing.first_seen_at,
                    },
                ),
            )
            continue
        vintage = retrieved_at.date()
        assigned = observation_id(observation.period_start, vintage)
        if assigned in used_ids:
            assigned = observation_id(
                observation.period_start,
                vintage,
                f"{observation.raw_value}:{retrieved_at.isoformat()}",
            )
        used_ids.add(assigned)
        stabilised.append(
            observation.model_copy(
                update={
                    "observation_id": assigned,
                    "provider_vintage_date": vintage,
                    "source_release_at": retrieved_at,
                    "retrieved_at": retrieved_at,
                    "first_seen_at": retrieved_at,
                },
            ),
        )
    return tuple(stabilised)


def _latest_by_period(
    points: tuple[StoredStatCpiPoint, ...],
) -> dict[date, StoredStatCpiPoint]:
    latest: dict[date, StoredStatCpiPoint] = {}
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
