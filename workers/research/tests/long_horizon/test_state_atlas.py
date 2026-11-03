"""Frozen atlas rules. These tests do not write a state row."""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from pathlib import Path

import jsonschema
import pytest

from aqil_research.certification.vintage_gate import GDP_SERIES
from aqil_research.long_horizon.events.definition import (
    EVENT_DEFINITION,
    FROZEN_PILOT_INTERSECTION,
    event_definition_hash,
)
from aqil_research.long_horizon.state_atlas.features import (
    EconomicPoint,
    drawdown,
    economic_features,
    labelled_advance,
    outcome_at,
    period_bound,
    trailing_return,
)
from aqil_research.long_horizon.state_atlas.rule import (
    SequenceRuleError,
    SymbolSequence,
    assign_sequence_status,
    condition_a,
    condition_b_alone,
    reconcile_checksum,
)
from aqil_research.long_horizon.state_atlas.specification import (
    ATLAS_SPECIFICATION,
    EVT_DEFINITION_HASH,
    FORBIDDEN_CLAIM_STATUSES,
    POINT_IN_TIME_DATASET,
    PROTECTED_EXECUTIONS,
    PROTECTED_HYPOTHESES,
    SEQUENCE_EXPERIMENT,
    assert_sequence_status_allowed,
    atlas_specification_hash,
    sequence_experiment_hash,
)
from aqil_research.methods.registry import default_method_registry

ROOT = Path(__file__).resolve().parents[4]


def _flat(level: str, count: int) -> list[Decimal]:
    return [Decimal(level)] * count


def _month(year: int, month: int, value: str) -> EconomicPoint:
    return EconomicPoint(date(year, month, 1), None, "monthly", Decimal(value))


def _symbol(name: str, **overrides: int) -> SymbolSequence:
    values = {
        "eligible": 20,
        "sequence": 4,
        "sequence_and_advance": 3,
        "control": 4,
        "control_and_advance": 1,
        "component": 5,
        "advances": 6,
    }
    values.update(overrides)
    return SymbolSequence(name, **values)


def test_specification_is_frozen_and_schemas_match() -> None:
    assert atlas_specification_hash() == atlas_specification_hash()
    assert sequence_experiment_hash() == sequence_experiment_hash()
    assert event_definition_hash() == EVT_DEFINITION_HASH
    assert EVENT_DEFINITION["definition_id"] == "EVT-DEF-001"
    assert EVENT_DEFINITION["version"] == 1
    assert ATLAS_SPECIFICATION["event_definition_hash"] == EVT_DEFINITION_HASH
    assert ATLAS_SPECIFICATION["publication_allowed"] is False
    assert SEQUENCE_EXPERIMENT["publication_allowed"] is False
    assert SEQUENCE_EXPERIMENT["category"] == "C"
    assert SEQUENCE_EXPERIMENT["not_macroeconomic_investment_intelligence"] is True
    assert SEQUENCE_EXPERIMENT["macro_vintage_ids"] == []
    assert SEQUENCE_EXPERIMENT["portfolio_comparison"] == "blocked"
    label = SEQUENCE_EXPERIMENT["outcome_label"]
    pilot = FROZEN_PILOT_INTERSECTION["outcome_label"]
    assert isinstance(label, dict)
    assert isinstance(pilot, dict)
    assert label["steps"] == pilot["steps"] == 126
    assert label["minimum_return"] == pilot["minimum_return"] == "0.10"
    assert set(SEQUENCE_EXPERIMENT["acceptance_criteria"]["forbidden_statuses"]) == set(
        FORBIDDEN_CLAIM_STATUSES
    )
    assert PROTECTED_HYPOTHESES == frozenset({"LH-H-001", "LH-H-002", "LH-H-003"})
    assert "LH-X-002" in PROTECTED_EXECUTIONS
    names = ("decision_anchor.v1.json", "state_observation.v1.json", "outcome_measure.v1.json")
    for name in names:
        original = (ROOT / "docs" / "schemas" / name).read_bytes()
        mirror = (ROOT / "packages" / "contracts" / "schemas" / name).read_bytes()
        assert original == mirror
    anchor = {
        "schema_version": "1.0",
        "anchor_id": "ATLAS-DEF-001:1:VWRA:listing_month_end:2019-07-31",
        "specification_id": "ATLAS-DEF-001",
        "specification_version": 1,
        "specification_hash": "a" * 64,
        "symbol": "VWRA",
        "anchor_kind": "listing_month_end",
        "session_date": "2019-07-31",
        "lookback_sufficient": False,
        "publication_allowed": False,
    }
    schema = json.loads((ROOT / "docs" / "schemas" / "decision_anchor.v1.json").read_text())
    jsonschema.validate(anchor, schema)
    anchor["anchor_kind"] = "market_transition"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(anchor, schema)
    state = {
        "schema_version": "1.0",
        "state_id": "state-1",
        "anchor_id": anchor["anchor_id"],
        "feature_id": "split_adjusted_close",
        "availability": "observed",
        "clock": "stored_sessions",
        "usable_as_decision_input": True,
        "value_text": "100",
        "publication_allowed": False,
    }
    state_schema = json.loads(
        (ROOT / "docs" / "schemas" / "state_observation.v1.json").read_text()
    )
    jsonschema.validate(state, state_schema)
    state["forward_price_return"] = "0.10"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(state, state_schema)
    outcome = {
        "schema_version": "1.0",
        "outcome_id": "outcome-1",
        "anchor_id": "anchor",
        "horizon_label": "6m",
        "session_steps": 126,
        "status": "censored",
        "value_text": None,
        "readable_as_state_input": False,
        "known_at_anchor": False,
        "publication_allowed": False,
    }
    outcome_schema = json.loads((ROOT / "docs" / "schemas" / "outcome_measure.v1.json").read_text())
    jsonschema.validate(outcome, outcome_schema)
    outcome["readable_as_state_input"] = True
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(outcome, outcome_schema)


