"""Census of the 26 stored method replays. This module does not score EIMI.

It reads stored points. It does not delete them and it does not replay a failed method.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date

import psycopg

from aqil_research.discovery.classification import SPECS
from aqil_research.long_horizon.vwra_discovery.comparison import STORED_METHOD_SPECIFICATION
from aqil_research.long_horizon.vwra_discovery.specification import NOT_A_MONTHLY_STATE
from aqil_research.methods.registry import default_method_registry


@dataclass(frozen=True)
class PointFact:
    series_key: str
    period_end: date
    direction: str | None
    state_label: str | None


@dataclass(frozen=True)
class DatasetCoverage:
    dataset_id: str
    stored_rows: int
    earliest: date | None
    latest: date | None


@dataclass(frozen=True)
class MethodCensus:
    method_id: str
    method_class: str
    method_version: str
    status: str
    reason: str | None
    reconstruction: str | None
    datasets: tuple[DatasetCoverage, ...]
    component_count: int
    distinct_dates: int
    earliest: date | None
    latest: date | None
    sample_window: str
    monthly_state_transition: bool
    timeline: str
    clock: str

    def inputs_text(self) -> str:
        if not self.datasets:
            return "none"
        parts = []
        for item in self.datasets:
            span = "no rows"
            if item.earliest is not None and item.latest is not None:
                span = f"{item.earliest.isoformat()} to {item.latest.isoformat()}"
            parts.append(f"{item.dataset_id} ({item.stored_rows} rows, {span})")
        return "; ".join(parts)


def load_census(connection: psycopg.Connection) -> tuple[MethodCensus, ...]:
    """Build the census from stored runs and points. Point-in-time output stays zero."""
    required = {
        method.method_id: tuple(method.required_dataset_ids())
        for method in default_method_registry().registered()
    }
    dataset_ids = tuple(
        dict.fromkeys(dataset_id for ids in required.values() for dataset_id in ids)
    )
    with connection.cursor() as cursor:
        cursor.execute(
            """
            select dataset_id, count(*)::int, min(period_start), max(period_start)
            from research.economic_observations
            where dataset_id = any(%s)
            group by dataset_id
            """,
            (list(dataset_ids),),
        )
        coverage = {
            str(dataset_id): DatasetCoverage(str(dataset_id), int(count), earliest, latest)
            for dataset_id, count, earliest, latest in cursor.fetchall()
        }
        cursor.execute(
            """
            select method_id, method_class, method_version, status, reason, reconstruction,
                   point_count
            from research.discovery_v2_method_runs
            where specification_id = %s
            order by method_id
            """,
            (STORED_METHOD_SPECIFICATION,),
        )
        runs = cursor.fetchall()
        cursor.execute(
            """
            select method_id, series_key, period_end, direction, state_label
            from research.discovery_v2_method_points
            where specification_id = %s
            """,
            (STORED_METHOD_SPECIFICATION,),
        )
        grouped: dict[str, list[PointFact]] = defaultdict(list)
        for method_id, series_key, period_end, direction, state_label in cursor.fetchall():
            grouped[str(method_id)].append(
                PointFact(str(series_key), period_end, direction, state_label)
            )
        cursor.execute(
            """
            select count(*)::int
            from research.discovery_v2_method_points
            where specification_id = %s
              and reconstruction not in (
                'retrospective_reconstruction', 'retrospective_latest_revised'
              )
            """,
            (STORED_METHOD_SPECIFICATION,),
        )
        point_in_time = int(cursor.fetchone()[0])
    if point_in_time != 0:
        raise ValueError("point-in-time methodology output is not zero")
    if len(runs) != 26:
        raise ValueError(f"expected 26 stored methods, found {len(runs)}")
    rows = [
        _one(run, required.get(str(run[0]), ()), coverage, grouped[str(run[0])]) for run in runs
    ]
    return tuple(rows)


def _one(
    run: tuple[object, ...],
    required: tuple[str, ...],
    coverage: dict[str, DatasetCoverage],
    points: list[PointFact],
) -> MethodCensus:
    method_id = str(run[0])
    status = str(run[3])
    spec = SPECS[method_id]
    distinct = sorted({point.period_end for point in points})
    sample = "full_sample" if bool(spec["full_sample_look_ahead"]) else "rolling"
    timeline = _timeline(method_id, distinct)
    return MethodCensus(
        method_id=method_id,
        method_class=str(run[1]),
        method_version=str(run[2]),
        status=status,
        reason=None if run[4] is None else str(run[4]),
        reconstruction=None if run[5] is None else str(run[5]),
        datasets=tuple(
            coverage.get(dataset_id, DatasetCoverage(dataset_id, 0, None, None))
            for dataset_id in required
        ),
        component_count=len(points),
        distinct_dates=len(distinct),
        earliest=distinct[0] if distinct else None,
        latest=distinct[-1] if distinct else None,
        sample_window=sample,
        monthly_state_transition=_transition(method_id, points, timeline),
        timeline=timeline,
        clock="retrospective",
    )


def _timeline(method_id: str, distinct: list[date]) -> str:
    if not distinct:
        return "no_output"
    if method_id in NOT_A_MONTHLY_STATE or len(distinct) == 1:
        return "sample_end_diagnostic"
    return "continuous_timeline"


def _transition(method_id: str, points: list[PointFact], timeline: str) -> bool:
    """A stored direction or state label must change. A level change is not a state."""
    if timeline != "continuous_timeline" or method_id in NOT_A_MONTHLY_STATE:
        return False
    by_series: dict[str, dict[date, PointFact]] = defaultdict(dict)
    for point in points:
        by_series[point.series_key].setdefault(point.period_end, point)
    for series in by_series.values():
        ends = sorted(series)
        for left, right in zip(ends, ends[1:], strict=False):
            earlier = series[left]
            later = series[right]
            direction_changed = earlier.direction != later.direction and (
                earlier.direction is not None or later.direction is not None
            )
            label_changed = earlier.state_label != later.state_label and (
                earlier.state_label is not None or later.state_label is not None
            )
            if direction_changed or label_changed:
                return True
    return False


def render_coverage(rows: tuple[MethodCensus, ...]) -> str:
    """UK English coverage table. Component counts stay separate from dates."""
    header = (
        "| Method | Class | Version | Status | Inputs and coverage | Distinct dates "
        "| Components | Earliest | Latest | Window | Monthly state transition "
        "| Timeline | Clock |"
    )
    rule = "| --- | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | --- | --- | --- |"
    body = ["# Method coverage", "", _conclusion(rows), "", header, rule]
    for row in rows:
        earliest = row.earliest.isoformat() if row.earliest else ""
        latest = row.latest.isoformat() if row.latest else ""
        transition = "yes" if row.monthly_state_transition else "no"
        reason = f" {row.reason}" if row.reason else ""
        body.append(
            "| "
            + " | ".join(
                (
                    row.method_id,
                    row.method_class,
                    row.method_version,
                    row.status + ("" if not reason else ""),
                    row.inputs_text().replace("|", "/"),
                    str(row.distinct_dates),
                    str(row.component_count),
                    earliest,
                    latest,
                    row.sample_window,
                    transition,
                    row.timeline,
                    row.clock,
                )
            )
            + " |"
        )
    failures = [row for row in rows if row.status != "succeeded"]
    if failures:
        body.extend(["", "## Stored failures", ""])
        for row in failures:
            body.append(
                f"- `{row.method_id}` stays {row.status}. {row.reason or 'No reason stored.'}"
            )
    body.append("")
    return "\n".join(body)


def _conclusion(rows: tuple[MethodCensus, ...]) -> str:
    components = sum(row.component_count for row in rows)
    dates = sum(row.distinct_dates for row in rows)
    continuous = sum(1 for row in rows if row.timeline == "continuous_timeline")
    sample_end = sum(1 for row in rows if row.timeline == "sample_end_diagnostic")
    transitions = sum(1 for row in rows if row.monthly_state_transition)
    return (
        "This census reads the stored VWRA-DISCOVERY-001 points. It does not delete them "
        "and it does not score EIMI. "
        f"Components total {components}. The sum of distinct output dates is {dates}. "
        "Those two counts are not the same thing, and neither count is a set of "
        "independent months. "
        f"{continuous} methods have a continuous timeline and {sample_end} are "
        "sample-end diagnostics. "
        f"{transitions} continuous timelines have a stored direction or state-label change. "
        "A numeric level that changes without a stored label is not called a monthly state. "
        "Point-in-time methodology outputs are 0. Every row is retrospective, including "
        "a rolling equation, because the inputs are latest revised. "
        "Census methods stay unavailable. Inflation autoregression stays the stored failure."
    )
