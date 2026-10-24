"""Keep an unchanged OECD CLI value on its first stored row."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from aqil_research.adapters.oecd_cli.constants import SERIES_KEY
from aqil_research.contracts.observation import EconomicObservation


@dataclass(frozen=True, slots=True)
class StoredOecdPoint:
    period_start: date
    observation_id: str
    raw_value: str
    provider_vintage_date: date
    source_release_at: datetime | None
    retrieved_at: datetime
    first_seen_at: datetime


def observation_id(period_start: date, vintage: date, disambiguator: str = "") -> str:
    """Stable id for one period and vintage. A disambiguator separates a same-day change."""
    key = f"{SERIES_KEY}:{period_start.isoformat()}:{vintage.isoformat()}"
    if disambiguator:
        key = f"{key}:{disambiguator}"
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]
    return f"oecd-cli-{period_start.strftime('%Y%m')}-{digest}"


def stabilise_oecd_observations(
    observations: tuple[EconomicObservation, ...],
    prior_points: tuple[StoredOecdPoint, ...],
    retrieved_at: datetime,
) -> tuple[EconomicObservation, ...]:
    """Reuse the stored identity when the finite decimal is unchanged."""
    latest: dict[date, StoredOecdPoint] = {}
    for point in prior_points:
        current = latest.get(point.period_start)
        if current is None or (point.provider_vintage_date, point.retrieved_at) >= (
            current.provider_vintage_date,
            current.retrieved_at,
        ):
            latest[point.period_start] = point
    used_ids = {point.observation_id for point in prior_points}
    stabilised: list[EconomicObservation] = []
    for observation in observations:
        existing = latest.get(observation.period_start)
        if existing is not None:
            try:
                same = Decimal(existing.raw_value) == Decimal(observation.raw_value)
            except InvalidOperation:
                same = existing.raw_value == observation.raw_value
            if same:
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
