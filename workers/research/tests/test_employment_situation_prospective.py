"""Prospective Employment Situation assessment. Synthetic inputs are labelled as such."""

from datetime import UTC, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from aqil_research.methods.configs import SAHM_PUBLISHED
from aqil_research.methods.sahm import SahmMethodError, run_sahm
from aqil_research.prospective.employment_situation import (
    NO_FORECAST_STATEMENT,
    OCTOBER_2026_RELEASE_AT,
    ProspectiveAssessmentError,
    assert_before_release,
    assessment_from_official_payload,
    build_assessment_payload,
    build_baseline_only_payload,
    evaluate_release,
    freeze_record,
    october_rate_that_reaches_threshold,
    payload_hash,
    recompute_hash,
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


def test_missing_sahm_input_stays_a_baseline_only_record(tmp_path) -> None:
    payload = build_baseline_only_payload(
        baseline={"period": "2026-09-01", "unemployment_rate": "4.2"},
        missing_reason="2025-10 is officially unavailable",
        observations=[{"period": "2026-09-01", "value": "4.2"}],
        retrieved_at="2026-10-18T00:40:00+00:00",
        source_uri="https://api.bls.gov/publicAPI/v2/timeseries/data/LNS14000000",
        schedule_verification="source_unavailable",
    )
    assert payload["october_rate_that_reaches_0_50"] is None
    assert payload["sahm_threshold_available"] is False
    now = datetime(2026, 10, 18, 1, 0, tzinfo=UTC)
    first = freeze_record(tmp_path, payload, now)
    second = freeze_record(tmp_path, payload, now)
    assert first["payload_hash"] == second["payload_hash"]
    assert len(list(tmp_path.glob("freeze-v*.json"))) == 1
    assert recompute_hash(first)
    changed = dict(payload)
    changed["baseline"] = {"period": "2026-09-01", "unemployment_rate": "4.3"}
    correction = freeze_record(tmp_path, changed, now)
    assert correction["version"] == 2
    assert json_loads(tmp_path / "freeze-v1.json")["payload_hash"] == first["payload_hash"]
    with pytest.raises(ProspectiveAssessmentError):
        freeze_record(tmp_path, changed, OCTOBER_2026_RELEASE_AT)


def test_new_york_release_instant_is_1330_utc() -> None:
    local = datetime(2026, 11, 6, 8, 30, tzinfo=ZoneInfo("America/New_York"))
    assert local.astimezone(UTC) == OCTOBER_2026_RELEASE_AT


def test_baseline_outcome_does_not_invent_a_threshold_result() -> None:
    payload = build_baseline_only_payload(
        baseline={"period": "2026-09-01", "unemployment_rate": "4.2"},
        missing_reason="missing official month",
        observations=[],
        retrieved_at="2026-10-18T00:40:00+00:00",
        source_uri="https://api.bls.gov/publicAPI/v2/timeseries/data/LNS14000000",
        schedule_verification="unverified",
    )
    frozen = {**payload, "payload_hash": payload_hash(payload)}
    outcome = evaluate_release(
        frozen,
        observed_rate="4.3",
        published_at=datetime(2026, 11, 6, 13, 30, tzinfo=UTC),
        retrieved_at=datetime(2026, 11, 6, 13, 31, tzinfo=UTC),
    )
    assert outcome["threshold_condition_met"] is None
    assert outcome["direction_versus_baseline"] == "increased"
    assert outcome["forecasting_skill"] is None


def test_official_dash_month_does_not_become_a_threshold() -> None:
    footnote = "Data unavailable due to the 2025 lapse in appropriations."
    payload = assessment_from_official_payload(
        {
            "status": "REQUEST_SUCCEEDED",
            "Results": {
                "series": [
                    {
                        "seriesID": "LNS14000000",
                        "data": [
                            {"year": "2026", "period": "M09", "value": "4.2", "footnotes": []},
                            {
                                "year": "2025",
                                "period": "M10",
                                "value": "-",
                                "footnotes": [
                                    {
                                        "code": "9",
                                        "text": footnote,
                                    }
                                ],
                            },
                        ],
                    }
                ]
            },
        },
        retrieved_at=datetime(2026, 10, 18, 3, 0, tzinfo=UTC),
        source_uri="https://api.bls.gov/publicAPI/v2/timeseries/data/",
        schedule_verification="source_unavailable",
    )
    assert payload["assessment_kind"] == "baseline_only"
    assert payload["baseline"]["unemployment_rate"] == "4.2"
    assert payload["october_rate_that_reaches_0_50"] is None
    assert "lapse in appropriations" in payload["sahm_unavailable_reason"]


def json_loads(path) -> dict:
    import json

    return json.loads(path.read_text(encoding="utf-8"))
