"""Monthly industrial-production Markov switching.

The seeded recovery is a numerical check on a simulated series. It is not a
claim about recessions, and it is not Hamilton 1989 quarterly US GNP.
"""

from __future__ import annotations

import json
import math
from datetime import UTC, date, datetime

import numpy as np
import pytest

from aqil_research.contracts.observation import (
    AnalysisMode,
    AvailabilityPrecision,
    EconomicObservation,
    Frequency,
    QualityStatus,
    SeasonalAdjustment,
    SeriesProvenance,
)
from aqil_research.methods.bry_boschan_monthly import G17_DATASET_ID
from aqil_research.methods.hamilton_monthly import (
    CANDIDATE_LAGS,
    FILTERED_PROBABILITY_NOTE,
    HAMILTON_MONTHLY_PUBLISHED,
    METHOD_ID,
    SMOOTHED_PROBABILITY_NOTE,
    VARIANT_STATEMENT,
    HamiltonMonthlyMethod,
    LagScore,
    _order_by_lower_mean,
    choose_lag,
    minimum_duration_alternative,
    seeded_parameter_recovery,
)
from aqil_research.methods.protocol import MethodContext
from aqil_research.methods.registry import MethodRegistry, default_method_registry

RETRIEVED = datetime(2026, 10, 30, 8, 0, tzinfo=UTC)
RECOVERY_ERROR_BOUNDS = {
    "lower_mean": 0.05,
    "higher_mean": 0.05,
    "innovation_variance": 0.03,
    "stay_lower_mean": 0.04,
    "lower_given_higher": 0.04,
    "autoregressive_lag_1": 0.05,
}


def test_registry_accepts_the_method_in_one_call() -> None:
    registry = MethodRegistry()
    registry.register(HamiltonMonthlyMethod())
    method = registry.get(METHOD_ID)
    assert method.method_id == METHOD_ID
    assert len(method.implementation_hash()) == 64
    registered = default_method_registry().get(METHOD_ID)
    assert registered.method_id == METHOD_ID
    assert registered.method_version == method.method_version


def test_smaller_lag_wins_an_exact_bic_tie() -> None:
    scores = tuple(
        LagScore(
            lag=lag,
            log_likelihood=-100.0,
            parameter_count=4 + lag,
            modelled_month_count=80,
            bic=10.0 if lag in {1, 3} else 11.0 + lag,
            library_bic=10.0,
            aic=9.0,
        )
        for lag in CANDIDATE_LAGS
    )
    assert choose_lag(scores) == 1


def test_lower_mean_is_stored_first_when_the_library_order_is_reversed() -> None:
    means = np.array([1.0, -1.0])
    transition = np.array([[0.2, 0.3], [0.8, 0.7]])
    durations = np.array([1.0 / 0.8, 1.0 / 0.3])
    filtered = np.array([[0.9, 0.1], [0.2, 0.8]])
    ordered = _order_by_lower_mean(
        means=means,
        mean_errors=np.array([0.1, 0.2]),
        transition=transition,
        transition_errors=np.array([0.04, 0.05]),
        filtered=filtered,
        smoothed=filtered.copy(),
        durations=durations,
    )
    assert ordered.swapped is True
    assert ordered.means.tolist() == [-1.0, 1.0]
    assert ordered.transition.tolist() == [[0.7, 0.8], [0.3, 0.2]]
    assert ordered.filtered[:, 0].tolist() == [0.1, 0.8]
    assert ordered.transition_errors.tolist() == [0.05, 0.04]
    assert ordered.durations[0] == pytest.approx(1.0 / 0.3)


def test_seeded_parameter_recovery_stays_inside_the_error_bounds() -> None:
    recovery = seeded_parameter_recovery()
    assert recovery["not_a_recession_claim"] is True
    assert recovery["not_hamilton_1989_quarterly_us_gnp"] is True
    assert recovery["data"] == "seeded simulation"
    assert recovery["converged"] is True
    assert recovery["regimes_look_identified"] is True
    specification = recovery["specification"]
    assert isinstance(specification, dict)
    assert specification["switching_trend"] is True
    assert specification["switching_autoregression"] is False
    assert specification["switching_variance"] is False
    assert specification["random_search_repetitions"] == 0
    errors = recovery["absolute_errors"]
    assert isinstance(errors, dict)
    for name, bound in RECOVERY_ERROR_BOUNDS.items():
        assert float(errors[name]) < bound
    assert "not a claim about recessions" in str(recovery["statement"])


