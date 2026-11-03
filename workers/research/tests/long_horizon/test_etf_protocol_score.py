"""Grid scoring without a database write."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from aqil_research.long_horizon.etf_protocol.rules import stored_direction_sign
from aqil_research.long_horizon.etf_protocol.score import AnchorState, score_dossier
from aqil_research.long_horizon.etf_protocol.specification import HORIZONS, declare_trials


def test_stored_direction_uses_the_sign_of_the_latest_change() -> None:
    assert stored_direction_sign("up") == Decimal(1)
    assert stored_direction_sign("flat") == Decimal(0)
    assert stored_direction_sign("down") == Decimal(-1)


def test_scored_rows_match_the_declared_grid_and_methods_have_no_effect() -> None:
    keys = declare_trials((), ("METHOD_A",))
    vwra = [key for key in keys if key.symbol == "VWRA"]
    anchors = [
        AnchorState(
            date(2020, 1, 31),
            {},
            {horizon: None for horizon in HORIZONS},
            {},
            None,
        )
    ]
    first = score_dossier(
        vwra,
        anchors,
        method_replay={"METHOD_A": "unavailable_input"},
        citations={},
        kind="single",
    )
    second = score_dossier(
        vwra,
        anchors,
        method_replay={"METHOD_A": "unavailable_input"},
        citations={},
        kind="single",
    )
    assert len(first.records) == len(vwra)
    assert [record.key.identity() for record in first.records] == [key.identity() for key in vwra]
    assert first.records == second.records
    methods = [record for record in first.records if record.key.kind == "method_refusal"]
    assert methods
    assert all(record.effect is None and record.result is None for record in methods)
    searches = [record for record in first.records if record.key.kind == "search_refusal"]
    assert [record.refusal for record in searches] == ["not_estimable_effective_sample"] * 3
    assert all(record.effect is None for record in searches)
    assert first.policy == "no_policy_registered"
    rising = [
        AnchorState(
            date(2021, month, 28),
            {
                "trailing_return_63": Decimal("0.08"),
                "trailing_return_252": Decimal("0.20"),
                "drawdown_252": Decimal("-0.12"),
                "volatility_63": Decimal("0.02"),
                "recovery_from_prior_trough_252": Decimal("0.04"),
            },
            {horizon: Decimal("0.11") for horizon in HORIZONS},
            {},
            Decimal("0.01"),
        )
        for month in range(1, 9)
    ]
    scored = score_dossier(
        vwra,
        rising,
        method_replay={"METHOD_A": "not_historically_replayed"},
        citations={"LH-E-002": "cited", "LH-E-004": "cited"},
        kind="single",
    )
    assert len(scored.records) == len(vwra)
    spearman = next(
        record
        for record in scored.records
        if record.key.feature == "trailing_return_63"
        and record.key.statistic == "spearman"
        and record.key.horizon_label == "6m"
        and record.key.outcome == "advance"
    )
    assert spearman.refusal == "insufficient_effective_sample" or spearman.effect is not None
    assert scored.status in {
        "insufficient_data",
        "rejected",
        "no_incremental_information",
        "inconclusive",
    }
