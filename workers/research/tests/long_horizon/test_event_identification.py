"""Synthetic locks for the frozen event rules. No stored price is read."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from aqil_research.long_horizon.events.definition import (
    EVENT_DEFINITION,
    FORBIDDEN_CLAIM_STATUSES,
    FROZEN_MACRO_INTERSECTION,
    FROZEN_PILOT_INTERSECTION,
    event_definition_hash,
    macro_intersection_hash,
    pilot_intersection_hash,
)
from aqil_research.long_horizon.events.identify import (
    EventDefinitionError,
    ListingSeries,
    assert_listing_series,
    confirmed_upswings,
    failed_rallies,
    negative_and_flat,
    persistent_and_early_bulls,
    recoveries,
    relative_and_leadership,
    single_listing_counts,
    sustained_advances,
)
from aqil_research.long_horizon.events.pilot_rule import (
    SymbolFrequency,
    assign_pilot_status,
    condition_at,
    evaluate_listing,
    outcome_at,
)

ROOT = Path(__file__).resolve().parents[4]


def _closes(*values: str) -> list[Decimal]:
    return [Decimal(value) for value in values]


def _rising(length: int, start: str = "100") -> list[Decimal]:
    base = Decimal(start)
    return [base + Decimal(index) for index in range(length)]


def _dates(length: int, start: date = date(2019, 1, 1)) -> list[date]:
    return [start + timedelta(days=index) for index in range(length)]


def _family(counts: list, family: str, horizon: str):
    found = [item for item in counts if item.family == family and item.horizon_label == horizon]
    assert len(found) == 1
    return found[0]


def test_thresholds_are_stable_and_total_return_stays_blocked() -> None:
    assert event_definition_hash() == event_definition_hash()
    assert pilot_intersection_hash() == pilot_intersection_hash()
    assert macro_intersection_hash() == macro_intersection_hash()
    assert EVENT_DEFINITION["total_return_events"] == "blocked"
    assert EVENT_DEFINITION["publication_allowed"] is False
    assert FROZEN_PILOT_INTERSECTION["category"] == "C"
    assert FROZEN_PILOT_INTERSECTION["not_macroeconomic_investment_intelligence"] is True
    assert FROZEN_PILOT_INTERSECTION["portfolio_comparison"] == "blocked"
    assert FROZEN_PILOT_INTERSECTION["macro_vintage_ids"] == []
    assert "not an untouched holdout" in str(FROZEN_PILOT_INTERSECTION["holdout_window"])
    assert FROZEN_PILOT_INTERSECTION["intersection"]["composite_score"] == "none"
    assert FROZEN_MACRO_INTERSECTION["category"] == "B"
    assert FROZEN_MACRO_INTERSECTION["estimated"] is False
    assert FROZEN_MACRO_INTERSECTION["values_read"] is False
    assert FROZEN_MACRO_INTERSECTION["macro_vintage_ids"] == []
    blocked = single_listing_counts(_rising(30))
    total = _family(blocked, "total_return_advance", "not_applicable")
    rally = _family(blocked, "rally_despite_deterioration", "not_applicable")
    assert total.status == "blocked" and total.events == ()
    assert rally.status == "blocked" and rally.events == ()
    assert "not relabelled" in total.reason


def test_specification_documents_quote_the_thresholds() -> None:
    event_text = (ROOT / "docs" / "research" / "events" / "EVENT_IDENTIFICATION.md").read_text(
        encoding="utf-8"
    )
    pilot_text = (ROOT / "docs" / "research" / "events" / "PILOT_SPECIFICATION.md").read_text(
        encoding="utf-8"
    )
    advances = EVENT_DEFINITION["sustained_advance"]
    assert isinstance(advances, dict)
    for horizon, row in advances.items():
        assert isinstance(row, dict)
        assert horizon in event_text
        assert str(row["minimum_return"]) in event_text
        assert str(row["maximum_drawdown"]) in event_text
    assert "0.20" in event_text
    assert "2019-07-25" in event_text
    assert "blocked" in event_text
    for token in ("0.10", "0.05", "0.40", "0.70", "252", "63", "126"):
        assert token in pilot_text
    assert "not an untouched holdout" in pilot_text
    assert "category C" in pilot_text


def test_vwra_before_the_first_stored_session_is_refused() -> None:
    with pytest.raises(EventDefinitionError, match="2019-07-25"):
        assert_listing_series(
            "VWRA",
            [date(2019, 7, 24)],
            [Decimal("50")],
            "USD",
            "USD",
        )
    assert_listing_series(
        "VWRA",
        [date(2019, 7, 25)],
        [Decimal("50")],
        "USD",
        "USD",
    )


def test_a_quote_unit_mismatch_is_not_converted() -> None:
    with pytest.raises(EventDefinitionError, match="quote unit"):
        assert_listing_series("CSPX", [date(2020, 1, 1)], [Decimal("1")], "USD", "GBX")


def test_sustained_advances_do_not_keep_overlapping_interiors() -> None:
    closes = _rising(800)
    counts = sustained_advances(closes)
    short = _family(counts, "sustained_advance", "1m")
    assert short.qualifier_window_count is not None
    assert short.qualifier_window_count > len(short.events) > 0
    for left, right in zip(short.events, short.events[1:], strict=False):
        assert left.end_index <= right.start_index
        assert left.end_index < right.end_index
    crashed = _rising(22)
    crashed[-1] = Decimal("1")
    failed = _family(sustained_advances(crashed), "sustained_advance", "1m")
    assert failed.events == ()


def test_an_unconfirmed_terminal_rise_is_not_a_bull() -> None:
    closes = _rising(140)
    open_rally = _family(persistent_and_early_bulls(closes), "persistent_bull", "20pct")
    assert open_rally.events == ()
    assert open_rally.censored_count == 1
    confirmed = closes + [closes[-1] * Decimal("0.7")]
    bulls = _family(persistent_and_early_bulls(confirmed), "persistent_bull", "20pct")
    assert len(bulls.events) == 1
    assert bulls.events[0].label_uses_later_prices is True
    assert bulls.events[0].historically_observable_at_event_date is False
    assert bulls.censored_count == 0
    early = _family(persistent_and_early_bulls(confirmed), "early_bull", "63s")
    assert len(early.events) == 1
    assert early.events[0].end_index == early.events[0].start_index + 63


def test_short_confirmed_swings_are_not_persistent_bulls() -> None:
    closes = _closes("100", "130", "100")
    swings, censored = confirmed_upswings(closes, Decimal("0.20"), Decimal("0.20"))
    assert len(swings) == 1 and censored == 0
    bulls = _family(persistent_and_early_bulls(closes), "persistent_bull", "20pct")
    assert bulls.events == ()


def test_recovery_requires_a_return_to_the_peak() -> None:
    recovered = _family(
        recoveries(_closes("100", "100", "80", "100")), "drawdown_recovery", "15pct"
    )
    assert len(recovered.events) == 1
    assert recovered.censored_count == 0
    still_open = _family(recoveries(_closes("100", "80", "85")), "drawdown_recovery", "15pct")
    assert still_open.events == ()
    assert still_open.censored_count == 1


def test_failed_rally_stops_when_the_rise_reaches_15_percent() -> None:
    failed = failed_rallies(_closes("100", "109", "100"))
    assert len(failed.events) == 1
    reached = failed_rallies(_closes("100", "116", "100"))
    assert reached.events == ()
    above_trough = failed_rallies(_closes("100", "110", "101"))
    assert above_trough.events == ()


def test_flat_band_takes_priority_over_negative() -> None:
    flat_closes = [Decimal("100")] * 126 + [Decimal("98")]
    counts = negative_and_flat(flat_closes)
    assert len(_family(counts, "flat_market", "6m").events) == 1
    assert _family(counts, "negative_market", "6m").events == ()
    down = [Decimal("100")] * 126 + [Decimal("90")]
    negative = negative_and_flat(down)
    assert len(_family(negative, "negative_market", "6m").events) == 1
    assert _family(negative, "flat_market", "6m").events == ()


def test_relative_performance_does_not_convert_currency() -> None:
    dates = tuple(_dates(260, date(2020, 1, 1)))
    flat = tuple(Decimal("100") for _ in dates)
    riser = flat[:-8] + tuple(Decimal("130") for _ in range(8))
    listings = [
        ListingSeries("AAA", "USD", dates, riser),
        ListingSeries("BBB", "USD", dates, flat),
        ListingSeries("CCC", "USD", dates, flat),
        ListingSeries("DDD", "USD", dates, flat),
        ListingSeries("EUNA", "EUR", dates, riser),
    ]
    counted = relative_and_leadership(listings)
    euna = counted["EUNA"]
    assert all(item.status == "blocked" and item.events == () for item in euna)
    relative = _family(counted["AAA"], "relative_outperformance", "12m")
    assert len(relative.events) == 1
    assert relative.events[0].label_uses_later_prices is True


def test_leadership_uses_only_the_dollar_listings_and_past_closes() -> None:
    dates = tuple(_dates(400, date(2019, 1, 1)))
    steady = tuple(Decimal(100 + index) for index in range(400))
    late = tuple(Decimal("100") if index < 300 else Decimal("1000") for index in range(400))
    quiet = tuple(Decimal("100") for _ in dates)
    listings = [
        ListingSeries("AAA", "USD", dates, steady),
        ListingSeries("BBB", "USD", dates, late),
        ListingSeries("CCC", "USD", dates, quiet),
        ListingSeries("EUNA", "EUR", dates, late),
    ]
    counted = relative_and_leadership(listings)
    assert counted["EUNA"][1].status == "blocked"
    moves = _family(counted["BBB"], "leadership_transition", "12m")
    assert len(moves.events) >= 1
    assert moves.events[0].historically_observable_at_event_date is True
    assert moves.events[0].label_uses_later_prices is False
    assert "not a signal" in moves.events[0].detail


def test_the_condition_ignores_later_prices() -> None:
    closes = [Decimal("100")] * 400
    for index in range(160, 220):
        closes[index] = Decimal("80")
    closes[252] = Decimal("90")
    assert condition_at(closes, 252) is True
    mutated = list(closes)
    mutated[253:] = [Decimal("1")] * (len(mutated) - 253)
    assert condition_at(mutated, 252) is True
    original_label, _original_return = outcome_at(closes, 252)
    changed_label, _changed_return = outcome_at(mutated, 252)
    assert original_label is not changed_label
    flat = [Decimal("100")] * 400
    assert condition_at(flat, 252) is False


def test_month_end_controls_are_not_chosen_by_the_later_return() -> None:
    dates = _dates(700, date(2019, 1, 1))
    closes = [Decimal("100")] * 700
    for index in range(160, 220):
        closes[index] = Decimal("80")
    closes[252] = Decimal("90")
    rows = evaluate_listing("AAA", dates, closes)
    assert rows
    assert all(row.selected_on_future_return is False for row in rows)
    assert any(row.condition_met for row in rows)
    assert any(not row.condition_met for row in rows)
    assert {row.decision_date.day for row in rows} != {15}


def test_status_rule_rejects_a_common_or_uninformative_pattern() -> None:
    def symbol(name: str, eligible: int, condition: int, event: int, both: int) -> SymbolFrequency:
        return SymbolFrequency(name, eligible, condition, event, both)

    common = [symbol(f"S{index}", 20, 10, 8, 5) for index in range(5)]
    status, reasons = assign_pilot_status(common)
    assert status == "rejected"
    assert any("common" in reason for reason in reasons)

    no_lift = [symbol(f"S{index}", 20, 4, 10, 2) for index in range(5)]
    assert assign_pilot_status(no_lift)[0] == "rejected"

    accompanies = [symbol(f"S{index}", 40, 8, 8, 7) for index in range(5)]
    status, reasons = assign_pilot_status(accompanies)
    assert status == "rejected"
    assert any("accompanies" in reason for reason in reasons)

    informative = [symbol(f"S{index}", 40, 6, 8, 4) for index in range(5)]
    assert assign_pilot_status(informative)[0] == "inconclusive"

    short = [symbol(f"S{index}", 40, 6, 8, 4) for index in range(4)]
    assert assign_pilot_status(short)[0] == "insufficient_data"
    assert FORBIDDEN_CLAIM_STATUSES == (
        "statistically_supported",
        "economically_useful",
        "forward_validated",
    )


def test_event_modules_do_not_score_a_portfolio_or_read_observation_values() -> None:
    package = ROOT / "workers" / "research" / "src" / "aqil_research" / "long_horizon" / "events"
    for path in package.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "raw_value" not in text
        assert "run_frozen_comparison" not in text
        assert "simulate(" not in text
