"""Keep an unchanged G.17 value on its original row.

The Board package is one latest-revised file. It does not carry a historical
vintage for each month. Aqil therefore reuses the first stored identity when
the value is unchanged, and opens a new identity only when the value changes.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from aqil_research.adapters.fed_g17.parse import (
    g17_observation_id,
    is_omitted_token,
    month_period_start,
)


@dataclass(frozen=True, slots=True)
class StoredG17Point:
    period_start: date
    observation_id: str
    raw_value: str
    provider_vintage_date: date
    source_release_at: datetime | None
    retrieved_at: datetime


def stabilise_g17_vintages(
    payload: dict[str, object],
    prior_points: tuple[StoredG17Point, ...],
    retrieved_at: datetime,
) -> dict[str, object]:
    """Attach a stable identity to each package row before parsing."""
    rows = payload.get("observations")
    if not isinstance(rows, list):
        return payload
    latest = _latest_by_period(prior_points)
    used_ids = {point.observation_id for point in prior_points}
    annotated: list[object] = []
    for item in rows:
        if not isinstance(item, dict):
            annotated.append(item)
            continue
        period_start = month_period_start(str(item.get("period", "")))
        value = str(item.get("value", "")).strip()
        if period_start is None or is_omitted_token(value):
            annotated.append(item)
            continue
        existing = latest.get(period_start)
        if existing is not None and _same_value(existing.raw_value, value):
            release = existing.source_release_at or existing.retrieved_at
            annotated.append(
                {
                    **item,
                    "vintage": existing.provider_vintage_date.isoformat(),
                    "observation_id": existing.observation_id,
                    "source_release_at": release.isoformat(),
                    "revision_basis": "latest_revised",
                },
            )
            continue
        vintage = retrieved_at.date()
        observation_id = g17_observation_id(period_start, vintage)
        if observation_id in used_ids:
            observation_id = g17_observation_id(
                period_start,
                vintage,
                f"{value}:{retrieved_at.isoformat()}",
            )
        annotated.append(
            {
                **item,
                "vintage": vintage.isoformat(),
                "observation_id": observation_id,
                "source_release_at": retrieved_at.isoformat(),
                "revision_basis": "latest_revised",
            },
        )
    return {**payload, "observations": annotated}


def _latest_by_period(
    points: tuple[StoredG17Point, ...],
) -> dict[date, StoredG17Point]:
    latest: dict[date, StoredG17Point] = {}
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
