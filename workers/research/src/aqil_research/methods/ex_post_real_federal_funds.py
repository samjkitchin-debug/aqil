"""Ex-post real federal funds rate from stored monthly levels.

Predeclared identity
---------------------
In month t the ex-post real federal funds rate is

    fed.h15.RIFSPFF_N.M in month t
    minus the realised 12-month percent change in bls.cu.CUSR0000SA0
    from month t-12 to month t.

Inflation transformation: percent change, not a log change,

    (index_t / index_t_minus_12 - 1) * 100.

The percent change uses those two CPI-U endpoints only. A missing month
between the endpoints is not interpolated and is not required. The funds
rate and the inflation rate are both in percent, so the difference is in
percentage points. Both displayed rates are rounded half up to four decimal
places, and the real rate is the rounded difference of those rounded rates.

The twelve months are trailing and end in the same month as the funds rate.
This is not inflation over the twelve months after t. It is not expected
inflation, so it is not an ex-ante real rate. It is not a Taylor rule and
it is not an output gap. No policy rate is prescribed.

Vintage: ``latest_revised`` only. This is not a real-time claim.
Persistence: this identity does not estimate an autoregression. It does not
report an Andrews–Chen median-unbiased estimator. The CPI-U autoregression
is the method that reports the ordinary least squares sum of autoregressive
coefficients.
Forecast qualification: none. No historical-mean comparison is computed.
Publication: ``publication_allowed`` is false.

Minimum history enforced here: one aligned month, which needs the funds rate
in month t and CPI-U levels in month t and month t-12.
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
from aqil_research.methods.parameters import MethodParameterDocument
from aqil_research.methods.prices_and_policy import (
    CPI_DATASET_ID,
    CPI_UNIT,
    FED_FUNDS_DATASET_ID,
    RATE_UNIT,
)
from aqil_research.methods.protocol import (
    MethodContext,
    MethodDependency,
    MethodExecutionResult,
    bind_dependency,
)

EX_POST_REAL_FEDERAL_FUNDS_RATE = "EX_POST_REAL_FEDERAL_FUNDS_RATE"
METHOD_VERSION = "1.0.0"
PUBLICATION_ALLOWED = False

HORIZON_MONTHS = 12
RATE_QUANTUM = Decimal("0.0001")
INFLATION_TRANSFORMATION = "twelve_month_percent_change"
INFLATION_FORMULA = "(index_t / index_t_minus_12 - 1) * 100"
ALIGNMENT = "trailing_same_month"

QUALIFICATION_STATEMENT = (
    "Not empirically qualified as a forecast. "
    "No predeclared historical-mean comparison was computed."
)
PERSISTENCE_NOTE = (
    "This identity does not estimate an autoregression. Inflation persistence, "
    "when estimated, is the ordinary least squares sum of autoregressive "
    "coefficients on the monthly log change of CPI-U. The Andrews–Chen "
    "median-unbiased estimator is not used."
)
IDENTITY = (
    "The ex-post real federal funds rate in month t is the federal funds rate "
    "in month t minus realised CPI-U inflation from month t-12 to month t. "
    f"Inflation is the percent change {INFLATION_FORMULA}. "
    "It is not a log change. The horizon is trailing and ends in the same month "
    "as the funds rate."
)

PUBLISHED_CONFIG = {
    "config_id": "ex-post-real-federal-funds-rate-v1",
    "label": "Ex-post real federal funds rate, trailing 12-month CPI-U percent change",
}


class ExPostRealFederalFundsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    config_id: str = Field(min_length=1)
    label: str = Field(min_length=1)


def implementation_hash() -> str:
    payload = "|".join(
        (
            EX_POST_REAL_FEDERAL_FUNDS_RATE,
            METHOD_VERSION,
            f"horizon-{HORIZON_MONTHS}",
            INFLATION_TRANSFORMATION,
            INFLATION_FORMULA,
            ALIGNMENT,
            "percent-change-not-log-change",
            "endpoints-only",
            "not-taylor-rule",
            "not-ex-ante",
            "no-output-gap",
            "no-autoregression",
            "not-andrews-chen-median-unbiased",
            "no-historical-mean-comparison",
            "latest-revised",
            "quantum-0.0001-half-up",
        ),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def add_months(anchor: date, delta: int) -> date:
    year = anchor.year + (anchor.month - 1 + delta) // 12
    month = (anchor.month - 1 + delta) % 12 + 1
    return date(year, month, 1)


def twelve_month_percent_change(later: Decimal, earlier: Decimal) -> Decimal:
    """Percent change between two CPI-U levels. Not a log change."""
    if earlier <= 0 or later <= 0:
        raise ValueError("CPI-U levels must be positive")
    return ((later / earlier) - Decimal(1)) * Decimal(100)


def quantize_rate(value: Decimal) -> Decimal:
    return value.quantize(RATE_QUANTUM, rounding=ROUND_HALF_UP)


def ex_post_real_rate(funds_percent: Decimal, inflation_percent: Decimal) -> Decimal:
    """Percentage points: rounded funds rate minus rounded percent-change inflation."""
    return quantize_rate(quantize_rate(funds_percent) - quantize_rate(inflation_percent))


class ExPostRealFederalFundsRateMethod:
    """Trailing ex-post real federal funds rate.

    Registration, inside ``default_method_registry``::

        registry.register(ExPostRealFederalFundsRateMethod())
    """

    method_id = EX_POST_REAL_FEDERAL_FUNDS_RATE
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
                "1 aligned month: a federal funds rate and CPI-U levels in that "
                "month and 12 months earlier"
            ),
            parameter_policy="none",
            new_observation_requires_recalculation=True,
            refit_is_different_command=False,
        )

    def accepted_config_payload(self) -> dict[str, object]:
        return dict(PUBLISHED_CONFIG)

    def parse_config(self, payload: dict[str, object]) -> ExPostRealFederalFundsConfig:
        return ExPostRealFederalFundsConfig.model_validate(payload)

    def config_hash(self, config: BaseModel) -> str:
        if not isinstance(config, ExPostRealFederalFundsConfig):
            raise TypeError("expected ExPostRealFederalFundsConfig")
        return MethodParameterDocument(
            config_id=config.config_id,
            label=config.label,
            scalars={
                "identity": "funds_minus_trailing_twelve_month_cpi_percent_change",
                "inflation_transformation": INFLATION_TRANSFORMATION,
                "horizon_months": str(HORIZON_MONTHS),
                "alignment": ALIGNMENT,
            },
        ).config_hash()

    def run(self, context: MethodContext, config: BaseModel) -> MethodExecutionResult:
        if not isinstance(config, ExPostRealFederalFundsConfig):
            raise TypeError("expected ExPostRealFederalFundsConfig")
        if context.analysis_mode != AnalysisMode.LATEST_REVISED:
            return _insufficient(
                "These levels are dated on latest_revised observations. "
                "A point-in-time request was not dated.",
            )
        funds = _eligible_rates(
            context.inputs_by_dataset.get(FED_FUNDS_DATASET_ID, {}),
            dataset_id=FED_FUNDS_DATASET_ID,
            unit=RATE_UNIT,
            seasonal_adjustment=SeasonalAdjustment.UNKNOWN,
            through=context.evaluation_period,
        )
        cpi = _eligible_rates(
            context.inputs_by_dataset.get(CPI_DATASET_ID, {}),
            dataset_id=CPI_DATASET_ID,
            unit=CPI_UNIT,
            seasonal_adjustment=SeasonalAdjustment.SEASONALLY_ADJUSTED,
            through=context.evaluation_period,
        )
        months = _aligned_months(funds, cpi)
        if not months:
            return _insufficient(
                "No month had a federal funds rate and CPI-U levels both in that "
                "month and 12 months earlier.",
            )
        calculation = _calculation(months)
        observation_ids = _observation_ids(months)
        latest = months[-1]
        return MethodExecutionResult(
            sufficiency="sufficient",
            calculation=calculation,
            observation_ids=observation_ids,
            assumptions=_assumptions(),
            limitations=_limitations(),
            missing_reason=None,
            statistical_interpretation=_interpretation(latest),
            causal_hypothesis="none",
            investment_implication="no_action",
            narrative=_narrative(latest),
        )


def _aligned_months(
    funds: dict[date, EconomicObservation],
    cpi: dict[date, EconomicObservation],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for period in sorted(funds):
        comparison = add_months(period, -HORIZON_MONTHS)
        funds_row = funds.get(period)
        later = cpi.get(period)
        earlier = cpi.get(comparison)
        if funds_row is None or later is None or earlier is None:
            continue
        inflation = twelve_month_percent_change(later.decimal_value(), earlier.decimal_value())
        funds_rate = funds_row.decimal_value()
        real = ex_post_real_rate(funds_rate, inflation)
        rows.append(
            {
                "period": period,
                "funds": funds_row,
                "later": later,
                "earlier": earlier,
                "funds_text": _text(funds_rate),
                "inflation_text": _text(inflation),
                "real_text": _text(real),
            },
        )
    return rows


def _calculation(months: list[dict[str, object]]) -> dict[str, object]:
    latest = months[-1]
    first = months[0]
    payload_months = [
        {
            "period": row["period"].isoformat(),
            "federal_funds_rate_percent": row["funds_text"],
            "cpi_u_inflation_percent": row["inflation_text"],
            "ex_post_real_rate_percentage_points": row["real_text"],
            "cpi_comparison_period": row["earlier"].period_start.isoformat(),
        }
        for row in months
    ]
    return {
        "sufficient": True,
        "method_id": EX_POST_REAL_FEDERAL_FUNDS_RATE,
        "publication_allowed": PUBLICATION_ALLOWED,
        "real_time_claim": False,
        "product_forecast": False,
        "empirically_qualified_as_forecast": False,
        "qualification_statement": QUALIFICATION_STATEMENT,
        "input_vintage": "latest_revised",
        "funds_dataset_id": FED_FUNDS_DATASET_ID,
        "cpi_dataset_id": CPI_DATASET_ID,
        "horizon_months": HORIZON_MONTHS,
        "inflation_transformation": INFLATION_TRANSFORMATION,
        "inflation_formula": INFLATION_FORMULA,
        "monthly_log_change_used": False,
        "alignment": ALIGNMENT,
        "identity": IDENTITY,
        "not_ex_ante": True,
        "not_taylor_rule": True,
        "output_gap_estimated": False,
        "policy_prescription": "none",
        "persistence_estimated": False,
        "andrews_chen_median_unbiased": False,
        "persistence_note": PERSISTENCE_NOTE,
        "sample_start": first["period"].isoformat(),
        "sample_end": latest["period"].isoformat(),
        "aligned_month_count": len(months),
        "latest_period": latest["period"].isoformat(),
        "latest_federal_funds_rate_percent": latest["funds_text"],
        "latest_cpi_u_inflation_percent": latest["inflation_text"],
        "latest_ex_post_real_rate_percentage_points": latest["real_text"],
        "months": payload_months,
    }


def _text(value: Decimal) -> str:
    return str(quantize_rate(value))


def _observation_ids(months: list[dict[str, object]]) -> tuple[str, ...]:
    seen: list[str] = []
    for row in months:
        for key in ("earlier", "later", "funds"):
            observation_id = row[key].observation_id
            if observation_id not in seen:
                seen.append(observation_id)
    return tuple(seen)


def _eligible_rates(
    series: dict[date, EconomicObservation],
    *,
    dataset_id: str,
    unit: str,
    seasonal_adjustment: SeasonalAdjustment,
    through: date,
) -> dict[date, EconomicObservation]:
    selected: dict[date, EconomicObservation] = {}
    for period, row in series.items():
        if period > through or row.period_start != period or row.period_start.day != 1:
            continue
        if row.dataset_id != dataset_id:
            continue
        if row.series_provenance != SeriesProvenance.LATEST_REVISED:
            continue
        if row.quality_status != QualityStatus.OBSERVED:
            continue
        if row.frequency != Frequency.MONTHLY:
            continue
        if row.unit != unit or row.seasonal_adjustment != seasonal_adjustment:
            continue
        selected[period] = row
    return selected


def _assumptions() -> tuple[str, ...]:
    return (
        IDENTITY,
        "Inputs are stored latest-revised monthly observations, not a real-time vintage.",
        (
            "The CPI-U percent change uses the two endpoints only. "
            "Gaps between them are not interpolated."
        ),
        "The federal funds rate is a level in percent per year. Seasonal adjustment is unknown.",
        "CPI-U is the seasonally adjusted index 1982-84=100.",
        PERSISTENCE_NOTE,
        QUALIFICATION_STATEMENT,
        "No output gap is estimated and no policy rate is prescribed.",
    )


def _limitations() -> tuple[str, ...]:
    return (
        "Publication allowed is false.",
        "The reading uses today's revised files and is not a real-time claim.",
        QUALIFICATION_STATEMENT,
        "This is not a Taylor rule, not an ex-ante real rate, and not an output gap.",
        "Trailing twelve-month inflation is not inflation over the following twelve months.",
        (
            "The inflation measure is a percent change, not the monthly log change "
            "used by the CPI-U autoregression."
        ),
        PERSISTENCE_NOTE,
    )


def _interpretation(latest: dict[str, object]) -> str:
    period = latest["period"].isoformat()
    return (
        f"In {period} the ex-post real federal funds rate is "
        f"{latest['real_text']} percentage points: "
        f"a federal funds rate of {latest['funds_text']} percent minus "
        f"trailing 12-month CPI-U inflation of {latest['inflation_text']} percent. "
        f"{IDENTITY} {PERSISTENCE_NOTE} {QUALIFICATION_STATEMENT}"
    )


def _narrative(latest: dict[str, object]) -> str:
    period = latest["period"].isoformat()
    return (
        f"Ex-post real federal funds rate in {period}: {latest['real_text']} percentage points. "
        "The inflation measure is the trailing 12-month percent change in CPI-U, not a log change. "
        "This is not a Taylor rule and not an ex-ante rate. "
        f"{QUALIFICATION_STATEMENT} Publication allowed is false."
    )


def _insufficient(reason: str) -> MethodExecutionResult:
    return MethodExecutionResult(
        sufficiency="insufficient",
        calculation={
            "method_id": EX_POST_REAL_FEDERAL_FUNDS_RATE,
            "publication_allowed": PUBLICATION_ALLOWED,
            "real_time_claim": False,
            "product_forecast": False,
            "empirically_qualified_as_forecast": False,
            "qualification_statement": QUALIFICATION_STATEMENT,
            "input_vintage": "latest_revised",
            "funds_dataset_id": FED_FUNDS_DATASET_ID,
            "cpi_dataset_id": CPI_DATASET_ID,
            "horizon_months": HORIZON_MONTHS,
            "inflation_transformation": INFLATION_TRANSFORMATION,
            "monthly_log_change_used": False,
            "not_ex_ante": True,
            "not_taylor_rule": True,
            "output_gap_estimated": False,
            "persistence_estimated": False,
            "andrews_chen_median_unbiased": False,
        },
        observation_ids=(),
        assumptions=_assumptions(),
        limitations=_limitations(),
        missing_reason=reason,
        statistical_interpretation="The ex-post real federal funds rate was not computed.",
        causal_hypothesis="none",
        investment_implication="insufficient_evidence",
        narrative=f"Ex-post real federal funds rate incomplete. Reason: {reason}",
    )
