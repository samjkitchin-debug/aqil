"""Census advance durable goods new orders — initial vs revised month-on-month changes."""

from __future__ import annotations

import hashlib
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from pydantic import BaseModel, ConfigDict, Field

from aqil_research.methods.protocol import MethodContext, MethodExecutionResult

CENSUS_ADV_ORDERS_METHOD_ID = "CENSUS_ADV_DURABLE_ORDERS"
CENSUS_ADV_ORDERS_METHOD_VERSION = "1.0.0"
CENSUS_DATASET_ID = "census.m3.adv.MDM.NO"


class CensusAdvOrdersConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    config_id: str = Field(min_length=1)
    label: str = Field(min_length=1)


class CensusAdvOrdersMethod:
    method_id = CENSUS_ADV_ORDERS_METHOD_ID
    method_version = CENSUS_ADV_ORDERS_METHOD_VERSION

    def implementation_hash(self) -> str:
        payload = f"{self.method_id}:{self.method_version}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def required_dataset_ids(self) -> tuple[str, ...]:
        return (CENSUS_DATASET_ID,)

    def vintage_history_dataset_ids(self) -> tuple[str, ...]:
        return (CENSUS_DATASET_ID,)

    def parse_config(self, payload: dict[str, object]) -> CensusAdvOrdersConfig:
        return CensusAdvOrdersConfig.model_validate(payload)

    def config_hash(self, config: BaseModel) -> str:
        if not isinstance(config, CensusAdvOrdersConfig):
            raise TypeError("expected CensusAdvOrdersConfig")
        from aqil_research.methods.parameters import MethodParameterDocument

        return MethodParameterDocument(
            config_id=config.config_id,
            label=config.label,
            scalars={},
        ).config_hash()

    def run(self, context: MethodContext, config: BaseModel) -> MethodExecutionResult:
        if not isinstance(config, CensusAdvOrdersConfig):
            raise TypeError("expected CensusAdvOrdersConfig")
        all_rows = context.all_vintages_by_dataset.get(CENSUS_DATASET_ID)
        if not all_rows:
            all_rows = tuple(context.inputs_by_dataset.get(CENSUS_DATASET_ID, {}).values())
        evaluation = context.evaluation_period
        current_period, prior_period = _month_pair(evaluation)
        current_rows = [obs for obs in all_rows if obs.period_start == current_period]
        if not current_rows:
            return _insufficient(f"missing orders for {current_period.isoformat()}")

        latest_current = max(current_rows, key=lambda row: row.provider_vintage_date)
        prior_rows = [obs for obs in all_rows if obs.period_start == prior_period]
        if not prior_rows:
            return _insufficient(f"missing prior-month orders for {prior_period.isoformat()}")

        initial_prior = min(prior_rows, key=lambda row: row.provider_vintage_date)
        revised_prior = max(prior_rows, key=lambda row: row.provider_vintage_date)

        current_level = Decimal(latest_current.raw_value)
        initial_prior_level = Decimal(initial_prior.raw_value)
        revised_prior_level = Decimal(revised_prior.raw_value)

        initial_mom = _pct_change(current_level, initial_prior_level)
        official_mom = _pct_change(current_level, revised_prior_level)

        cited_ids = tuple(
            sorted(
                {
                    latest_current.observation_id,
                    initial_prior.observation_id,
                    revised_prior.observation_id,
                },
            ),
        )
        calculation = {
            "evaluation_period": evaluation.isoformat(),
            "current_period": current_period.isoformat(),
            "prior_period": prior_period.isoformat(),
            "current_level_millions_usd": str(current_level),
            "prior_initial_estimate_millions_usd": str(initial_prior_level),
            "prior_latest_revised_millions_usd": str(revised_prior_level),
            "initial_estimate_to_initial_estimate_pct_change": str(initial_mom),
            "official_month_on_month_pct_change": str(official_mom),
            "mom_distinction": (
                "initial_estimate_to_initial_estimate uses the first-published prior month; "
                "official_month_on_month uses the latest revised prior month."
            ),
        }
        return MethodExecutionResult(
            sufficiency="sufficient",
            calculation=calculation,
            observation_ids=cited_ids,
            assumptions=(
                "Census advance report MDM new orders, seasonally adjusted, "
                "in millions of dollars.",
                config.label,
            ),
            limitations=_limitations(),
            missing_reason=None,
            statistical_interpretation=(
                "Descriptive manufacturing-demand indicator from the advance M3 release. "
                "Not a validated predictor of corporate earnings, ETF returns, "
                "or allocation changes."
            ),
            causal_hypothesis="No causal mechanism is asserted.",
            investment_implication="no_action",
            narrative=(
                f"Advance durable goods new orders for {current_period.isoformat()}: "
                f"initial-estimate m/m {initial_mom}% versus official m/m {official_mom}% "
                "(prior month revised from "
                f"{initial_prior_level} to {revised_prior_level} millions)."
            ),
        )


def _month_pair(anchor: date) -> tuple[date, date]:
    if anchor.day != 1:
        raise ValueError("evaluation_period must be a month-start date")
    year = anchor.year
    month = anchor.month
    if month == 1:
        prior = date(year - 1, 12, 1)
    else:
        prior = date(year, month - 1, 1)
    return anchor, prior


def _pct_change(current: Decimal, prior: Decimal) -> Decimal:
    if prior == 0:
        raise ValueError("prior level is zero; percent change undefined")
    change = (current - prior) / prior * Decimal("100")
    return change.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _limitations() -> tuple[str, ...]:
    return (
        "Advance estimates are revised in the full M3 release; vintages must be stored separately.",
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
        statistical_interpretation="Insufficient Census advance orders for the evaluation window.",
        causal_hypothesis="Unresolved.",
        investment_implication="insufficient_evidence",
        narrative=reason,
    )
