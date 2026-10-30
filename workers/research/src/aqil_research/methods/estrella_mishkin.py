"""10-year minus 3-month Treasury spread.

Estrella and Mishkin, Current Issues in Economics and Finance, June 1996
(Federal Reserve Bank of New York), state that the spread between the ten-year
Treasury note and the three-month Treasury bill predicts recessions two to six
quarters ahead. One model in that article estimates the probability of recession
four quarters ahead from the current spread. The article prints a table of
spreads and probabilities. It does not print the probit coefficients.

This module calculates the latest revised difference between two H.15
investment-basis constant-maturity yields. It does not estimate that probit.
The short rate is ``fed.h15.RIFLGFCM03_N.M``, not the discount-basis
three-month Treasury bill and not the federal funds rate.
"""

from __future__ import annotations

import hashlib
from datetime import date
from decimal import InvalidOperation

from pydantic import BaseModel, ConfigDict, Field

from aqil_research.contracts.observation import (
    AnalysisMode,
    EconomicObservation,
    Frequency,
    SeriesProvenance,
)
from aqil_research.methods.parameters import MethodParameterDocument
from aqil_research.methods.protocol import (
    MethodContext,
    MethodDependency,
    MethodExecutionResult,
    bind_dependency,
)

METHOD_ID = "ESTRELLA_MISHKIN_TERM_SPREAD"
METHOD_VERSION = "1.0.0"
PUBLICATION_ALLOWED = False

TEN_YEAR_DATASET_ID = "fed.h15.RIFLGFCY10_N.M"
THREE_MONTH_DATASET_ID = "fed.h15.RIFLGFCM03_N.M"
FEDERAL_FUNDS_DATASET_ID = "fed.h15.RIFSPFF_N.M"

PAPER_CITATION = (
    "Estrella and Mishkin, Current Issues in Economics and Finance, June 1996, "
    "Federal Reserve Bank of New York"
)
PAPER_STATED_HORIZON = "two to six quarters ahead"
PAPER_PROBIT_EXAMPLE = "four quarters ahead"

_NOT_A_PROBABILITY = (
    "This is the latest revised yield spread. It is not a real-time recession probability."
)
_COEFFICIENTS = (
    "No coefficients were estimated. The June 1996 Current Issues article "
    "does not print the probit coefficients."
)


class EstrellaMishkinConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    config_id: str = Field(min_length=1)
    label: str = Field(min_length=1)


ESTRELLA_MISHKIN_PUBLISHED = {
    "config_id": "estrella_mishkin_spread_v1",
    "label": "10-year minus 3-month constant-maturity spread",
}


