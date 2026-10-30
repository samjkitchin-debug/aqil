"""Ex-post real federal funds rate. Not a Taylor rule.

The nominal rate is fed.h15.RIFSPFF_N.M, in per cent per year. CPI inflation is
the twelve-month percent change in bls.cu.CUSR0000SA0, using the two endpoints
only. The real rate at month t subtracts inflation realised after t:

    pi_{t,t+12} = 100 * (P_{t+12} / P_t - 1)
    r_t = i_t - pi_{t,t+12}

No output gap, inflation target, or recommended policy rate is calculated.
Parameter policy is none. Refit is rejected. publication_allowed stays false.
The reading is retrospective on latest_revised observations. It is not a
forecast, and it is not empirically qualified.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
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
from aqil_research.methods.parameters import MethodParameterDocument
from aqil_research.methods.protocol import (
    MethodContext,
    MethodDependency,
    MethodExecutionResult,
    bind_dependency,
)

EX_POST_REAL_FUNDS_RATE = "EX_POST_REAL_FUNDS_RATE"
METHOD_VERSION = "0.1.0"
PUBLICATION_ALLOWED = False

FED_FUNDS_DATASET_ID = "fed.h15.RIFSPFF_N.M"
CPI_DATASET_ID = "bls.cu.CUSR0000SA0"
CPI_UNIT = "1982-84=100"
RATE_UNIT = "percent_per_year"

HORIZON_MONTHS = 12
INFLATION_EQUATION = "pi_{t,t+12} = 100 * (P_{t+12} / P_t - 1)"
REAL_RATE_EQUATION = "r_t = i_t - 100 * (P_{t+12} / P_t - 1)"
CHANGE_QUANTUM = Decimal("0.0001")

NOT_A_TAYLOR_RULE = "This is not a Taylor rule."
NOT_A_FORECAST = "It is not a qualified forecast and it is not a product forecast."
NO_POLICY_RULE = "No output gap, inflation target, or recommended policy rate is calculated."
ENDPOINTS_SENTENCE = (
    "CPI-U inflation uses the index at month t and the index twelve months later. "
    "A missing month between those endpoints is not treated as observed and is not interpolated."
)

PUBLISHED_CONFIG = {
    "config_id": "ex-post-real-funds-rate-v1",
    "label": "Ex-post real federal funds rate",
}


@dataclass(frozen=True, slots=True)
class _RealRateWindow:
    end: date
    start: date
    end_row: EconomicObservation
    start_row: EconomicObservation
    funds_row: EconomicObservation
    inflation: Decimal
    real_rate: Decimal


class ExPostRealFundsRateConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    config_id: str = Field(min_length=1)
    label: str = Field(min_length=1)


def implementation_hash() -> str:
    payload = "|".join(
        (
            EX_POST_REAL_FUNDS_RATE,
            METHOD_VERSION,
            INFLATION_EQUATION,
            REAL_RATE_EQUATION,
            f"horizon-{HORIZON_MONTHS}",
            "endpoints-only",
            "no-taylor-rule",
            "no-output-gap",
            "no-inflation-target",
            "no-recommended-policy-rate",
            "parameter-policy-none",
        ),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def ex_post_real_rate(
    funds_percent_per_year: Decimal,
    price_at_t: Decimal,
    price_at_t_plus_horizon: Decimal,
) -> tuple[Decimal, Decimal]:
    """Return subsequent CPI inflation and the ex-post real funds rate.

    Both results are exact decimals, before display rounding.
    """
    if price_at_t == 0:
        raise ValueError("CPI-U at month t is zero, so inflation is undefined")
    inflation = ((price_at_t_plus_horizon / price_at_t) - Decimal(1)) * Decimal(100)
    return inflation, funds_percent_per_year - inflation


class ExPostRealFundsRateMethod:
    """Retrospective ex-post real federal funds rate.

    Registration, for the integrator, inside ``default_method_registry``::

        registry.register(ExPostRealFundsRateMethod())

    Refit is rejected. Parameter policy is none, and ``refit_is_different_command``
    is false.
    """

    method_id = EX_POST_REAL_FUNDS_RATE
    method_version = METHOD_VERSION

    def implementation_hash(self) -> str:
        return implementation_hash()

    def required_dataset_ids(self) -> tuple[str, ...]:
        return (FED_FUNDS_DATASET_ID, CPI_DATASET_ID)

    def dependency(self) -> MethodDependency:
        return bind_dependency(
            self.required_dataset_ids(),
            frequency=("monthly",),
            minimum_history=(
                "a federal funds rate and a positive CPI-U index on month t, "
                f"plus the CPI-U index {HORIZON_MONTHS} months later, "
                "with that later month on or before the evaluation period"
            ),
            parameter_policy="none",
            depends_on_method_ids=(),
            new_observation_requires_recalculation=True,
            refit_is_different_command=False,
        )

    def accepted_config_payload(self) -> dict[str, object]:
        return dict(PUBLISHED_CONFIG)

    def parse_config(self, payload: dict[str, object]) -> ExPostRealFundsRateConfig:
        return ExPostRealFundsRateConfig.model_validate(payload)

    def config_hash(self, config: BaseModel) -> str:
        if not isinstance(config, ExPostRealFundsRateConfig):
            raise TypeError("expected ExPostRealFundsRateConfig")
        return MethodParameterDocument(
            config_id=config.config_id,
            label=config.label,
            scalars={
                "equation": REAL_RATE_EQUATION,
                "horizon_months": str(HORIZON_MONTHS),
                "parameter_policy": "none",
                "taylor_rule": "false",
            },
        ).config_hash()

    def run(self, context: MethodContext, config: BaseModel) -> MethodExecutionResult:
        if not isinstance(config, ExPostRealFundsRateConfig):
            raise TypeError("expected ExPostRealFundsRateConfig")
        if context.analysis_mode != AnalysisMode.LATEST_REVISED:
            return _insufficient(
                "These series are dated on latest_revised observations. "
                "A point-in-time request was not dated.",
            )
        cpi = _eligible_cpi(
            context.inputs_by_dataset.get(CPI_DATASET_ID, {}),
            context.evaluation_period,
        )
        funds = _eligible_funds(
            context.inputs_by_dataset.get(FED_FUNDS_DATASET_ID, {}),
            context.evaluation_period,
        )
        if not cpi:
            return _insufficient("No eligible latest-revised CPI-U level was available.")
        if not funds:
            return _insufficient("No eligible latest-revised federal funds rate was available.")
        windows = _windows(cpi, funds, context.evaluation_period)
        if not windows:
            return _insufficient(
                "No month has a federal funds rate, a positive CPI-U index, and the "
                f"CPI-U index {HORIZON_MONTHS} months later on or before the evaluation period.",
            )
        latest = max(windows, key=lambda window: window.end)
        start = latest.start
        end_row = latest.end_row
        start_row = latest.start_row
        funds_row = latest.funds_row
        inflation = latest.inflation
        real_rate = latest.real_rate
        calculation = {
            **_identity_flags(),
            "sufficient": True,
            "evaluation_period": context.evaluation_period.isoformat(),
            "funds_month": start.isoformat(),
            "inflation_end_month": end_row.period_start.isoformat(),
            "horizon_months": HORIZON_MONTHS,
            "inflation_equation": INFLATION_EQUATION,
            "equation": REAL_RATE_EQUATION,
            "alignment": "federal funds rate at month t minus CPI-U inflation from t to t+12",
            "endpoints_only": True,
            "federal_funds_dataset_id": FED_FUNDS_DATASET_ID,
            "cpi_dataset_id": CPI_DATASET_ID,
            "federal_funds_percent_per_year": funds_row.raw_value,
            "cpi_index_at_t": start_row.raw_value,
            "cpi_index_at_t_plus_horizon": end_row.raw_value,
            "cpi_unit": CPI_UNIT,
            "inflation_percent": _quantize(inflation),
            "real_funds_rate_percent_per_year": _quantize(real_rate),
            "computable_month_count": len(windows),
            "twelve_month_price_rank": False,
        }
        observation_ids = tuple(
            sorted(
                {
                    funds_row.observation_id,
                    start_row.observation_id,
                    end_row.observation_id,
                },
            ),
        )
        return MethodExecutionResult(
            sufficiency="sufficient",
            calculation=calculation,
            observation_ids=observation_ids,
            assumptions=_assumptions(),
            limitations=_limitations(),
            missing_reason=None,
            statistical_interpretation=_interpretation(),
            causal_hypothesis="none",
            investment_implication="no_action",
            narrative=_narrative(calculation),
        )


def _eligible_cpi(
    series: dict[date, EconomicObservation],
    evaluation_period: date,
) -> dict[date, EconomicObservation]:
    selected: dict[date, EconomicObservation] = {}
    for period, row in series.items():
        if period > evaluation_period or not _cpi_row_is_eligible(period, row):
            continue
        if row.decimal_value() <= 0:
            continue
        selected[period] = row
    return selected


def _eligible_funds(
    series: dict[date, EconomicObservation],
    evaluation_period: date,
) -> dict[date, EconomicObservation]:
    selected: dict[date, EconomicObservation] = {}
    for period, row in series.items():
        if period > evaluation_period or not _funds_row_is_eligible(period, row):
            continue
        selected[period] = row
    return selected


def _cpi_row_is_eligible(period: date, row: EconomicObservation) -> bool:
    return (
        period.day == 1
        and row.period_start == period
        and row.dataset_id == CPI_DATASET_ID
        and row.series_provenance == SeriesProvenance.LATEST_REVISED
        and row.quality_status == QualityStatus.OBSERVED
        and row.frequency == Frequency.MONTHLY
        and row.seasonal_adjustment == SeasonalAdjustment.SEASONALLY_ADJUSTED
        and row.unit == CPI_UNIT
    )


def _funds_row_is_eligible(period: date, row: EconomicObservation) -> bool:
    return (
        period.day == 1
        and row.period_start == period
        and row.dataset_id == FED_FUNDS_DATASET_ID
        and row.series_provenance == SeriesProvenance.LATEST_REVISED
        and row.quality_status == QualityStatus.OBSERVED
        and row.frequency == Frequency.MONTHLY
        and row.seasonal_adjustment == SeasonalAdjustment.UNKNOWN
        and row.unit == RATE_UNIT
    )


def _windows(
    cpi: dict[date, EconomicObservation],
    funds: dict[date, EconomicObservation],
    evaluation_period: date,
) -> list[_RealRateWindow]:
    found: list[_RealRateWindow] = []
    for end, end_row in cpi.items():
        if end > evaluation_period:
            continue
        start = _add_months(end, -HORIZON_MONTHS)
        start_row = cpi.get(start)
        funds_row = funds.get(start)
        if start_row is None or funds_row is None or start > evaluation_period:
            continue
        inflation, real_rate = ex_post_real_rate(
            funds_row.decimal_value(),
            start_row.decimal_value(),
            end_row.decimal_value(),
        )
        found.append(
            _RealRateWindow(
                end=end,
                start=start,
                end_row=end_row,
                start_row=start_row,
                funds_row=funds_row,
                inflation=inflation,
                real_rate=real_rate,
            ),
        )
    return found


def _add_months(anchor: date, delta: int) -> date:
    year = anchor.year + (anchor.month - 1 + delta) // 12
    month = (anchor.month - 1 + delta) % 12 + 1
    return date(year, month, 1)


def _quantize(value: Decimal) -> str:
    return str(value.quantize(CHANGE_QUANTUM, rounding=ROUND_HALF_UP))


def _assumptions() -> tuple[str, ...]:
    return (
        "Inputs are stored latest-revised monthly observations.",
        REAL_RATE_EQUATION,
        INFLATION_EQUATION,
        f"The horizon is {HORIZON_MONTHS} months, and inflation is subsequent to month t.",
        ENDPOINTS_SENTENCE,
        (
            "The federal funds rate is the stored level in per cent per year. "
            "It is not annualised again."
        ),
        NOT_A_TAYLOR_RULE,
        NO_POLICY_RULE,
        "Parameter policy is none. Refit is rejected.",
        (
            "The reported month is the latest t whose inflation endpoint is on or "
            "before the evaluation period."
        ),
    )


def _limitations() -> tuple[str, ...]:
    return (
        "Publication allowed is false.",
        NOT_A_TAYLOR_RULE,
        NO_POLICY_RULE,
        NOT_A_FORECAST,
        ENDPOINTS_SENTENCE,
        (
            "The real rate at month t uses the CPI-U index twelve months later. "
            "It was not known at month t. This file is latest_revised, so the "
            "reading is retrospective."
        ),
        "Refit is rejected because the parameter policy is none.",
        "This subtraction is not the twelve-month CPI-U price rank.",
    )


def _interpretation() -> str:
    return (
        f"Ex-post real federal funds rate, {REAL_RATE_EQUATION}. "
        f"Inflation is {INFLATION_EQUATION}. "
        f"{NOT_A_TAYLOR_RULE} {NO_POLICY_RULE} {NOT_A_FORECAST}"
    )


def _narrative(calculation: dict[str, object]) -> str:
    return (
        f"Ex-post real federal funds rate for {calculation['funds_month']} is "
        f"{calculation['real_funds_rate_percent_per_year']} per cent per year. "
        f"The federal funds rate on that month was "
        f"{calculation['federal_funds_percent_per_year']} per cent per year. "
        f"CPI-U inflation from {calculation['funds_month']} to "
        f"{calculation['inflation_end_month']} is {calculation['inflation_percent']} per cent. "
        f"The horizon is twelve months. {NOT_A_TAYLOR_RULE} {NO_POLICY_RULE} {NOT_A_FORECAST} "
        "The calculation is retrospective and uses latest_revised observations. "
        "Publication allowed is false."
    )


def _identity_flags() -> dict[str, object]:
    return {
        "method_id": EX_POST_REAL_FUNDS_RATE,
        "publication_allowed": PUBLICATION_ALLOWED,
        "product_forecast": False,
        "taylor_rule": False,
        "output_gap_used": False,
        "inflation_target_used": False,
        "recommended_policy_rate_computed": False,
        "empirically_qualified_as_forecast": False,
        "retrospective": True,
        "input_vintage": "latest_revised",
        "parameter_policy": "none",
        "refit_rejected": True,
    }


def _insufficient(reason: str) -> MethodExecutionResult:
    return MethodExecutionResult(
        sufficiency="insufficient",
        calculation={
            **_identity_flags(),
            "horizon_months": HORIZON_MONTHS,
            "equation": REAL_RATE_EQUATION,
            "twelve_month_price_rank": False,
        },
        observation_ids=(),
        assumptions=(REAL_RATE_EQUATION, NOT_A_TAYLOR_RULE, NO_POLICY_RULE),
        limitations=_limitations(),
        missing_reason=reason,
        statistical_interpretation="The ex-post real federal funds rate was not computed.",
        causal_hypothesis="none",
        investment_implication="insufficient_evidence",
        narrative=(
            f"Ex-post real federal funds rate incomplete. Reason: {reason} "
            f"{NOT_A_TAYLOR_RULE} {NO_POLICY_RULE} {NOT_A_FORECAST}"
        ),
    )
