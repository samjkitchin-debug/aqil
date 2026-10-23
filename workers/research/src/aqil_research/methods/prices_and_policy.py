"""Prices and policy reading: CPI-U 12-month change and two separate H.15 levels.

CPI-U uses the stored index months only. Federal funds and the 10-year yield
stay separate percent-per-year levels. Euro-area HICP is not an input.
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

PRICES_AND_POLICY_METHOD_ID = "PRICES_AND_POLICY"
PRICES_AND_POLICY_METHOD_VERSION = "1.0.0"

CPI_DATASET_ID = "bls.cu.CUSR0000SA0"
FUNDS_DATASET_ID = "fed.h15.RIFSPFF_N.M"
YIELD_DATASET_ID = "fed.h15.RIFLGFCY10_N.M"

CPI_UNIT = "1982-84=100"
RATE_UNIT = "percent_per_year"
PERCENT_UNIT = "percent"
CHANGE_UNIT = "percentage_points"
CHANGE_SCALE = Decimal("0.0001")

CAUSAL_HYPOTHESIS = "No causal mechanism is established."
POINT_IN_TIME_REASON = "Point-in-time is insufficient because these files are not vintage panels."
RANK_RULE = "1 plus the count of stored values strictly below the latest value"


class PricesAndPolicyConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    config_id: str = Field(min_length=1)
    label: str = Field(min_length=1)


class PricesAndPolicyMethod:
    method_id = PRICES_AND_POLICY_METHOD_ID
    method_version = PRICES_AND_POLICY_METHOD_VERSION

    def implementation_hash(self) -> str:
        payload = f"{self.method_id}:{self.method_version}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def required_dataset_ids(self) -> tuple[str, ...]:
        return (CPI_DATASET_ID, FUNDS_DATASET_ID, YIELD_DATASET_ID)

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
            return _insufficient(POINT_IN_TIME_REASON)

        end = context.evaluation_period
        cpi_start = _add_months(end, -12)
        rate_start = _add_months(end, -1)
        cpi = _observed(context, CPI_DATASET_ID)
        funds = _observed(context, FUNDS_DATASET_ID)
        treasury = _observed(context, YIELD_DATASET_ID)

        gap = _endpoint_gap("CPI-U 12-month", cpi_start, end, cpi)
        if gap is None:
            gap = _endpoint_gap("federal funds one-month", rate_start, end, funds)
        if gap is None:
            gap = _endpoint_gap("10-year yield one-month", rate_start, end, treasury)
        if gap is not None:
            return _insufficient(gap)

        _require_cpi(cpi)
        _require_rate(funds, "Federal funds")
        _require_rate(treasury, "10-year yield")

        earlier_index = cpi[cpi_start].decimal_value()
        later_index = cpi[end].decimal_value()
        if earlier_index == 0:
            return _insufficient(
                f"CPI-U earlier index is zero for window {cpi_start.isoformat()} "
                f"to {end.isoformat()}.",
            )

        cpi_change = _percent_change(later_index, earlier_index)
        funds_level = funds[end].decimal_value()
        funds_prior = funds[rate_start].decimal_value()
        yield_level = treasury[end].decimal_value()
        yield_prior = treasury[rate_start].decimal_value()
        funds_change = _points(funds_level, funds_prior)
        yield_change = _points(yield_level, yield_prior)
        cpi_rank = _rank(cpi, later_index)
        funds_rank = _rank(funds, funds_level)
        yield_rank = _rank(treasury, yield_level)

        calculation: dict[str, object] = {
            "analysis_mode": AnalysisMode.LATEST_REVISED.value,
            "evaluation_period": end.isoformat(),
            "cpi_u": {
                "dataset_id": CPI_DATASET_ID,
                "transformation": "twelve_month_percent_change",
                "formula": "(later_index / earlier_index - 1) * 100",
                "unit": PERCENT_UNIT,
                "index_unit": CPI_UNIT,
                "seasonal_adjustment": SeasonalAdjustment.SEASONALLY_ADJUSTED.value,
                "window_start": cpi_start.isoformat(),
                "window_end": end.isoformat(),
                "earlier_index": str(earlier_index),
                "later_index": str(later_index),
                "percent_change": str(cpi_change),
                "earlier_observation_id": cpi[cpi_start].observation_id,
                "later_observation_id": cpi[end].observation_id,
                "observation_ids": _ids(cpi),
                "latest_value_rank": cpi_rank,
                "stored_value_count": len(cpi),
                "rank_rule": RANK_RULE,
            },
            "federal_funds": {
                "dataset_id": FUNDS_DATASET_ID,
                "transformation": "level_and_one_month_change",
                "level_unit": RATE_UNIT,
                "change_unit": CHANGE_UNIT,
                "seasonal_adjustment": SeasonalAdjustment.UNKNOWN.value,
                "level_period": end.isoformat(),
                "prior_period": rate_start.isoformat(),
                "level": str(funds_level),
                "prior_level": str(funds_prior),
                "one_month_change": str(funds_change),
                "level_observation_id": funds[end].observation_id,
                "prior_observation_id": funds[rate_start].observation_id,
                "observation_ids": _ids(funds),
                "latest_value_rank": funds_rank,
                "stored_value_count": len(funds),
                "rank_rule": RANK_RULE,
            },
            "treasury_10_year_yield": {
                "dataset_id": YIELD_DATASET_ID,
                "transformation": "level_and_one_month_change",
                "level_unit": RATE_UNIT,
                "change_unit": CHANGE_UNIT,
                "seasonal_adjustment": SeasonalAdjustment.UNKNOWN.value,
                "level_period": end.isoformat(),
                "prior_period": rate_start.isoformat(),
                "level": str(yield_level),
                "prior_level": str(yield_prior),
                "one_month_change": str(yield_change),
                "level_observation_id": treasury[end].observation_id,
                "prior_observation_id": treasury[rate_start].observation_id,
                "observation_ids": _ids(treasury),
                "latest_value_rank": yield_rank,
                "stored_value_count": len(treasury),
                "rank_rule": RANK_RULE,
            },
        }
        observation_ids = tuple(
            sorted(set(_ids(cpi)) | set(_ids(funds)) | set(_ids(treasury))),
        )
        narrative = (
            f"CPI-U 12-month change from {cpi_start.isoformat()} to {end.isoformat()} "
            f"is {cpi_change} percent "
            f"(index {earlier_index} to {later_index}, {CPI_UNIT}). "
            f"The latest index ranks {cpi_rank} among {len(cpi)} stored values. "
            f"The federal funds rate is {funds_level} percent per year, "
            f"a one-month change of {funds_change} percentage points. "
            f"The 10-year yield is {yield_level} percent per year, "
            f"a one-month change of {yield_change} percentage points. "
            f"{CAUSAL_HYPOTHESIS}"
        )
        return MethodExecutionResult(
            sufficiency="sufficient",
            calculation=calculation,
            observation_ids=observation_ids,
            assumptions=(
                "CPI-U 12-month percent change is (later index / earlier index - 1) * 100 "
                "when both months exist. Reported changes are rounded half up to 0.0001.",
                "Federal funds and the 10-year yield are separate levels in percent per year. "
                "One-month changes are in percentage points.",
                "Each latest value ranks as 1 plus the count of stored values strictly below it.",
                "Analysis mode is latest_revised.",
                config.label,
            ),
            limitations=_limitations(),
            missing_reason=None,
            statistical_interpretation=(
                "Descriptive CPI-U 12-month percent change and separate federal funds "
                "and 10-year yield levels. Not a forecast."
            ),
            causal_hypothesis=CAUSAL_HYPOTHESIS,
            investment_implication="no_action",
            narrative=narrative,
        )


def _limitations() -> tuple[str, ...]:
    return (
        "The euro-area HICP series ends December 2025 and is excluded. "
        "That series is ecb.icp.M.U2.Y.000000.3.INX, unit index, 2015 = 100, "
        "and it is not an input.",
        "CPI-U is an index (1982-84=100), seasonally adjusted. "
        "A missing month is not interpolated.",
        "Federal funds and the 10-year yield stay separate percent-per-year levels. "
        "Their seasonal adjustment is unknown. No real rate is calculated.",
    )


def _insufficient(reason: str) -> MethodExecutionResult:
    return MethodExecutionResult(
        sufficiency="insufficient",
        calculation=None,
        observation_ids=(),
        assumptions=(),
        limitations=_limitations(),
        missing_reason=reason,
        statistical_interpretation=reason,
        causal_hypothesis=CAUSAL_HYPOTHESIS,
        investment_implication="insufficient_evidence",
        narrative=reason,
    )


def _observed(
    context: MethodContext,
    dataset_id: str,
) -> dict[date, EconomicObservation]:
    rows = context.inputs_by_dataset.get(dataset_id, {})
    return {
        period: obs
        for period, obs in rows.items()
        if obs.dataset_id == dataset_id and obs.quality_status == QualityStatus.OBSERVED
    }


def _require_cpi(series: dict[date, EconomicObservation]) -> None:
    for obs in series.values():
        if obs.frequency != Frequency.MONTHLY:
            raise ValueError("CPI-U requires monthly frequency")
        if obs.unit != CPI_UNIT:
            raise ValueError("CPI-U requires unit 1982-84=100")
        if obs.seasonal_adjustment != SeasonalAdjustment.SEASONALLY_ADJUSTED:
            raise ValueError("CPI-U requires seasonal adjustment")
        if obs.series_provenance != SeriesProvenance.LATEST_REVISED:
            raise ValueError("CPI-U requires latest_revised provenance")


def _require_rate(series: dict[date, EconomicObservation], name: str) -> None:
    for obs in series.values():
        if obs.frequency != Frequency.MONTHLY:
            raise ValueError(f"{name} requires monthly frequency")
        if obs.unit != RATE_UNIT:
            raise ValueError(f"{name} requires unit percent_per_year")
        if obs.seasonal_adjustment != SeasonalAdjustment.UNKNOWN:
            raise ValueError(f"{name} requires seasonal adjustment unknown")
        if obs.series_provenance != SeriesProvenance.LATEST_REVISED:
            raise ValueError(f"{name} requires latest_revised provenance")


def _endpoint_gap(
    label: str,
    start: date,
    end: date,
    series: dict[date, EconomicObservation],
) -> str | None:
    missing = [day.isoformat() for day in (start, end) if day not in series]
    if not missing:
        return None
    joined = " and ".join(missing)
    return f"Missing {label} endpoint {joined} for window {start.isoformat()} to {end.isoformat()}."


def _percent_change(later: Decimal, earlier: Decimal) -> Decimal:
    change = ((later / earlier) - 1) * Decimal(100)
    return change.quantize(CHANGE_SCALE, rounding=ROUND_HALF_UP)


def _points(later: Decimal, earlier: Decimal) -> Decimal:
    return (later - earlier).quantize(CHANGE_SCALE, rounding=ROUND_HALF_UP)


def _rank(series: dict[date, EconomicObservation], latest: Decimal) -> int:
    below = sum(1 for obs in series.values() if obs.decimal_value() < latest)
    return 1 + below


def _ids(series: dict[date, EconomicObservation]) -> list[str]:
    return sorted(obs.observation_id for obs in series.values())


def _add_months(anchor: date, delta: int) -> date:
    year = anchor.year + (anchor.month - 1 + delta) // 12
    month = (anchor.month - 1 + delta) % 12 + 1
    return date(year, month, 1)
