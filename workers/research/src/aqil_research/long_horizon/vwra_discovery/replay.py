"""Replay the registered methods on stored latest-revised inputs."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal

import psycopg
from psycopg.rows import dict_row

from aqil_research.contracts.observation import AnalysisMode, EconomicObservation
from aqil_research.discovery.classification import SPECS
from aqil_research.long_horizon.money import decimal_text
from aqil_research.long_horizon.vwra_discovery.extract import RawPoint, extract_points
from aqil_research.long_horizon.vwra_discovery.guards import missing_datasets, unavailable_reason
from aqil_research.long_horizon.vwra_discovery.specification import (
    CONFIRMATION_DELAY_METHODS,
    ROLE_CLASS,
)
from aqil_research.methods.protocol import MethodContext
from aqil_research.methods.registry import default_method_registry
from aqil_research.vintages.asof import select_as_of_series
from aqil_research.workflow.parameter_versions import (
    ParameterPromotionRefused,
    load_accepted_factor_parameters,
)

READ_CLOCK = datetime(2026, 11, 4, tzinfo=UTC)
LOOP_METHODS = frozenset(
    {
        "SAHM_UNEMPLOYMENT_GAP",
        "PERIOD_LEVEL_CHANGE",
        "SLOOS_CIL_LENDING_STANDARDS",
        "LABOUR_MARKET_CONDITIONS",
        "PRICES_AND_POLICY",
        "INDUSTRIAL_PRODUCTION_ACTIVITY",
        "CREDIT_STANDARDS_AND_VOLUMES",
        "ESTRELLA_MISHKIN_TERM_SPREAD",
        "EX_POST_REAL_FUNDS_RATE",
    }
)
CPI_DATASET = "bls.cu.CUSR0000SA0"


@dataclass(frozen=True)
class StoredPoint:
    series_key: str
    period_start: date
    period_end: date
    value_text: str | None
    direction: str | None
    change_text: str | None
    state_label: str | None
    unit: str


@dataclass
class MethodRun:
    method_id: str
    method_version: str
    implementation_hash: str
    config_hash: str
    parameter_policy: str
    method_class: str
    reconstruction: str | None
    status: str
    reason: str | None
    points: list[StoredPoint]
    required_datasets: tuple[str, ...]

    @property
    def numeric_count(self) -> int:
        return sum(1 for point in self.points if point.value_text is not None)


def load_panel(
    connection: psycopg.Connection,
    dataset_ids: tuple[str, ...],
) -> tuple[dict[str, dict[date, EconomicObservation]], dict[str, int]]:
    """Latest-revised rows, plus a count of every stored row for each dataset."""
    with connection.cursor() as cursor:
        cursor.execute(
            """
            select dataset_id, count(*)::int
            from research.economic_observations
            where dataset_id = any(%s)
            group by dataset_id
            """,
            (list(dataset_ids),),
        )
        counts = {str(dataset_id): int(count) for dataset_id, count in cursor.fetchall()}
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            select o.observation_id, o.dataset_id, o.provider_id, o.source_id, o.rights_record_id,
                   o.period_start, o.period_end, o.frequency, o.geography, o.unit,
                   o.seasonal_adjustment, o.raw_value, o.quality_status, o.series_provenance,
                   o.provider_vintage_date, o.source_release_at, o.earliest_model_available_at,
                   o.availability_precision, o.retrieved_at, o.first_seen_at, o.source_locator,
                   o.adapter_version, o.supersedes_observation_id
            from research.economic_observations o
            join research.source_retrievals r on r.retrieval_id = o.retrieval_id
            where r.collection_mode = 'live'
              and o.series_provenance = 'latest_revised'
              and o.dataset_id = any(%s)
            """,
            (list(dataset_ids),),
        )
        fetched = cursor.fetchall()
    grouped: dict[str, list[EconomicObservation]] = defaultdict(list)
    for row in fetched:
        grouped[str(row["dataset_id"])].append(EconomicObservation.model_validate(row))
    series: dict[str, dict[date, EconomicObservation]] = {}
    for dataset_id in dataset_ids:
        series[dataset_id] = select_as_of_series(
            tuple(grouped.get(dataset_id, ())),
            dataset_id,
            READ_CLOCK,
            AnalysisMode.LATEST_REVISED,
        )
    return series, counts