class EstrellaMishkinSpreadMethod:
    """AnalyticalMethod for the latest revised term spread. Not registered."""

    method_id = METHOD_ID
    method_version = METHOD_VERSION

    def implementation_hash(self) -> str:
        payload = f"{self.method_id}:{self.method_version}:{PAPER_STATED_HORIZON}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def required_dataset_ids(self) -> tuple[str, ...]:
        return (TEN_YEAR_DATASET_ID, THREE_MONTH_DATASET_ID)

    def dependency(self) -> MethodDependency:
        return bind_dependency(
            self.required_dataset_ids(),
            frequency=("monthly",),
            minimum_history="the evaluation month on both constant-maturity yields",
            parameter_policy="none",
            depends_on_method_ids=(),
            new_observation_requires_recalculation=True,
            refit_is_different_command=False,
        )

    def accepted_config_payload(self) -> dict[str, object]:
        return dict(ESTRELLA_MISHKIN_PUBLISHED)

    def parse_config(self, payload: dict[str, object]) -> EstrellaMishkinConfig:
        return EstrellaMishkinConfig.model_validate(payload)

    def config_hash(self, config: BaseModel) -> str:
        if not isinstance(config, EstrellaMishkinConfig):
            raise TypeError("expected EstrellaMishkinConfig")
        return MethodParameterDocument(
            config_id=config.config_id,
            label=config.label,
            scalars={},
        ).config_hash()

    def run(self, context: MethodContext, config: BaseModel) -> MethodExecutionResult:
        if not isinstance(config, EstrellaMishkinConfig):
            raise TypeError("expected EstrellaMishkinConfig")
        if context.analysis_mode != AnalysisMode.LATEST_REVISED:
            return _insufficient(
                "latest_revised is required. This spread is not a real-time probability.",
            )
        period = context.evaluation_period
        ten_year = _eligible(
            context.inputs_by_dataset.get(TEN_YEAR_DATASET_ID, {}),
            TEN_YEAR_DATASET_ID,
            period,
        )
        three_month = _eligible(
            context.inputs_by_dataset.get(THREE_MONTH_DATASET_ID, {}),
            THREE_MONTH_DATASET_ID,
            period,
        )
        if ten_year is None or three_month is None:
            return _insufficient(
                f"missing constant-maturity yield for {period.isoformat()}",
            )
        spread = ten_year.decimal_value() - three_month.decimal_value()
        return MethodExecutionResult(
            sufficiency="sufficient",
            calculation={
                "method_id": METHOD_ID,
                "publication_allowed": PUBLICATION_ALLOWED,
                "input_vintage": "latest_revised",
                "real_time_probability": False,
                "paper": PAPER_CITATION,
                "paper_stated_horizon": PAPER_STATED_HORIZON,
                "paper_probit_example_horizon": PAPER_PROBIT_EXAMPLE,
                "coefficients_estimated": False,
                "paper_coefficients_reproduced": False,
                "probit_estimated": False,
                "evaluation_period": period.isoformat(),
                "ten_year_dataset_id": TEN_YEAR_DATASET_ID,
                "three_month_dataset_id": THREE_MONTH_DATASET_ID,
                "ten_year_yield": str(ten_year.decimal_value()),
                "three_month_yield": str(three_month.decimal_value()),
                "spread": str(spread),
            },
            observation_ids=tuple(
                sorted((ten_year.observation_id, three_month.observation_id)),
            ),
            assumptions=(
                f"{PAPER_CITATION} states a horizon of {PAPER_STATED_HORIZON}.",
                f"The paper's probit example is {PAPER_PROBIT_EXAMPLE}.",
                "The spread is the 10-year constant-maturity yield minus the "
                "3-month constant-maturity yield, both quoted on an investment basis.",
                "The 3-month series is not the discount-basis Treasury bill.",
                "The federal funds rate is not the short rate.",
            ),
            limitations=(
                "publication_allowed is false.",
                _NOT_A_PROBABILITY,
                _COEFFICIENTS,
            ),
            missing_reason=None,
            statistical_interpretation=(
                f"Latest revised 10-year minus 3-month spread at {period.isoformat()}. "
                f"{_NOT_A_PROBABILITY} {_COEFFICIENTS}"
            ),
            causal_hypothesis="No causal mechanism is established.",
            investment_implication="no_action",
            narrative=(
                f"The 10-year minus 3-month constant-maturity spread at {period.isoformat()} "
                f"is {spread} percentage points. {_NOT_A_PROBABILITY} "
                "publication_allowed is false."
            ),
        )


def _eligible(
    rows: dict[date, EconomicObservation],
    dataset_id: str,
    period: date,
) -> EconomicObservation | None:
    observation = rows.get(period)
    if observation is None:
        return None
    if observation.dataset_id != dataset_id:
        return None
    if observation.dataset_id == FEDERAL_FUNDS_DATASET_ID:
        return None
    if observation.series_provenance != SeriesProvenance.LATEST_REVISED:
        return None
    if observation.frequency != Frequency.MONTHLY:
        return None
    try:
        observation.decimal_value()
    except (InvalidOperation, ValueError):
        return None
    return observation


def _insufficient(reason: str) -> MethodExecutionResult:
    return MethodExecutionResult(
        sufficiency="insufficient",
        calculation=None,
        observation_ids=(),
        assumptions=(),
        limitations=(
            "publication_allowed is false.",
            _NOT_A_PROBABILITY,
            _COEFFICIENTS,
        ),
        missing_reason=reason,
        statistical_interpretation="The yield spread was not calculated.",
        causal_hypothesis="No causal mechanism is established.",
        investment_implication="insufficient_evidence",
        narrative=f"Spread incomplete. Reason: {reason}",
    )
