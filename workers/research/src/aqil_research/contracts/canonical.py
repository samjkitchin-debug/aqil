"""Canonical serialisation for reproducible content hashes."""

from __future__ import annotations

from aqil_research.contracts.observation import EconomicObservation


def observation_canonical_dict(row: EconomicObservation) -> dict[str, object]:
    """All fields that materially affect analytical meaning and provenance."""
    return row.model_dump(mode="json", exclude_none=True)