def replay_methods(
    connection: psycopg.Connection,
    series: dict[str, dict[date, EconomicObservation]],
    counts: dict[str, int],
) -> list[MethodRun]:
    try:
        parameters: dict[str, object] | None | str = load_accepted_factor_parameters(connection)
    except ParameterPromotionRefused as exc:
        parameters = str(exc)
    runs: list[MethodRun] = []
    for method in default_method_registry().registered():
        print(f"replay {method.method_id}", flush=True)
        runs.append(_one(method, series, counts, parameters))
    return runs


def _one(method: object, series: dict, counts: dict[str, int], parameters: object) -> MethodRun:
    method_id = str(method.method_id)
    required = tuple(method.required_dataset_ids())
    dependency = method.dependency()
    spec = SPECS[method_id]
    payload = dict(method.accepted_config_payload())
    missing = missing_datasets(required, counts)
    reconstruction = _reconstruction(method_id, bool(spec["full_sample_look_ahead"]))
    if missing:
        config = method.parse_config(payload)
        return _empty(
            method,
            required,
            dependency.parameter_policy,
            method.config_hash(config),
            "unavailable",
            "unavailable",
            unavailable_reason(missing),
            None,
        )
    if dependency.parameter_policy == "refit_separate":
        if not isinstance(parameters, dict):
            config = method.parse_config(payload)
            reason = (
                "The accepted parameter version is not available. "
                "This replay does not refit and does not replace the parameter version."
            )
            if isinstance(parameters, str):
                reason = parameters
            return _empty(
                method,
                required,
                dependency.parameter_policy,
                method.config_hash(config),
                ROLE_CLASS[str(spec["role"])],
                "failed",
                reason,
                reconstruction,
            )
        payload["execution_mode"] = "calculate"
        payload["accepted_parameters"] = parameters
    config = method.parse_config(payload)
    config_hash = method.config_hash(config)
    method_class = ROLE_CLASS[str(spec["role"])]
    try:
        raw, failure = _calculate(method, method_id, required, series, config)
    except Exception as exc:
        return _empty(
            method,
            required,
            dependency.parameter_policy,
            config_hash,
            method_class,
            "failed",
            str(exc),
            reconstruction,
        )
    if failure is not None:
        return _empty(
            method,
            required,
            dependency.parameter_policy,
            config_hash,
            method_class,
            "failed",
            failure,
            reconstruction,
        )
    points, duplicate = _with_changes(raw)
    if duplicate is not None:
        return _empty(
            method,
            required,
            dependency.parameter_policy,
            config_hash,
            method_class,
            "failed",
            duplicate,
            reconstruction,
        )
    if not any(point.value_text is not None for point in points):
        return _empty(
            method,
            required,
            dependency.parameter_policy,
            config_hash,
            method_class,
            "failed",
            "the calculation did not contain a continuous number",
            reconstruction,
        )
    return MethodRun(
        method_id,
        str(method.method_version),
        str(method.implementation_hash()),
        config_hash,
        dependency.parameter_policy,
        method_class,
        reconstruction,
        "succeeded",
        None,
        points,
        required,
    )


def _reconstruction(method_id: str, full_sample: bool) -> str:
    if full_sample or method_id in CONFIRMATION_DELAY_METHODS:
        return "retrospective_reconstruction"
    return "retrospective_latest_revised"


