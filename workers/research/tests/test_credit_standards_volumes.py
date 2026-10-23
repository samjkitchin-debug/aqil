"""CREDIT_STANDARDS_AND_VOLUMES on a synthetic fixture.

These tests do not open a database.
"""

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
from aqil_research.methods.credit_standards_volumes import (
    CREDIT_STANDARDS_AND_VOLUMES_METHOD_ID,
    CREDIT_STANDARDS_AND_VOLUMES_METHOD_VERSION,
    H8_DATASET_ID,
    SLOOS_DATASET_ID,
    CreditStandardsVolumesMethod,
)
from aqil_research.methods.protocol import MethodContext, MethodExecutionResult

FIXTURE = (
    Path(__file__).parent
    / "fixtures"
    / "credit_standards_volumes"
    / "credit_standards_and_volumes.json"
)
FRAGMENT = (
    Path(__file__).resolve().parents[3]
    / "docs"
    / "sources"
    / "fragments"
    / "CREDIT_STANDARDS_AND_VOLUMES.json"
)
RETRIEVED = datetime(2026, 10, 16, 12, 0, tzinfo=UTC)
VINTAGE = date(2026, 10, 16)


def test_both_changes_present() -> None:
    fixture = _fixture()
    expected = fixture["expected"]
    latest_share = Decimal(expected["latest_sloos_share"])
    prior_share = Decimal(expected["prior_sloos_share"])
    latest_level = Decimal(expected["latest_h8_level_usd_millions"])
    earlier_level = Decimal(expected["comparison_h8_level_usd_millions"])
    assert latest_share - prior_share == Decimal(expected["difference_percentage_points"])
    assert latest_level - earlier_level == Decimal(expected["change_usd_millions"])
    latest_week = date.fromisoformat("2026-10-07")
    assert latest_week - timedelta(weeks=52) == date.fromisoformat(
        expected["comparison_period_start"],
    )

    result = _run(fixture, AnalysisMode.LATEST_REVISED)
    assert result.sufficiency == "sufficient"
    assert result.investment_implication == "no_action"
    assert result.causal_hypothesis == "No causal mechanism is established."
    assert result.missing_reason is None
    assert result.calculation is not None
    standards = result.calculation["lending_standards"]
    bank = result.calculation["bank_credit"]
    assert isinstance(standards, dict)
    assert isinstance(bank, dict)
    assert standards["latest_share"] == expected["latest_sloos_share"]
    assert standards["latest_observation_id"] == expected["latest_sloos_observation_id"]
    assert standards["prior_share"] == expected["prior_sloos_share"]
    assert standards["prior_observation_id"] == expected["prior_sloos_observation_id"]
    assert standards["difference_percentage_points"] == expected["difference_percentage_points"]
    assert standards["unit"] == "percent_net_tightening"
    assert bank["latest_level_usd_millions"] == expected["latest_h8_level_usd_millions"]
    assert bank["latest_observation_id"] == expected["latest_h8_observation_id"]
    assert bank["comparison_period_start"] == expected["comparison_period_start"]
    assert bank["comparison_observation_id"] == expected["comparison_h8_observation_id"]
    assert bank["comparison_level_usd_millions"] == expected["comparison_h8_level_usd_millions"]
    assert bank["change_usd_millions"] == expected["change_usd_millions"]
    assert bank["sufficiency"] == "sufficient"
    assert bank["unit"] == "usd_millions"
    assert result.observation_ids == tuple(
        sorted(
            [
                expected["latest_sloos_observation_id"],
                expected["prior_sloos_observation_id"],
                expected["latest_h8_observation_id"],
                expected["comparison_h8_observation_id"],
            ],
        ),
    )
    for unused in expected["unused_observation_ids"]:
        assert unused not in result.observation_ids
    assert "because of" not in result.narrative.lower()
    assert "caused" not in result.narrative.lower()


def test_missing_52_week_period_reports_latest_level() -> None:
    fixture = _fixture()
    fixture["bank_credit"] = [
        row for row in fixture["bank_credit"] if row["period_start"] != "2025-10-08"
    ]
    assert any(row["period_start"] == "2025-10-01" for row in fixture["bank_credit"])
    assert any(row["period_start"] == "2026-07-01" for row in fixture["bank_credit"])

    result = _run(fixture, AnalysisMode.LATEST_REVISED)
    expected = fixture["expected"]
    assert result.sufficiency == "sufficient"
    assert result.calculation is not None
    assert result.investment_implication == "no_action"
    standards = result.calculation["lending_standards"]
    bank = result.calculation["bank_credit"]
    assert isinstance(standards, dict)
    assert isinstance(bank, dict)
    assert standards["difference_percentage_points"] == expected["difference_percentage_points"]
    assert bank["latest_level_usd_millions"] == expected["latest_h8_level_usd_millions"]
    assert bank["latest_observation_id"] == expected["latest_h8_observation_id"]
    assert bank["comparison_period_start"] == "2025-10-08"
    assert bank["comparison_observation_id"] is None
    assert bank["comparison_level_usd_millions"] is None
    assert bank["change_usd_millions"] is None
    assert bank["sufficiency"] == "insufficient"
    assert bank["missing_reason"] == (
        "missing exact H.8 period_start 2025-10-08 for the 52-week change"
    )
    assert "h8-20251001" not in result.observation_ids
    assert "h8-20260701" not in result.observation_ids
    assert "h8-20261007" in result.observation_ids
    assert "18000000.0" not in json.dumps(bank)
    assert "18500000.0" not in json.dumps(bank)


