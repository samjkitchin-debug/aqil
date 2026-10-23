"""Industrial production activity — level, 12-month percent change, and historical rank.

The rank is the rank of overlapping 12-month percent changes in today's revised
file, not the rank of the level. Input is the seasonally adjusted G.17 total
index only. This is production, not GDP.
"""

from __future__ import annotations

import hashlib
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

INDUSTRIAL_PRODUCTION_METHOD_ID = "INDUSTRIAL_PRODUCTION_ACTIVITY"
INDUSTRIAL_PRODUCTION_METHOD_VERSION = "1.1.0"
INDUSTRIAL_PRODUCTION_DATASET_ID = "fed.g17.IP.B50001.S"
INDUSTRIAL_PRODUCTION_UNIT = "index_2017_100"
MONTHS_BACK = 12
PERCENT_QUANTUM = Decimal("0.0001")
CAUSAL_HYPOTHESIS = "No causal mechanism is established."
REVISED_HISTORY_SENTENCE = (
    "The historical distribution uses today's revised file and is not what was known "
    "on each past date."
)
ENDPOINTS_ONLY_SENTENCE = (
    "The 12-month percent change uses the two endpoints only. "
    "A missing month between those endpoints is not treated as observed and is not interpolated."
)
RANK_DEFINITION = (
    "Rank of overlapping 12-month percent changes in industrial production "
    f"({INDUSTRIAL_PRODUCTION_DATASET_ID}): "
    "1 plus the count of those percent changes strictly below the latest "
    "12-month percent change. "
    f"{REVISED_HISTORY_SENTENCE}"
)
SCOPE_SENTENCE = "This is industrial production, not GDP. Census advance orders were not collected."


class IndustrialProductionActivityConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    config_id: str = Field(min_length=1)
    label: str = Field(min_length=1)


