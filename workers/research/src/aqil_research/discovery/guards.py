"""Leakage guards. A failed guard is a refused cell, not a softer label."""

from __future__ import annotations

from datetime import date, datetime

from aqil_research.contracts.observation import (
    AnalysisMode,
    EconomicObservation,
    SeriesProvenance,
)
from aqil_research.discovery.calendar import add_months
from aqil_research.vintages.asof import select_as_of_series


class LeakageError(Exception):
    """Raised when a result would use information from after the decision time."""


def point_in_time_class(provenance: SeriesProvenance, requested_mode: AnalysisMode) -> str:
    """Return the only class a stored provenance may be given."""
    if provenance == SeriesProvenance.LATEST_REVISED:
        if requested_mode == AnalysisMode.POINT_IN_TIME:
            raise LeakageError("a latest_revised input cannot be saved as point_in_time")
        return "retrospective_assumed_lag"
    if requested_mode == AnalysisMode.POINT_IN_TIME:
        return "point_in_time"
    return "retrospective_assumed_lag"


def assert_entry_on_or_after_decision(entry: date, decision: date) -> None:
    if entry < decision:
        raise LeakageError("a return window cannot start before the decision time")


def assert_signal_known(period: date, lag_months: int, decision: date) -> None:
    """Reject a macro period that is still inside its assumed availability lag."""
    if lag_months < 0:
        raise LeakageError("an availability lag cannot be negative")
    known_on = add_months(period, lag_months)
    if decision < known_on:
        raise LeakageError("a macro value is not known at this decision time")


def assert_no_future_value(
    periods: tuple[date, ...] | list[date], decision: date, lag_months: int
) -> None:
    for period in periods:
        assert_signal_known(period, lag_months, decision)


def recorded_series_class(
    observations: tuple[EconomicObservation, ...],
    dataset_id: str,
    decision_at: datetime,
    mode: AnalysisMode,
) -> str:
    """Classify a series only after the existing as-of selector has been applied."""
    provenances = {row.series_provenance for row in observations if row.dataset_id == dataset_id}
    if SeriesProvenance.LATEST_REVISED in provenances and mode == AnalysisMode.POINT_IN_TIME:
        raise LeakageError("a latest_revised input cannot be saved as point_in_time")
    selected = select_as_of_series(observations, dataset_id, decision_at, mode)
    if mode == AnalysisMode.POINT_IN_TIME and SeriesProvenance.LATEST_REVISED in provenances:
        if selected:
            raise LeakageError("a latest_revised input cannot be saved as point_in_time")
        raise LeakageError("latest_revised rows were dropped and cannot be labelled point_in_time")
    if not provenances:
        raise LeakageError("no observations were available for this series")
    if provenances == {SeriesProvenance.LATEST_REVISED}:
        return "retrospective_assumed_lag"
    if mode == AnalysisMode.POINT_IN_TIME:
        return "point_in_time"
    return "retrospective_assumed_lag"
