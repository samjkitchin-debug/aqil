"""Spencer-15 variant. Not the 1971 listing and not a FORTRAN replica."""

from __future__ import annotations

import csv
import io
import math
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
from aqil_research.contracts.observation import (
    AnalysisMode,
    AvailabilityPrecision,
    EconomicObservation,
    Frequency,
    QualityStatus,
    SeasonalAdjustment,
    SeriesProvenance,
)
from aqil_research.methods.bry_boschan_monthly import (
    BRY_BOSCHAN_MONTHLY_1971,
    G17_DATASET_ID,
    date_specific_cycles,
)
from aqil_research.methods.bry_boschan_spencer15 import (
    BRY_BOSCHAN_SPENCER15_VARIANT,
    CHRONOLOGY_CLASS,
    ENDPOINT_BAN_MONTHS,
    MA12_LAGS,
    MA12_LEADS,
    MINIMUM_CYCLE_MONTHS,
    MINIMUM_PHASE_MONTHS,
    SPENCER_DIVISOR,
    SPENCER_WEIGHTS,
    BryBoschanSpencer15Method,
    _drop_endpoints,
    _drop_short_cycles,
    _drop_short_phases,
    _enforce_alternation,
    _Turn,
    assess_spencer15_health,
    centred_spencer,
    date_spencer15_variant,
    legacy_variant_implementation_hash,
    length_bound_sensitivity,
    moving_average,
    nber_reference_diagnostic,
    spencer_weights_sum,
)
from aqil_research.methods.configs import BRY_BOSCHAN_SPENCER15_PUBLISHED
from aqil_research.methods.protocol import MethodContext
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


def _month_gap(left: date, right: date) -> int:
    return abs((left.year - right.year) * 12 + (left.month - right.month))


def test_alternation_keeps_the_more_extreme_contiguous_turn() -> None:
    turns = [
        _Turn(10, "peak", Decimal(3)),
        _Turn(14, "peak", Decimal(8)),
        _Turn(30, "trough", Decimal(1)),
        _Turn(34, "trough", Decimal(0)),
    ]
    kept = _enforce_alternation(turns)
    assert [turn.kind for turn in kept] == ["peak", "trough"]
    assert kept[0].index == 14
    assert kept[1].index == 34


def test_short_phase_uses_the_five_month_constant() -> None:
    short_end = 20 + MINIMUM_PHASE_MONTHS - 1
    kept_end = 50 + MINIMUM_PHASE_MONTHS
    turns = [
        _Turn(20, "peak", Decimal(5)),
        _Turn(short_end, "trough", Decimal(1)),
        _Turn(50, "peak", Decimal(6)),
        _Turn(kept_end, "trough", Decimal(2)),
    ]
    kept = _drop_short_phases(turns)
    indexes = [turn.index for turn in kept]
    assert short_end not in indexes
    assert kept_end in indexes
    assert MINIMUM_PHASE_MONTHS == 5


def test_short_cycle_uses_the_fifteen_month_constant() -> None:
    short_peak = 10 + MINIMUM_CYCLE_MONTHS - 1
    kept_trough = 40 + MINIMUM_CYCLE_MONTHS
    turns = [
        _Turn(10, "peak", Decimal(5)),
        _Turn(short_peak, "peak", Decimal(9)),
        _Turn(40, "trough", Decimal(1)),
        _Turn(kept_trough, "trough", Decimal(2)),
    ]
    kept = {(turn.kind, turn.index) for turn in _drop_short_cycles(turns)}
    assert ("peak", 10) not in kept
    assert ("peak", short_peak) in kept
    assert ("trough", 40) in kept
    assert ("trough", kept_trough) in kept
    assert MINIMUM_CYCLE_MONTHS == 15


