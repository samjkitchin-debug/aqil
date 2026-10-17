"""Test methodology: level change over a fixed month window (interface proof only)."""

from __future__ import annotations

import hashlib
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from pydantic import BaseModel, ConfigDict, Field

from aqil_research.contracts.observation import EconomicObservation, Frequency
from aqil_research.methods.protocol import MethodContext, MethodExecutionResult
from aqil_research.methods.sahm import SahmMethodError
from aqil_research.vintages.asof import monthly_decimal_series

PERIOD_CHANGE_METHOD_ID = "PERIOD_LEVEL_CHANGE"
PERIOD_CHANGE_METHOD_VERSION = "1.0.0"


class PeriodChangeConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    config_id: str = Field(min_length=1)
    months_back: int = Field(ge=1, le=120)
    label: str = Field(min_length=1)


class PeriodChangeMethod:
    method_id = PERIOD_CHANGE_METHOD_ID
    method_version = PERIOD_CHANGE_METHOD_VERSION

    def implementation_hash(self) -> str:
        payload = f"{self.method_id}:{self.method_version}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def required_dataset_ids(self) -> tuple[str, ...]:
        return ("bls.ln.LNS14000000",)

    def parse_config(self, payload: dict[str, object]) -> PeriodChangeConfig:
        return PeriodChangeConfig.model_validate(payload)

    def config_hash(self, config: BaseModel) -> str:
        if not isinstance(config, PeriodChangeConfig):
            raise TypeError("expected PeriodChangeConfig")
        from aqil_research.methods.parameters import MethodParameterDocument

        return MethodParameterDocument(
            config_id=config.config_id,
            label=config.label,
            scalars={"months_back": str(config.months_back)},
        ).config_hash()

    def run(self, context: MethodContext, config: BaseModel) -> MethodExecutionResult:
        if not isinstance(config, PeriodChangeConfig):
            raise TypeError("expected PeriodChangeConfig")
        values = monthly_decimal_series(context.by_period)
        end = context.evaluation_period
        start = _add_months(end, -config.months_back)
        if start not in values or end not in values:
            return MethodExecutionResult(
                sufficiency="insufficient",
                calculation=None,
                observation_ids=(),
                assumptions=(),
                limitations=_limitations(),
                missing_reason=(
                    f"missing endpoints for window {start.isoformat()} to {end.isoformat()}"
                ),
                statistical_interpretation="Window endpoints were not available.",
                causal_hypothesis="Unresolved.",
                investment_implication="insufficient_evidence",
                narrative="Insufficient observations for the configured window.",
            )
        _validate_monthly_percent(context.by_period)
        change = (values[end] - values[start]).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        obs_ids = tuple(
            sorted(
                {
                    context.by_period[end].observation_id,
                    context.by_period[start].observation_id,
                },
            ),
        )
        calculation = {
            "evaluation_period": end.isoformat(),
            "window_start": start.isoformat(),
            "months_back": config.months_back,
            "level_at_end": str(values[end]),
            "level_at_start": str(values[start]),
            "level_change": str(change),
        }
        return MethodExecutionResult(
            sufficiency="sufficient",
            calculation=calculation,
            observation_ids=obs_ids,
            assumptions=(
                "Monthly percent observations with contiguous calendar months.",
                f"Window length is {config.months_back} months ({config.label}).",
            ),
            limitations=_limitations(),
            missing_reason=None,
            statistical_interpretation=(
                "This is a descriptive level change over a fixed window, not a forecast or signal."
            ),
            causal_hypothesis="No causal mechanism is asserted.",
            investment_implication="no_action",
            narrative=(
                f"Level change from {start.isoformat()} to {end.isoformat()}: "
                f"{values[start]}% to {values[end]}% ({change} percentage points). "
                "Not an investment recommendation."
            ),
        )


def _limitations() -> tuple[str, ...]:
    return (
        "Interface demonstration only; not a production investment model.",
        "Not comparable to the Sahm rule or NBER recession dating.",
    )


def _validate_monthly_percent(by_period: dict[date, EconomicObservation]) -> None:
    for row in by_period.values():
        if row.frequency != Frequency.MONTHLY:
            raise SahmMethodError("period change requires monthly frequency")
        if row.unit != "percent":
            raise SahmMethodError("period change requires percent unit")


def _add_months(anchor: date, delta: int) -> date:
    year = anchor.year + (anchor.month - 1 + delta) // 12
    month = (anchor.month - 1 + delta) % 12 + 1
    return date(year, month, 1)
