"""CPI-U and H.15 policy rates — descriptive levels, changes, and ranks.

CPI-U is ranked on overlapping 12-month percent changes. The federal funds rate
and the 10-year Treasury yield are ranked on the level. The historical
distribution uses today's revised file.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from pydantic import BaseModel, ConfigDict, Field

from aqil_research.contracts.observation import (
    AnalysisMode,
    EconomicObservation,
    Frequency,
    QualityStatus,
    SeasonalAdjustment,
    SeriesProvenance,
)
from aqil_research.methods.protocol import MethodContext, MethodExecutionResult

PRICES_AND_POLICY_METHOD_ID = "PRICES_AND_POLICY"
PRICES_AND_POLICY_METHOD_VERSION = "1.1.0"

CPI_DATASET_ID = "bls.cu.CUSR0000SA0"
FED_FUNDS_DATASET_ID = "fed.h15.RIFSPFF_N.M"
TREASURY_10Y_DATASET_ID = "fed.h15.RIFLGFCY10_N.M"

CPI_UNIT = "1982-84=100"
RATE_UNIT = "percent_per_year"
CPI_FORMULA = "(index_t / index_t-12 - 1) * 100"
CHANGE_QUANTUM = Decimal("0.0001")
CAUSAL_HYPOTHESIS = "No causal mechanism is established."
REVISED_HISTORY_SENTENCE = (
    "The historical distribution uses today's revised file and is not what was known "
    "on each past date."
)
CPI_ENDPOINTS_SENTENCE = (
    "The CPI-U 12-month percent change uses the two endpoints only. "
    "A missing month between those endpoints is not treated as observed and is not interpolated."
)
CPI_RANK_DEFINITION = (
    f"Rank of overlapping 12-month percent changes in CPI-U ({CPI_DATASET_ID}): "
    "1 plus the count of those percent changes strictly below the latest "
    "12-month percent change. "
    f"{CPI_ENDPOINTS_SENTENCE} {REVISED_HISTORY_SENTENCE}"
)
FUNDS_RANK_DEFINITION = (
    f"Rank of the federal funds rate level ({FED_FUNDS_DATASET_ID}): "
    "1 plus the count of stored federal funds rate levels strictly below the latest level. "
    f"{REVISED_HISTORY_SENTENCE}"
)
TREASURY_RANK_DEFINITION = (
    f"Rank of the 10-year Treasury yield level ({TREASURY_10Y_DATASET_ID}): "
    "1 plus the count of stored 10-year Treasury yield levels strictly below the latest level. "
    f"{REVISED_HISTORY_SENTENCE}"
)

_POINT_IN_TIME_REASON = (
    "point_in_time is insufficient because these series are latest_revised "
    "files and not a vintage panel"
)
_STATISTICAL = (
    "Descriptive reading of the stored CPI-U index over twelve months and of the "
    "stored federal funds rate and 10-year yield over one month. "
    f"CPI-U ({CPI_DATASET_ID}) is ranked on overlapping 12-month percent changes. "
    f"The federal funds rate ({FED_FUNDS_DATASET_ID}) and the 10-year Treasury yield "
    f"({TREASURY_10Y_DATASET_ID}) are ranked on the level. "
    f"{REVISED_HISTORY_SENTENCE}"
)


class PricesAndPolicyConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    config_id: str = Field(min_length=1)
    label: str = Field(min_length=1)


@dataclass(frozen=True, slots=True)
class _SeriesReading:
    payload: dict[str, object]
    history: tuple[EconomicObservation, ...]
    period: date
    comparison_period: date
    level: str
    comparison_level: str
    change: str
    kind: str


class PricesAndPolicyMethod:
    method_id = PRICES_AND_POLICY_METHOD_ID
    method_version = PRICES_AND_POLICY_METHOD_VERSION

    def implementation_hash(self) -> str:
        payload = f"{self.method_id}:{self.method_version}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def required_dataset_ids(self) -> tuple[str, ...]:
        return (CPI_DATASET_ID, FED_FUNDS_DATASET_ID, TREASURY_10Y_DATASET_ID)

    def parse_config(self, payload: dict[str, object]) -> PricesAndPolicyConfig:
        return PricesAndPolicyConfig.model_validate(payload)

    def config_hash(self, config: BaseModel) -> str:
        if not isinstance(config, PricesAndPolicyConfig):
            raise TypeError("expected PricesAndPolicyConfig")
        from aqil_research.methods.parameters import MethodParameterDocument

        return MethodParameterDocument(
            config_id=config.config_id,
            label=config.label,
            scalars={},
        ).config_hash()

    def run(self, context: MethodContext, config: BaseModel) -> MethodExecutionResult:
        if not isinstance(config, PricesAndPolicyConfig):
            raise TypeError("expected PricesAndPolicyConfig")
        if context.analysis_mode != AnalysisMode.LATEST_REVISED:
            return _insufficient(
                _POINT_IN_TIME_REASON,
                "A point-in-time request has no eligible latest_revised rows from these files.",
            )

        evaluation = context.evaluation_period
        cpi = _eligible_series(context.inputs_by_dataset.get(CPI_DATASET_ID, {}))
        funds = _eligible_series(context.inputs_by_dataset.get(FED_FUNDS_DATASET_ID, {}))
        treasury = _eligible_series(context.inputs_by_dataset.get(TREASURY_10Y_DATASET_ID, {}))
        prior_month = _add_months(evaluation, -1)
        twelve_month_start = _add_months(evaluation, -12)

        readings: list[_SeriesReading] = []
        failures: list[str] = []
        for reading in (
            _cpi_window(cpi, start=twelve_month_start, end=evaluation),
            _rate_window(
                funds,
                prior=prior_month,
                end=evaluation,
                label="federal funds",
                ranked_series=f"federal funds rate ({FED_FUNDS_DATASET_ID})",
                rank_definition=FUNDS_RANK_DEFINITION,
            ),
            _rate_window(
                treasury,
                prior=prior_month,
                end=evaluation,
                label="10-year yield",
                ranked_series=f"10-year Treasury yield ({TREASURY_10Y_DATASET_ID})",
                rank_definition=TREASURY_RANK_DEFINITION,
            ),
        ):
            if isinstance(reading, str):
                failures.append(reading)
            else:
                readings.append(reading)
        if failures:
            return _insufficient("; ".join(failures))

        cpi_reading, funds_reading, treasury_reading = readings
        used = (
            *cpi_reading.history,
            *funds_reading.history,
            *treasury_reading.history,
        )
        calculation = {
            "evaluation_period": evaluation.isoformat(),
            "analysis_mode": AnalysisMode.LATEST_REVISED.value,
            "cpi_u": cpi_reading.payload,
            "federal_funds": funds_reading.payload,
            "treasury_10_year": treasury_reading.payload,
        }
        return MethodExecutionResult(
            sufficiency="sufficient",
            calculation=calculation,
            observation_ids=tuple(sorted({row.observation_id for row in used})),
            assumptions=_assumptions(config.label),
            limitations=_limitations(),
            missing_reason=None,
            statistical_interpretation=_STATISTICAL,
            causal_hypothesis=CAUSAL_HYPOTHESIS,
            investment_implication="no_action",
            narrative=_narrative(cpi_reading, funds_reading, treasury_reading),
        )


def _eligible_series(
    series: dict[date, EconomicObservation],
) -> dict[date, EconomicObservation]:
    selected: dict[date, EconomicObservation] = {}
    for period, row in series.items():
        if row.period_start != period:
            raise ValueError(f"observation {row.observation_id} is not keyed by period_start")
        if row.series_provenance != SeriesProvenance.LATEST_REVISED:
            continue
        if row.quality_status != QualityStatus.OBSERVED:
            continue
        _validate_contract(row)
        selected[period] = row
    return selected


def _validate_contract(row: EconomicObservation) -> None:
    if row.frequency != Frequency.MONTHLY:
        raise ValueError(f"{row.dataset_id} requires monthly frequency")
    if row.dataset_id == CPI_DATASET_ID:
        if row.unit != CPI_UNIT:
            raise ValueError("CPI-U requires unit 1982-84=100")
        if row.seasonal_adjustment != SeasonalAdjustment.SEASONALLY_ADJUSTED:
            raise ValueError("CPI-U requires seasonally adjusted observations")
        return
    if row.dataset_id in {FED_FUNDS_DATASET_ID, TREASURY_10Y_DATASET_ID}:
        if row.unit != RATE_UNIT:
            raise ValueError(f"{row.dataset_id} requires unit percent_per_year")
        if row.seasonal_adjustment != SeasonalAdjustment.UNKNOWN:
            raise ValueError(f"{row.dataset_id} requires seasonal adjustment unknown")
        return
    raise ValueError(f"unexpected dataset {row.dataset_id}")


def _cpi_window(
    series: dict[date, EconomicObservation],
    *,
    start: date,
    end: date,
) -> _SeriesReading | str:
    missing = _missing_endpoint_reason(
        series,
        start=start,
        end=end,
        label="CPI-U",
        span="12-month",
    )
    if missing is not None:
        return missing
    prior = series[start]
    current = series[end]
    prior_level = prior.decimal_value()
    if prior_level == 0:
        return (
            f"CPI-U comparison index at {start.isoformat()} is zero, "
            "so the 12-month percent change is undefined"
        )
    change = ((current.decimal_value() / prior_level) - Decimal(1)) * Decimal(100)
    history = _history_through(series, end)
    quantized_change = Decimal(_quantize(change))
    changes = _overlapping_cpi_percent_changes(series, end)
    below = sum(1 for item in changes if item < quantized_change)
    rank = below + 1
    return _SeriesReading(
        payload={
            "dataset_id": CPI_DATASET_ID,
            "unit": CPI_UNIT,
            "seasonal_adjustment": SeasonalAdjustment.SEASONALLY_ADJUSTED.value,
            "transformation": "twelve_month_percent_change",
            "formula": CPI_FORMULA,
            "period": end.isoformat(),
            "comparison_period": start.isoformat(),
            "index_level": current.raw_value,
            "comparison_index_level": prior.raw_value,
            "twelve_month_percent_change": _quantize(change),
            "endpoints_only": True,
            "values_strictly_below": below,
            "rank": rank,
            "change_count": len(changes),
            "rank_basis": "overlapping_twelve_month_percent_change",
            "ranked_series": f"CPI-U ({CPI_DATASET_ID})",
            "rank_definition": CPI_RANK_DEFINITION,
        },
        history=history,
        period=end,
        comparison_period=start,
        level=current.raw_value,
        comparison_level=prior.raw_value,
        change=_quantize(change),
        kind="cpi",
    )


def _rate_window(
    series: dict[date, EconomicObservation],
    *,
    prior: date,
    end: date,
    label: str,
    ranked_series: str,
    rank_definition: str,
) -> _SeriesReading | str:
    missing = _missing_endpoint_reason(
        series,
        start=prior,
        end=end,
        label=label,
        span="one-month",
    )
    if missing is not None:
        return missing
    previous = series[prior]
    current = series[end]
    change = current.decimal_value() - previous.decimal_value()
    history = _history_through(series, end)
    below, rank = _rank(current.decimal_value(), history)
    return _SeriesReading(
        payload={
            "dataset_id": current.dataset_id,
            "unit": RATE_UNIT,
            "seasonal_adjustment": SeasonalAdjustment.UNKNOWN.value,
            "transformation": "level_and_one_month_change",
            "period": end.isoformat(),
            "prior_period": prior.isoformat(),
            "level_percent_per_year": current.raw_value,
            "prior_level_percent_per_year": previous.raw_value,
            "one_month_change_percentage_points": _quantize(change),
            "values_strictly_below": below,
            "rank": rank,
            "level_count": len(history),
            "rank_basis": "level",
            "ranked_series": ranked_series,
            "rank_definition": rank_definition,
        },
        history=history,
        period=end,
        comparison_period=prior,
        level=current.raw_value,
        comparison_level=previous.raw_value,
        change=_quantize(change),
        kind="rate",
    )


def _missing_endpoint_reason(
    series: dict[date, EconomicObservation],
    *,
    start: date,
    end: date,
    label: str,
    span: str,
) -> str | None:
    missing = [period.isoformat() for period in (start, end) if period not in series]
    if not missing:
        return None
    joined = " and ".join(missing)
    return (
        f"missing {label} endpoint {joined} for the {span} window "
        f"{start.isoformat()} to {end.isoformat()}"
    )


def _overlapping_cpi_percent_changes(
    series: dict[date, EconomicObservation],
    end: date,
) -> list[Decimal]:
    changes: list[Decimal] = []
    for period in sorted(series):
        if period > end:
            continue
        start = _add_months(period, -12)
        if start not in series:
            continue
        start_level = series[start].decimal_value()
        if start_level == 0:
            continue
        raw = ((series[period].decimal_value() / start_level) - Decimal(1)) * Decimal(100)
        changes.append(raw.quantize(CHANGE_QUANTUM, rounding=ROUND_HALF_UP))
    return changes


def _history_through(
    series: dict[date, EconomicObservation],
    end: date,
) -> tuple[EconomicObservation, ...]:
    return tuple(row for period, row in sorted(series.items()) if period <= end)


def _rank(level: Decimal, history: tuple[EconomicObservation, ...]) -> tuple[int, int]:
    below = sum(1 for row in history if row.decimal_value() < level)
    return below, below + 1


def _quantize(value: Decimal) -> str:
    return str(value.quantize(CHANGE_QUANTUM, rounding=ROUND_HALF_UP))


def _add_months(anchor: date, delta: int) -> date:
    year = anchor.year + (anchor.month - 1 + delta) // 12
    month = (anchor.month - 1 + delta) % 12 + 1
    return date(year, month, 1)


def _assumptions(label: str) -> tuple[str, ...]:
    return (
        "Inputs are stored latest-revised monthly observations.",
        "Each window is computed only when both stored endpoints exist.",
        CPI_ENDPOINTS_SENTENCE,
        CPI_RANK_DEFINITION,
        FUNDS_RANK_DEFINITION,
        TREASURY_RANK_DEFINITION,
        label,
    )


def _limitations() -> tuple[str, ...]:
    return (
        "The reading is internal.",
        (
            "HICP (ecb.icp.M.U2.Y.000000.3.INX) is a separate series ending "
            "2025-12-01 (index, 2015 = 100)."
        ),
        (
            "CPI-U is the seasonally adjusted index 1982-84=100. "
            f"The 12-month percent change is {CPI_FORMULA} when both months are stored."
        ),
        (
            "Federal funds and the 10-year yield are levels in percent per year. "
            "Seasonal adjustment is unknown. One-month changes are in percentage points."
        ),
        CPI_ENDPOINTS_SENTENCE,
        CPI_RANK_DEFINITION,
        FUNDS_RANK_DEFINITION,
        TREASURY_RANK_DEFINITION,
    )


def _narrative(
    cpi: _SeriesReading,
    funds: _SeriesReading,
    treasury: _SeriesReading,
) -> str:
    return (
        f"CPI-U ({CPI_DATASET_ID}) 12-month percent change from "
        f"{cpi.comparison_period.isoformat()} to {cpi.period.isoformat()} is {cpi.change} percent "
        f"(index {cpi.comparison_level} to {cpi.level}, {CPI_UNIT}, seasonally adjusted). "
        f"{CPI_ENDPOINTS_SENTENCE} "
        f"The rank of overlapping 12-month percent changes in CPI-U ({CPI_DATASET_ID}) "
        f"is {cpi.payload['rank']} of {cpi.payload['change_count']}. "
        f"The rank of the federal funds rate level ({FED_FUNDS_DATASET_ID}) "
        f"is {funds.payload['rank']} of {funds.payload['level_count']} stored levels. "
        f"Federal funds were {funds.level} percent per year on {funds.period.isoformat()}, "
        f"a one-month change of {funds.change} percentage points. "
        f"The rank of the 10-year Treasury yield level ({TREASURY_10Y_DATASET_ID}) "
        f"is {treasury.payload['rank']} of {treasury.payload['level_count']} stored levels. "
        f"The 10-year yield was {treasury.level} percent per year on "
        f"{treasury.period.isoformat()}, a one-month change of {treasury.change} "
        "percentage points. "
        f"{REVISED_HISTORY_SENTENCE} "
        "The reading is internal."
    )


def _insufficient(
    reason: str,
    interpretation: str = "The requested window does not have both stored endpoints.",
) -> MethodExecutionResult:
    return MethodExecutionResult(
        sufficiency="insufficient",
        calculation=None,
        observation_ids=(),
        assumptions=(),
        limitations=_limitations(),
        missing_reason=reason,
        statistical_interpretation=interpretation,
        causal_hypothesis=CAUSAL_HYPOTHESIS,
        investment_implication="insufficient_evidence",
        narrative=reason,
    )
