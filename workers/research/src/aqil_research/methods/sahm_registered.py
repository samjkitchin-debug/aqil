"""Sahm rule registered as an AnalyticalMethod."""

from __future__ import annotations

from pydantic import BaseModel

from aqil_research.interpret.sahm import render_sahm_narrative
from aqil_research.methods.configs import SAHM_PUBLISHED
from aqil_research.methods.protocol import (
    MethodContext,
    MethodDependency,
    MethodExecutionResult,
    bind_dependency,
)
from aqil_research.methods.sahm import (
    AVERAGE_WINDOW_MONTHS,
    LOOKBACK_MONTHS,
    SAHM_METHOD_ID,
    SAHM_METHOD_VERSION,
    SahmConfig,
    SahmMethodError,
    run_sahm,
    sahm_implementation_hash,
    sahm_threshold_crossed,
)


class SahmAnalyticalMethod:
    method_id = SAHM_METHOD_ID
    method_version = SAHM_METHOD_VERSION

    def implementation_hash(self) -> str:
        return sahm_implementation_hash()

    def required_dataset_ids(self) -> tuple[str, ...]:
        return ("bls.ln.LNS14000000",)

    def dependency(self) -> MethodDependency:
        months = LOOKBACK_MONTHS + AVERAGE_WINDOW_MONTHS
        return bind_dependency(
            self.required_dataset_ids(),
            frequency=("monthly",),
            minimum_history=(
                f"{months} monthly observations covering the three-month average "
                "and the 12-month lookback"
            ),
            parameter_policy="none",
            new_observation_requires_recalculation=True,
            refit_is_different_command=False,
        )

    def accepted_config_payload(self) -> dict[str, object]:
        return SAHM_PUBLISHED.model_dump(mode="json")

    def parse_config(self, payload: dict[str, object]) -> SahmConfig:
        return SahmConfig.model_validate(payload)

    def config_hash(self, config: BaseModel) -> str:
        if not isinstance(config, SahmConfig):
            raise TypeError("expected SahmConfig")
        return config.config_hash()

    def run(self, context: MethodContext, config: BaseModel) -> MethodExecutionResult:
        if not isinstance(config, SahmConfig):
            raise TypeError("expected SahmConfig")
        try:
            output = run_sahm(
                context.primary_series(),
                context.evaluation_period,
                config,
            )
        except SahmMethodError as exc:
            return MethodExecutionResult(
                sufficiency="insufficient",
                calculation=None,
                observation_ids=(),
                assumptions=(),
                limitations=(),
                missing_reason=str(exc),
                statistical_interpretation=(
                    "Calculation could not be completed with the available inputs."
                ),
                causal_hypothesis="Unresolved because inputs were insufficient.",
                investment_implication="insufficient_evidence",
                narrative=f"Calculation incomplete. Reason: {exc}",
            )
        calculation = output.to_dict()
        calculation["threshold_met"] = output.triggered
        cited_ids = frozenset(output.observation_ids)
        series = context.primary_series()
        frozen_series = {
            period: obs for period, obs in series.items() if obs.observation_id in cited_ids
        }
        calculation["threshold_crossed"] = sahm_threshold_crossed(
            frozen_series,
            context.evaluation_period,
            config,
        )
        return MethodExecutionResult(
            sufficiency="sufficient",
            calculation=calculation,
            observation_ids=output.observation_ids,
            assumptions=output.assumptions,
            limitations=output.limitations,
            missing_reason=None,
            statistical_interpretation=(
                "The Sahm gap is a published recession-association measure. "
                "It is not a forward forecast."
            ),
            causal_hypothesis="No causal mechanism is asserted in this calculation.",
            investment_implication="no_action",
            narrative=render_sahm_narrative(output, context.analysis_mode, config.label),
        )
