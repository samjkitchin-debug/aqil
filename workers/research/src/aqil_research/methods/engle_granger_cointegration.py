"""Engle-Granger cointegration of one predeclared pair of log levels.

The pair is industrial production ``fed.g17.IP.B50001.S`` and payroll
employment ``bls.ce.CES0000000001``. Both enter as natural logarithms of the
latest revised levels. Growth rates are not used.

The procedure is the augmented Engle-Granger two-step test:

1. Ordinary least squares of log industrial production on log payroll
   employment and a constant. The constant is a column of ones. This
   normalisation is predeclared. It is not a causal ordering.
2. An augmented Dickey-Fuller test on that residual with no constant and no
   trend. The lag is chosen by AIC up to the Schwert ceiling that
   statsmodels uses when ``maxlag`` is omitted.

The null is no cointegration. Rejection uses the five percent critical value
from ``statsmodels.tsa.adfvalues.mackinnoncrit`` for two series and a constant
(MacKinnon 2010). That is not the Engle and Granger (1987) table, and it is
not the ordinary augmented Dickey-Fuller critical value. A failure to reject
is stored as the result.

The result describes co-movement in revised log levels. It is not a causal
claim and it does not assign a leading indicator. ``publication_allowed``
stays false.
"""

from __future__ import annotations

import hashlib
import math
from collections.abc import Mapping, Sequence
from datetime import date

import numpy as np
from pydantic import BaseModel, ConfigDict, Field
from statsmodels.regression.linear_model import OLS
from statsmodels.tsa.adfvalues import mackinnoncrit, mackinnonp
from statsmodels.tsa.stattools import adfuller

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

ENGLE_GRANGER_COINTEGRATION = "ENGLE_GRANGER_COINTEGRATION"
METHOD_VERSION = "1.0.0"
PUBLICATION_ALLOWED = False

INDUSTRIAL_PRODUCTION_DATASET_ID = "fed.g17.IP.B50001.S"
PAYROLL_DATASET_ID = "bls.ce.CES0000000001"
INDUSTRIAL_PRODUCTION_UNIT = "index_2017_100"
PAYROLL_UNIT = "thousands"
DATASET_IDS = (INDUSTRIAL_PRODUCTION_DATASET_ID, PAYROLL_DATASET_ID)
UNITS = {
    INDUSTRIAL_PRODUCTION_DATASET_ID: INDUSTRIAL_PRODUCTION_UNIT,
    PAYROLL_DATASET_ID: PAYROLL_UNIT,
}
LABELS = {
    INDUSTRIAL_PRODUCTION_DATASET_ID: "Industrial production",
    PAYROLL_DATASET_ID: "Total nonfarm payroll employment",
}

MINIMUM_OVERLAP_MONTHS = 120
SIGNIFICANCE = 0.05
COINTEGRATING_SERIES_COUNT = 2
FIRST_STAGE_TREND = "c"
RESIDUAL_REGRESSION = "n"
CRITICAL_VALUE_SOURCE = (
    "MacKinnon (2010) response surface from statsmodels mackinnoncrit "
    "for two series with a constant. Not the Engle and Granger (1987) table."
)
NO_CAUSAL_CLAIM = "No causal mechanism is established."
NOT_A_LEADING_INDICATOR = "No leading indicator is assigned."

PUBLISHED_CONFIG = {
    "config_id": "engle-granger-cointegration-v1",
    "label": (
        "Engle-Granger cointegration of industrial production and payroll employment log levels"
    ),
}


class EngleGrangerCointegrationConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    config_id: str = Field(min_length=1)
    label: str = Field(min_length=1)


