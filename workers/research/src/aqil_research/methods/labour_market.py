"""Labour-market conditions: levels, 12-month endpoint changes, and ranks.

Each series is reported on its own latest stored month. The joint reading uses
only months present in all three. A 12-month change uses those two endpoints
and does not require the months between them. A missing endpoint fails that
change. Nothing is interpolated and nothing is stored as zero.

Unemployment and job openings are ranked on the level. Payrolls are ranked on
overlapping 12-month percent changes. The historical distribution uses today's
revised file.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from aqil_research.contracts.observation import (
    AnalysisMode,
    EconomicObservation,
    Frequency,
    QualityStatus,
    SeasonalAdjustment,
)
from aqil_research.methods.protocol import MethodContext, MethodExecutionResult

LABOUR_MARKET_METHOD_ID = "LABOUR_MARKET_CONDITIONS"
LABOUR_MARKET_METHOD_VERSION = "1.1.0"
UNEMPLOYMENT_DATASET_ID = "bls.ln.LNS14000000"
PAYROLLS_DATASET_ID = "bls.ce.CES0000000001"
OPENINGS_DATASET_ID = "bls.jt.JTS000000000000000JOL"

_CAUSAL_HYPOTHESIS = "No causal mechanism is established."
_POINTS_TRANSFORMATION = "12-month difference in percentage points"
_LEVEL_PERCENT_TRANSFORMATION = "12-month difference in thousands and percent change"
_POINT_IN_TIME_REASON = (
    "A point-in-time context is insufficient because these series are not a vintage panel."
)
_REVISED_HISTORY_SENTENCE = (
    "The historical distribution uses today's revised file and is not what was known "
    "on each past date."
)
_ENDPOINTS_ONLY_SENTENCE = (
    "A 12-month change uses the two endpoints only and does not require the months "
    "between them. A missing month between those endpoints is not treated as observed "
    "and is not interpolated."
)

_MISSING_ENDPOINT_INTERPRETATION = (
    "A 12-month change needs both endpoint months. The missing month was not interpolated."
)


@dataclass(frozen=True, slots=True)
class _SeriesSpec:
    dataset_id: str
    unit: str
    change_kind: Literal["percentage_points", "level_and_percent"]
    rank_kind: Literal["level", "overlapping_twelve_month_percent_change"]
    series_name: str


_SERIES_SPECS: tuple[_SeriesSpec, ...] = (
    _SeriesSpec(
        UNEMPLOYMENT_DATASET_ID,
        "percent",
        "percentage_points",
        "level",
        "unemployment rate",
    ),
    _SeriesSpec(
        PAYROLLS_DATASET_ID,
        "thousands",
        "level_and_percent",
        "overlapping_twelve_month_percent_change",
        "payrolls",
    ),
    _SeriesSpec(
        OPENINGS_DATASET_ID,
        "thousands",
        "level_and_percent",
        "level",
        "job openings",
    ),
)


class LabourMarketConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    config_id: str = Field(min_length=1)
    label: str = Field(min_length=1)


class LabourMarketConditionsMethod:
    method_id = LABOUR_MARKET_METHOD_ID
    method_version = LABOUR_MARKET_METHOD_VERSION

    def implementation_hash(self) -> str:
        payload = f"{self.method_id}:{self.method_version}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def required_dataset_ids(self) -> tuple[str, ...]:
        return tuple(spec.dataset_id for spec in _SERIES_SPECS)

    def parse_config(self, payload: dict[str, object]) -> LabourMarketConfig:
        return LabourMarketConfig.model_validate(payload)

    def config_hash(self, config: BaseModel) -> str:
        if not isinstance(config, LabourMarketConfig):
            raise TypeError("expected LabourMarketConfig")
        from aqil_research.methods.parameters import MethodParameterDocument

        return MethodParameterDocument(
            config_id=config.config_id,
            label=config.label,
            scalars={},
        ).config_hash()

    def run(self, context: MethodContext, config: BaseModel) -> MethodExecutionResult:
        if not isinstance(config, LabourMarketConfig):
            raise TypeError("expected LabourMarketConfig")
        if context.analysis_mode != AnalysisMode.LATEST_REVISED:
            return _insufficient(
                _POINT_IN_TIME_REASON,
                _POINT_IN_TIME_REASON,
            )

        series_by_id: dict[str, dict[date, EconomicObservation]] = {}
        for spec in _SERIES_SPECS:
            rows = context.inputs_by_dataset.get(spec.dataset_id) or {}
            if not rows:
                return _insufficient(
                    f"missing stored observations for {spec.dataset_id}",
                    "A labour-market series has no stored observations.",
                )
            problem = _validate_series(spec, rows)
            if problem is not None:
                return _insufficient(
                    problem,
                    "A stored labour-market observation failed validation.",
                )
            series_by_id[spec.dataset_id] = rows

        series_calculations: list[dict[str, object]] = []
        for spec in _SERIES_SPECS:
            calculation, failure = _series_calculation(spec, series_by_id[spec.dataset_id])
            if failure is not None:
                return _insufficient(
                    failure,
                    _MISSING_ENDPOINT_INTERPRETATION,
                )
            series_calculations.append(calculation)

        joint, joint_failure = _joint_calculation(series_by_id)
        if joint_failure is not None:
            return _insufficient(
                joint_failure,
                _MISSING_ENDPOINT_INTERPRETATION,
            )

        observation_ids = tuple(
            sorted(obs.observation_id for rows in series_by_id.values() for obs in rows.values()),
        )
        calculation: dict[str, object] = {
            "method_id": self.method_id,
            "method_version": self.method_version,
            "analysis_mode": AnalysisMode.LATEST_REVISED.value,
            "observation_ids": list(observation_ids),
            "series": series_calculations,
            "joint": joint,
        }
        return MethodExecutionResult(
            sufficiency="sufficient",
            calculation=calculation,
            observation_ids=observation_ids,
            assumptions=_assumptions(config.label),
            limitations=_limitations(),
            missing_reason=None,
            statistical_interpretation=(
                "Descriptive latest levels and 12-month endpoint changes for the "
                "unemployment rate, payrolls, and job openings. "
                "The unemployment rate and job openings are ranked on the level. "
                "Payrolls are ranked on overlapping 12-month percent changes. "
                f"{_REVISED_HISTORY_SENTENCE}"
            ),
            causal_hypothesis=_CAUSAL_HYPOTHESIS,
            investment_implication="no_action",
            narrative=_narrative(series_calculations, joint),
        )


def _series_calculation(
    spec: _SeriesSpec,
    series: dict[date, EconomicObservation],
) -> tuple[dict[str, object], str | None]:
    latest_period = max(series)
    prior_period = _add_months(latest_period, -12)
    latest = series[latest_period]
    if prior_period not in series:
        return {}, _missing_endpoint(spec.dataset_id, prior_period, latest_period)
    change = _change_payload(spec, series[prior_period], latest)
    if isinstance(change, str):
        return {}, change
    latest_value = latest.decimal_value()
    rank, history_count, failure = _series_rank(spec, series, latest_period)
    if failure is not None:
        return {}, failure
    return {
        "dataset_id": spec.dataset_id,
        "latest_period": latest_period.isoformat(),
        "level": _decimal_text(latest_value),
        "unit": spec.unit,
        "level_transformation": "latest stored level",
        "seasonal_adjustment": SeasonalAdjustment.SEASONALLY_ADJUSTED.value,
        "observation_id": latest.observation_id,
        "rank": rank,
        "history_count": history_count,
        "rank_basis": spec.rank_kind,
        "ranked_series": f"{spec.series_name} ({spec.dataset_id})",
        "rank_transformation": _rank_transformation(spec),
        "twelve_month_change": change,
    }, None


def _joint_calculation(
    series_by_id: dict[str, dict[date, EconomicObservation]],
) -> tuple[dict[str, object], str | None]:
    common = set.intersection(*(set(rows) for rows in series_by_id.values()))
    if not common:
        return {}, "no month is present in all three series for the joint reading"
    latest_common = max(common)
    prior = _add_months(latest_common, -12)
    if prior not in common:
        absent = [
            spec.dataset_id for spec in _SERIES_SPECS if prior not in series_by_id[spec.dataset_id]
        ]
        listed = ", ".join(absent) if absent else "one or more series"
        return {}, (
            f"missing endpoint {prior.isoformat()} for joint 12-month change "
            f"from {prior.isoformat()} to {latest_common.isoformat()}; absent from {listed}"
        )
    levels: list[dict[str, object]] = []
    changes: list[dict[str, object]] = []
    for spec in _SERIES_SPECS:
        rows = series_by_id[spec.dataset_id]
        end = rows[latest_common]
        levels.append(
            {
                "dataset_id": spec.dataset_id,
                "period": latest_common.isoformat(),
                "level": _decimal_text(end.decimal_value()),
                "unit": spec.unit,
                "seasonal_adjustment": SeasonalAdjustment.SEASONALLY_ADJUSTED.value,
                "observation_id": end.observation_id,
            },
        )
        change = _change_payload(spec, rows[prior], end)
        if isinstance(change, str):
            return {}, change
        changes.append(change)
    return {
        "latest_common_period": latest_common.isoformat(),
        "months_rule": "only months present in all three series",
        "levels": levels,
        "twelve_month_change": {
            "window_start": prior.isoformat(),
            "window_end": latest_common.isoformat(),
            "endpoints_only": True,
            "series": changes,
        },
    }, None


def _change_payload(
    spec: _SeriesSpec,
    start: EconomicObservation,
    end: EconomicObservation,
) -> dict[str, object] | str:
    start_value = start.decimal_value()
    end_value = end.decimal_value()
    payload: dict[str, object] = {
        "dataset_id": spec.dataset_id,
        "window_start": start.period_start.isoformat(),
        "window_end": end.period_start.isoformat(),
        "start_level": _decimal_text(start_value),
        "end_level": _decimal_text(end_value),
        "start_unit": spec.unit,
        "end_unit": spec.unit,
        "start_observation_id": start.observation_id,
        "end_observation_id": end.observation_id,
        "endpoints_only": True,
    }
    if spec.change_kind == "percentage_points":
        change = (end_value - start_value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        payload["transformation"] = _POINTS_TRANSFORMATION
        payload["change_percentage_points"] = str(change)
        payload["change_unit"] = "percentage_points"
        return payload
    if start_value == 0:
        return (
            f"percent change is undefined for {spec.dataset_id} "
            f"because the {start.period_start.isoformat()} level is zero"
        )
    difference = end_value - start_value
    percent = _quantized_percent_change(start_value, end_value)
    payload["transformation"] = _LEVEL_PERCENT_TRANSFORMATION
    payload["change_thousands"] = _decimal_text(difference)
    payload["change_unit"] = "thousands"
    payload["percent_change"] = str(percent)
    payload["percent_change_unit"] = "percent"
    return payload


def _validate_series(
    spec: _SeriesSpec,
    rows: dict[date, EconomicObservation],
) -> str | None:
    for period, obs in rows.items():
        label = f"{spec.dataset_id} {period.isoformat()}"
        if obs.dataset_id != spec.dataset_id:
            return f"{label} is stored under the wrong dataset"
        if obs.frequency != Frequency.MONTHLY or period.day != 1:
            return f"{label} is not a monthly observation"
        if obs.unit != spec.unit:
            return f"{label} unit is {obs.unit}, expected {spec.unit}"
        if obs.seasonal_adjustment != SeasonalAdjustment.SEASONALLY_ADJUSTED:
            return f"{label} is not seasonally adjusted"
        if obs.quality_status != QualityStatus.OBSERVED:
            return f"{label} is not an observed value"
    return None


def _series_rank(
    spec: _SeriesSpec,
    series: dict[date, EconomicObservation],
    latest_period: date,
) -> tuple[int, int, str | None]:
    if spec.rank_kind == "level":
        latest_value = series[latest_period].decimal_value()
        stored_values = [row.decimal_value() for row in series.values()]
        rank = 1 + sum(1 for value in stored_values if value < latest_value)
        return rank, len(stored_values), None
    changes: list[Decimal] = []
    latest_change: Decimal | None = None
    for period in sorted(series):
        prior = _add_months(period, -12)
        if prior not in series:
            continue
        start_value = series[prior].decimal_value()
        if start_value == 0:
            if period == latest_period:
                return (
                    0,
                    0,
                    (
                        f"percent change is undefined for {spec.dataset_id} "
                        f"because the {prior.isoformat()} level is zero"
                    ),
                )
            continue
        change = _quantized_percent_change(start_value, series[period].decimal_value())
        changes.append(change)
        if period == latest_period:
            latest_change = change
    if latest_change is None:
        return (
            0,
            0,
            _missing_endpoint(
                spec.dataset_id,
                _add_months(latest_period, -12),
                latest_period,
            ),
        )
    rank = 1 + sum(1 for change in changes if change < latest_change)
    return rank, len(changes), None


def _quantized_percent_change(start_value: Decimal, end_value: Decimal) -> Decimal:
    return ((end_value - start_value) / start_value * Decimal("100")).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )


def _rank_transformation(spec: _SeriesSpec) -> str:
    if spec.rank_kind == "level":
        definition = (
            f"Rank of the {spec.series_name} level ({spec.dataset_id}): "
            f"1 plus the count of stored {spec.series_name} levels strictly below "
            "the latest level."
        )
    else:
        definition = (
            f"Rank of overlapping 12-month percent changes in {spec.series_name} "
            f"({spec.dataset_id}): "
            "1 plus the count of those percent changes strictly below the latest "
            "12-month percent change."
        )
    return f"{definition} {_REVISED_HISTORY_SENTENCE}"


def _missing_endpoint(dataset_id: str, start: date, end: date) -> str:
    return (
        f"missing endpoint {start.isoformat()} for {dataset_id} "
        f"12-month change from {start.isoformat()} to {end.isoformat()}"
    )


def _add_months(anchor: date, delta: int) -> date:
    year = anchor.year + (anchor.month - 1 + delta) // 12
    month = (anchor.month - 1 + delta) % 12 + 1
    return date(year, month, 1)


def _decimal_text(value: Decimal) -> str:
    return format(value, "f")


def _assumptions(label: str) -> tuple[str, ...]:
    return (
        "Each series is reported on its own latest stored month.",
        "The joint reading uses only months present in all three series.",
        "Unemployment 12-month change is the difference in percentage points.",
        (
            "Payrolls and job openings 12-month change is the difference "
            "in thousands and the percent change."
        ),
        _ENDPOINTS_ONLY_SENTENCE,
        *(_rank_transformation(spec) for spec in _SERIES_SPECS),
        "Inputs are seasonally adjusted.",
        "Analysis mode is latest_revised.",
        label,
    )


def _limitations() -> tuple[str, ...]:
    return (
        "The reading is internal.",
        (
            "Latest-revised series are not a vintage panel, "
            "so a point-in-time context is insufficient."
        ),
        "A missing 12-month endpoint is not interpolated and is not stored as zero.",
        _ENDPOINTS_ONLY_SENTENCE,
        _REVISED_HISTORY_SENTENCE,
        "No composite score is calculated.",
        _CAUSAL_HYPOTHESIS,
    )


def _insufficient(reason: str, interpretation: str) -> MethodExecutionResult:
    return MethodExecutionResult(
        sufficiency="insufficient",
        calculation=None,
        observation_ids=(),
        assumptions=(),
        limitations=_limitations(),
        missing_reason=reason,
        statistical_interpretation=interpretation,
        causal_hypothesis=_CAUSAL_HYPOTHESIS,
        investment_implication="insufficient_evidence",
        narrative=reason,
    )


def _narrative(series_rows: list[dict[str, object]], joint: dict[str, object]) -> str:
    sentences: list[str] = []
    for row in series_rows:
        change = row["twelve_month_change"]
        if not isinstance(change, dict):
            continue
        if "change_percentage_points" in change:
            change_text = f"{change['change_percentage_points']} percentage points"
        else:
            change_text = (
                f"{change['change_thousands']} thousands ({change['percent_change']} percent)"
            )
        if row["rank_basis"] == "overlapping_twelve_month_percent_change":
            rank_text = (
                f"The rank of overlapping 12-month percent changes in {row['ranked_series']} "
                f"is {row['rank']} of {row['history_count']}."
            )
        else:
            rank_text = (
                f"The rank of the {row['ranked_series']} level is {row['rank']} "
                f"of {row['history_count']} stored levels."
            )
        sentences.append(
            f"{row['dataset_id']} was {row['level']} {row['unit']} in {row['latest_period']} "
            f"(observation {row['observation_id']}), a 12-month change of {change_text}. "
            f"{rank_text}"
        )
    sentences.append(
        "The joint reading uses "
        f"{joint['latest_common_period']}, the latest month present in all three series."
    )
    sentences.append(_ENDPOINTS_ONLY_SENTENCE)
    sentences.append(_REVISED_HISTORY_SENTENCE)
    sentences.append(_CAUSAL_HYPOTHESIS)
    return " ".join(sentences)