def test_method_stores_filtered_and_smoothed_probabilities_separately() -> None:
    series = _series(_separated_growth(80))
    result = HamiltonMonthlyMethod().run(_context(series), _config())
    assert result.sufficiency == "sufficient"
    assert result.calculation is not None
    calculation = result.calculation
    json.dumps(calculation)
    assert calculation["publication_allowed"] is False
    assert calculation["operational"] is False
    assert calculation["empirically_qualified"] is False
    assert calculation["real_time_assessment"] is False
    assert calculation["not_hamilton_1989_quarterly_us_gnp"] is True
    assert calculation["variant_statement"] == VARIANT_STATEMENT
    assert VARIANT_STATEMENT in result.narrative
    assert "not a real-time assessment" in result.narrative
    assert calculation["filtered_regime_probabilities_note"] == FILTERED_PROBABILITY_NOTE
    assert calculation["smoothed_regime_probabilities_note"] == SMOOTHED_PROBABILITY_NOTE
    assert "future observations" in SMOOTHED_PROBABILITY_NOTE
    assert "future observations" not in FILTERED_PROBABILITY_NOTE
    assert "not real-time" in FILTERED_PROBABILITY_NOTE
    assert "not real-time" in SMOOTHED_PROBABILITY_NOTE
    assert "not what an observer could have known" in FILTERED_PROBABILITY_NOTE
    assert "not what an observer could have known" in SMOOTHED_PROBABILITY_NOTE
    filtered = calculation["filtered_regime_probabilities"]
    smoothed = calculation["smoothed_regime_probabilities"]
    assert isinstance(filtered, list)
    assert isinstance(smoothed, list)
    assert filtered is not smoothed
    assert len(filtered) == len(smoothed)
    assert len(filtered) == calculation["sample"]["modelled_month_count"]
    for left, right in zip(filtered, smoothed, strict=True):
        assert isinstance(left, dict)
        assert isinstance(right, dict)
        assert math.isclose(
            float(left["lower_mean"]) + float(left["higher_mean"]), 1.0, abs_tol=1e-6
        )
        assert math.isclose(
            float(right["lower_mean"]) + float(right["higher_mean"]),
            1.0,
            abs_tol=1e-6,
        )
    selection = calculation["lag_selection"]
    assert isinstance(selection, dict)
    values = selection["values"]
    assert isinstance(values, list)
    assert [row["lag"] for row in values] == list(CANDIDATE_LAGS)
    chosen = selection["chosen_lag"]
    assert chosen == min((row["bic"], row["lag"]) for row in values)[1]
    diagnosis = calculation["estimation_diagnosis"]
    assert isinstance(diagnosis, dict)
    assert diagnosis["operational"] is False
    assert diagnosis["empirically_qualified"] is False
    assert isinstance(diagnosis["regimes_look_identified"], bool)
    if diagnosis["regimes_look_identified"]:
        assert diagnosis["reasons"] == []
    else:
        assert diagnosis["reasons"]
    diagnostic = calculation["nber_retrospective_diagnostic"]
    assert isinstance(diagnostic, dict)
    assert diagnostic["gates_the_method"] is False
    assert diagnostic["is_identification"] is False
    assert diagnostic["retrospective_only"] is True
    assert "does not gate the method" in str(diagnostic["statement"])
    assert result.investment_implication == "no_action"
    assert len(result.observation_ids) == len(series)


