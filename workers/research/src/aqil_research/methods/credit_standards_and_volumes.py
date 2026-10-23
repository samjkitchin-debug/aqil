"""Credit standards and volumes — SLOOS share beside weekly H.8 bank credit.

Does not replace SLOOS_CIL_LENDING_STANDARDS. The survey share stays in
percent_net_tightening. Weekly bank credit stays in usd_millions.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

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

CREDIT_STANDARDS_AND_VOLUMES_METHOD_ID = "CREDIT_STANDARDS_AND_VOLUMES"
CREDIT_STANDARDS_AND_VOLUMES_METHOD_VERSION = "1.0.0"
SLOOS_DATASET_ID = "fed.sloos.SUBLPDCILS_N.Q"
H8_DATASET_ID = "fed.h8.B1001NCBA"
SLOOS_UNIT = "percent_net_tightening"
H8_UNIT = "usd_millions"
WEEKS_EARLIER = 52
CAUSAL_HYPOTHESIS = "No causal mechanism is established."
POINT_IN_TIME_REASON = (
    "A point-in-time request is insufficient because these files are not vintage panels."
)


class CreditStandardsAndVolumesConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    config_id: str = Field(min_length=1)
    label: str = Field(min_length=1)


@dataclass(frozen=True, slots=True)
class _StandardsChange:
    latest: EconomicObservation
    prior: EconomicObservation
    difference: Decimal


@dataclass(frozen=True, slots=True)
class _VolumeReading:
    latest: EconomicObservation
    comparison_period_start: date
    comparison: EconomicObservation | None
    change: Decimal | None


class CreditStandardsAndVolumesMethod:
    method_id = CREDIT_STANDARDS_AND_VOLUMES_METHOD_ID
    method_version = CREDIT_STANDARDS_AND_VOLUMES_METHOD_VERSION

    def implementation_hash(self) -> str:
        payload = f"{self.method_id}:{self.method_version}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def required_dataset_ids(self) -> tuple[str, ...]:
        return (SLOOS_DATASET_ID, H8_DATASET_ID)

    def parse_config(self, payload: dict[str, object]) -> CreditStandardsAndVolumesConfig:
        return CreditStandardsAndVolumesConfig.model_validate(payload)

    def config_hash(self, config: BaseModel) -> str:
        if not isinstance(config, CreditStandardsAndVolumesConfig):
            raise TypeError("expected CreditStandardsAndVolumesConfig")
        from aqil_research.methods.parameters import MethodParameterDocument

        return MethodParameterDocument(
            config_id=config.config_id,
            label=config.label,
            scalars={},
        ).config_hash()

    def run(self, context: MethodContext, config: BaseModel) -> MethodExecutionResult:
        if not isinstance(config, CreditStandardsAndVolumesConfig):
            raise TypeError("expected CreditStandardsAndVolumesConfig")
        if context.analysis_mode != AnalysisMode.LATEST_REVISED:
            return _insufficient(POINT_IN_TIME_REASON)

        standards = _standards_change(context)
        if isinstance(standards, str):
            return _insufficient(standards)
        volume = _volume_reading(context)
        if isinstance(volume, str):
            return _insufficient(volume)
        return _sufficient(context, config, standards, volume)


def _standards_change(context: MethodContext) -> _StandardsChange | str:
    evaluation = context.evaluation_period
    rows = _eligible(
        context.inputs_by_dataset.get(SLOOS_DATASET_ID, {}),
        anchor=evaluation,
        dataset_id=SLOOS_DATASET_ID,
        frequency=Frequency.QUARTERLY,
        unit=SLOOS_UNIT,
        seasonal_adjustment=SeasonalAdjustment.NOT_SEASONALLY_ADJUSTED,
    )
    latest = _latest(rows)
    if latest is None:
        return (
            "missing required latest observation for "
            f"{SLOOS_DATASET_ID} on or before {evaluation.isoformat()}"
        )
    prior = _prior(rows, latest)
    if prior is None:
        return f"no prior stored quarter before {latest.period_start.isoformat()}"
    difference = latest.decimal_value() - prior.decimal_value()
    return _StandardsChange(latest=latest, prior=prior, difference=difference)


def _volume_reading(context: MethodContext) -> _VolumeReading | str:
    evaluation = context.evaluation_period
    rows = _eligible(
        context.inputs_by_dataset.get(H8_DATASET_ID, {}),
        anchor=evaluation,
        dataset_id=H8_DATASET_ID,
        frequency=Frequency.WEEKLY,
        unit=H8_UNIT,
        seasonal_adjustment=SeasonalAdjustment.SEASONALLY_ADJUSTED,
    )
    latest = _latest(rows)
    if latest is None:
        return (
            "missing required latest observation for "
            f"{H8_DATASET_ID} on or before {evaluation.isoformat()}"
        )
    comparison_period = latest.period_start - timedelta(weeks=WEEKS_EARLIER)
    comparison = _on_period(rows, comparison_period)
    change = None if comparison is None else latest.decimal_value() - comparison.decimal_value()
    return _VolumeReading(
        latest=latest,
        comparison_period_start=comparison_period,
        comparison=comparison,
        change=change,
    )


def _eligible(
    series: dict[date, EconomicObservation],
    *,
    anchor: date,
    dataset_id: str,
    frequency: Frequency,
    unit: str,
    seasonal_adjustment: SeasonalAdjustment,
) -> list[EconomicObservation]:
    chosen: list[EconomicObservation] = []
    for period, obs in series.items():
        if period != obs.period_start or period > anchor:
            continue
        if obs.dataset_id != dataset_id or obs.frequency != frequency or obs.unit != unit:
            continue
        if obs.seasonal_adjustment != seasonal_adjustment:
            continue
        if obs.series_provenance != SeriesProvenance.LATEST_REVISED:
            continue
        if obs.quality_status != QualityStatus.OBSERVED:
            continue
        chosen.append(obs)
    return chosen


def _latest(rows: list[EconomicObservation]) -> EconomicObservation | None:
    if not rows:
        return None
    return max(rows, key=lambda row: row.period_start)


def _prior(
    rows: list[EconomicObservation],
    latest: EconomicObservation,
) -> EconomicObservation | None:
    earlier = [row for row in rows if row.period_start < latest.period_start]
    if not earlier:
        return None
    return max(earlier, key=lambda row: row.period_start)


def _on_period(
    rows: list[EconomicObservation],
    period: date,
) -> EconomicObservation | None:
    for row in rows:
        if row.period_start == period:
            return row
    return None


def _sufficient(
    context: MethodContext,
    config: CreditStandardsAndVolumesConfig,
    standards: _StandardsChange,
    volume: _VolumeReading,
) -> MethodExecutionResult:
    latest_share = _plain(standards.latest.decimal_value())
    prior_share = _plain(standards.prior.decimal_value())
    difference = _plain(standards.difference)
    latest_level = _plain(volume.latest.decimal_value())
    volume_ready = volume.comparison is not None and volume.change is not None
    comparison_level = (
        None if volume.comparison is None else _plain(volume.comparison.decimal_value())
    )
    change = None if volume.change is None else _plain(volume.change)
    sought = volume.comparison_period_start.isoformat()
    volume_reason = None
    if not volume_ready:
        volume_reason = f"missing H.8 week {sought} for the 52-week change"
    used = [
        standards.latest.observation_id,
        standards.prior.observation_id,
        volume.latest.observation_id,
    ]
    if volume.comparison is not None:
        used.append(volume.comparison.observation_id)
    calculation: dict[str, object] = {
        "transformation": (
            "latest_share minus prior_stored_quarter in percentage points "
            f"(unit {SLOOS_UNIT}); "
            f"latest_level minus the week {WEEKS_EARLIER} weeks earlier in {H8_UNIT}"
        ),
        "analysis_mode": AnalysisMode.LATEST_REVISED.value,
        "evaluation_period": context.evaluation_period.isoformat(),
        "survey_balance_converted_to_dollars": False,
        "lending_standards": {
            "dataset_id": SLOOS_DATASET_ID,
            "unit": SLOOS_UNIT,
            "frequency": Frequency.QUARTERLY.value,
            "seasonal_adjustment": SeasonalAdjustment.NOT_SEASONALLY_ADJUSTED.value,
            "transformation": "latest_share_minus_prior_stored_quarter",
            "latest_period_start": standards.latest.period_start.isoformat(),
            "latest_observation_id": standards.latest.observation_id,
            "latest_share": latest_share,
            "prior_period_start": standards.prior.period_start.isoformat(),
            "prior_observation_id": standards.prior.observation_id,
            "prior_share": prior_share,
            "difference_percentage_points": difference,
        },
        "bank_credit": {
            "dataset_id": H8_DATASET_ID,
            "unit": H8_UNIT,
            "frequency": Frequency.WEEKLY.value,
            "seasonal_adjustment": SeasonalAdjustment.SEASONALLY_ADJUSTED.value,
            "transformation": "latest_level_minus_exact_period_start_52_weeks_earlier",
            "weeks_earlier": WEEKS_EARLIER,
            "latest_period_start": volume.latest.period_start.isoformat(),
            "latest_observation_id": volume.latest.observation_id,
            "latest_level_usd_millions": latest_level,
            "comparison_period_start": sought,
            "comparison_observation_id": (
                None if volume.comparison is None else volume.comparison.observation_id
            ),
            "comparison_level_usd_millions": comparison_level,
            "change_usd_millions": change,
            "sufficiency": "sufficient" if volume_ready else "insufficient",
            "missing_reason": volume_reason,
        },
    }
    return MethodExecutionResult(
        sufficiency="sufficient",
        calculation=calculation,
        observation_ids=tuple(sorted(set(used))),
        assumptions=(
            "SLOOS SUBLPDCILS_N.Q is a quarterly net tightening share in "
            "percent_net_tightening, not seasonally adjusted.",
            "H.8 B1001NCBA is weekly bank credit in usd_millions, seasonally adjusted.",
            "The two series are reported beside each other. "
            "The survey balance is not converted into dollars.",
            f"The volume comparison uses the exact period_start {WEEKS_EARLIER} weeks earlier.",
            config.label,
        ),
        limitations=_limitations(),
        missing_reason=None,
        statistical_interpretation=(
            "Descriptive reading of the latest SLOOS net tightening share beside "
            "the latest H.8 bank credit level. The survey balance stays in "
            "percent_net_tightening and the volume stays in usd_millions. "
            "No causal mechanism is established."
        ),
        causal_hypothesis=CAUSAL_HYPOTHESIS,
        investment_implication="no_action",
        narrative=_narrative(
            standards,
            volume,
            latest_share,
            prior_share,
            difference,
            latest_level,
            change,
        ),
    )


def _narrative(
    standards: _StandardsChange,
    volume: _VolumeReading,
    latest_share: str,
    prior_share: str,
    difference: str,
    latest_level: str,
    change: str | None,
) -> str:
    standards_text = (
        f"The latest SLOOS net tightening share for {standards.latest.period_start.isoformat()} "
        f"is {latest_share} per cent net tightening, a difference of {difference} "
        f"percentage points from the prior stored quarter "
        f"{standards.prior.period_start.isoformat()} at {prior_share}."
    )
    if volume.comparison is None or change is None:
        volume_text = (
            f"Beside it, H.8 bank credit for the week of {volume.latest.period_start.isoformat()} "
            f"is {latest_level} millions of dollars. "
            f"The week 52 weeks earlier ({volume.comparison_period_start.isoformat()}) is absent, "
            "so the 52-week change is insufficient."
        )
    else:
        volume_text = (
            f"Beside it, H.8 bank credit for the week of {volume.latest.period_start.isoformat()} "
            f"is {latest_level} millions of dollars, a change of {change} millions of dollars "
            f"versus the week of {volume.comparison.period_start.isoformat()}."
        )
    return (
        f"{standards_text} {volume_text} "
        "The survey balance is not converted into dollars. "
        "No causal mechanism is established. "
        "The reading is internal."
    )


def _limitations() -> tuple[str, ...]:
    return (
        "The survey balance is not converted into dollars.",
        "No causal mechanism is established between lending standards and bank credit.",
        "A missing exact week is not interpolated and is not filled with zero.",
        "The reading is internal.",
        "Not an earnings or ETF-return forecasting model.",
        "Do not infer ETF allocation changes from this output.",
    )


def _insufficient(reason: str) -> MethodExecutionResult:
    return MethodExecutionResult(
        sufficiency="insufficient",
        calculation=None,
        observation_ids=(),
        assumptions=(),
        limitations=_limitations(),
        missing_reason=reason,
        statistical_interpretation=(
            "A required latest observation is missing, a required prior quarter is missing, "
            "or the analysis mode is not latest_revised, so the reading is not reported."
        ),
        causal_hypothesis=CAUSAL_HYPOTHESIS,
        investment_implication="insufficient_evidence",
        narrative=reason,
    )


def _plain(value: Decimal) -> str:
    return format(value, "f")
