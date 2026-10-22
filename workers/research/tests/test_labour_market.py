"""Fixture tests for LABOUR_MARKET_CONDITIONS 1.0.0. No database connection."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
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
from aqil_research.methods.labour_market import LabourMarketConditionsMethod
from aqil_research.methods.protocol import MethodContext, MethodExecutionResult

FIXTURE = Path(__file__).parent / "fixtures" / "labour_market_conditions.json"
FRAGMENT = (
    Path(__file__).resolve().parents[3]
    / "docs"
    / "sources"
    / "fragments"
    / "LABOUR_MARKET_CONDITIONS.json"
)
UNEMPLOYMENT = "bls.ln.LNS14000000"
PAYROLLS = "bls.ce.CES0000000001"
OPENINGS = "bls.jt.JTS000000000000000JOL"
_CAUSAL = "No causal mechanism is established."


def _observation(row: dict[str, str]) -> EconomicObservation:
    period = date.fromisoformat(row["period_start"])
    retrieved = datetime(period.year, period.month, 16, 12, 0, tzinfo=UTC)
    return EconomicObservation(
        observation_id=row["observation_id"],
        dataset_id=row["dataset_id"],
        provider_id="bls",
        source_id="labour_market_fixture",
        rights_record_id="labour_market_fixture",
        period_start=period,
        frequency=Frequency.MONTHLY,
        geography="US",
        unit=row["unit"],
        seasonal_adjustment=SeasonalAdjustment.SEASONALLY_ADJUSTED,
        raw_value=row["raw_value"],
        quality_status=QualityStatus.OBSERVED,
        series_provenance=SeriesProvenance.LATEST_REVISED,
        provider_vintage_date=date(period.year, period.month, 15),
        availability_precision=AvailabilityPrecision.UNKNOWN,
        retrieved_at=retrieved,
        first_seen_at=retrieved,
        adapter_version="labour_market_fixture_v1",
    )


def _context(rows: list[dict[str, str]], mode: AnalysisMode) -> MethodContext:
    by_dataset: dict[str, dict[date, EconomicObservation]] = {}
    for row in rows:
        obs = _observation(row)
        by_dataset.setdefault(obs.dataset_id, {})[obs.period_start] = obs
    return MethodContext(
        inputs_by_dataset=by_dataset,
        evaluation_period=date(2026, 9, 1),
        analysis_mode=mode,
        primary_dataset_id=UNEMPLOYMENT,
    )


def _run(rows: list[dict[str, str]], mode: AnalysisMode) -> MethodExecutionResult:
    method = LabourMarketConditionsMethod()
    config = method.parse_config(
        {
            "config_id": "labour_market_conditions_fixture",
            "label": "Fixture labour market window",
        },
    )
    return method.run(_context(rows, mode), config)


def _by_dataset(calculation: dict[str, object]) -> dict[str, dict[str, object]]:
    series = calculation["series"]
    assert isinstance(series, list)
    return {row["dataset_id"]: row for row in series}


def test_sufficient_fixture_window_uses_endpoints_only() -> None:
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    rows = payload["sufficient_window"]
    assert "2025-10-01" not in {row["period_start"] for row in rows}
    unemployment_periods = {
        row["period_start"] for row in rows if row["dataset_id"] == UNEMPLOYMENT
    }
    assert "2025-10-01" not in unemployment_periods
    assert all(row["raw_value"] != "0" for row in rows)

    result = _run(rows, AnalysisMode.LATEST_REVISED)
    assert result.sufficiency == "sufficient"
    assert result.missing_reason is None
    assert result.investment_implication == "no_action"
    assert result.causal_hypothesis == _CAUSAL
    assert result.calculation is not None
    assert "composite_score" not in json.dumps(result.calculation)

    calculation = result.calculation
    series = _by_dataset(calculation)
    unemployment = series[UNEMPLOYMENT]
    payrolls = series[PAYROLLS]
    openings = series[OPENINGS]

    assert unemployment["latest_period"] == "2026-09-01"
    assert unemployment["level"] == "4.4"
    assert unemployment["unit"] == "percent"
    assert unemployment["observation_id"] == "ln-2026-09"
    assert unemployment["rank"] == 5
    assert unemployment["history_count"] == 5
    unemployment_change = unemployment["twelve_month_change"]
    assert unemployment_change["window_start"] == "2025-09-01"
    assert unemployment_change["window_end"] == "2026-09-01"
    assert unemployment_change["change_percentage_points"] == "0.30"
    assert unemployment_change["change_unit"] == "percentage_points"
    assert unemployment_change["start_observation_id"] == "ln-2025-09"
    assert unemployment_change["end_observation_id"] == "ln-2026-09"
    assert unemployment_change["endpoints_only"] is True

    assert payrolls["latest_period"] == "2026-09-01"
    assert payrolls["level"] == "1155"
    assert payrolls["unit"] == "thousands"
    assert payrolls["observation_id"] == "ce-2026-09"
    assert payrolls["rank"] == 5
    assert payrolls["history_count"] == 5
    payrolls_change = payrolls["twelve_month_change"]
    assert payrolls_change["change_thousands"] == "105"
    assert payrolls_change["percent_change"] == "10.00"
    assert payrolls_change["change_unit"] == "thousands"
    assert payrolls_change["percent_change_unit"] == "percent"
    assert payrolls_change["start_observation_id"] == "ce-2025-09"
    assert payrolls_change["end_observation_id"] == "ce-2026-09"

    assert openings["latest_period"] == "2026-08-01"
    assert openings["level"] == "660"
    assert openings["unit"] == "thousands"
    assert openings["observation_id"] == "jt-2026-08"
    assert openings["rank"] == 3
    assert openings["history_count"] == 4
    openings_change = openings["twelve_month_change"]
    assert openings_change["window_start"] == "2025-08-01"
    assert openings_change["window_end"] == "2026-08-01"
    assert openings_change["change_thousands"] == "60"
    assert openings_change["percent_change"] == "10.00"
    assert openings_change["start_observation_id"] == "jt-2025-08"
    assert openings_change["end_observation_id"] == "jt-2026-08"

    joint = calculation["joint"]
    assert joint["latest_common_period"] == "2026-08-01"
    joint_change = joint["twelve_month_change"]
    assert joint_change["window_start"] == "2025-08-01"
    assert joint_change["window_end"] == "2026-08-01"
    assert "2025-10-01" not in (joint_change["window_start"], joint_change["window_end"])
    joint_by_id = {row["dataset_id"]: row for row in joint_change["series"]}
    assert joint_by_id[UNEMPLOYMENT]["change_percentage_points"] == "0.30"
    assert joint_by_id[UNEMPLOYMENT]["start_observation_id"] == "ln-2025-08"
    assert joint_by_id[UNEMPLOYMENT]["end_observation_id"] == "ln-2026-08"
    assert joint_by_id[PAYROLLS]["change_thousands"] == "100"
    assert joint_by_id[PAYROLLS]["percent_change"] == "10.00"
    assert joint_by_id[OPENINGS]["change_thousands"] == "60"
    assert joint_by_id[OPENINGS]["percent_change"] == "10.00"

    assert list(result.observation_ids) == calculation["observation_ids"]
    assert "ln-2025-09" in result.observation_ids
    assert all("2025-10" not in observation_id for observation_id in result.observation_ids)

    fragment = json.loads(FRAGMENT.read_text(encoding="utf-8"))
    assert fragment["method_id"] == "LABOUR_MARKET_CONDITIONS"
    assert fragment["method_version"] == "1.0.0"
    assert result.sufficiency == fragment["sufficiency"]
    assert result.investment_implication == fragment["investment_implication"]
    assert result.causal_hypothesis == fragment["causal_hypothesis"]
    assert result.missing_reason == fragment["missing_reason"]
    assert list(result.observation_ids) == fragment["observation_ids"]
    assert result.calculation == fragment["calculation"]


def test_missing_october_2025_unemployment_endpoint_is_insufficient() -> None:
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    rows = payload["missing_october_2025_unemployment"]
    unemployment_periods = {
        row["period_start"] for row in rows if row["dataset_id"] == UNEMPLOYMENT
    }
    assert "2026-10-01" in unemployment_periods
    assert "2025-11-01" in unemployment_periods
    assert "2025-10-01" not in unemployment_periods
    assert all(row["raw_value"] != "0" for row in rows)

    result = _run(rows, AnalysisMode.LATEST_REVISED)
    assert result.sufficiency == "insufficient"
    assert result.calculation is None
    assert result.observation_ids == ()
    assert result.investment_implication == "insufficient_evidence"
    assert result.causal_hypothesis == _CAUSAL
    assert result.missing_reason == (
        "missing endpoint 2025-10-01 for bls.ln.LNS14000000 "
        "12-month change from 2025-10-01 to 2026-10-01"
    )


def test_point_in_time_context_is_insufficient() -> None:
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    result = _run(payload["sufficient_window"], AnalysisMode.POINT_IN_TIME)
    assert result.sufficiency == "insufficient"
    assert result.calculation is None
    assert result.observation_ids == ()
    assert result.investment_implication == "insufficient_evidence"
    assert result.causal_hypothesis == _CAUSAL
    assert result.missing_reason == (
        "A point-in-time context is insufficient because these series are not a vintage panel."
    )
