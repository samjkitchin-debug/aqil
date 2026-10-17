"""SLOOS C&I lending standards — net tightening share (SUBLPDCILS_N.Q)."""

from __future__ import annotations

import hashlib
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from pydantic import BaseModel, ConfigDict, Field

from aqil_research.contracts.observation import EconomicObservation, Frequency
from aqil_research.methods.protocol import MethodContext, MethodExecutionResult

SLOOS_CIL_METHOD_ID = "SLOOS_CIL_LENDING_STANDARDS"
SLOOS_CIL_METHOD_VERSION = "1.0.0"
SLOOS_DATASET_ID = "fed.sloos.SUBLPDCILS_N.Q"


class SloosCilConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    config_id: str = Field(min_length=1)
    label: str = Field(min_length=1)


class SloosCilMethod:
    method_id = SLOOS_CIL_METHOD_ID
    method_version = SLOOS_CIL_METHOD_VERSION

    def implementation_hash(self) -> str:
        payload = f"{self.method_id}:{self.method_version}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def required_dataset_ids(self) -> tuple[str, ...]:
        return (SLOOS_DATASET_ID,)

    def parse_config(self, payload: dict[str, object]) -> SloosCilConfig:
        return SloosCilConfig.model_validate(payload)

    def config_hash(self, config: BaseModel) -> str:
        if not isinstance(config, SloosCilConfig):
            raise TypeError("expected SloosCilConfig")
        from aqil_research.methods.parameters import MethodParameterDocument

        return MethodParameterDocument(
            config_id=config.config_id,
            label=config.label,
            scalars={},
        ).config_hash()

    def run(self, context: MethodContext, config: BaseModel) -> MethodExecutionResult:
        if not isinstance(config, SloosCilConfig):
            raise TypeError("expected SloosCilConfig")
        series = context.inputs_by_dataset.get(SLOOS_DATASET_ID, {})
        evaluation = context.evaluation_period
        obs = _latest_on_or_before(series, evaluation)
        if obs is None:
            return _insufficient(f"no SLOOS observation on or before {evaluation.isoformat()}")

        value = Decimal(obs.raw_value).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
        zero_semantics = (
            "A reading of 0.0 means the net share of banks tightening C&I standards "
            "equals the net share easing — not that every respondent reported unchanged standards."
        )
        direction = _direction_label(value)
        calculation = {
            "evaluation_period": evaluation.isoformat(),
            "observation_period": obs.period_start.isoformat(),
            "net_tightening_share_percent": str(value),
            "direction_label": direction,
            "zero_means_net_balance_not_unanimous_unchanged": True,
            "series_id": "SUBLPDCILS_N.Q",
        }
        return MethodExecutionResult(
            sufficiency="sufficient",
            calculation=calculation,
            observation_ids=(obs.observation_id,),
            assumptions=(
                "Quarterly Senior Loan Officer Opinion Survey net tightening share for "
                "C&I loans to large and middle-market firms.",
                config.label,
            ),
            limitations=_limitations(),
            missing_reason=None,
            statistical_interpretation=(
                "Descriptive credit-conditions indicator from bank lending-officer survey responses. "
                "Not a validated predictor of corporate earnings, ETF returns, or allocation changes."
            ),
            causal_hypothesis="No causal mechanism is asserted.",
            investment_implication="no_action",
            narrative=(
                f"SLOOS C&I standards for {obs.period_start.isoformat()}: net tightening share "
                f"{value}% ({direction}). {zero_semantics}"
            ),
        )


def _latest_on_or_before(
    series: dict[date, EconomicObservation],
    anchor: date,
) -> EconomicObservation | None:
    candidates = [
        obs
        for period, obs in series.items()
        if period <= anchor and obs.frequency == Frequency.QUARTERLY
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda row: row.period_start)


def _direction_label(value: Decimal) -> str:
    if value > 0:
        return "net_tightening"
    if value < 0:
        return "net_easing"
    return "balanced_net_tightening_and_easing"


def _limitations() -> tuple[str, ...]:
    return (
        "Survey-based qualitative standards indicator; subject to revision in later SLOOS releases.",
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
        statistical_interpretation="Insufficient SLOOS observations for the evaluation date.",
        causal_hypothesis="Unresolved.",
        investment_implication="insufficient_evidence",
        narrative=reason,
    )