class IndustrialProductionActivityMethod:
    method_id = INDUSTRIAL_PRODUCTION_METHOD_ID
    method_version = INDUSTRIAL_PRODUCTION_METHOD_VERSION

    def implementation_hash(self) -> str:
        payload = f"{self.method_id}:{self.method_version}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def required_dataset_ids(self) -> tuple[str, ...]:
        return (INDUSTRIAL_PRODUCTION_DATASET_ID,)

    def parse_config(self, payload: dict[str, object]) -> IndustrialProductionActivityConfig:
        return IndustrialProductionActivityConfig.model_validate(payload)

    def config_hash(self, config: BaseModel) -> str:
        if not isinstance(config, IndustrialProductionActivityConfig):
            raise TypeError("expected IndustrialProductionActivityConfig")
        from aqil_research.methods.parameters import MethodParameterDocument

        return MethodParameterDocument(
            config_id=config.config_id,
            label=config.label,
            scalars={"months_back": str(MONTHS_BACK)},
        ).config_hash()

    def run(self, context: MethodContext, config: BaseModel) -> MethodExecutionResult:
        if not isinstance(config, IndustrialProductionActivityConfig):
            raise TypeError("expected IndustrialProductionActivityConfig")
        if context.analysis_mode != AnalysisMode.LATEST_REVISED:
            return _insufficient(
                (
                    f"{context.analysis_mode.value} is insufficient because "
                    f"{INDUSTRIAL_PRODUCTION_DATASET_ID} is not a vintage panel"
                ),
                statistical_interpretation=(
                    "Point-in-time analysis is insufficient because the stored "
                    "industrial production file is not a vintage panel."
                ),
            )

        series = context.inputs_by_dataset.get(INDUSTRIAL_PRODUCTION_DATASET_ID, {})
        eligible = _eligible_series(series, context.evaluation_period)
        if not eligible:
            return _insufficient(
                f"missing endpoint for window ending {context.evaluation_period.isoformat()}",
                statistical_interpretation=_missing_endpoint_interpretation(),
            )

        latest_period = max(eligible)
        earlier_period = _add_months(latest_period, -MONTHS_BACK)
        if earlier_period not in eligible:
            return _insufficient(
                (
                    "missing endpoint for window "
                    f"{earlier_period.isoformat()} to {latest_period.isoformat()}"
                ),
                statistical_interpretation=_missing_endpoint_interpretation(),
            )

        latest = eligible[latest_period]
        earlier = eligible[earlier_period]
        latest_value = latest.decimal_value()
        earlier_value = earlier.decimal_value()
        if earlier_value == 0:
            return _insufficient(
                (
                    "missing endpoint for window "
                    f"{earlier_period.isoformat()} to {latest_period.isoformat()}: "
                    "earlier level is zero and the percent change is undefined"
                ),
                statistical_interpretation=_missing_endpoint_interpretation(),
            )

        percent_change = _twelve_month_percent_change(latest_value, earlier_value)
        changes = _overlapping_percent_changes(eligible)
        latest_change = Decimal(percent_change)
        below = sum(1 for change in changes if change < latest_change)
        rank = 1 + below
        change_count = len(changes)
        observation_ids = tuple(sorted(obs.observation_id for obs in eligible.values()))
        latest_level = latest.raw_value
        earlier_level = earlier.raw_value
        calculation: dict[str, object] = {
            "transformation": "twelve_month_percent_change",
            "formula": "(later/earlier - 1) * 100",
            "dataset_id": INDUSTRIAL_PRODUCTION_DATASET_ID,
            "unit": INDUSTRIAL_PRODUCTION_UNIT,
            "seasonal_adjustment": SeasonalAdjustment.SEASONALLY_ADJUSTED.value,
            "analysis_mode": AnalysisMode.LATEST_REVISED.value,
            "evaluation_period": context.evaluation_period.isoformat(),
            "latest_period": latest_period.isoformat(),
            "earlier_period": earlier_period.isoformat(),
            "latest_level": latest_level,
            "earlier_level": earlier_level,
            "months_back": MONTHS_BACK,
            "twelve_month_percent_change": percent_change,
            "endpoints_only": True,
            "historical_rank": rank,
            "stored_changes_strictly_below_latest": below,
            "stored_change_count": change_count,
            "stored_values_strictly_below_latest": below,
            "stored_value_count": change_count,
            "rank_basis": "overlapping_twelve_month_percent_change",
            "ranked_series": f"industrial production ({INDUSTRIAL_PRODUCTION_DATASET_ID})",
            "rank_definition": RANK_DEFINITION,
            "observation_ids": list(observation_ids),
        }
        return MethodExecutionResult(
            sufficiency="sufficient",
            calculation=calculation,
            observation_ids=observation_ids,
            assumptions=_assumptions(config.label),
            limitations=_limitations(),
            missing_reason=None,
            statistical_interpretation=(
                "This is a descriptive 12-month percent change in seasonally adjusted "
                "industrial production (index 2017=100). "
                f"The rank is the rank of overlapping 12-month percent changes in "
                f"industrial production ({INDUSTRIAL_PRODUCTION_DATASET_ID}), not the level. "
                f"{REVISED_HISTORY_SENTENCE} "
                "It is not a GDP figure and not a forecast."
            ),
            causal_hypothesis=CAUSAL_HYPOTHESIS,
            investment_implication="no_action",
            narrative=_sufficient_narrative(
                latest_period=latest_period,
                earlier_period=earlier_period,
                latest_level=latest_level,
                earlier_level=earlier_level,
                percent_change=percent_change,
                rank=rank,
                change_count=change_count,
            ),
        )


def _sufficient_narrative(
    *,
    latest_period: date,
    earlier_period: date,
    latest_level: str,
    earlier_level: str,
    percent_change: str,
    rank: int,
    change_count: int,
) -> str:
    return (
        f"Industrial production ({INDUSTRIAL_PRODUCTION_DATASET_ID}) for "
        f"{latest_period.isoformat()} is {latest_level} "
        "(index 2017=100, seasonally adjusted). "
        f"The 12-month percent change from {earlier_period.isoformat()} "
        f"({earlier_level}) to {latest_period.isoformat()} ({latest_level}) is {percent_change}. "
        f"{ENDPOINTS_ONLY_SENTENCE} "
        f"The rank of overlapping 12-month percent changes in industrial production "
        f"({INDUSTRIAL_PRODUCTION_DATASET_ID}) is {rank} of {change_count}. "
        f"{RANK_DEFINITION} "
        f"{SCOPE_SENTENCE} "
        "No causal mechanism is established. "
        "The reading is internal."
    )


