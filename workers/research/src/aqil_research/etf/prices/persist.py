"""Shared price persistence. Adapters do not write rows.

A second refresh with the same close does not insert another revision.
A rejected or failed provider leaves the previous close in place.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from aqil_research.etf.prices.models import PriceObservation
from aqil_research.sources.rights import (
    OperationalStatus,
    RightsOperation,
    SourceRightsRecord,
    source_usable,
)


class PricePersistenceError(Exception):
    """Raised when a price must not be written."""


@dataclass(frozen=True)
class PriceWrite:
    observation: PriceObservation
    action: str


def storage_allowed(
    record: SourceRightsRecord | None,
    *,
    display_audience: str,
) -> bool:
    """Store only when retention is permitted for the audience that can read it.

    ``any_signed_in`` is the current production audience. That needs retention
    and display rights. An unknown or disabled row refuses both.
    """

    if record is None or record.operational_status != OperationalStatus.ENABLED:
        return False
    if not source_usable(record, RightsOperation.AUTOMATED_ACCESS):
        return False
    if not source_usable(record, RightsOperation.RAW_DATA_RETENTION):
        return False
    if not source_usable(record, RightsOperation.HISTORICAL_ARCHIVING):
        return False
    if display_audience == "founder":
        return source_usable(record, RightsOperation.INTERNAL_COMPUTATION)
    if display_audience == "any_signed_in":
        return source_usable(record, RightsOperation.REDISTRIBUTION) and source_usable(
            record,
            RightsOperation.COMMERCIAL_PUBLICATION,
        )
    return False


def plan_price_writes(
    existing: tuple[PriceObservation, ...],
    incoming: tuple[PriceObservation, ...],
) -> tuple[PriceWrite, ...]:
    """Append a changed close. Skip an identical close. Never delete."""

    writes: list[PriceWrite] = []
    held = list(existing)
    for observation in incoming:
        if observation.value < 0:
            raise PricePersistenceError("a negative price is rejected")
        matches = [
            row
            for row in held
            if row.listing_key == observation.listing_key
            and row.source_id == observation.source_id
            and row.price_type == observation.price_type
            and row.session_date == observation.session_date
        ]
        if any(_same_content(row, observation) for row in matches):
            writes.append(PriceWrite(observation, "skip"))
            continue
        revision = max((row.revision for row in matches), default=0) + 1
        stored = observation.model_copy(update={"revision": revision})
        held.append(stored)
        writes.append(PriceWrite(stored, "append"))
    return tuple(writes)


def apply_price_writes(
    existing: tuple[PriceObservation, ...],
    writes: tuple[PriceWrite, ...],
) -> tuple[PriceObservation, ...]:
    """Apply appends. A skip leaves the previous row untouched."""

    stored = list(existing)
    for write in writes:
        if write.action == "append":
            stored.append(write.observation)
    return tuple(stored)


def mark_stale(
    existing: tuple[PriceObservation, ...],
    *,
    retrieved_at: datetime,
    max_age_hours: int = 48,
) -> tuple[PriceObservation, ...]:
    """Return copies marked stale when the retrieval is older than the limit.

    The original rows are not mutated. A stale quote stays a quote.
    """

    marked: list[PriceObservation] = []
    for row in existing:
        age = retrieved_at - row.retrieved_at
        if age.total_seconds() > max_age_hours * 3600 and row.quality == "accepted":
            marked.append(row.model_copy(update={"quality": "stale"}))
        else:
            marked.append(row)
    return tuple(marked)


def _same_content(left: PriceObservation, right: PriceObservation) -> bool:
    return (
        left.value == right.value
        and left.quote_unit == right.quote_unit
        and left.currency == right.currency
        and left.adjustment_status == right.adjustment_status
        and left.adjustment_definition == right.adjustment_definition
        and left.quality == right.quality
    )
