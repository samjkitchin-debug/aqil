"""Guards for the frozen EIMI comparison. Live checks skip when the database is down."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import psycopg
import pytest

from aqil_research.long_horizon.pilot import LOCAL_RESEARCH_URL
from aqil_research.long_horizon.vwra_discovery.align import (
    is_market_feature,
    market_values,
    refuse_fx_count,
    state_on_or_before,
)
from aqil_research.long_horizon.vwra_discovery.battery import score_horizons
from aqil_research.long_horizon.vwra_discovery.comparison import (
    FORBIDDEN_PROMOTIONS,
    SPECIFICATION_ID,
    excess_return,
    exclusive_class,
    is_advance,
    match_month_ends,
    portfolio_claim_status,
    specification_document,
)
from aqil_research.long_horizon.vwra_discovery.sequence import sequence_flags

VWRA_ARTIFACTS = {
    "LH-X-001": "cf77b6fb62f02eaf84828549189893dd7c45aaa49f0470cd6754a27ffa19d514",
    "LH-X-008": "5342e697307bab1a035533ffc087346c777596a81233e73c42f5a3f40a3b2b0c",
    "LH-X-009": "882ff96372ff1af1ad4a49c0fc0907b5153032f724db60398933752467a33feb",
    "LH-X-010": "47c80b5dd2402b88aa2578b0f60682e2246b1769d7459c1e3547e78f47493eaa",
    "LH-X-011": "6495408b4a4136052fe8ff881d14b1c27648838851c17c1baafac80e0bfdfe4c",
}


def test_matched_dates_use_the_five_day_rule_and_the_listing_date() -> None:
    vwra = (
        ("v-early", date(2019, 7, 24)),
        ("v-near", date(2019, 8, 30)),
        ("v-far", date(2019, 10, 31)),
    )
    eimi = (
        ("e-early", date(2019, 7, 24)),
        ("e-five", date(2019, 8, 25)),
        ("e-ten", date(2019, 10, 21)),
        ("e-closer", date(2019, 8, 28)),
    )
    paired = match_month_ends(vwra, eimi)
    assert all(item[1] >= date(2019, 7, 25) for item in paired)
    by_vwra = {item[0]: item for item in paired}
    assert "v-early" not in by_vwra
    assert "v-far" not in by_vwra
    assert by_vwra["v-near"][2] == "e-closer"
    assert by_vwra["v-near"][4] == 2
    assert excess_return(None, Decimal("0.10")) is None
    assert excess_return(Decimal("0.02"), None) is None


def test_each_eimi_anchor_is_used_once_and_the_earlier_session_wins_a_tie() -> None:
    vwra = (("v1", date(2020, 1, 31)), ("v2", date(2020, 2, 28)))
    eimi = (("e-late", date(2020, 2, 3)), ("e-early", date(2020, 1, 31)))
    paired = match_month_ends(vwra, eimi)
    assert [item[2] for item in paired] == ["e-early"]
    assert paired[0][4] == 0


def test_a_later_price_state_is_dropped_and_an_outcome_is_not_a_state() -> None:
    shared = date(2020, 1, 31)
    assert market_values(date(2020, 2, 3), shared, {"trailing_return_63": "0.05"}) == {}
    assert market_values(shared, shared, {"trailing_return_63": "0.05"}) == {
        "trailing_return_63": "0.05"
    }
    assert is_market_feature("split_adjusted_close") is True
    assert state_on_or_before("trailing_return_63", date(2020, 2, 1), shared, "0.05") is None
    with pytest.raises(ValueError, match="outcome"):
        state_on_or_before("outcome_return_126", shared, shared, "0.05")


def test_no_foreign_exchange_rate_is_invented() -> None:
    refuse_fx_count(0)
    with pytest.raises(ValueError, match="fx_observations"):
        refuse_fx_count(1)


def test_exclusive_classes_partition_zero_and_do_not_promote() -> None:
    assert exclusive_class(Decimal("0.02"), Decimal("0.01")) == "eimi_ahead_both_positive"
    assert exclusive_class(Decimal("0.02"), Decimal("-0.01")) == "eimi_positive_vwra_negative"
    assert exclusive_class(Decimal("-0.02"), Decimal("-0.04")) == "both_negative_eimi_declines_less"
    assert exclusive_class(Decimal("0.01"), Decimal("0.02")) == "vwra_ahead"
    assert exclusive_class(Decimal("0"), Decimal("0")) == "no_sign"
    rows = score_horizons(
        [
            {"EIMI:126": Decimal("0.20"), "VWRA:126": Decimal("0.05")},
            {"EIMI:126": None, "VWRA:126": Decimal("0.05")},
        ]
    )
    accounted = sum(row.trial.result_text is not None for row in rows) + sum(
        row.trial.refusal_reason is not None for row in rows
    )
    assert accounted == len(rows)
    censored = [
        row for row in rows if row.trial.feature == "censored" and row.trial.outcome == "excess_126"
    ]
    assert censored and censored[0].trial.result_text == "1"
    assert (
        portfolio_claim_status(
            reconciled=True,
            passive_terminal=Decimal("10"),
            alternatives={"eimi": Decimal("11")},
        )
        == "inconclusive"
    )
    assert (
        portfolio_claim_status(
            reconciled=True,
            passive_terminal=Decimal("10"),
            alternatives={"eimi": Decimal("9")},
        )
        == "rejected"
    )
    assert (
        portfolio_claim_status(
            reconciled=False,
            passive_terminal=Decimal("10"),
            alternatives={"eimi": Decimal("11")},
        )
        == "insufficient_data"
    )
    for status in (
        portfolio_claim_status(
            reconciled=True, passive_terminal=Decimal("1"), alternatives={"eimi": Decimal("2")}
        ),
        "rejected",
        "insufficient_data",
    ):
        assert status not in FORBIDDEN_PROMOTIONS


def test_the_sequence_was_not_retuned_to_the_five_percent_binary() -> None:
    flags = sequence_flags(["0.03", "0.02", "0.02"], [None, None, "0.01"])
    assert flags == [False, False, True]
    assert is_advance(Decimal("0.10")) is True
    document = specification_document()
    assert document["divergence_excess"] == "0.10"
    assert document["publication_allowed"] is False
    assert "0.05" in str(document["sequence_implementation"])
    assert document["sequence"]["momentum_sign"] == "positive"


def test_vwra_discovery_rows_stay_unchanged() -> None:
    try:
        connection = psycopg.connect(LOCAL_RESEARCH_URL, connect_timeout=3)
    except psycopg.OperationalError:
        pytest.skip("local research database is unavailable")
    with connection:
        connection.read_only = True
        with connection.cursor() as cursor:
            cursor.execute("select to_regclass('research.discovery_v2_trials')")
            if cursor.fetchone()[0] is None:
                pytest.skip("discovery tables are absent")
            cursor.execute(
                """
                select count(*)::int
                from research.discovery_v2_trials
                where specification_id = 'VWRA-DISCOVERY-001'
                """
            )
            assert cursor.fetchone()[0] == 1526
            cursor.execute("select count(*)::int from research.discovery_v2_method_points")
            assert cursor.fetchone()[0] == 21919
            cursor.execute("select count(*)::int from research.discovery_v2_method_runs")
            assert cursor.fetchone()[0] == 26
            cursor.execute(
                """
                select count(*)::int
                from research.discovery_v2_anchor_features f
                join research.decision_anchors a on a.anchor_id = f.anchor_id
                where a.symbol = 'VWRA'
                """
            )
            assert cursor.fetchone()[0] == 4040
            cursor.execute(
                """
                select execution_id, artifact_sha256
                from research.experiment_executions
                where execution_id = any(%s)
                order by execution_id
                """,
                (["LH-X-001", "LH-X-008", "LH-X-009", "LH-X-010", "LH-X-011"],),
            )
            found = {row[0]: row[1] for row in cursor.fetchall()}
    assert set(found) == {"LH-X-001", "LH-X-008", "LH-X-009", "LH-X-010", "LH-X-011"}
    for execution_id, digest in VWRA_ARTIFACTS.items():
        assert found[execution_id] == digest


def test_second_comparison_run_inserts_nothing() -> None:
    try:
        connection = psycopg.connect(LOCAL_RESEARCH_URL, connect_timeout=3)
    except psycopg.OperationalError:
        pytest.skip("local research database is unavailable")
    with connection:
        connection.read_only = True
        with connection.cursor() as cursor:
            cursor.execute("select to_regclass('research.experiment_executions')")
            if cursor.fetchone()[0] is None:
                pytest.skip("executions are absent")
            cursor.execute(
                """
                select count(*)::int
                from research.experiment_executions
                where execution_id = 'LH-X-012'
                """
            )
            if cursor.fetchone()[0] == 0:
                pytest.skip("the comparison has not been stored")
    from aqil_research.long_horizon.vwra_discovery.compare import run

    result = run(persist=True)
    assert result["inserted_executions"] == 0
    assert result["coverage"]["publication_allowed"] is False
    assert SPECIFICATION_ID == "EIMI-VWRA-COMPARISON-001"
