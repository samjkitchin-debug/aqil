"""Frozen ETF protocol rules. These tests do not write a database row."""

from __future__ import annotations

import json
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import jsonschema
import pytest

from aqil_research.long_horizon.etf_protocol.events import (
    catalogue_new_families,
    failed_recoveries,
    sustained_declines,
    trend_reversals,
    volatility_transitions,
)
from aqil_research.long_horizon.etf_protocol.rules import (
    assert_effect_null,
    assert_session_allowed,
    benjamini_hochberg,
    binary_flag,
    conjunction_status,
    control_increment_status,
    method_refusal,
    predictor_value,
    promotion_decision,
    relative_class,
    rows_to_insert,
    search_refusal,
    spearman,
    trailing_volatility_median,
)
from aqil_research.long_horizon.etf_protocol.specification import (
    ADVANCE_MINIMUM,
    BINARY_TRANSFORMS,
    EVENT_DEFINITION_V2,
    FORBIDDEN_CLAIM_STATUSES,
    POINT_IN_TIME_DATASET,
    PRICE_FEATURES,
    PROTOCOL,
    SEARCH_REFUSAL_REASON,
    SEARCH_REFUSALS,
    assert_status_allowed,
    assert_v1_hash_unchanged,
    declare_trials,
    event_definition_v2_hash,
    protocol_hash,
    threshold_table,
)
from aqil_research.long_horizon.events.definition import EVENT_DEFINITION, event_definition_hash
from aqil_research.long_horizon.state_atlas.specification import EVT_DEFINITION_HASH
from aqil_research.methods.registry import default_method_registry

ROOT = Path(__file__).resolve().parents[4]


def _line(start: str, count: int, step: str) -> list[Decimal]:
    price = Decimal(start)
    change = Decimal(step)
    values = []
    for _index in range(count):
        values.append(price)
        price += change
    return values


def test_thresholds_are_shared_and_v1_is_unchanged() -> None:
    assert event_definition_hash() == EVT_DEFINITION_HASH
    assert_v1_hash_unchanged()
    assert protocol_hash() == protocol_hash()
    assert event_definition_v2_hash() == event_definition_v2_hash()
    assert threshold_table("VWRA") is threshold_table("EIMI")
    assert threshold_table("VWRA") is threshold_table("EIMI-VWRA")
    assert threshold_table("VWRA")["trailing_return_63"] == "0.05"
    assert threshold_table("EIMI")["drawdown_252_magnitude"] == "0.10"
    assert ADVANCE_MINIMUM == "0.10"
    decline = EVENT_DEFINITION_V2["families"]["sustained_decline"]
    advance = EVENT_DEFINITION["sustained_advance"]
    assert isinstance(decline, dict)
    assert isinstance(advance, dict)
    for horizon, raw in advance.items():
        assert isinstance(raw, dict)
        mirrored = decline[horizon]
        assert isinstance(mirrored, dict)
        assert mirrored["steps"] == raw["steps"]
        assert mirrored["maximum_return"] == f"-{raw['minimum_return']}"
        assert mirrored["maximum_rally"] == raw["maximum_drawdown"]
        assert mirrored["minimum_down_session_fraction"] == "0.55"
    bear = EVENT_DEFINITION_V2["families"]["persistent_bear"]
    bull = EVENT_DEFINITION["persistent_bull"]
    assert isinstance(bear, dict)
    assert isinstance(bull, dict)
    assert bear["minimum_decline"] == bull["minimum_rise"] == "0.20"
    assert bear["confirming_rally"] == bull["confirming_decline"] == "0.20"
    assert bear["minimum_session_steps"] == 126
    reversal = EVENT_DEFINITION_V2["families"]["trend_reversal"]
    assert isinstance(reversal, dict)
    assert reversal["historically_observable_at_event_date"] is False
    assert set(PROTOCOL["forbidden_claim_statuses"]) == set(FORBIDDEN_CLAIM_STATUSES)
    assert PROTOCOL["publication_allowed"] is False
    with pytest.raises(ValueError, match="cannot promote"):
        assert_status_allowed("statistically_supported")


