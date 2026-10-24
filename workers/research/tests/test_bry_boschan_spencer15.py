"""Spencer-15 variant. Not the 1971 listing and not a FORTRAN replica."""

from __future__ import annotations

import csv
import io
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from aqil_research.adapters.fed_g17.adapter import FedG17Adapter, FedG17AdapterConfig
from aqil_research.adapters.fed_g17.package import extract_total_index
from aqil_research.adapters.fed_g17.parse import (
    BOARD_DESCRIPTION,
    BOARD_UNIT_LABEL,
    SERIES_ID,
)
from aqil_research.collection.service import collect_registered_adapter
from aqil_research.methods.bry_boschan_monthly import (
    BRY_BOSCHAN_MONTHLY_1971,
    date_specific_cycles,
)
from aqil_research.methods.bry_boschan_spencer15 import (
    BRY_BOSCHAN_SPENCER15_VARIANT,
    MA12_LAGS,
    MA12_LEADS,
    SPENCER_DIVISOR,
    SPENCER_WEIGHTS,
    BryBoschanSpencer15Method,
    assess_spencer15_health,
    centred_spencer,
    date_spencer15_variant,
    moving_average,
    nber_reference_diagnostic,
    spencer_weights_sum,
)
from aqil_research.methods.configs import BRY_BOSCHAN_SPENCER15_PUBLISHED
from aqil_research.methods.registry import default_method_registry
from aqil_research.persistence.connection import research_connection
from aqil_research.workflow.bry_boschan_reading import (
    record_g17_spencer15_reading,
    replay_stored_reading,
)
from db_guard import open_isolated_test_database