def test_point_in_time_is_insufficient() -> None:
    result = _run(_fixture(), AnalysisMode.POINT_IN_TIME)
    assert result.sufficiency == "insufficient"
    assert result.calculation is None
    assert result.observation_ids == ()
    assert result.investment_implication == "insufficient_evidence"
    assert result.causal_hypothesis == "No causal mechanism is established."
    assert result.missing_reason == (
        "Point-in-time is insufficient because these files are not vintage panels."
    )


def test_sloos_share_is_not_converted_to_dollars() -> None:
    result = _run(_fixture(), AnalysisMode.LATEST_REVISED)
    assert result.calculation is not None
    standards = result.calculation["lending_standards"]
    bank = result.calculation["bank_credit"]
    units = result.calculation["units"]
    assert isinstance(standards, dict)
    assert isinstance(bank, dict)
    assert isinstance(units, dict)
    assert standards["unit"] == "percent_net_tightening"
    assert units["lending_standards_share"] == "percent_net_tightening"
    assert units["lending_standards_difference"] == "percentage_points"
    blob = json.dumps(standards)
    assert "usd" not in blob
    assert "$" not in blob
    assert standards["latest_share"] == "11.2"
    assert standards["difference_percentage_points"] == "2.7"
    assert standards["latest_share"] != bank["latest_level_usd_millions"]
    assert standards["difference_percentage_points"] != bank["change_usd_millions"]
    narrative = result.narrative.lower()
    assert "11.2 million" not in narrative
    assert "11.2 usd" not in narrative
    fragment = json.loads(FRAGMENT.read_text(encoding="utf-8"))
    assert fragment["method_id"] == CREDIT_STANDARDS_AND_VOLUMES_METHOD_ID
    assert fragment["method_version"] == CREDIT_STANDARDS_AND_VOLUMES_METHOD_VERSION
    for key in fragment["calculation_keys"]["lending_standards"]:
        assert key in standards
    for key in fragment["calculation_keys"]["bank_credit"]:
        assert key in bank


def _run(fixture: dict[str, object], mode: AnalysisMode) -> MethodExecutionResult:
    sloos = {
        date.fromisoformat(str(row["period_start"])): _observation(row, series="sloos")
        for row in _rows(fixture, "sloos")
    }
    bank = {
        date.fromisoformat(str(row["period_start"])): _observation(row, series="bank_credit")
        for row in _rows(fixture, "bank_credit")
    }
    method = CreditStandardsVolumesMethod()
    context = MethodContext(
        inputs_by_dataset={SLOOS_DATASET_ID: sloos, H8_DATASET_ID: bank},
        evaluation_period=date.fromisoformat(str(fixture["evaluation_period"])),
        analysis_mode=mode,
        primary_dataset_id=SLOOS_DATASET_ID,
    )
    return method.run(context, method.parse_config({"config_id": "fixture", "label": "Fixture"}))


def _fixture() -> dict[str, object]:
    loaded = json.loads(FIXTURE.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise TypeError("fixture must be an object")
    return loaded


def _rows(fixture: dict[str, object], key: str) -> list[dict[str, object]]:
    rows = fixture[key]
    if not isinstance(rows, list):
        raise TypeError(f"{key} must be a list")
    return [row for row in rows if isinstance(row, dict)]


def _observation(row: dict[str, object], *, series: str) -> EconomicObservation:
    if series == "sloos":
        dataset_id = SLOOS_DATASET_ID
        frequency = Frequency.QUARTERLY
        unit = "percent_net_tightening"
        seasonal = SeasonalAdjustment.NOT_SEASONALLY_ADJUSTED
        source_id = "federal_reserve_sloos_cil_standards"
    else:
        dataset_id = H8_DATASET_ID
        frequency = Frequency.WEEKLY
        unit = "usd_millions"
        seasonal = SeasonalAdjustment.SEASONALLY_ADJUSTED
        source_id = "federal_reserve_h8_bank_credit"
    return EconomicObservation(
        observation_id=str(row["observation_id"]),
        dataset_id=dataset_id,
        provider_id="federal_reserve_board",
        source_id=source_id,
        rights_record_id=source_id,
        period_start=date.fromisoformat(str(row["period_start"])),
        frequency=frequency,
        geography="US",
        unit=unit,
        seasonal_adjustment=seasonal,
        raw_value=str(row["raw_value"]),
        quality_status=QualityStatus.OBSERVED,
        series_provenance=SeriesProvenance.LATEST_REVISED,
        provider_vintage_date=VINTAGE,
        availability_precision=AvailabilityPrecision.UNKNOWN,
        retrieved_at=RETRIEVED,
        first_seen_at=RETRIEVED,
        adapter_version="credit_standards_volumes_fixture_v1",
    )
