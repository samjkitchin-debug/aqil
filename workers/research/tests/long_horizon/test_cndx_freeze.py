"""Guards for the frozen CNDX comparison. The scorer is not the first writer."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import psycopg
import pytest

from aqil_research.long_horizon.pilot import LOCAL_RESEARCH_URL
from aqil_research.long_horizon.vwra_discovery.battery import score_horizons
from aqil_research.long_horizon.vwra_discovery.cndx_comparison import (
    EXCLUSIVE_CLASSES,
    EXCLUSIVE_RENAME,
    HYPOTHESES,
    excess_survives_price_control,
    matched_floor,
    refuse_before_listing,
    relative_classification,
    specification_document,
    specification_hash,
)
from aqil_research.long_horizon.vwra_discovery.comparison import specification_hash as eimi_hash
from aqil_research.long_horizon.vwra_discovery.lh017_correction import (
    ORIGINAL_SENTENCE,
    STORED_CASEBOOK_COUNTS,
    stored_sentence,
)
from aqil_research.long_horizon.vwra_discovery.portfolio_rule import RelativeMomentumPolicy

EIMI_SPECIFICATION_HASH = "d59b453d69ffd52b5eeaac8e611fe653d5fd858addb9182f485f6f9415571e37"


def test_lh017_sentence_quotes_the_stored_casebook_counts() -> None:
    sentence = stored_sentence()
    assert "EIMI ahead 5" in sentence
    assert "VWRA ahead 4" in sentence
    assert "both advance 25" in sentence
    assert "both decline 7" in sentence
    assert "leadership reversal 0" in sentence
    assert "approximately neutral 73" in sentence
    assert STORED_CASEBOOK_COUNTS["eimi_ahead"] == 5
    assert ORIGINAL_SENTENCE == "LH-E-017 has no stored result."


def test_cndx_thresholds_match_the_frozen_eimi_rule_and_do_not_invent_a_total_return() -> None:
    document = specification_document()
    assert document["publication_allowed"] is False
    assert document["price_type"] == "adjusted_close"
    assert document["total_return"] == "not_represented"
    assert document["divergence_excess"] == "0.10"
    assert document["advance_minimum"] == "0.10"
    assert document["sequence"]["momentum_sign"] == "positive"
    assert "0.05" in str(document["sequence_implementation"])
    assert "terminal_wealth" not in document
    assert eimi_hash() == EIMI_SPECIFICATION_HASH
    assert len(specification_hash()) == 64
    assert document["forbidden_promotions"] == [
        "statistically_supported",
        "economically_useful",
        "forward_validated",
    ]


def test_default_horizon_labels_stay_on_the_eimi_names() -> None:
    rows = score_horizons([{"EIMI:126": Decimal("0.20"), "VWRA:126": Decimal("0.10")}])
    named = [
        row.trial.feature
        for row in rows
        if row.trial.outcome == "excess_126" and row.trial.result_text == "1"
    ]
    assert "eimi_ahead_both_positive" in named
    assert "cndx_ahead_both_positive" not in named


def test_cndx_horizon_labels_are_renamed_without_editing_the_rule() -> None:
    rows = score_horizons(
        [{"CNDX:126": Decimal("0.20"), "VWRA:126": Decimal("0.10")}],
        peer="CNDX",
        pair_symbol="CNDX-VWRA",
        hypothesis_id="LH-H-023",
        hypotheses=HYPOTHESES,
        class_names=EXCLUSIVE_CLASSES,
        rename=EXCLUSIVE_RENAME,
    )
    named = [
        row
        for row in rows
        if row.trial.outcome == "excess_126" and row.trial.feature == "cndx_ahead_both_positive"
    ]
    assert named
    assert named[0].symbol == "CNDX-VWRA"
    assert named[0].trial.experiment_id == "LH-E-023"
    assert named[0].trial.result_text == "1"


def test_excess_survival_is_a_strict_margin_and_a_missing_value_does_not_survive() -> None:
    assert excess_survives_price_control(Decimal("0.40"), Decimal("0.30")) is True
    assert excess_survives_price_control(Decimal("-0.40"), Decimal("0.30")) is True
    assert excess_survives_price_control(Decimal("0.30"), Decimal("0.30")) is False
    assert excess_survives_price_control(Decimal("0.20"), Decimal("-0.30")) is False
    assert excess_survives_price_control(None, Decimal("0.10")) is False
    assert relative_classification(False, False) == "structural_exposure_or_price_momentum"
    assert relative_classification(True, False) == "excess_partial_survives_price_control"
    assert matched_floor(date(2016, 11, 3), date(2019, 7, 25)) == date(2019, 7, 25)
    with pytest.raises(ValueError, match="before the first stored session"):
        refuse_before_listing(date(2016, 11, 2), date(2016, 11, 3), "CNDX")


def test_the_default_momentum_peer_remains_eimi() -> None:
    policy = RelativeMomentumPolicy({})
    assert policy.peer == "EIMI"
    assert policy.control == "VWRA"
    assert policy.baseline == "VWRA"


def test_lh017_version_one_stays_and_version_two_quotes_the_counts() -> None:
    try:
        connection = psycopg.connect(LOCAL_RESEARCH_URL, connect_timeout=3)
    except psycopg.OperationalError:
        pytest.skip("local research database is unavailable")
    with connection:
        row = connection.execute(
            """
            select proposition
            from research.scientific_claims
            where claim_id = 'LH-C-017' and version = 1
            """
        ).fetchone()
        corrected = connection.execute(
            """
            select proposition
            from research.scientific_claims
            where claim_id = 'LH-C-017' and version = 2
            """
        ).fetchone()
        finding = connection.execute(
            "select statement from research.discovery_v2_findings where finding_id = 'CMP-F-017'"
        ).fetchone()
        evidence = connection.execute(
            """
            select body->>'statement'
            from research.evidence_records
            where evidence_id = 'LH-V-017'
            """
        ).fetchone()
    assert row is not None
    assert row[0] == ORIGINAL_SENTENCE
    assert finding is not None and finding[0] == ORIGINAL_SENTENCE
    assert evidence is not None and evidence[0] == ORIGINAL_SENTENCE
    assert corrected is not None
    assert corrected[0] == stored_sentence()


def test_second_cndx_persist_inserts_nothing_and_leaves_earlier_artifacts() -> None:
    try:
        connection = psycopg.connect(LOCAL_RESEARCH_URL, connect_timeout=3)
    except psycopg.OperationalError:
        pytest.skip("local research database is unavailable")
    with connection:
        found = connection.execute(
            """
            select count(*)::int
            from research.experiment_executions
            where execution_id = any(%s)
            """,
            ([f"LH-X-{index:03d}" for index in range(19, 26)],),
        ).fetchone()
        before = connection.execute(
            """
            select execution_id, artifact_sha256
            from research.experiment_executions
            where execution_id = any(%s)
            order by execution_id
            """,
            ([f"LH-X-{index:03d}" for index in range(1, 19)],),
        ).fetchall()
    if found is None or int(found[0]) != 7:
        pytest.skip("the CNDX comparison has not been stored")
    from aqil_research.long_horizon.vwra_discovery.cndx import run

    result = run(persist=True)
    assert result["inserted_executions"] == 0
    with psycopg.connect(LOCAL_RESEARCH_URL) as again:
        after = again.execute(
            """
            select execution_id, artifact_sha256
            from research.experiment_executions
            where execution_id = any(%s)
            order by execution_id
            """,
            ([f"LH-X-{index:03d}" for index in range(1, 19)],),
        ).fetchall()
    assert after == before