def test_endpoint_censor_uses_the_six_month_constant() -> None:
    size = 48
    banned_start = ENDPOINT_BAN_MONTHS - 1
    allowed_start = ENDPOINT_BAN_MONTHS
    allowed_end = size - 1 - ENDPOINT_BAN_MONTHS
    banned_end = allowed_end + 1
    turns = [
        _Turn(banned_start, "peak", Decimal(1)),
        _Turn(allowed_start, "trough", Decimal(1)),
        _Turn(allowed_end, "peak", Decimal(1)),
        _Turn(banned_end, "trough", Decimal(1)),
    ]
    kept = [turn.index for turn in _drop_endpoints(turns, size)]
    assert kept == [allowed_start, allowed_end]
    relaxed = [turn.index for turn in _drop_endpoints(turns, size, endpoint_ban_months=0)]
    assert relaxed == [banned_start, allowed_start, allowed_end, banned_end]
    assert ENDPOINT_BAN_MONTHS == 6


def test_dated_output_obeys_alternation_phase_cycle_and_endpoint_rules() -> None:
    levels = []
    for index in range(240):
        raw = 100 + 40 * math.sin(2 * math.pi * index / 48)
        levels.append((_month(index), Decimal(str(raw))))
    dated = date_spencer15_variant(tuple(levels))
    combined = sorted(
        [("peak", item) for item in dated.peaks] + [("trough", item) for item in dated.troughs],
        key=lambda item: item[1],
    )
    assert combined
    first = levels[0][0]
    last = levels[-1][0]
    for index in range(len(combined) - 1):
        assert combined[index][0] != combined[index + 1][0]
        assert _month_gap(combined[index][1], combined[index + 1][1]) >= MINIMUM_PHASE_MONTHS
    for kind in ("peak", "trough"):
        group = [item[1] for item in combined if item[0] == kind]
        for index in range(len(group) - 1):
            assert _month_gap(group[index], group[index + 1]) >= MINIMUM_CYCLE_MONTHS
    for _kind, turn in combined:
        assert _month_gap(turn, first) >= ENDPOINT_BAN_MONTHS
        assert _month_gap(turn, last) >= ENDPOINT_BAN_MONTHS


def test_length_bound_sensitivity_is_separate_from_production_dates() -> None:
    levels = _asymmetric_peak()
    production = date_spencer15_variant(levels)
    repeated = date_spencer15_variant(
        levels,
        minimum_cycle_months=MINIMUM_CYCLE_MONTHS,
        minimum_phase_months=MINIMUM_PHASE_MONTHS,
        endpoint_ban_months=ENDPOINT_BAN_MONTHS,
    )
    assert repeated.peaks == production.peaks
    assert repeated.troughs == production.troughs
    diagnostic = length_bound_sensitivity(levels)
    assert diagnostic["replaces_production_chronology"] is False
    assert diagnostic["production_bounds"] == {
        "minimum_cycle_months": MINIMUM_CYCLE_MONTHS,
        "minimum_phase_months": MINIMUM_PHASE_MONTHS,
        "endpoint_ban_months": ENDPOINT_BAN_MONTHS,
    }
    assert diagnostic["production_peak_count"] == len(production.peaks)
    assert diagnostic["production_trough_count"] == len(production.troughs)
    phase_case = diagnostic["without_five_month_phase_rule"]
    endpoint_case = diagnostic["without_six_month_endpoint_ban"]
    assert isinstance(phase_case, dict)
    assert isinstance(endpoint_case, dict)
    assert phase_case["bounds"]["minimum_phase_months"] == 1
    assert phase_case["bounds"]["minimum_cycle_months"] == MINIMUM_CYCLE_MONTHS
    assert endpoint_case["bounds"]["endpoint_ban_months"] == 0
    assert endpoint_case["bounds"]["minimum_phase_months"] == MINIMUM_PHASE_MONTHS
    unchanged = date_spencer15_variant(levels)
    assert unchanged.peaks == production.peaks
    assert unchanged.troughs == production.troughs


