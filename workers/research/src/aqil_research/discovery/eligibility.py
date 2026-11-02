"""Sample floors. They are gates, not targets to be relaxed."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SampleFloors:
    exploratory_decision_points: int = 36
    exploratory_non_overlapping: int = 8
    statistical_decision_points: int = 60
    statistical_non_overlapping: int = 15


def meets_exploratory(decision_points: int, non_overlapping: int, floors: SampleFloors) -> bool:
    return (
        decision_points >= floors.exploratory_decision_points
        and non_overlapping >= floors.exploratory_non_overlapping
    )


def meets_statistical(decision_points: int, non_overlapping: int, floors: SampleFloors) -> bool:
    return (
        decision_points >= floors.statistical_decision_points
        and non_overlapping >= floors.statistical_non_overlapping
    )
