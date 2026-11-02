"""Controls that must pass before an empirical table is trusted."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

import numpy as np
import pytest

from aqil_research.contracts.observation import (
    AnalysisMode,
    AvailabilityPrecision,
    SeriesProvenance,
)
from aqil_research.discovery.association import associate, benjamini_hochberg, claim_class
from aqil_research.discovery.features import (
    change_from_previous_stored,
    difference_over,
    past_rolling_percentile,
)
from aqil_research.discovery.guards import (
    LeakageError,
    assert_entry_on_or_after_decision,
    assert_signal_known,
    point_in_time_class,
    recorded_series_class,
)
from aqil_research.discovery.outcomes import OutcomeError, listing_total_return
from aqil_research.methods.registry import default_method_registry
from fixtures.observation_factory import make_observation, month_start


def test_latest_revised_cannot_be_saved_as_point_in_time() -> None:
    with pytest.raises(LeakageError, match="latest_revised"):
        point_in_time_class(SeriesProvenance.LATEST_REVISED, AnalysisMode.POINT_IN_TIME)
    observation = make_observation(
        period_start=month_start(2024, 1),
        raw_value="4.0",
        provider_vintage_date=month_start(2024, 2),
        series_provenance=SeriesProvenance.LATEST_REVISED,
        availability_precision=AvailabilityPrecision.UNKNOWN,
        earliest_model_available_at=None,
    )
    with pytest.raises(LeakageError, match="latest_revised"):
        recorded_series_class(
            (observation,),
            observation.dataset_id,
            datetime(2024, 3, 1, tzinfo=UTC),
            AnalysisMode.POINT_IN_TIME,
        )


def test_return_window_before_the_decision_is_rejected() -> None:
    with pytest.raises(LeakageError, match="before the decision"):
        assert_entry_on_or_after_decision(date(2024, 1, 2), date(2024, 1, 3))
    with pytest.raises(LeakageError, match="before the decision"):
        listing_total_return(
            distribution_policy="accumulating",
            start_value=Decimal("10"),
            end_value=Decimal("11"),
            quote_unit="USD",
            dividend=None,
            uses_adjusted_close=True,
            inception_bound=date(2024, 1, 1),
            entry=date(2024, 1, 2),
            decision=date(2024, 1, 3),
        )


def test_distributing_total_return_without_a_dividend_is_rejected() -> None:
    with pytest.raises(OutcomeError, match="distributing"):
        listing_total_return(
            distribution_policy="distributing",
            start_value=Decimal("10"),
            end_value=Decimal("11"),
            quote_unit="USD",
            dividend=None,
            uses_adjusted_close=False,
            inception_bound=date(2020, 1, 1),
            entry=date(2024, 1, 3),
            decision=date(2024, 1, 3),
        )


def test_synthetic_slope_is_recovered() -> None:
    signal = [float(index) for index in range(40)]
    outcome = [
        2.0 * value + (0.1 if index % 2 == 0 else -0.1) for index, value in enumerate(signal)
    ]
    fit = associate(signal, outcome, maxlags=1, block=1, replicates=30, seed=7)
    assert fit.slope == pytest.approx(2.0, abs=0.05)
    assert fit.pearson_r > 0.99


def test_null_shuffle_is_not_economically_useful() -> None:
    generator = np.random.default_rng(11)
    signal = generator.normal(size=60).tolist()
    outcome = [2.0 * value for value in signal]
    shuffled = generator.permutation(signal).tolist()
    fit = associate(shuffled, outcome, maxlags=1, block=1, replicates=20, seed=11)
    label = claim_class(
        is_null_control=True,
        below_floor=False,
        statistical_bar=True,
        bh_rejects=fit.slope_p < 0.05,
        holdout_confirms=True,
        economic_advantage=True,
        bootstrap_excludes_zero=True,
        forward_frozen=False,
    )
    assert label == "not_claimed"
    assert label != "economically_useful"


def test_future_macro_value_is_rejected() -> None:
    with pytest.raises(LeakageError, match="not known"):
        assert_signal_known(date(2024, 6, 1), 1, date(2024, 6, 1))


def test_past_percentile_ignores_a_later_spike() -> None:
    series = {
        date(2024, 1, 1): Decimal("1"),
        date(2024, 2, 1): Decimal("2"),
        date(2024, 3, 1): Decimal("3"),
        date(2024, 4, 1): Decimal("100"),
    }
    ranked = past_rolling_percentile(series, window=2)
    assert date(2024, 3, 1) in ranked
    assert ranked[date(2024, 3, 1)] == Decimal(1)
    assert date(2024, 1, 1) not in ranked


def test_a_gap_is_not_bridged_by_a_twelve_month_change() -> None:
    series = {date(2024, 1, 1): Decimal("1"), date(2025, 2, 1): Decimal("2")}
    assert difference_over(series, 12) == {}
    stored = change_from_previous_stored(series)
    assert stored[date(2025, 2, 1)][1] == 13


def test_forward_validated_is_not_assigned_by_freezing_after_the_outcome() -> None:
    label = claim_class(
        is_null_control=False,
        below_floor=False,
        statistical_bar=True,
        bh_rejects=True,
        holdout_confirms=True,
        economic_advantage=True,
        bootstrap_excludes_zero=True,
        forward_frozen=True,
    )
    assert label == "not_claimed"


def test_benjamini_hochberg_matches_the_worked_example() -> None:
    adjusted = benjamini_hochberg([0.01, 0.04, 0.03])
    assert adjusted[0] == pytest.approx(0.03)
    assert adjusted[1] == pytest.approx(0.04)
    assert adjusted[2] == pytest.approx(0.04)


def test_classification_covers_every_executable_registration() -> None:
    from aqil_research.discovery.classification import SPECS

    registered = {method.method_id for method in default_method_registry().registered()}
    assert registered == set(SPECS)
    assert len(registered) == 26


def test_a_long_price_gap_is_not_filled() -> None:
    from aqil_research.discovery.pairs import align_forward_returns

    paired = align_forward_returns(
        {date(2010, 1, 1): Decimal("4.0")},
        (date(2019, 7, 25), date(2020, 7, 27)),
        {date(2019, 7, 25): Decimal("10"), date(2020, 7, 27): Decimal("11")},
        horizon_months=12,
        lag_months=1,
        quote_unit="USD",
        distribution_policy="accumulating",
        inception_bound=date(2019, 7, 25),
        dividend=None,
        maximum_gap_days=10,
    )
    assert paired.pairs == ()
    assert paired.missing_windows == 1


def test_cash_beats_immediate_investment_when_prices_fall() -> None:
    from aqil_research.discovery.economic import adverse_flags, beats_immediate
    from aqil_research.discovery.pairs import AlignedPair

    first = date(2020, 1, 2)
    second = date(2020, 2, 3)
    pairs = [
        AlignedPair(date(2019, 12, 1), first, first, second, Decimal("1"), Decimal("-0.5")),
        AlignedPair(
            date(2020, 1, 1), second, second, date(2020, 3, 2), Decimal("2"), Decimal("-0.2")
        ),
    ]
    prices = {
        first: Decimal("10"),
        second: Decimal("5"),
        date(2020, 3, 2): Decimal("4"),
    }
    flags = adverse_flags([1.0, 2.0], "positive")
    invested = [not flag for flag in flags]
    assert invested == [False, False]
    assert beats_immediate(pairs, invested, prices, date(2020, 3, 2), (0, 10))
