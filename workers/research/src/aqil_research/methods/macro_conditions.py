"""Combined labour, credit and manufacturing conditions panel."""

from __future__ import annotations

import hashlib
from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from aqil_research.methods.census_adv_orders import (
    CENSUS_ADV_ORDERS_METHOD_ID,
    CENSUS_DATASET_ID,
    CensusAdvOrdersConfig,
    CensusAdvOrdersMethod,
)
from aqil_research.methods.configs import SAHM_PUBLISHED
from aqil_research.methods.protocol import MethodContext, MethodExecutionResult
from aqil_research.methods.sahm_registered import SahmAnalyticalMethod
from aqil_research.methods.sloos_cil import (
    SLOOS_CIL_METHOD_ID,
    SLOOS_DATASET_ID,
    SloosCilConfig,
    SloosCilMethod,
)

MACRO_CONDITIONS_METHOD_ID = "MACRO_CONDITIONS_PANEL"
MACRO_CONDITIONS_METHOD_VERSION = "1.0.0"
LABOUR_DATASET_ID = "bls.ln.LNS14000000"


class MacroConditionsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    config_id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    labour_evaluation_period: str = Field(min_length=1)
    sloos_evaluation_period: str = Field(min_length=1)
    census_evaluation_period: str = Field(min_length=1)
    sahm_config_id: str = Field(default=SAHM_PUBLISHED.config_id)


class MacroConditionsMethod:
    method_id = MACRO_CONDITIONS_METHOD_ID
    method_version = MACRO_CONDITIONS_METHOD_VERSION

    def implementation_hash(self) -> str:
        payload = f"{self.method_id}:{self.method_version}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def required_dataset_ids(self) -> tuple[str, ...]:
        return (LABOUR_DATASET_ID, SLOOS_DATASET_ID, CENSUS_DATASET_ID)

    def vintage_history_dataset_ids(self) -> tuple[str, ...]:
        return (CENSUS_DATASET_ID,)

    def parse_config(self, payload: dict[str, object]) -> MacroConditionsConfig:
        return MacroConditionsConfig.model_validate(payload)

    def config_hash(self, config: BaseModel) -> str:
        if not isinstance(config, MacroConditionsConfig):
            raise TypeError("expected MacroConditionsConfig")
        from aqil_research.methods.parameters import MethodParameterDocument

        return MethodParameterDocument(
            config_id=config.config_id,
            label=config.label,
            scalars={
                "labour_evaluation_period": config.labour_evaluation_period,
                "sloos_evaluation_period": config.sloos_evaluation_period,
                "census_evaluation_period": config.census_evaluation_period,
                "sahm_config_id": config.sahm_config_id,
            },
        ).config_hash()

    def run(self, context: MethodContext, config: BaseModel) -> MethodExecutionResult:
        if not isinstance(config, MacroConditionsConfig):
            raise TypeError("expected MacroConditionsConfig")
        sahm_config = SAHM_PUBLISHED

        labour_period = date.fromisoformat(config.labour_evaluation_period)
        sloos_period = date.fromisoformat(config.sloos_evaluation_period)
        census_period = date.fromisoformat(config.census_evaluation_period)

        sahm_method = SahmAnalyticalMethod()
        sahm_context = MethodContext(
            inputs_by_dataset=context.inputs_by_dataset,
            evaluation_period=labour_period,
            analysis_mode=context.analysis_mode,
            primary_dataset_id=LABOUR_DATASET_ID,
        )
        sahm_result = sahm_method.run(sahm_context, sahm_config)

        sloos_method = SloosCilMethod()
        sloos_context = MethodContext(
            inputs_by_dataset=context.inputs_by_dataset,
            evaluation_period=sloos_period,
            analysis_mode=context.analysis_mode,
            primary_dataset_id=SLOOS_DATASET_ID,
        )
        sloos_result = sloos_method.run(
            sloos_context,
            SloosCilConfig(config_id="sloos_panel_embed", label="Embedded SLOOS panel"),
        )

        census_method = CensusAdvOrdersMethod()
        census_context = MethodContext(
            inputs_by_dataset=context.inputs_by_dataset,
            evaluation_period=census_period,
            analysis_mode=context.analysis_mode,
            primary_dataset_id=CENSUS_DATASET_ID,
            all_vintages_by_dataset=context.all_vintages_by_dataset,
        )
        census_result = census_method.run(
            census_context,
            CensusAdvOrdersConfig(config_id="census_panel_embed", label="Embedded Census panel"),
        )

        sufficiency = (
            "sufficient"
            if all(
                result.sufficiency == "sufficient"
                for result in (sahm_result, sloos_result, census_result)
            )
            else "insufficient"
        )
        observation_ids = tuple(
            sorted(
                set(sahm_result.observation_ids)
                | set(sloos_result.observation_ids)
                | set(census_result.observation_ids),
            ),
        )
        calculation = {
            "labour": {
                "method_id": sahm_method.method_id,
                "evaluation_period": config.labour_evaluation_period,
                "result": sahm_result.calculation,
                "sufficiency": sahm_result.sufficiency,
            },
            "business_credit": {
                "method_id": SLOOS_CIL_METHOD_ID,
                "evaluation_period": config.sloos_evaluation_period,
                "result": sloos_result.calculation,
                "sufficiency": sloos_result.sufficiency,
            },
            "manufacturing_demand": {
                "method_id": CENSUS_ADV_ORDERS_METHOD_ID,
                "evaluation_period": config.census_evaluation_period,
                "result": census_result.calculation,
                "sufficiency": census_result.sufficiency,
            },
            "near_term_forward_spread": {
                "status": "blocked",
                "reason": (
                    "Near-term forward spread implementation is blocked pending exact formula "
                    "and source-rights resolution. No conventional yield spread was substituted."
                ),
            },
        }
        limitations = (
            "Combined descriptive panel only; components retain their own evidence limits.",
            "Not a validated earnings or ETF-return predictor; no ETF allocation output.",
            "Near-term forward spread slot is intentionally blocked.",
        )
        narrative = _combined_narrative(sahm_result, sloos_result, census_result)
        return MethodExecutionResult(
            sufficiency=sufficiency,
            calculation=calculation,
            observation_ids=observation_ids,
            assumptions=(
                "Labour via published Sahm rule; credit via SLOOS C&I standards; "
                "manufacturing via Census advance durable goods new orders.",
                config.label,
            ),
            limitations=limitations,
            missing_reason=(
                None if sufficiency == "sufficient" else "one or more panels insufficient"
            ),
            statistical_interpretation=(
                "Joint read of labour deterioration, bank credit standards "
                "and advance factory orders. "
                "Each line of evidence has distinct revision and availability limits."
            ),
            causal_hypothesis="No unified causal model is asserted across panels.",
            investment_implication="no_action",
            narrative=narrative,
        )


def _combined_narrative(*results: MethodExecutionResult) -> str:
    parts = [result.narrative for result in results if result.narrative]
    blocked = (
        "Near-term forward spread: blocked (no substitute spread used). "
    )
    return " ".join(parts) + " " + blocked