def test_near_trough_ignores_later_closes() -> None:
    near = _flat("100", 252) + [Decimal("89")]
    assert condition_a(near, 252) is True
    extended = near + [Decimal("10000")]
    assert condition_a(extended, 252) is True
    assert trailing_return(extended, 252, 21).value == trailing_return(near, 252, 21).value
    assert drawdown(extended, 252, 21).value == drawdown(near, 252, 21).value
    above = _flat("100", 252) + [Decimal("91")]
    assert condition_a(above, 252) is False
    long = near + _flat("100", 126)
    _status, text = outcome_at(long, 252, 126)
    mutated = long[:-1] + [Decimal("1")]
    assert condition_a(mutated, 252) is True
    assert outcome_at(mutated, 252, 126)[1] != text
    short = _flat("100", 21)
    assert outcome_at(short, 0, 21) == ("censored", None)
    assert labelled_advance(short, 0) == ("censored", None, None)


def test_standalone_bounce_uses_the_decision_window_only() -> None:
    closes = _flat("100", 189) + _flat("80", 63) + [Decimal("88")]
    assert condition_b_alone(closes, 252) is True
    assert condition_a(closes, 252) is False
    assert condition_b_alone(closes + [Decimal("1")], 252) is True


def test_period_bound_does_not_invent_a_release_date() -> None:
    assert period_bound(date(2020, 1, 1), None, "monthly") == date(2020, 1, 31)
    assert period_bound(date(2020, 1, 1), None, "quarterly") == date(2020, 3, 31)
    assert period_bound(date(2020, 1, 1), date(2020, 1, 15), "monthly") == date(2020, 1, 15)
    assert period_bound(date(2026, 10, 21), None, "weekly") == date(2026, 10, 21)


def test_economic_window_refuses_a_full_sample_and_a_gap() -> None:
    points = [_month(2018, month, str(month)) for month in range(1, 13)]
    points += [_month(2019, month, str(20 + month)) for month in range(1, 13)]
    points += [_month(2020, month, str(40 + month)) for month in range(1, 13)]
    anchor = date(2020, 12, 31)
    first = economic_features(points, anchor)
    older = [_month(2010, 1, "1000"), *points]
    second = economic_features(older, anchor)
    assert first["trailing_standardisation"] == second["trailing_standardisation"]
    future = [*points, _month(2021, 1, "999")]
    assert economic_features(future, anchor)["level"] == first["level"]
    assert first["trailing_standardisation"].availability == "observed"
    gapped = [point for point in points if point.period_start != date(2020, 6, 1)]
    assert economic_features(gapped, anchor)["year_on_year"].availability == (
        "insufficient_gap_not_filled"
    )
    zero = [_month(2020, 1, "0"), _month(2020, 2, "1")]
    assert economic_features(zero, date(2020, 2, 29))["percent_change"].availability == (
        "insufficient_zero_base"
    )
    assert ATLAS_SPECIFICATION["retrospective_usable_as_decision_input"] is False
    assert ATLAS_SPECIFICATION["full_sample_standardisation"] == "refused"
    assert POINT_IN_TIME_DATASET == GDP_SERIES


def test_checksum_reconciliation_inserts_once() -> None:
    assert reconcile_checksum(None, "abc") == "insert"
    assert reconcile_checksum("abc", "abc") == "unchanged"
    with pytest.raises(SequenceRuleError, match="not overwritten"):
        reconcile_checksum("abc", "def")


def test_sequence_status_rule_on_synthetic_counts() -> None:
    supported = [_symbol(f"S{index}") for index in range(5)]
    status, _reasons = assign_sequence_status(supported)
    assert status == "inconclusive"
    flat = [
        _symbol(f"S{index}", sequence_and_advance=1, control_and_advance=1) for index in range(5)
    ]
    assert assign_sequence_status(flat)[0] == "no_incremental_information"
    common = [
        _symbol(
            f"S{index}",
            sequence=4,
            sequence_and_advance=4,
            control_and_advance=1,
            advances=4,
        )
        for index in range(5)
    ]
    assert assign_sequence_status(common)[0] == "rejected"
    assert assign_sequence_status([_symbol("ONLY")])[0] == "insufficient_data"
    for forbidden in FORBIDDEN_CLAIM_STATUSES:
        with pytest.raises(ValueError, match="cannot promote"):
            assert_sequence_status_allowed(forbidden)


def test_registered_methods_stay_latest_revised() -> None:
    methods = default_method_registry().registered()
    assert len(methods) == 26
    for method in methods:
        dependency = method.dependency()
        assert dependency.vintage_class == "latest_revised"
        assert GDP_SERIES not in method.required_dataset_ids()
        assert method.method_id != ""
    unavailable = ATLAS_SPECIFICATION["unavailable_dimensions"]
    assert isinstance(unavailable, list)
    assert "CENSUS_ADV_DURABLE_ORDERS" in unavailable
    assert "fred.alfred.UNRATE" in unavailable
    assert "surprise" in unavailable
    assert "euna_relative_performance" in unavailable