def test_grid_is_identical_for_both_symbols_and_methods_are_refusals() -> None:
    datasets = ("bea.vintage.real_gdp.pct_preceding", "fed.example")
    methods = tuple(method.method_id for method in default_method_registry().registered())
    assert len(methods) == 26
    declared = declare_trials(datasets, methods)
    vwra = [row for row in declared if row.symbol == "VWRA"]
    eimi = [row for row in declared if row.symbol == "EIMI"]
    pair = [row for row in declared if row.symbol == "EIMI-VWRA"]
    vwra_shape = [
        (row.feature, row.transform, row.horizon_label, row.outcome, row.statistic) for row in vwra
    ]
    eimi_shape = [
        (row.feature, row.transform, row.horizon_label, row.outcome, row.statistic) for row in eimi
    ]
    assert vwra_shape == eimi_shape
    assert {
        row.feature for row in vwra if row.kind == "score" and row.transform == "continuous"
    } >= set(PRICE_FEATURES)
    assert "volatility_63" not in BINARY_TRANSFORMS
    searches = [row for row in vwra if row.kind == "search_refusal"]
    assert [row.feature for row in searches] == list(SEARCH_REFUSALS)
    for _row in searches:
        score = search_refusal()
        assert_effect_null(score)
        assert score.refusal == SEARCH_REFUSAL_REASON
    method_rows = [row for row in vwra if row.kind == "method_refusal"]
    assert len(method_rows) == 26
    for replay in ("not_historically_replayed", "unavailable_input"):
        score = method_refusal(replay)
        assert score.effect is None
        assert score.result is None
    pit = [row for row in vwra if row.feature.startswith(f"{POINT_IN_TIME_DATASET}:")]
    assert pit
    assert {row.eligibility for row in pit} == {"point_in_time_indicator"}
    assert all(
        row.eligibility == "category_b_retrospective"
        for row in vwra
        if ":fed.example:" in f":{row.feature}"
    )
    assert len(pair) != len(vwra)
    assert rows_to_insert(declared, {row.identity() for row in declared}) == ()
    again = declare_trials(list(reversed(datasets)), list(reversed(methods)))
    assert [row.identity() for row in again] == [row.identity() for row in declared]


def test_future_close_does_not_enter_a_predictor() -> None:
    closes = [Decimal("100") + Decimal(index) for index in range(400)]
    base_return = predictor_value(closes, 300, "trailing_return_63")
    base_drawdown = predictor_value(closes, 300, "drawdown_252")
    base_median = trailing_volatility_median(closes, 380)
    later = list(closes)
    later[390] = Decimal("1")
    later.append(Decimal("100000"))
    assert predictor_value(later, 300, "trailing_return_63") == base_return
    assert predictor_value(later, 300, "drawdown_252") == base_drawdown
    assert trailing_volatility_median(later, 380) == base_median
    later[300] = Decimal("40")
    assert predictor_value(later, 300, "trailing_return_63") != base_return


def test_vwra_first_session_is_refused() -> None:
    with pytest.raises(ValueError, match="2019-07-25"):
        assert_session_allowed("VWRA", date(2019, 7, 24))
    assert_session_allowed("VWRA", date(2019, 7, 25))
    assert_session_allowed("EIMI", date(2014, 1, 2))


def test_synthetic_events_follow_the_mirrored_rules() -> None:
    decline = _line("100", 22, "-1")
    found = sustained_declines(decline)
    one_month = next(row for row in found if row.horizon_label == "1m")
    assert one_month.events
    assert one_month.events[0].historically_observable_at_event_date is False
    bounced = _line("100", 10, "-1") + _line("91", 12, "2")
    bounced_count = next(row for row in sustained_declines(bounced) if row.horizon_label == "1m")
    assert bounced_count.events == ()
    failed = failed_recoveries(
        [Decimal("100"), Decimal("80"), Decimal("90"), Decimal("80"), Decimal("70")]
    )
    assert failed.events
    assert "trough" in failed.events[0].detail
    start = date(2016, 1, 1)
    dates = tuple(start + timedelta(days=offset) for offset in range(800))
    prices = [Decimal("100")] * 252 + [Decimal("80")] * 252 + [Decimal("200")] * 296
    reversal = trend_reversals(dates, prices)
    assert reversal.events
    assert all(event.historically_observable_at_event_date is False for event in reversal.events)
    noisy = []
    level = Decimal("100")
    for index in range(500):
        level = level + (Decimal("4") if index % 2 == 0 else Decimal("-3"))
        noisy.append(level)
    for _index in range(80):
        noisy.append(noisy[-1] + Decimal("0.01"))
    noisy.append(noisy[-1] * Decimal("1.25"))
    transitions = volatility_transitions(noisy)
    assert transitions.events
    assert all(event.historically_observable_at_event_date is True for event in transitions.events)
    catalogue = catalogue_new_families(dates, prices)
    assert {row.family for row in catalogue} == {
        "sustained_decline",
        "persistent_bear",
        "failed_recovery",
        "trend_reversal",
        "volatility_transition",
    }


