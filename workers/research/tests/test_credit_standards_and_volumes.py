"""CREDIT_STANDARDS_AND_VOLUMES on a small fixture. No database."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from aqil_research.contracts.observation import (
    AnalysisMode,
    AvailabilityPrecision,
    EconomicObservation,
    Frequency,
    QualityStatus,
    SeasonalAdjustment,
    SeriesProvenance,
)
from aqil_research.methods.credit_standards_and_volumes import (
    CREDIT_STANDARDS_AND_VOLUMES_METHOD_ID,
    CREDIT_STANDARDS_AND_VOLUMES_METHOD_VERSION,
    H8_DATASET_ID,
    SLOOS_DATASET_ID,
    CreditStandardsAndVolumesMethod,
)
from aqil_research.methods.protocol import MethodContext, MethodExecutionResult
from aqil_research.methods.registry import default_method_registry

FIXTURE = Path(__file__).parent / "fixtures" / "credit_standards_and_volumes.json"
FRAGMENT = (
    Path(__file__).resolve().parents[3]
    / "docs"
    / "sources"
    / "fragments"
    / "CREDIT_STANDARDS_AND_VOLUMES.json"
)
RETRIEVED = datetime(2026, 10, 22, 12, 0, tzinfo=UTC)
VINTAGE = date(2026, 10, 22)


def test_fixture_calculation_reports_share_quarter_and_52_week_change() -> None:
    payload = _load_fixture()
    expected = payload["expected"]
    assert isinstance(expected, dict)
    latest_share = Decimal(str(expected["latest_sloos_share"]))
    prior_share = Decimal(str(expected["prior_sloos_share"]))
    latest_level = Decimal(str(expected["latest_h8_usd_millions"]))
    earlier_level = Decimal(str(expected["week_52_earlier_usd_millions"]))
    assert latest_share - prior_share == Decimal(str(expected["difference_percentage_points"]))
    assert latest_level - earlier_level == Decimal(str(expected["change_usd_millions"]))
    latest_h8 = date.fromisoformat(str(expected["latest_h8_period"]))
    assert latest_h8 - timedelta(weeks=52) == date.fromisoformat(
        str(expected["week_52_earlier_period"]),
    )

    result = _run(payload)
    assert result.sufficiency == "sufficient"
    assert result.investment_implication == "no_action"
    assert result.causal_hypothesis == "No causal mechanism is established."
    assert result.missing_reason is None
    assert result.observation_ids == tuple(expected["observation_ids"])
    assert "sloos-2025-10-01" not in result.observation_ids
    assert "h8-2025-10-01" not in result.observation_ids
    assert "h8-2026-10-14" not in result.observation_ids

    calc = result.calculation
    assert calc is not None
    assert calc["analysis_mode"] == "latest_revised"
    assert calc["survey_balance_converted_to_dollars"] is False
    assert "percent_net_tightening" in str(calc["transformation"])
    assert "usd_millions" in str(calc["transformation"])
    standards = calc["lending_standards"]
    credit = calc["bank_credit"]
    assert isinstance(standards, dict)
    assert isinstance(credit, dict)
    assert standards["dataset_id"] == SLOOS_DATASET_ID
    assert standards["unit"] == "percent_net_tightening"
    assert standards["frequency"] == "quarterly"
    assert standards["seasonal_adjustment"] == "not_seasonally_adjusted"
    assert standards["transformation"] == "latest_share_minus_prior_stored_quarter"
    assert standards["latest_period_start"] == expected["latest_sloos_period"]
    assert standards["latest_share"] == expected["latest_sloos_share"]
    assert standards["prior_period_start"] == expected["prior_sloos_period"]
    assert standards["prior_share"] == expected["prior_sloos_share"]
    assert standards["difference_percentage_points"] == expected["difference_percentage_points"]
    assert credit["dataset_id"] == H8_DATASET_ID
    assert credit["unit"] == "usd_millions"
    assert credit["frequency"] == "weekly"
    assert credit["seasonal_adjustment"] == "seasonally_adjusted"
    assert credit["transformation"] == "latest_level_minus_exact_period_start_52_weeks_earlier"
    assert credit["weeks_earlier"] == 52
    assert credit["latest_period_start"] == expected["latest_h8_period"]
    assert credit["latest_level_usd_millions"] == expected["latest_h8_usd_millions"]
    assert credit["comparison_period_start"] == expected["week_52_earlier_period"]
    assert credit["comparison_level_usd_millions"] == expected["week_52_earlier_usd_millions"]
    assert credit["change_usd_millions"] == expected["change_usd_millions"]
    assert credit["sufficiency"] == "sufficient"
    assert credit["missing_reason"] is None
    assert credit["change_usd_millions"] != standards["difference_percentage_points"]
    assert "usd" not in json.dumps(standards)
    assert "caused" not in result.narrative.lower()
    assert "The reading is internal." in result.narrative
    assert "not converted into dollars" in result.narrative
    fragment = json.loads(FRAGMENT.read_text(encoding="utf-8"))
    assert fragment["method_id"] == CREDIT_STANDARDS_AND_VOLUMES_METHOD_ID
    assert fragment["method_version"] == "1.0.0"
    for key in fragment["calculation_keys"]["lending_standards"]:
        assert key in standards
    for key in fragment["calculation_keys"]["bank_credit"]:
        assert key in credit


def test_absent_exact_week_keeps_the_latest_level() -> None:
    payload = _load_fixture()
    h8_rows = payload["h8"]
    assert isinstance(h8_rows, list)
    payload["h8"] = [row for row in h8_rows if row["role"] != "week_52_weeks_earlier"]
    result = _run(payload)
    assert result.sufficiency == "sufficient"
    assert result.investment_implication == "no_action"
    assert result.calculation is not None
    credit = result.calculation["bank_credit"]
    assert isinstance(credit, dict)
    assert credit["latest_level_usd_millions"] == "17890123"
    assert credit["comparison_period_start"] == "2025-10-08"
    assert credit["comparison_observation_id"] is None
    assert credit["change_usd_millions"] is None
    assert credit["sufficiency"] == "insufficient"
    assert credit["missing_reason"] == "missing H.8 week 2025-10-08 for the 52-week change"
    assert "h8-2025-10-08" not in result.observation_ids
    assert "h8-2025-10-01" not in result.observation_ids
    assert "h8-2026-10-07" in result.observation_ids
    assert "52-week change is insufficient" in result.narrative


def test_missing_prior_quarter_fails_closed() -> None:
    payload = _load_fixture()
    sloos_rows = payload["sloos"]
    assert isinstance(sloos_rows, list)
    payload["sloos"] = [row for row in sloos_rows if row["role"] == "latest"]
    result = _run(payload)
    assert result.sufficiency == "insufficient"
    assert result.calculation is None
    assert result.observation_ids == ()
    assert result.investment_implication == "insufficient_evidence"
    assert result.missing_reason == "no prior stored quarter before 2026-07-01"


def test_missing_required_latest_observation_fails_closed() -> None:
    payload = _load_fixture()
    without_sloos = json.loads(json.dumps(payload))
    without_sloos["sloos"] = []
    sloos_result = _run(without_sloos)
    assert sloos_result.sufficiency == "insufficient"
    assert sloos_result.calculation is None
    assert sloos_result.observation_ids == ()
    assert sloos_result.investment_implication == "insufficient_evidence"
    assert sloos_result.causal_hypothesis == "No causal mechanism is established."
    assert sloos_result.missing_reason == (
        "missing required latest observation for fed.sloos.SUBLPDCILS_N.Q on or before 2026-10-07"
    )

    without_h8 = json.loads(json.dumps(payload))
    without_h8["h8"] = []
    h8_result = _run(without_h8)
    assert h8_result.sufficiency == "insufficient"
    assert h8_result.calculation is None
    assert h8_result.observation_ids == ()
    assert h8_result.investment_implication == "insufficient_evidence"
    assert h8_result.missing_reason == (
        "missing required latest observation for fed.h8.B1001NCBA on or before 2026-10-07"
    )


def test_point_in_time_is_insufficient() -> None:
    result = _run(_load_fixture(), analysis_mode=AnalysisMode.POINT_IN_TIME)
    assert result.sufficiency == "insufficient"
    assert result.calculation is None
    assert result.observation_ids == ()
    assert result.investment_implication == "insufficient_evidence"
    assert result.causal_hypothesis == "No causal mechanism is established."
    assert result.missing_reason == (
        "A point-in-time request is insufficient because these files are not vintage panels."
    )


def test_ineligible_rows_are_not_the_required_latest() -> None:
    payload = _load_fixture()
    wrong_unit = _run(payload, sloos_unit="percent")
    assert wrong_unit.sufficiency == "insufficient"
    assert wrong_unit.calculation is None
    assert wrong_unit.observation_ids == ()

    retracted = _run(payload, retract_latest_sloos=True)
    assert retracted.sufficiency == "sufficient"
    assert retracted.calculation is not None
    standards = retracted.calculation["lending_standards"]
    assert isinstance(standards, dict)
    assert standards["latest_share"] == "11.2"
    assert standards["prior_share"] == "9.0"
    assert standards["difference_percentage_points"] == "2.2"
    assert "sloos-2026-07-01" not in retracted.observation_ids


def test_method_identity_is_registered() -> None:
    method = CreditStandardsAndVolumesMethod()
    assert method.method_id == CREDIT_STANDARDS_AND_VOLUMES_METHOD_ID
    assert method.method_version == CREDIT_STANDARDS_AND_VOLUMES_METHOD_VERSION
    assert method.method_version == "1.0.0"
    assert method.required_dataset_ids() == (SLOOS_DATASET_ID, H8_DATASET_ID)
    assert method.implementation_hash() == method.implementation_hash()
    config = method.parse_config({"config_id": "credit-1", "label": "Fixture"})
    other = method.parse_config({"config_id": "credit-1", "label": "Other"})
    assert method.config_hash(config) != method.config_hash(other)
    registered = default_method_registry().get(CREDIT_STANDARDS_AND_VOLUMES_METHOD_ID)
    assert registered.method_id == CREDIT_STANDARDS_AND_VOLUMES_METHOD_ID
    assert registered.method_version == "1.0.0"


def _run(
    payload: dict[str, object],
    *,
    analysis_mode: AnalysisMode = AnalysisMode.LATEST_REVISED,
    sloos_unit: str = "percent_net_tightening",
    retract_latest_sloos: bool = False,
) -> MethodExecutionResult:
    sloos = {
        obs.period_start: obs
        for obs in _rows(
            payload["sloos"],
            dataset_id=SLOOS_DATASET_ID,
            frequency=Frequency.QUARTERLY,
            unit=sloos_unit,
            seasonal_adjustment=SeasonalAdjustment.NOT_SEASONALLY_ADJUSTED,
            retract_latest=retract_latest_sloos,
        )
    }
    h8 = {
        obs.period_start: obs
        for obs in _rows(
            payload["h8"],
            dataset_id=H8_DATASET_ID,
            frequency=Frequency.WEEKLY,
            unit="usd_millions",
            seasonal_adjustment=SeasonalAdjustment.SEASONALLY_ADJUSTED,
            retract_latest=False,
        )
    }
    method = CreditStandardsAndVolumesMethod()
    context = MethodContext(
        inputs_by_dataset={SLOOS_DATASET_ID: sloos, H8_DATASET_ID: h8},
        evaluation_period=date.fromisoformat(str(payload["evaluation_period"])),
        analysis_mode=analysis_mode,
        primary_dataset_id=SLOOS_DATASET_ID,
    )
    return method.run(context, method.parse_config({"config_id": "fixture", "label": "Fixture"}))


def _rows(
    raw: object,
    *,
    dataset_id: str,
    frequency: Frequency,
    unit: str,
    seasonal_adjustment: SeasonalAdjustment,
    retract_latest: bool,
) -> tuple[EconomicObservation, ...]:
    assert isinstance(raw, list)
    periods = [date.fromisoformat(str(item["period_start"])) for item in raw]
    latest_period = max(periods) if periods else None
    rows: list[EconomicObservation] = []
    for item in raw:
        assert isinstance(item, dict)
        period = date.fromisoformat(str(item["period_start"]))
        quality = QualityStatus.OBSERVED
        if retract_latest and period == latest_period:
            quality = QualityStatus.RETRACTED
        rows.append(
            EconomicObservation(
                observation_id=str(item["observation_id"]),
                dataset_id=dataset_id,
                provider_id="federal_reserve_board",
                source_id="credit_standards_fixture",
                rights_record_id="credit_standards_fixture",
                period_start=period,
                frequency=frequency,
                geography="US",
                unit=unit,
                seasonal_adjustment=seasonal_adjustment,
                raw_value=str(item["raw_value"]),
                quality_status=quality,
                series_provenance=SeriesProvenance.LATEST_REVISED,
                provider_vintage_date=VINTAGE,
                earliest_model_available_at=None,
                availability_precision=AvailabilityPrecision.UNKNOWN,
                retrieved_at=RETRIEVED,
                first_seen_at=RETRIEVED,
                source_release_at=RETRIEVED,
                adapter_version="credit_standards_fixture_v1",
            ),
        )
    return tuple(rows)


def _load_fixture() -> dict[str, object]:
    loaded = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded
