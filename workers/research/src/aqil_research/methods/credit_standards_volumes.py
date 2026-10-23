"""Credit standards and volumes — SLOOS share beside weekly H.8 bank credit.

The survey share stays in percent_net_tightening. Weekly bank credit stays in
usd_millions. A missing exact week 52 weeks earlier leaves only that volume
change unavailable.
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


class CreditStandardsVolumesConfig(BaseModel):
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


class CreditStandardsVolumesMethod:
    method_id = CREDIT_STANDARDS_AND_VOLUMES_METHOD_ID
    method_version = CREDIT_STANDARDS_AND_VOLUMES_METHOD_VERSION

    def implementation_hash(self) -> str:
        payload = f"{self.method_id}:{self.method_version}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def required_dataset_ids(self) -> tuple[str, ...]:
        return (SLOOS_DATASET_ID, H8_DATASET_ID)

    def parse_config(self, payload: dict[str, object]) -> CreditStandardsVolumesConfig:
        return CreditStandardsVolumesConfig.model_validate(payload)

    def config_hash(self, config: BaseModel) -> str:
        if not isinstance(config, CreditStandardsVolumesConfig):
            raise TypeError("expected CreditStandardsVolumesConfig")
        from aqil_research.methods.parameters import MethodParameterDocument

        return MethodParameterDocument(
            config_id=config.config_id,
            label=config.label,
            scalars={},
        ).config_hash()

    def run(self, context: MethodContext, config: BaseModel) -> MethodExecutionResult:
        if not isinstance(config, CreditStandardsVolumesConfig):
            raise TypeError("expected CreditStandardsVolumesConfig")
        if context.analysis_mode != AnalysisMode.LATEST_REVISED:
            return _insufficient(
                "Point-in-time is insufficient because these files are not vintage panels.",
            )

        standards = _standards_change(context)
        if isinstance(standards, str):
            return _insufficient(standards)
        volume = _volume_reading(context)
        if isinstance(volume, str):
            return _insufficient(volume)
        return _sufficient(context, config, standards, volume)


def _standards_change(context: MethodContext) -> _StandardsChange | str:
    evaluation = context.evaluation_period
    rows = [
        obs
        for obs in context.inputs_by_dataset.get(SLOOS_DATASET_ID, {}).values()
        if _standards_row(obs) and obs.period_start <= evaluation
    ]
    if not rows:
        return f"no SLOOS observation on or before {evaluation.isoformat()}"
    latest = max(rows, key=lambda obs: obs.period_start)
    earlier = [obs for obs in rows if obs.period_start < latest.period_start]
    if not earlier:
        return f"no prior stored SLOOS quarter before {latest.period_start.isoformat()}"
    prior = max(earlier, key=lambda obs: obs.period_start)
    difference = latest.decimal_value() - prior.decimal_value()
    return _StandardsChange(latest=latest, prior=prior, difference=difference)


def _volume_reading(context: MethodContext) -> _VolumeReading | str:
    evaluation = context.evaluation_period
    rows = {
        obs.period_start: obs
        for obs in context.inputs_by_dataset.get(H8_DATASET_ID, {}).values()
        if _volume_row(obs) and obs.period_start <= evaluation
    }
    if not rows:
        return f"no H.8 observation on or before {evaluation.isoformat()}"
    latest = rows[max(rows)]
    comparison_period = latest.period_start - timedelta(weeks=WEEKS_EARLIER)
    comparison = rows.get(comparison_period)
    change = None if comparison is None else latest.decimal_value() - comparison.decimal_value()
    return _VolumeReading(
        latest=latest,
        comparison_period_start=comparison_period,
        comparison=comparison,
        change=change,
    )


def _standards_row(obs: EconomicObservation) -> bool:
    return (
        obs.dataset_id == SLOOS_DATASET_ID
        and obs.unit == SLOOS_UNIT
        and obs.frequency == Frequency.QUARTERLY
        and obs.seasonal_adjustment == SeasonalAdjustment.NOT_SEASONALLY_ADJUSTED
        and obs.series_provenance == SeriesProvenance.LATEST_REVISED
        and obs.quality_status == QualityStatus.OBSERVED
    )


def _volume_row(obs: EconomicObservation) -> bool:
    return (
        obs.dataset_id == H8_DATASET_ID
        and obs.unit == H8_UNIT
        and obs.frequency == Frequency.WEEKLY
        and obs.seasonal_adjustment == SeasonalAdjustment.SEASONALLY_ADJUSTED
        and obs.series_provenance == SeriesProvenance.LATEST_REVISED
        and obs.quality_status == QualityStatus.OBSERVED
    )


def _sufficient(
    context: MethodContext,
    config: CreditStandardsVolumesConfig,
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
        volume_reason = (
            f"missing exact H.8 period_start {sought} for the {WEEKS_EARLIER}-week change"
        )
    observation_ids = [
        standards.latest.observation_id,
        standards.prior.observation_id,
        volume.latest.observation_id,
    ]
    if volume.comparison is not None:
        observation_ids.append(volume.comparison.observation_id)
    calculation: dict[str, object] = {
        "analysis_mode": AnalysisMode.LATEST_REVISED.value,
        "evaluation_period": context.evaluation_period.isoformat(),
        "units": {
            "lending_standards_share": SLOOS_UNIT,
            "lending_standards_difference": "percentage_points",
            "bank_credit_level": H8_UNIT,
            "bank_credit_change": H8_UNIT,
        },
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
        observation_ids=tuple(sorted(observation_ids)),
        assumptions=(
            "Latest-revised SLOOS net tightening share, quarterly and not seasonally adjusted.",
            "Latest-revised H.8 bank credit, weekly and seasonally adjusted, in usd_millions.",
            f"The volume comparison looks up the exact period_start {WEEKS_EARLIER} weeks earlier.",
            config.label,
        ),
        limitations=_limitations(),
        missing_reason=None,
        statistical_interpretation=_interpretation(),
        causal_hypothesis=CAUSAL_HYPOTHESIS,
        investment_implication="no_action",
        narrative=_narrative(
            standards,
            volume,
            latest_share,
            prior_share,
            difference,
            latest_level,
            comparison_level,
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
    comparison_level: str | None,
    change: str | None,
) -> str:
    standards_text = (
        f"The latest SLOOS net tightening share is {latest_share} {SLOOS_UNIT} "
        f"for the quarter starting {standards.latest.period_start.isoformat()} "
        f"({standards.latest.observation_id}). "
        f"The prior stored quarter starting {standards.prior.period_start.isoformat()} "
        f"({standards.prior.observation_id}) is {prior_share} {SLOOS_UNIT}. "
        f"The difference is {difference} percentage points. "
    )
    level_text = (
        f"The latest H.8 bank credit week starting {volume.latest.period_start.isoformat()} "
        f"({volume.latest.observation_id}) is {latest_level} {H8_UNIT}. "
    )
    if volume.comparison is None or comparison_level is None or change is None:
        volume_text = (
            f"The change versus the week starting {volume.comparison_period_start.isoformat()} "
            "is insufficient because that exact period_start is not stored. "
        )
    else:
        volume_text = (
            f"The week starting {volume.comparison.period_start.isoformat()} "
            f"({volume.comparison.observation_id}) is {comparison_level} {H8_UNIT}. "
            f"The change is {change} {H8_UNIT}. "
        )
    return standards_text + level_text + volume_text + CAUSAL_HYPOTHESIS


def _interpretation() -> str:
    return (
        "Descriptive reading of the latest stored SLOOS net-tightening share against the "
        "prior stored quarter, beside the latest stored H.8 bank-credit level and, when "
        "that exact week exists, the change over 52 weeks. The survey share stays in "
        "percent_net_tightening. Weekly observations stay on their stored weeks."
    )


def _limitations() -> tuple[str, ...]:
    return (
        "The survey share stays in percent_net_tightening.",
        "Weekly bank credit stays on its stored weeks.",
        "A missing exact comparison week leaves that volume change unavailable.",
        "These files are not vintage panels.",
        CAUSAL_HYPOTHESIS,
        "The reading is internal.",
    )


def _insufficient(reason: str) -> MethodExecutionResult:
    return MethodExecutionResult(
        sufficiency="insufficient",
        calculation=None,
        observation_ids=(),
        assumptions=(),
        limitations=_limitations(),
        missing_reason=reason,
        statistical_interpretation="Insufficient stored observations for this credit reading.",
        causal_hypothesis=CAUSAL_HYPOTHESIS,
        investment_implication="insufficient_evidence",
        narrative=reason,
    )


def _plain(value: Decimal) -> str:
    return format(value, "f")