def test_point_in_time_input_is_not_estimated() -> None:
    series = _series(_separated_growth(8))
    context = MethodContext(
        inputs_by_dataset={G17_DATASET_ID: series},
        evaluation_period=max(series),
        analysis_mode=AnalysisMode.POINT_IN_TIME,
        primary_dataset_id=G17_DATASET_ID,
    )
    result = HamiltonMonthlyMethod().run(context, _config())
    assert result.sufficiency == "insufficient"
    assert result.calculation is not None
    assert result.calculation["publication_allowed"] is False
    assert result.calculation["operational"] is False
    assert "latest_revised" in str(result.missing_reason)


def test_short_sample_is_not_estimated() -> None:
    result = HamiltonMonthlyMethod().run(_context(_series(_separated_growth(12))), _config())
    assert result.sufficiency == "insufficient"
    assert result.calculation is not None
    assert result.calculation["empirically_qualified"] is False
    assert "minimum" in str(result.missing_reason)


def test_six_month_duration_alternative_is_not_identified_at_two_months() -> None:
    record = minimum_duration_alternative(2.0)
    assert record["predeclared"] is True
    assert record["estimated"] is False
    assert record["identified"] is False
    assert record["adopted"] is False
    assert record["recession_label"] is False
    assert record["minimum_months"] == 6.0
    assert "not a recession label" in str(record["reason"])
    longer = minimum_duration_alternative(8.0)
    assert longer["estimated"] is False
    assert longer["adopted"] is False
    assert longer["identified"] is False


def test_non_positive_index_is_rejected() -> None:
    series = _series(_separated_growth(12))
    first = min(series)
    series[first] = _observation(first, "0.0")
    result = HamiltonMonthlyMethod().run(_context(series), _config())
    assert result.sufficiency == "insufficient"
    assert "positive" in str(result.missing_reason)


def _config() -> object:
    return HamiltonMonthlyMethod().parse_config(dict(HAMILTON_MONTHLY_PUBLISHED))


def _context(series: dict[date, EconomicObservation]) -> MethodContext:
    return MethodContext(
        inputs_by_dataset={G17_DATASET_ID: series},
        evaluation_period=max(series),
        analysis_mode=AnalysisMode.LATEST_REVISED,
        primary_dataset_id=G17_DATASET_ID,
    )


def _series(growth: np.ndarray) -> dict[date, EconomicObservation]:
    level = 100.0
    period = date(1990, 1, 1)
    series = {period: _observation(period, f"{level:.10f}")}
    for change in growth:
        period = _next_month(period)
        level *= math.exp(float(change))
        series[period] = _observation(period, f"{level:.10f}")
    return series


def _separated_growth(count: int) -> np.ndarray:
    generator = np.random.default_rng(11)
    means = np.array([-0.8, 0.6])
    stay = np.array([0.9, 0.92])
    state = 1
    previous_mean = means[1]
    values = np.empty(count)
    level = means[1]
    for index in range(count):
        state = state if generator.random() < stay[state] else 1 - state
        current_mean = means[state]
        level = current_mean + 0.2 * (level - previous_mean) + 0.45 * generator.standard_normal()
        values[index] = level
        previous_mean = current_mean
    return values


def _observation(period: date, value: str) -> EconomicObservation:
    return EconomicObservation(
        observation_id=f"hamilton-{period.isoformat()}",
        dataset_id=G17_DATASET_ID,
        provider_id="federal_reserve_board",
        source_id="federal_reserve_g17_total_ip",
        rights_record_id="federal_reserve_g17_total_ip",
        period_start=period,
        frequency=Frequency.MONTHLY,
        geography="US",
        unit="index_2017_100",
        seasonal_adjustment=SeasonalAdjustment.SEASONALLY_ADJUSTED,
        raw_value=value,
        quality_status=QualityStatus.OBSERVED,
        series_provenance=SeriesProvenance.LATEST_REVISED,
        provider_vintage_date=date(2026, 10, 17),
        availability_precision=AvailabilityPrecision.UNKNOWN,
        retrieved_at=RETRIEVED,
        first_seen_at=RETRIEVED,
        adapter_version="hamilton_monthly_test_v1",
    )


def _next_month(month_start: date) -> date:
    if month_start.month == 12:
        return date(month_start.year + 1, 1, 1)
    return date(month_start.year, month_start.month + 1, 1)