def _assumptions(label: str) -> tuple[str, ...]:
    return (
        "Input is fed.g17.IP.B50001.S, unit index_2017_100, seasonally adjusted.",
        "The latest level is the latest stored month on or before the evaluation period.",
        (
            "The 12-month percent change is (later/earlier - 1) * 100, "
            "rounded half up to 4 decimal places."
        ),
        (
            "Both window endpoints must be stored. Intermediate months are not required "
            "and are not interpolated. A missing month between the endpoints is not "
            "treated as observed."
        ),
        ENDPOINTS_ONLY_SENTENCE,
        RANK_DEFINITION,
        "No composite score is calculated.",
        label,
    )


def _limitations() -> tuple[str, ...]:
    return (
        "This is industrial production, not GDP.",
        "Census advance orders were not collected.",
        "No causal mechanism is established.",
        "The reading is internal.",
        "A missing 12-month endpoint fails the window and is not interpolated.",
        ENDPOINTS_ONLY_SENTENCE,
        REVISED_HISTORY_SENTENCE,
    )


def _missing_endpoint_interpretation() -> str:
    return (
        "The 12-month window is insufficient because a stored endpoint is missing. "
        "The missing month is not interpolated."
    )


def _insufficient(reason: str, *, statistical_interpretation: str) -> MethodExecutionResult:
    sentence = reason[:1].upper() + reason[1:]
    return MethodExecutionResult(
        sufficiency="insufficient",
        calculation=None,
        observation_ids=(),
        assumptions=(),
        limitations=_limitations(),
        missing_reason=reason,
        statistical_interpretation=statistical_interpretation,
        causal_hypothesis=CAUSAL_HYPOTHESIS,
        investment_implication="insufficient_evidence",
        narrative=(
            f"{sentence}. {SCOPE_SENTENCE} No causal mechanism is established. "
            "The reading is internal."
        ),
    )


def _eligible_series(
    series: dict[date, EconomicObservation],
    evaluation: date,
) -> dict[date, EconomicObservation]:
    eligible: dict[date, EconomicObservation] = {}
    for period, obs in series.items():
        if obs.period_start != period:
            raise ValueError("observation period_start does not match the series key")
        if period > evaluation:
            continue
        _require_contract(obs)
        if obs.quality_status != QualityStatus.OBSERVED:
            continue
        eligible[period] = obs
    return eligible


def _require_contract(obs: EconomicObservation) -> None:
    if obs.dataset_id != INDUSTRIAL_PRODUCTION_DATASET_ID:
        raise ValueError(f"unexpected dataset {obs.dataset_id}")
    if obs.frequency != Frequency.MONTHLY:
        raise ValueError("industrial production activity requires monthly frequency")
    if obs.unit != INDUSTRIAL_PRODUCTION_UNIT:
        raise ValueError("industrial production activity requires unit index_2017_100")
    if obs.seasonal_adjustment != SeasonalAdjustment.SEASONALLY_ADJUSTED:
        raise ValueError("industrial production activity requires seasonally adjusted values")
    if obs.series_provenance != SeriesProvenance.LATEST_REVISED:
        raise ValueError("industrial production activity requires latest_revised rows")


def _overlapping_percent_changes(
    series: dict[date, EconomicObservation],
) -> list[Decimal]:
    changes: list[Decimal] = []
    for period in sorted(series):
        earlier_period = _add_months(period, -MONTHS_BACK)
        if earlier_period not in series:
            continue
        earlier_value = series[earlier_period].decimal_value()
        if earlier_value == 0:
            continue
        changes.append(
            Decimal(
                _twelve_month_percent_change(series[period].decimal_value(), earlier_value),
            ),
        )
    return changes


def _twelve_month_percent_change(later: Decimal, earlier: Decimal) -> str:
    change = ((later / earlier) - Decimal(1)) * Decimal(100)
    quantized = change.quantize(PERCENT_QUANTUM, rounding=ROUND_HALF_UP)
    return format(quantized, "f")


def _add_months(anchor: date, delta: int) -> date:
    year = anchor.year + (anchor.month - 1 + delta) // 12
    month = (anchor.month - 1 + delta) % 12 + 1
    return date(year, month, 1)