def test_pair_status_relative_class_and_promotion_are_frozen() -> None:
    assert (
        conjunction_status(
            eligible=20,
            pair_count=4,
            pair_advances=3,
            drawdown_count=6,
            drawdown_advances=2,
            volatility_count=6,
            volatility_advances=2,
            advances=5,
        )
        == "inconclusive"
    )
    assert (
        conjunction_status(
            eligible=20,
            pair_count=4,
            pair_advances=2,
            drawdown_count=6,
            drawdown_advances=4,
            volatility_count=6,
            volatility_advances=2,
            advances=5,
        )
        == "no_incremental_information"
    )
    assert (
        conjunction_status(
            eligible=4,
            pair_count=1,
            pair_advances=1,
            drawdown_count=1,
            drawdown_advances=0,
            volatility_count=1,
            volatility_advances=0,
            advances=1,
        )
        == "insufficient_data"
    )
    assert relative_class(Decimal("0.2"), Decimal("0.1")) == "eimi_ahead_both_positive"
    assert relative_class(Decimal("0.1"), Decimal("-0.2")) == "eimi_positive_vwra_negative"
    assert relative_class(Decimal("-0.1"), Decimal("-0.4")) == "both_negative_eimi_declines_less"
    assert relative_class(Decimal("0.1"), Decimal("0.4")) == "vwra_ahead"
    assert relative_class(Decimal("0.2"), Decimal("0.2")) == "no_sign"
    assert relative_class(Decimal("0"), Decimal("-0.1")) == "no_sign"
    assert (
        promotion_decision(
            point_in_time=False,
            uninspected_evaluation=False,
            incremental_information=True,
        )
        == "no_policy_registered"
    )
    assert (
        promotion_decision(
            point_in_time=True,
            uninspected_evaluation=False,
            incremental_information=True,
        )
        == "no_policy_registered"
    )
    assert (
        control_increment_status(
            control_estimated=True,
            any_candidate_beats_control=False,
            any_candidate_estimated=True,
        )
        == "no_incremental_information"
    )
    score = spearman([(Decimal(index), Decimal(index)) for index in range(1, 8)])
    assert score.effect is not None
    assert score.refusal is None
    flags = benjamini_hochberg(["0.001", "0.20", "0.90"])
    assert flags[0] is True
    assert binary_flag("volatility_63", Decimal("0.2")) is None
    assert binary_flag("drawdown_252", Decimal("-0.10")) is True
    assert binary_flag("trailing_return_63", Decimal("0.04")) is False


def test_trial_schema_matches_its_mirror() -> None:
    name = "etf_protocol_trial.v1.json"
    original = (ROOT / "docs" / "schemas" / name).read_bytes()
    mirror = (ROOT / "packages" / "contracts" / "schemas" / name).read_bytes()
    assert original == mirror
    document = {
        "schema_version": "1.0",
        "trial_id": "ET-1",
        "specification_id": "ETF-PROT-001",
        "specification_version": 1,
        "specification_hash": "a" * 64,
        "dossier_id": "LH-X-005",
        "symbol": "VWRA",
        "feature": "trailing_return_63",
        "transform": "continuous",
        "horizon_label": "6m",
        "outcome": "advance",
        "statistic": "spearman",
        "eligibility": "category_c_price_only",
        "effect_text": None,
        "publication_allowed": False,
    }
    schema = json.loads(original)
    jsonschema.validate(document, schema)
    document["publication_allowed"] = True
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(document, schema)
    source = (
        ROOT
        / "workers"
        / "research"
        / "src"
        / "aqil_research"
        / "long_horizon"
        / "etf_protocol"
        / "specification.py"
    ).read_text(encoding="utf-8")
    assert "import psycopg" not in source
    assert "connect(" not in source
    package = (
        ROOT / "workers" / "research" / "src" / "aqil_research" / "long_horizon" / "etf_protocol"
    )
    for path in package.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "statsmodels" not in text
        assert "simulator" not in text