def implementation_hash() -> str:
    payload = "|".join(
        (
            ENGLE_GRANGER_COINTEGRATION,
            METHOD_VERSION,
            "log-levels",
            "ols-with-constant",
            "adf-residual-no-constant-no-trend",
            "aic-schwert-max-lag",
            "mackinnon-2010-n2-constant",
            f"significance-{SIGNIFICANCE}",
            f"minimum-overlap-{MINIMUM_OVERLAP_MONTHS}",
            "not-the-1987-table",
            "single-residual-procedure",
            "no-growth-rates",
        ),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def schwert_max_lag(observation_count: int) -> int:
    """Return the lag ceiling statsmodels uses for an omitted ``maxlag``.

    The formula is ceil(12 * (n / 100) ** 0.25), capped so a residual
    regression with no constant still has degrees of freedom. Greene
    attributes the ceiling to Schwert (1989). ``n`` is the length of the
    cointegrating residual.
    """

    if observation_count < 3:
        raise ValueError("the residual sample is too short for a lag ceiling")
    ceiling = int(math.ceil(12.0 * (observation_count / 100.0) ** 0.25))
    cap = observation_count // 2 - 1
    if cap < 0:
        raise ValueError("the residual sample is too short for a lag ceiling")
    return min(cap, ceiling)


def engle_granger_from_log_levels(
    left: Sequence[float],
    right: Sequence[float],
) -> dict[str, object]:
    """Two-step test. ``left`` is log industrial production.

    The first regression includes a constant. The residual test does not.
    Critical values use MacKinnon (2010) for N=2, not ordinary ADF values.
    """

    y_values = np.asarray(list(left), dtype=np.float64)
    x_values = np.asarray(list(right), dtype=np.float64)
    if y_values.ndim != 1 or x_values.ndim != 1 or y_values.shape != x_values.shape:
        raise ValueError("the two log-level samples must be the same length")
    if y_values.size < MINIMUM_OVERLAP_MONTHS:
        raise ValueError(
            f"the overlap has {y_values.size} months, below {MINIMUM_OVERLAP_MONTHS}",
        )
    if not np.isfinite(y_values).all() or not np.isfinite(x_values).all():
        raise ValueError("log levels must be finite")
    exog = np.column_stack((x_values, np.ones(y_values.shape[0], dtype=np.float64)))
    if not np.all(exog[:, 1] == 1.0):
        raise RuntimeError("the cointegrating regression is missing its constant")
    fitted = OLS(y_values, exog).fit()
    slope = float(fitted.params[0])
    intercept = float(fitted.params[1])
    r_squared = float(fitted.rsquared)
    collinear_limit = 1.0 - 100.0 * math.sqrt(float(np.finfo(np.float64).eps))
    if not math.isfinite(r_squared) or r_squared >= collinear_limit:
        raise ValueError("the cointegrating regression is too collinear to test")
    residual = np.asarray(fitted.resid, dtype=np.float64)
    max_lag = schwert_max_lag(int(residual.size))
    adf_stat, _ordinary_p, used_lag, adf_observations, _ordinary_crit, _ic = adfuller(
        residual,
        maxlag=max_lag,
        regression=RESIDUAL_REGRESSION,
        autolag="aic",
        result_object=False,
    )
    statistic = float(adf_stat)
    if not math.isfinite(statistic):
        raise ValueError("the residual unit-root statistic is not finite")
    sample_size = int(y_values.size)
    critical = mackinnoncrit(
        N=COINTEGRATING_SERIES_COUNT,
        regression=FIRST_STAGE_TREND,
        nobs=sample_size - 1,
    )
    p_value = float(
        mackinnonp(
            statistic,
            regression=FIRST_STAGE_TREND,
            N=COINTEGRATING_SERIES_COUNT,
        ),
    )
    five_percent = float(critical[1])
    if not all(math.isfinite(float(value)) for value in critical) or not math.isfinite(p_value):
        raise ValueError("the MacKinnon critical value is not finite")
    rejects = statistic < five_percent
    return {
        "sufficient": True,
        "method_id": ENGLE_GRANGER_COINTEGRATION,
        "publication_allowed": PUBLICATION_ALLOWED,
        "transformation": "natural_log_levels",
        "growth_rates_used": False,
        "normalisation": ("log industrial production on log payroll employment with a constant"),
        "causal_claim": False,
        "leading_indicator_assigned": False,
        "observation_count": sample_size,
        "first_stage": {
            "estimator": "ordinary_least_squares",
            "constant_included": True,
            "constant_column": "last",
            "slope": _figure(slope),
            "intercept": _figure(intercept),
            "r_squared": _figure(r_squared),
        },
        "second_stage": {
            "test": "augmented_dickey_fuller_on_the_residual",
            "regression": "no_constant_no_trend",
            "lag_rule": "aic",
            "max_lag_rule": "schwert_1989_ceiling_used_by_statsmodels",
            "max_lag": int(max_lag),
            "used_lag": int(used_lag),
            "adf_observation_count": int(adf_observations),
            "statistic": _figure(statistic),
            "p_value": _figure(p_value),
            "critical_values": {
                "1%": _figure(float(critical[0])),
                "5%": _figure(five_percent),
                "10%": _figure(float(critical[2])),
            },
            "critical_value_observations": sample_size - 1,
            "critical_value_source": CRITICAL_VALUE_SOURCE,
            "ordinary_adf_critical_values_used": False,
            "ordinary_adf_p_value_used": False,
        },
        "null_hypothesis": "no_cointegration",
        "significance": SIGNIFICANCE,
        "rejects_no_cointegration_at_five_percent": bool(rejects),
        "statistic": _figure(statistic),
        "critical_value_five_percent": _figure(five_percent),
        "p_value": _figure(p_value),
        "critical_value_source": CRITICAL_VALUE_SOURCE,
    }


def next_month(month_start: date) -> date:
    if month_start.month == 12:
        return date(month_start.year + 1, 1, 1)
    return date(month_start.year, month_start.month + 1, 1)


def longest_contiguous_overlap(
    left: Mapping[date, float],
    right: Mapping[date, float],
) -> tuple[tuple[date, ...], tuple[float, ...], tuple[float, ...], int]:
    """Earliest longest month where both positive levels exist. No interpolation."""

    overlap = sorted(set(left) & set(right))
    chosen = _longest_run(overlap)
    if not chosen:
        return (), (), (), len(overlap)
    left_values = tuple(math.log(left[month]) for month in chosen)
    right_values = tuple(math.log(right[month]) for month in chosen)
    return tuple(chosen), left_values, right_values, len(overlap) - len(chosen)


class EngleGrangerCointegrationMethod:
    """One Engle-Granger test on revised log levels of production and payrolls."""

    method_id = ENGLE_GRANGER_COINTEGRATION
    method_version = METHOD_VERSION

    def implementation_hash(self) -> str:
        return implementation_hash()

    def required_dataset_ids(self) -> tuple[str, ...]:
        return DATASET_IDS

    def dependency(self) -> MethodDependency:
        return bind_dependency(
            self.required_dataset_ids(),
            frequency=("monthly",),
            minimum_history=(
                f"{MINIMUM_OVERLAP_MONTHS} contiguous months of positive "
                "latest-revised levels for both series"
            ),
            parameter_policy="none",
            new_observation_requires_recalculation=True,
            refit_is_different_command=False,
        )

    def accepted_config_payload(self) -> dict[str, object]:
        return dict(PUBLISHED_CONFIG)

    def parse_config(self, payload: dict[str, object]) -> EngleGrangerCointegrationConfig:
        return EngleGrangerCointegrationConfig.model_validate(payload)

    def config_hash(self, config: BaseModel) -> str:
        if not isinstance(config, EngleGrangerCointegrationConfig):
            raise TypeError("expected EngleGrangerCointegrationConfig")
        return MethodParameterDocument(
            config_id=config.config_id,
            label=config.label,
            scalars={
                "transformation": "natural_log_levels",
                "left_hand_side": INDUSTRIAL_PRODUCTION_DATASET_ID,
                "right_hand_side": PAYROLL_DATASET_ID,
                "first_stage": "ols_with_constant",
                "second_stage": "adf_residual_no_constant_no_trend",
                "lag_rule": "aic_schwert",
                "critical_values": "mackinnon_2010_n2_constant",
                "significance": str(SIGNIFICANCE),
            },
        ).config_hash()

    def run(self, context: MethodContext, config: BaseModel) -> MethodExecutionResult:
        if not isinstance(config, EngleGrangerCointegrationConfig):
            raise TypeError("expected EngleGrangerCointegrationConfig")
        if context.analysis_mode != AnalysisMode.LATEST_REVISED:
            return _insufficient(
                "These levels are dated on latest_revised observations. "
                "A point-in-time request was not dated.",
            )
        levels: dict[str, dict[date, float]] = {}
        series_by_dataset: dict[str, Mapping[date, EconomicObservation]] = {}
        for dataset_id in DATASET_IDS:
            series = context.inputs_by_dataset.get(dataset_id)
            if not series:
                return _insufficient(f"No observations were available for {LABELS[dataset_id]}.")
            series_by_dataset[dataset_id] = series
            extracted = _eligible_levels(dataset_id, series)
            if not extracted:
                return _insufficient(
                    f"No eligible latest-revised level was available for {LABELS[dataset_id]}.",
                )
            levels[dataset_id] = extracted
        months, left, right, excluded = longest_contiguous_overlap(
            levels[INDUSTRIAL_PRODUCTION_DATASET_ID],
            levels[PAYROLL_DATASET_ID],
        )
        if len(months) < MINIMUM_OVERLAP_MONTHS:
            return _insufficient(
                "The contiguous overlap of positive log levels is shorter than "
                f"{MINIMUM_OVERLAP_MONTHS} months.",
            )
        try:
            calculation = engle_granger_from_log_levels(left, right)
        except (ValueError, np.linalg.LinAlgError):
            return _insufficient("The Engle-Granger test did not return a finite result.")
        calculation = {
            **calculation,
            "sample_start": months[0].isoformat(),
            "sample_end": months[-1].isoformat(),
            "excluded_overlap_months": excluded,
            "left_dataset_id": INDUSTRIAL_PRODUCTION_DATASET_ID,
            "right_dataset_id": PAYROLL_DATASET_ID,
            "left_label": LABELS[INDUSTRIAL_PRODUCTION_DATASET_ID],
            "right_label": LABELS[PAYROLL_DATASET_ID],
            "input_vintage": "latest_revised",
        }
        return MethodExecutionResult(
            sufficiency="sufficient",
            calculation=calculation,
            observation_ids=_observation_ids(series_by_dataset, months),
            assumptions=_assumptions(excluded),
            limitations=_limitations(),
            missing_reason=None,
            statistical_interpretation=_interpretation(calculation),
            causal_hypothesis=NO_CAUSAL_CLAIM,
            investment_implication="no_action",
            narrative=_narrative(calculation),
        )


def _figure(value: float) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("a stored figure must be finite")
    return float(f"{number:.8g}")


def _longest_run(months: list[date]) -> list[date]:
    best: list[date] = []
    current: list[date] = []
    for month in months:
        if current and month != next_month(current[-1]):
            if len(current) > len(best):
                best = current
            current = [month]
        else:
            current.append(month)
    if len(current) > len(best):
        best = current
    return best


def _eligible_levels(
    dataset_id: str,
    series: Mapping[date, EconomicObservation],
) -> dict[date, float]:
    levels: dict[date, float] = {}
    for period, observation in series.items():
        if not _level_is_eligible(dataset_id, observation):
            continue
        value = float(observation.decimal_value())
        if math.isfinite(value) and value > 0:
            levels[period] = value
    return levels


def _level_is_eligible(dataset_id: str, observation: EconomicObservation) -> bool:
    return (
        observation.dataset_id == dataset_id
        and observation.series_provenance == SeriesProvenance.LATEST_REVISED
        and observation.quality_status == QualityStatus.OBSERVED
        and observation.frequency == Frequency.MONTHLY
        and observation.seasonal_adjustment == SeasonalAdjustment.SEASONALLY_ADJUSTED
        and observation.unit == UNITS[dataset_id]
        and observation.period_start.day == 1
    )


def _observation_ids(
    series_by_dataset: Mapping[str, Mapping[date, EconomicObservation]],
    months: Sequence[date],
) -> tuple[str, ...]:
    identifiers: list[str] = []
    for dataset_id in DATASET_IDS:
        series = series_by_dataset[dataset_id]
        for month in months:
            observation = series.get(month)
            if observation is not None:
                identifiers.append(observation.observation_id)
    return tuple(identifiers)


def _assumptions(excluded: int) -> tuple[str, ...]:
    assumptions = [
        "Both series are natural logarithms of latest-revised levels.",
        (
            "The overlap is the earliest longest contiguous run of months "
            "in which both levels are positive."
        ),
        "The first step is ordinary least squares with a constant.",
        (
            "The left-hand side is log industrial production. "
            "The right-hand side is log payroll employment."
        ),
        (
            "The second step is an augmented Dickey-Fuller test of the residual "
            "with no constant and no trend."
        ),
        (
            "The residual lag is chosen by AIC up to the Schwert ceiling "
            "that statsmodels uses when maxlag is omitted."
        ),
        (
            "The five percent critical value is the MacKinnon 2010 response "
            "surface for two series with a constant."
        ),
    ]
    if excluded:
        assumptions.append("Months outside that overlap were left out. Gaps were not interpolated.")
    return tuple(assumptions)


def _limitations() -> tuple[str, ...]:
    return (
        "Publication allowed is false.",
        "The inputs are latest revised levels. Revision sensitivity is blocked.",
        "The normalisation is predeclared. The reverse regression was not estimated.",
        CRITICAL_VALUE_SOURCE,
        (
            "Ordinary augmented Dickey-Fuller critical values are not used. "
            "They would make rejection easier, and this test does not do that."
        ),
        (
            "A failure to reject no-cointegration is the result. "
            "The five percent level was not loosened."
        ),
        "The result describes co-movement in revised log levels.",
        NO_CAUSAL_CLAIM,
        NOT_A_LEADING_INDICATOR,
        "Only this residual test on this pair was run.",
    )


def _interpretation(calculation: Mapping[str, object]) -> str:
    second = calculation["second_stage"]
    if not isinstance(second, dict):
        return "The Engle-Granger test did not return a residual regression."
    statistic = calculation["statistic"]
    critical = calculation["critical_value_five_percent"]
    used_lag = second["used_lag"]
    if calculation["rejects_no_cointegration_at_five_percent"] is True:
        decision = "rejects no-cointegration at five percent"
    else:
        decision = "does not reject no-cointegration at five percent"
    return (
        f"The augmented Dickey-Fuller statistic on the cointegrating residual is {statistic}. "
        f"The five percent MacKinnon critical value for two series with a constant is {critical}. "
        f"The test {decision}. The residual lag chosen by AIC is {used_lag}. "
        "The residual regression has no constant and no trend. "
        "This describes co-movement in revised log levels. "
        f"{NO_CAUSAL_CLAIM} {NOT_A_LEADING_INDICATOR}"
    )


def _narrative(calculation: Mapping[str, object]) -> str:
    if calculation["rejects_no_cointegration_at_five_percent"] is True:
        decision = "rejects no-cointegration at five percent"
    else:
        decision = "does not reject no-cointegration at five percent"
    return (
        "Engle-Granger test of log industrial production on log payroll employment. "
        f"The test {decision}. "
        "This is a description of co-movement in revised log levels. "
        f"{NO_CAUSAL_CLAIM} {NOT_A_LEADING_INDICATOR} Publication allowed is false."
    )


def _insufficient(reason: str) -> MethodExecutionResult:
    return MethodExecutionResult(
        sufficiency="insufficient",
        calculation={
            "method_id": ENGLE_GRANGER_COINTEGRATION,
            "publication_allowed": PUBLICATION_ALLOWED,
            "transformation": "natural_log_levels",
            "growth_rates_used": False,
            "causal_claim": False,
            "leading_indicator_assigned": False,
        },
        observation_ids=(),
        assumptions=("The series would have entered as natural logarithms of levels.",),
        limitations=("Publication allowed is false.", NO_CAUSAL_CLAIM),
        missing_reason=reason,
        statistical_interpretation="The Engle-Granger test was not computed.",
        causal_hypothesis=NO_CAUSAL_CLAIM,
        investment_implication="insufficient_evidence",
        narrative=f"Engle-Granger cointegration incomplete. Reason: {reason}",
    )