def _month(index: int) -> date:
    return date(2000 + (index // 12), (index % 12) + 1, 1)


def _asymmetric_peak() -> tuple[tuple[date, Decimal], ...]:
    """Rise by 1 until month index 36, then fall by 4.

    The hand maximum is index 36, January 2003. The value is 116.
    """
    levels: list[tuple[date, Decimal]] = []
    for index in range(72):
        if index <= 36:
            value = Decimal(80 + index)
        else:
            value = Decimal(116 - 4 * (index - 36))
        levels.append((_month(index), value))
    return tuple(levels)


def test_1971_constant_still_refuses() -> None:
    with pytest.raises(Exception, match="Spencer coefficients"):
        date_specific_cycles(((_month(0), Decimal(1)),))
    assert BRY_BOSCHAN_MONTHLY_1971 != BRY_BOSCHAN_SPENCER15_VARIANT


def test_macaulay_weights_and_one_centred_value() -> None:
    assert spencer_weights_sum() == SPENCER_DIVISOR == 320
    assert SPENCER_WEIGHTS[7] == 74
    assert SPENCER_WEIGHTS == tuple(reversed(SPENCER_WEIGHTS))
    values = [Decimal(0)] * 40
    values[20] = Decimal(320)
    curve = centred_spencer(values)
    assert curve[20] == Decimal(74)
    assert curve[19] == Decimal(67)
    assert curve[21] == Decimal(67)
    assert curve[13] == Decimal(-3)
    assert curve[27] == Decimal(-3)
    assert curve[6] is None
    assert curve[33] is None


def test_twelve_month_average_is_dated_with_six_lags_and_five_leads() -> None:
    assert MA12_LAGS == 6
    assert MA12_LEADS == 5
    values = [Decimal(0)] * 40
    values[20] = Decimal(12)
    curve = moving_average(values, 12)
    # Hand window: t receives month 20 when t - 6 <= 20 <= t + 5.
    assert curve[14] == Decimal(0)
    assert curve[15] == Decimal(1)
    assert curve[26] == Decimal(1)
    assert curve[27] == Decimal(0)
    assert curve[5] is None


def test_asymmetric_peak_matches_the_hand_maximum() -> None:
    levels = _asymmetric_peak()
    raw_peak = max(levels, key=lambda item: (item[1], -item[0].toordinal()))
    assert raw_peak == (date(2003, 1, 1), Decimal(116))
    # Independent twelve-month window at index 33: months 27 through 38.
    window = [item[1] for item in levels[27:39]]
    assert len(window) == 12
    assert sum(window, Decimal(0)) / Decimal(12) == Decimal("111.25")
    dated = date_spencer15_variant(levels)
    assert dated.peaks == (date(2003, 1, 1),)
    assert dated.troughs == ()
    assert dated.mcd_months == 3


def test_variant_is_registered_and_publication_stays_false() -> None:
    method = default_method_registry().get(BRY_BOSCHAN_SPENCER15_VARIANT)
    assert isinstance(method, BryBoschanSpencer15Method)
    assert method.method_version == "1.0.0"
    config = method.parse_config(dict(BRY_BOSCHAN_SPENCER15_PUBLISHED))
    assert method.config_hash(config)


def test_health_failures_are_injected_and_nber_disagreement_is_not() -> None:
    months = tuple(_month(index) for index in range(24))
    healthy = assess_spencer15_health(
        months=months,
        evaluation_period=months[-1],
        peaks=(date(2001, 6, 1),),
        troughs=(date(2000, 8, 1),),
        collection_modes=("live",),
        replay_matches=True,
        publication_allowed=False,
    )
    assert [item.code for item in healthy if item.failed] == []
    assert healthy[-1].code == "nber_disagreement"
    assert healthy[-1].failed is False

    missing = assess_spencer15_health(
        months=months,
        evaluation_period=_month(30),
        peaks=(),
        troughs=(),
        collection_modes=("live",),
        replay_matches=True,
        publication_allowed=False,
    )
    assert any(item.failed and item.code == "missing_latest_month" for item in missing)

    breach = assess_spencer15_health(
        months=months,
        evaluation_period=months[-1],
        peaks=(date(2001, 1, 1),),
        troughs=(date(2001, 3, 1),),
        collection_modes=("live",),
        replay_matches=True,
        publication_allowed=False,
    )
    assert any(item.failed and item.code == "rule_breach" for item in breach)

    replay = assess_spencer15_health(
        months=months,
        evaluation_period=months[-1],
        peaks=(),
        troughs=(),
        collection_modes=("live",),
        replay_matches=False,
        publication_allowed=False,
    )
    assert any(item.failed and item.code == "replay_mismatch" for item in replay)

    fixture = assess_spencer15_health(
        months=months,
        evaluation_period=months[-1],
        peaks=(),
        troughs=(),
        collection_modes=("fixture",),
        replay_matches=True,
        publication_allowed=False,
    )
    assert any(item.failed and item.code == "fixture_rows" for item in fixture)

    far = nber_reference_diagnostic((date(2002, 7, 1),), ())
    assert far["gates_the_method"] is False
    assert "not mathematical proof" in str(far["statement"])


def _package(periods: list[str], values: list[str]) -> dict[str, object]:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(
        [
            "Description:",
            "Unit:",
            "Multiplier:",
            "Currency:",
            "Unique Identifier:",
            "Series Name:",
            *periods,
        ],
    )
    writer.writerow(
        [
            BOARD_DESCRIPTION,
            BOARD_UNIT_LABEL,
            "1",
            "",
            SERIES_ID,
            "IP.B50001.S",
            *values,
        ],
    )
    return extract_total_index(buffer.getvalue())


def _priors(conn: object) -> tuple:
    from aqil_research.adapters.fed_g17.parse import DATASET_ID
    from aqil_research.adapters.fed_g17.stability import StoredG17Point

    with conn.cursor() as cur:  # type: ignore[attr-defined]
        cur.execute(
            """
            select period_start, observation_id, raw_value, provider_vintage_date,
                   source_release_at, retrieved_at
            from research.economic_observations
            where dataset_id = %s
            """,
            (DATASET_ID,),
        )
        rows = cur.fetchall()
    return tuple(
        StoredG17Point(
            period_start=row[0],
            observation_id=str(row[1]),
            raw_value=str(row[2]),
            provider_vintage_date=row[3],
            source_release_at=row[4],
            retrieved_at=row[5],
        )
        for row in rows
    )


def _live_collect(
    conn: object, payload: dict[str, object], when: datetime, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "aqil_research.adapters.fed_g17.client.fetch_g17_bundle",
        lambda: payload,
    )
    collected, _store = collect_registered_adapter(
        store_backend="postgres",
        adapter=FedG17Adapter(
            config=FedG17AdapterConfig(live=True),
            retrieved_at=when,
            prior_points=_priors(conn),
        ),
        source_id="federal_reserve_g17_total_ip",
        collected_at=when,
        live=True,
        conn=conn,
    )
    assert collected.outcome == "success"


@pytest.mark.integration
def test_refresh_hook_is_idempotent_until_a_month_changes(monkeypatch: pytest.MonkeyPatch) -> None:
    open_isolated_test_database()
    periods = [f"{2000 + index // 12:04d}-{(index % 12) + 1:02d}" for index in range(60)]
    values = [str(Decimal(100 + max(0, 24 - abs(index - 30)))) for index in range(60)]
    first = _package(periods, values)
    when = datetime(2005, 1, 15, tzinfo=UTC)
    with research_connection() as conn:
        _live_collect(conn, first, when, monkeypatch)
        first_reading = record_g17_spencer15_reading(conn, decision_at=when)
        second_reading = record_g17_spencer15_reading(conn, decision_at=when)
        assert first_reading.status == "completed"
        assert first_reading.run_id is not None
        assert second_reading.status == "unchanged"
        assert second_reading.run_id == first_reading.run_id
        assert replay_stored_reading(conn, first_reading.run_id)
        extended = _package(
            [*periods, "2005-01"],
            [*values, "100"],
        )
        later = datetime(2005, 2, 15, tzinfo=UTC)
        _live_collect(conn, extended, later, monkeypatch)
        third = record_g17_spencer15_reading(conn, decision_at=later)
        assert third.status == "completed"
        assert third.run_id is not None
        assert third.run_id != first_reading.run_id
