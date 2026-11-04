"""Join and leakage guards. These functions do not read a database."""

from __future__ import annotations

from datetime import date

from aqil_research.long_horizon.vwra_discovery.specification import (
    CENSUS_DATASET,
    VWRA_FIRST_SESSION,
    assert_vwra_session,
    join_allowed,
)


def assert_state_feature(feature_id: str) -> None:
    """A forward outcome is not a state."""
    if feature_id.startswith("outcome_") or "surprise" in feature_id:
        raise ValueError(f"{feature_id} is not a state")


def missing_datasets(
    required: tuple[str, ...],
    stored_counts: dict[str, int],
) -> tuple[str, ...]:
    """Dataset ids with no stored rows. Census stays in this list when its count is zero."""
    return tuple(dataset_id for dataset_id in required if stored_counts.get(dataset_id, 0) == 0)


def unavailable_reason(missing: tuple[str, ...]) -> str:
    if not missing:
        raise ValueError("an unavailable method needs the missing dataset")
    names = ", ".join(missing)
    if CENSUS_DATASET in missing:
        return f"No stored observations for {names}."
    return f"No stored observations for {names}."


def refuse_early_session(session: date) -> None:
    assert_vwra_session(session)
    if session < VWRA_FIRST_SESSION:
        raise ValueError(session.isoformat())


def latest_period(period_ends: tuple[date, ...], anchor: date) -> date | None:
    """The latest period end on or before the anchor. A later period is dropped."""
    eligible = [item for item in period_ends if join_allowed(item, anchor)]
    if not eligible:
        return None
    return max(eligible)
