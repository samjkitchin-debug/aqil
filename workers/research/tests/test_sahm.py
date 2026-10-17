from datetime import date
from decimal import Decimal

import pytest

from aqil_research.methods.configs import SAHM_PUBLISHED, SAHM_SENSITIVITY
from aqil_research.methods.sahm import SahmMethodError, run_sahm
from fixtures.observation_factory import (
    constant_unemployment_series,
    make_observation,
    month_start,
)


def _series_dict(rows: tuple) -> dict[date, object]:
    return {row.period_start: row for row in rows}


def test_sahm_hand_calculated_trigger_at_published_threshold() -> None:
    base = constant_unemployment_series(month_start(2023, 10), 12, "4.0")
    spike_months = (
        make_observation(
            period_start=month_start(2024, 10),
            raw_value="4.5",
            provider_vintage_date=date(2024, 11, 5),
        ),
        make_observation(
            period_start=month_start(2024, 11),
            raw_value="4.5",
            provider_vintage_date=date(2024, 12, 5),
        ),
        make_observation(
            period_start=month_start(2024, 12),
            raw_value="4.5",
            provider_vintage_date=date(2025, 1, 5),
        ),
    )
    by_period = _series_dict(base + spike_months)
    output = run_sahm(by_period, month_start(2024, 12), SAHM_PUBLISHED)
    assert output.three_month_average == Decimal("4.5000")
    assert output.prior_twelve_month_low_of_average == Decimal("4.0000")
    assert output.gap_percentage_points == Decimal("0.5000")
    assert output.triggered is True


def test_sahm_threshold_crossed_requires_prior_month_below() -> None:
    from aqil_research.methods.sahm import sahm_threshold_crossed

    base = constant_unemployment_series(month_start(2023, 1), 21, "4.0")
    spike_months = (
        make_observation(
            period_start=month_start(2024, 10),
            raw_value="4.5",
            provider_vintage_date=date(2024, 11, 5),
        ),
        make_observation(
            period_start=month_start(2024, 11),
            raw_value="4.5",
            provider_vintage_date=date(2024, 12, 5),
        ),
        make_observation(
            period_start=month_start(2024, 12),
            raw_value="4.5",
            provider_vintage_date=date(2025, 1, 5),
        ),
    )
    by_period = _series_dict(base + spike_months)
    assert run_sahm(by_period, month_start(2024, 12), SAHM_PUBLISHED).triggered is True
    assert run_sahm(by_period, month_start(2024, 11), SAHM_PUBLISHED).triggered is False
    assert sahm_threshold_crossed(by_period, month_start(2024, 12), SAHM_PUBLISHED) is True


def test_sensitivity_config_changes_threshold_not_method() -> None:
    base = constant_unemployment_series(month_start(2023, 10), 12, "4.0")
    last_three = (
        make_observation(
            period_start=month_start(2024, 10),
            raw_value="4.30",
            provider_vintage_date=date(2024, 11, 5),
        ),
        make_observation(
            period_start=month_start(2024, 11),
            raw_value="4.30",
            provider_vintage_date=date(2024, 12, 5),
        ),
        make_observation(
            period_start=month_start(2024, 12),
            raw_value="4.30",
            provider_vintage_date=date(2025, 1, 5),
        ),
    )
    by_period = _series_dict(base + last_three)
    published = run_sahm(by_period, month_start(2024, 12), SAHM_PUBLISHED)
    sensitivity = run_sahm(by_period, month_start(2024, 12), SAHM_SENSITIVITY)
    assert published.gap_percentage_points == Decimal("0.3000")
    assert published.triggered is False
    assert sensitivity.triggered is True
    assert SAHM_PUBLISHED.config_hash() != SAHM_SENSITIVITY.config_hash()


def test_rejects_missing_months() -> None:
    rows = constant_unemployment_series(month_start(2024, 1), 5, "4.0")
    with pytest.raises(SahmMethodError, match="missing months"):
        run_sahm(_series_dict(rows), month_start(2024, 12), SAHM_PUBLISHED)


def test_rejects_wrong_unit() -> None:
    row = make_observation(
        period_start=month_start(2024, 1),
        raw_value="4.0",
        provider_vintage_date=date(2024, 2, 1),
    )
    bad = row.model_copy(update={"unit": "index"})
    with pytest.raises(SahmMethodError, match="unit"):
        run_sahm({bad.period_start: bad}, month_start(2024, 1), SAHM_PUBLISHED)
