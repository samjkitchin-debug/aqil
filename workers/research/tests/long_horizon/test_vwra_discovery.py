"""Guards for the retrospective VWRA dossier. These tests do not write a database."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from aqil_research.discovery.eligibility import SampleFloors
from aqil_research.long_horizon.etf_protocol.specification import (
    ADVANCE_MINIMUM,
    PRIMARY_STEPS,
)
from aqil_research.long_horizon.state_atlas.specification import SESSION_STEPS
from aqil_research.long_horizon.vwra_discovery.extract import extract_points
from aqil_research.long_horizon.vwra_discovery.guards import (
    assert_state_feature,
    latest_period,
    missing_datasets,
    unavailable_reason,
)
from aqil_research.long_horizon.vwra_discovery.market import downside_volatility, trend_persistence
from aqil_research.long_horizon.vwra_discovery.sequence import sequence_counts, sequence_flags
from aqil_research.long_horizon.vwra_discovery.specification import (
    CENSUS_DATASET,
    LOGISTIC_DECISION_POINTS,
    LOGISTIC_NON_OVERLAPPING,
    NON_OVERLAP_SESSION_GAP,
    VWRA_FIRST_SESSION,
    assert_vwra_session,
    join_allowed,
    method_finding,
    percent_change_ratio,
    sequence_finding,
    specification_hash,
)


def test_a_session_before_the_vwra_listing_is_refused() -> None:
    with pytest.raises(ValueError, match="2019-07-25"):
        assert_vwra_session(date(2019, 7, 24))
    assert_vwra_session(VWRA_FIRST_SESSION)


def test_a_later_period_is_not_joined_and_an_outcome_is_not_a_state() -> None:
    anchor = date(2020, 1, 31)
    assert join_allowed(date(2020, 1, 31), anchor) is True
    assert join_allowed(date(2020, 2, 1), anchor) is False
    assert latest_period((date(2020, 2, 29), date(2019, 12, 31)), anchor) == date(2019, 12, 31)
    with pytest.raises(ValueError, match="not a state"):
        assert_state_feature("outcome_126")
    with pytest.raises(ValueError, match="not a state"):
        assert_state_feature("cpi_surprise")


def test_percent_change_is_not_a_percentage_point_difference() -> None:
    ratio = percent_change_ratio("110", "100")
    assert ratio == "0.1"
    assert ratio != "10"
    difference = Decimal("4.5") - Decimal("4.0")
    assert difference == Decimal("0.5")
    assert ratio != str(difference)


def test_census_methods_stay_unavailable_when_no_rows_are_stored() -> None:
    missing = missing_datasets(
        ("bls.ln.LNS14000000", CENSUS_DATASET),
        {"bls.ln.LNS14000000": 1054, CENSUS_DATASET: 0},
    )
    assert missing == (CENSUS_DATASET,)
    assert "census.m3.adv.MDM.NO" in unavailable_reason(missing)
    assert missing_datasets(("bls.ln.LNS14000000",), {"bls.ln.LNS14000000": 10}) == ()


def test_a_calculation_without_a_number_is_not_an_empty_success() -> None:
    points, reason = extract_points("SAHM_UNEMPLOYMENT_GAP", None, date(2020, 1, 1))
    assert points == []
    assert reason is not None
    points, reason = extract_points(
        "SAHM_UNEMPLOYMENT_GAP",
        {
            "evaluation_period": "2020-01-01",
            "gap_percentage_points": "0.50",
            "threshold_met": False,
        },
        date(2020, 1, 1),
    )
    assert reason is None
    assert points[0].value_text == "0.5"
    assert points[0].unit == "percentage_points"
    assert points[0].state_label == "threshold_not_met"


def test_probit_that_was_not_estimated_is_a_failure() -> None:
    points, reason = extract_points(
        "CONSTANT_MATURITY_SPREAD_RECESSION_PROBIT",
        {"fit_status": "not_estimated", "probabilities_accepted": False, "probabilities": []},
        date(2020, 1, 1),
    )
    assert points == []
    assert reason is not None
    assert "not_estimated" in reason


def test_downside_volatility_does_not_read_a_later_close() -> None:
    closes = [Decimal(item) for item in ("100", "99", "97", "96", "200")]
    early = downside_volatility(closes, 2, 2)
    later = downside_volatility(closes, 3, 2)
    assert early is not None
    assert later is not None
    assert early != later
    assert early == downside_volatility(closes[:3], 2, 2)
    assert downside_volatility(closes, 1, 2) is None
    assert trend_persistence(closes, 2, 2) == "2"


def test_sequence_uses_the_frozen_window_and_cannot_promote() -> None:
    year_on_year = ["0.03", "0.02", "0.02", "0.02", "0.02"]
    momentum = ["-0.01", "-0.01", "0.01", "-0.02", "-0.02"]
    flags = sequence_flags(year_on_year, momentum)
    assert flags == [False, False, True, False, False]
    counts = sequence_counts(
        sequence=flags,
        deceleration=[False, True, False, False, False],
        momentum_positive=[False, True, False, False, False],
        advances=[False, False, False, True, None],
    )
    assert counts["false_positives"] == 1
    assert counts["missed_advances"] == 1
    assert sequence_finding(str(counts["comparison_status"])) in {
        "descriptive",
        "retrospective_exploratory",
        "inconclusive",
        "insufficient_sample",
        "rejected",
    }
    assert method_finding(0) == "insufficient_sample"
    assert method_finding(1) == "descriptive"


def test_sample_floors_match_the_frozen_literals() -> None:
    floors = SampleFloors()
    assert LOGISTIC_DECISION_POINTS == floors.statistical_decision_points == 60
    assert LOGISTIC_NON_OVERLAPPING == floors.statistical_non_overlapping == 15
    assert NON_OVERLAP_SESSION_GAP == PRIMARY_STEPS == SESSION_STEPS["6m"] == 126
    assert ADVANCE_MINIMUM == "0.10"
    assert len(specification_hash()) == 64