def test_method_labels_the_chronology_retrospective_full_sample() -> None:
    levels = _asymmetric_peak()
    series = {period: _g17_observation(period, value) for period, value in levels}
    context = MethodContext(
        inputs_by_dataset={G17_DATASET_ID: series},
        evaluation_period=max(series),
        analysis_mode=AnalysisMode.LATEST_REVISED,
        primary_dataset_id=G17_DATASET_ID,
    )
    method = BryBoschanSpencer15Method()
    result = method.run(context, method.parse_config(dict(BRY_BOSCHAN_SPENCER15_PUBLISHED)))
    assert result.sufficiency == "sufficient"
    assert result.calculation is not None
    assert result.calculation["chronology_class"] == CHRONOLOGY_CLASS
    assert result.calculation["contemporaneous_recession_call"] is False
    assert result.calculation["centred_spencer_smoother"] is True
    assert result.calculation["publication_allowed"] is False
    revision = result.calculation["revision_sensitivity"]
    assert isinstance(revision, dict)
    assert revision["status"] == "blocked"
    sensitivity = result.calculation["length_bound_sensitivity"]
    assert isinstance(sensitivity, dict)
    assert sensitivity["replaces_production_chronology"] is False
    diagnostic = result.calculation["nber_reference_diagnostic"]
    assert isinstance(diagnostic, dict)
    assert diagnostic["gates_the_method"] is False
    assert "centred Spencer smoother" in result.narrative
    assert "retrospective full sample" in result.narrative


def test_legacy_revision_keeps_dating_lists_and_omits_new_diagnostics() -> None:
    levels = _asymmetric_peak()
    series = {period: _g17_observation(period, value) for period, value in levels}
    context = MethodContext(
        inputs_by_dataset={G17_DATASET_ID: series},
        evaluation_period=max(series),
        analysis_mode=AnalysisMode.LATEST_REVISED,
        primary_dataset_id=G17_DATASET_ID,
    )
    config = dict(BRY_BOSCHAN_SPENCER15_PUBLISHED)
    current = default_method_registry().get(BRY_BOSCHAN_SPENCER15_VARIANT)
    legacy = BryBoschanSpencer15Method(payload_revision="legacy")
    assert current.implementation_hash() != legacy.implementation_hash()
    assert legacy.implementation_hash() == legacy_variant_implementation_hash()
    current_result = current.run(context, current.parse_config(config))
    legacy_result = legacy.run(context, legacy.parse_config(config))
    assert current_result.calculation is not None
    assert legacy_result.calculation is not None
    assert legacy_result.calculation["peaks"] == current_result.calculation["peaks"]
    assert legacy_result.calculation["troughs"] == current_result.calculation["troughs"]
    assert legacy_result.calculation["publication_allowed"] is False
    assert "chronology_class" not in legacy_result.calculation
    assert "length_bound_sensitivity" not in legacy_result.calculation
    assert "nber_reference_diagnostic" not in legacy_result.calculation
    assert "retrospective full sample" not in legacy_result.narrative
    assert current_result.calculation["chronology_class"] == CHRONOLOGY_CLASS


def _g17_observation(period: date, value: Decimal) -> EconomicObservation:
    retrieved = datetime(2026, 10, 25, 8, 0, tzinfo=UTC)
    return EconomicObservation(
        observation_id=f"g17-{period.isoformat()}",
        dataset_id=G17_DATASET_ID,
        provider_id="federal_reserve_board",
        source_id="federal_reserve_g17_total_ip",
        rights_record_id="federal_reserve_g17_total_ip",
        period_start=period,
        frequency=Frequency.MONTHLY,
        geography="US",
        unit="index_2017_100",
        seasonal_adjustment=SeasonalAdjustment.SEASONALLY_ADJUSTED,
        raw_value=format(value, "f"),
        quality_status=QualityStatus.OBSERVED,
        series_provenance=SeriesProvenance.LATEST_REVISED,
        provider_vintage_date=date(2026, 10, 17),
        availability_precision=AvailabilityPrecision.UNKNOWN,
        retrieved_at=retrieved,
        first_seen_at=retrieved,
        adapter_version="spencer15_label_test_v1",
    )


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
