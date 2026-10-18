"""Prospective Employment Situation assessment. Synthetic inputs are labelled as such."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from aqil_research.methods.configs import SAHM_PUBLISHED
from aqil_research.methods.sahm import SahmMethodError, run_sahm
from aqil_research.prospective.employment_situation import (
    NO_FORECAST_STATEMENT,
    OCTOBER_2026_RELEASE_AT,
    ProspectiveAssessmentError,
    assert_before_release,
    build_assessment_payload,
    evaluate_release,
    october_rate_that_reaches_threshold,
    payload_hash,
)
from fixtures.observation_factory import make_observation, month_start


def _flat(rate: str, start_year: int = 2024, months: int = 24) -> dict:
    rows = {}
    year, month = start_year, 1
    for _ in range(months):
        period = month_start(year, month)
        rows[period] = make_observation(
            period_start=period,
            raw_value=rate,
            provider_vintage_date=period,
        )
        month += 1
        if month == 13:
            month = 1
            year += 1
    return rows


def test_threshold_rate_on_a_flat_series_is_half_a_point_above_the_level() -> None:
    rows = _flat("4.0", months=30)
    evaluation = month_start(2026, 6)
    rate = october_rate_that_reaches_threshold(rows, evaluation, SAHM_PUBLISHED)
    assert rate == Decimal("5.5")
    trial = dict(rows)
    template = rows[evaluation]
    trial[evaluation] = template.model_copy(update={"raw_value": "5.4"})
    assert run_sahm(trial, evaluation, SAHM_PUBLISHED).triggered is False
    trial[evaluation] = template.model_copy(update={"raw_value": "5.5"})
    assert run_sahm(trial, evaluation, SAHM_PUBLISHED).triggered is True


def test_missing_month_is_rejected() -> None:
    rows = _flat("4.0", months=10)
    with pytest.raises(SahmMethodError):
        run_sahm(rows, month_start(2025, 12), SAHM_PUBLISHED)


def test_freeze_rejected_at_and_after_release() -> None:
    assert_before_release(datetime(2026, 11, 6, 13, 29, tzinfo=UTC))
    with pytest.raises(ProspectiveAssessmentError):
        assert_before_release(OCTOBER_2026_RELEASE_AT)
    with pytest.raises(ProspectiveAssessmentError):
        assert_before_release(datetime(2026, 11, 6, 13, 31, tzinfo=UTC))


def test_daylight_saving_instant_is_1330_utc() -> None:
    assert OCTOBER_2026_RELEASE_AT == datetime(2026, 11, 6, 13, 30, tzinfo=UTC)


def test_outcome_cannot_precede_release_or_award_skill() -> None:
    payload = build_assessment_payload(
        baseline={
            "period": "2026-09-01",
            "unemployment_rate": "4.2",
            "gap_percentage_points": "0.00",
        },
        threshold_rate="5.0",
        observations=[],
        retrieved_at="2026-10-18T00:00:00+00:00",
        source_uri="https://api.bls.gov/publicAPI/v2/timeseries/data/LNS14000000",
    )
    frozen = {**payload, "payload_hash": payload_hash(payload)}
    with pytest.raises(ProspectiveAssessmentError):
        evaluate_release(
            frozen,
            observed_rate="4.3",
            published_at=datetime(2026, 11, 6, 13, 29, tzinfo=UTC),
            retrieved_at=datetime(2026, 11, 6, 14, 0, tzinfo=UTC),
        )
    outcome = evaluate_release(
        frozen,
        observed_rate="4.3",
        published_at=datetime(2026, 11, 6, 13, 30, tzinfo=UTC),
        retrieved_at=datetime(2026, 11, 6, 13, 31, tzinfo=UTC),
    )
    assert outcome["forecasting_skill"] is None
    assert outcome["threshold_condition_met"] is False
    assert frozen["statement"] == NO_FORECAST_STATEMENT
    assert payload_hash(payload) == frozen["payload_hash"]


def test_synthetic_label_is_distinct_from_a_verified_event() -> None:
    verified = build_assessment_payload(
        baseline={
            "period": "2026-09-01",
            "unemployment_rate": "4.0",
            "gap_percentage_points": "0.00",
        },
        threshold_rate="5.5",
        observations=[],
        retrieved_at="2026-10-18T00:00:00+00:00",
        source_uri="https://api.bls.gov/publicAPI/v2/timeseries/data/LNS14000000",
    )
    assert verified["evidence_class"] == "verified_real_event"
    assert verified["evidence_class"] != "synthetic_demonstration"


def test_research_payload_does_not_name_an_allocation_change() -> None:
    payload = build_assessment_payload(
        baseline={
            "period": "2026-09-01",
            "unemployment_rate": "4.0",
            "gap_percentage_points": "0.00",
        },
        threshold_rate="5.5",
        observations=[],
        retrieved_at="2026-10-18T00:00:00+00:00",
        source_uri="https://api.bls.gov/publicAPI/v2/timeseries/data/LNS14000000",
    )
    assert payload["no_directional_forecast"] is True
    assert "etf_recommendation" not in payload