def _empty(
    method: object,
    required: tuple[str, ...],
    parameter_policy: str,
    config_hash: str,
    method_class: str,
    status: str,
    reason: str,
    reconstruction: str | None,
) -> MethodRun:
    return MethodRun(
        str(method.method_id),
        str(method.method_version),
        str(method.implementation_hash()),
        config_hash,
        parameter_policy,
        method_class,
        reconstruction,
        status,
        reason,
        [],
        required,
    )


def _calculate(
    method: object,
    method_id: str,
    required: tuple[str, ...],
    series: dict,
    config: object,
):
    owned = {dataset_id: series.get(dataset_id, {}) for dataset_id in required}
    if method_id not in LOOP_METHODS:
        evaluation = max(owned[required[0]])
        result = _invoke(method, owned, evaluation, required[0], config)
        if result.sufficiency != "sufficient":
            return [], result.missing_reason or "insufficient"
        return extract_points(method_id, result.calculation, evaluation)
    dates = _dates(method_id, owned, required)
    collected: list[RawPoint] = []
    last_reason = "no evaluation date produced a number"
    for index, evaluation in enumerate(dates):
        if index % 120 == 0:
            print(f"  {method_id} {evaluation.isoformat()}", flush=True)
        truncated = {
            dataset_id: {period: row for period, row in rows.items() if period <= evaluation}
            for dataset_id, rows in owned.items()
        }
        try:
            result = _invoke(method, truncated, evaluation, required[0], config)
        except Exception as exc:
            last_reason = str(exc)
            continue
        if result.sufficiency != "sufficient" or result.calculation is None:
            last_reason = result.missing_reason or "insufficient"
            continue
        points, failure = extract_points(method_id, result.calculation, evaluation)
        if failure is not None:
            last_reason = failure
            continue
        collected.extend(_keep(method_id, points, evaluation))
    if not collected:
        return [], last_reason
    return collected, None


def _dates(method_id: str, owned: dict, required: tuple[str, ...]) -> list[date]:
    if method_id == "EX_POST_REAL_FUNDS_RATE":
        return sorted(owned.get(CPI_DATASET, {}))
    return sorted(owned[required[0]])


def _keep(method_id: str, points: list[RawPoint], evaluation: date) -> list[RawPoint]:
    if method_id == "CREDIT_STANDARDS_AND_VOLUMES":
        return [point for point in points if point.period_start <= evaluation]
    return [point for point in points if point.period_start == evaluation]


def _invoke(method: object, series: dict, evaluation: date, primary: str, config: object):
    context = MethodContext(
        inputs_by_dataset=series,
        evaluation_period=evaluation,
        analysis_mode=AnalysisMode.LATEST_REVISED,
        primary_dataset_id=primary,
    )
    return method.run(context, config)


def _with_changes(points: list[RawPoint]) -> tuple[list[StoredPoint], str | None]:
    grouped: dict[str, list[RawPoint]] = defaultdict(list)
    for point in points:
        grouped[point.series_key].append(point)
    stored: list[StoredPoint] = []
    for series_key in sorted(grouped):
        rows = sorted(grouped[series_key], key=lambda item: (item.period_start, item.period_end))
        seen: dict[date, str | None] = {}
        previous: str | None = None
        for point in rows:
            if point.period_start in seen and seen[point.period_start] != point.value_text:
                return [], f"duplicate period {point.period_start.isoformat()} for {series_key}"
            if point.period_start in seen:
                continue
            seen[point.period_start] = point.value_text
            change = None
            direction = None
            if previous is not None and point.value_text is not None:
                difference = Decimal(point.value_text) - Decimal(previous)
                change = decimal_text(difference)
                if difference > 0:
                    direction = "up"
                elif difference < 0:
                    direction = "down"
                else:
                    direction = "flat"
            stored.append(
                StoredPoint(
                    series_key,
                    point.period_start,
                    point.period_end,
                    point.value_text,
                    direction,
                    change,
                    point.state_label,
                    point.unit,
                )
            )
            if point.value_text is not None:
                previous = point.value_text
    return stored, None
