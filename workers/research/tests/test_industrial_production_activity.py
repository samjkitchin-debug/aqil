"""Fixture tests for INDUSTRIAL_PRODUCTION_ACTIVITY 1.1.0. No database connection."""

from __future__ import annotations

import json
import re
from datetime import UTC, date, datetime
from decimal import ROUND_HALF_UP, Decimal
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
from aqil_research.methods.industrial_production_activity import (
    INDUSTRIAL_PRODUCTION_DATASET_ID,
    INDUSTRIAL_PRODUCTION_METHOD_ID,
    INDUSTRIAL_PRODUCTION_METHOD_VERSION,
    IndustrialProductionActivityMethod,
)
from aqil_research.methods.protocol import MethodContext, MethodExecutionResult

FIXTURE = Path(__file__).parent / "fixtures" / "industrial_production" / "activity_window.json"
FRAGMENT = (
    Path(__file__).resolve().parents[3]
    / "docs"
    / "sources"
    / "fragments"
    / "INDUSTRIAL_PRODUCTION_ACTIVITY.json"
)
RETRIEVED = datetime(2026, 10, 22, 9, 0, tzinfo=UTC)
VINTAGE = date(2026, 10, 17)
EVALUATION = date(2026, 9, 1)
EARLIER = date(2025, 9, 1)
CONFIG = {
    "config_id": "industrial-production-activity-1.0.0",
    "label": "Industrial production activity",
}
_GDP_FIGURE = re.compile(r"\bgdp\b\s*[:=]?\s*\d", flags=re.IGNORECASE)


def _load_fixture() -> dict[str, object]:
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("industrial production fixture must be an object")
    return payload


def _series(*, drop_periods: set[str] | None = None) -> dict[date, EconomicObservation]:
    payload = _load_fixture()
    drop = drop_periods or set()
    observations = payload["observations"]
    if not isinstance(observations, list):
        raise TypeError("fixture observations must be a list")
    series: dict[date, EconomicObservation] = {}
    for row in observations:
        if not isinstance(row, dict):
            raise TypeError("fixture observation must be an object")
        period_text = str(row["period_start"])
        if period_text in drop:
            continue
        period = date.fromisoformat(period_text)
        series[period] = EconomicObservation(
            observation_id=str(row["observation_id"]),
            dataset_id=str(payload["dataset_id"]),
            provider_id="federal_reserve_board",
            source_id="federal_reserve_g17_total_ip",
            rights_record_id="federal_reserve_g17_total_ip",
            period_start=period,
            frequency=Frequency.MONTHLY,
            geography="US",
            unit=str(payload["unit"]),
            seasonal_adjustment=SeasonalAdjustment(str(payload["seasonal_adjustment"])),
            raw_value=str(row["raw_value"]),
            quality_status=QualityStatus.OBSERVED,
            series_provenance=SeriesProvenance.LATEST_REVISED,
            provider_vintage_date=VINTAGE,
            availability_precision=AvailabilityPrecision.UNKNOWN,
            retrieved_at=RETRIEVED,
            first_seen_at=RETRIEVED,
            adapter_version="industrial_production_activity_fixture_v1",
        )
    return series


def _run(
    series: dict[date, EconomicObservation],
    mode: AnalysisMode = AnalysisMode.LATEST_REVISED,
) -> MethodExecutionResult:
    method = IndustrialProductionActivityMethod()
    context = MethodContext(
        inputs_by_dataset={INDUSTRIAL_PRODUCTION_DATASET_ID: series},
        evaluation_period=EVALUATION,
        analysis_mode=mode,
        primary_dataset_id=INDUSTRIAL_PRODUCTION_DATASET_ID,
    )
    return method.run(context, method.parse_config(CONFIG))


def _assert_no_gdp_figure(narrative: str) -> None:
    folded = narrative.casefold()
    assert "this is industrial production, not gdp" in folded
    assert "census advance orders were not collected" in folded
    assert "gdp is" not in folded
    assert "gdp was" not in folded
    assert "gdp of" not in folded
    assert "gdp rose" not in folded
    assert "gdp growth" not in folded
    assert "gross domestic product is" not in folded
    assert _GDP_FIGURE.search(narrative) is None


def test_sufficient_twelve_month_percent_change() -> None:
    payload = _load_fixture()
    observations = payload["observations"]
    assert isinstance(observations, list)
    result = _run(_series())
    method = IndustrialProductionActivityMethod()
    fragment = json.loads(FRAGMENT.read_text(encoding="utf-8"))

    assert method.method_id == INDUSTRIAL_PRODUCTION_METHOD_ID
    assert method.method_version == INDUSTRIAL_PRODUCTION_METHOD_VERSION == "1.1.0"
    assert method.required_dataset_ids() == (INDUSTRIAL_PRODUCTION_DATASET_ID,)
    assert result.sufficiency == "sufficient"
    assert result.missing_reason is None
    assert result.investment_implication == "no_action"
    assert result.causal_hypothesis == "No causal mechanism is established."
    calculation = result.calculation
    assert calculation is not None
    assert "composite_score" not in calculation
    assert "score" not in calculation

    later = Decimal("104.0400")
    earlier = Decimal("102.0000")
    expected_change = ((later / earlier) - Decimal(1)) * Decimal(100)
    expected_change = expected_change.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    levels = [Decimal(str(row["raw_value"])) for row in observations]
    level_rank = 1 + sum(1 for level in levels if level < later)
    assert level_rank == 4
    assert calculation["latest_period"] == "2026-09-01"
    assert calculation["earlier_period"] == EARLIER.isoformat()
    assert calculation["latest_level"] == "104.0400"
    assert calculation["earlier_level"] == "102.0000"
    assert calculation["formula"] == "(later/earlier - 1) * 100"
    assert calculation["unit"] == "index_2017_100"
    assert calculation["analysis_mode"] == "latest_revised"
    assert calculation["twelve_month_percent_change"] == format(expected_change, "f")
    assert calculation["twelve_month_percent_change"] == "2.0000"
    assert calculation["endpoints_only"] is True
    assert calculation["historical_rank"] == 1
    assert calculation["historical_rank"] != level_rank
    assert calculation["stored_changes_strictly_below_latest"] == 0
    assert calculation["stored_change_count"] == 2
    assert calculation["stored_value_count"] == calculation["stored_change_count"]
    assert calculation["rank_basis"] == "overlapping_twelve_month_percent_change"
    assert (
        calculation["ranked_series"]
        == f"industrial production ({INDUSTRIAL_PRODUCTION_DATASET_ID})"
    )
    assert "overlapping 12-month percent changes" in str(calculation["rank_definition"])
    assert "today's revised file" in str(calculation["rank_definition"])
    assert set(result.observation_ids) == {str(row["observation_id"]) for row in observations}
    assert list(result.observation_ids) == sorted(result.observation_ids)
    assert list(result.observation_ids) == fragment["observation_ids"]
    assert fragment["method_version"] == "1.0.0"
    assert fragment["calculation"]["historical_rank"] == level_rank
    assert fragment["publication_allowed"] is False
    assert "composite_score" not in fragment
    assert "endpoints only" in result.narrative.casefold()
    assert "not treated as observed" in result.narrative.casefold()
    assert "2025-10" not in result.narrative
    assert "today's revised file" in result.narrative
    assert INDUSTRIAL_PRODUCTION_DATASET_ID in result.narrative
    _assert_no_gdp_figure(result.narrative)


def test_missing_endpoint_fails_the_window() -> None:
    result = _run(_series(drop_periods={"2025-09-01"}))
    assert result.sufficiency == "insufficient"
    assert result.calculation is None
    assert result.observation_ids == ()
    assert result.investment_implication == "insufficient_evidence"
    assert result.causal_hypothesis == "No causal mechanism is established."
    assert result.missing_reason == ("missing endpoint for window 2025-09-01 to 2026-09-01")
    assert "2.0000" not in result.narrative
    assert "interpolat" not in (result.missing_reason or "")
    _assert_no_gdp_figure(result.narrative)


def test_point_in_time_request_is_insufficient() -> None:
    result = _run(_series(), AnalysisMode.POINT_IN_TIME)
    assert result.sufficiency == "insufficient"
    assert result.calculation is None
    assert result.observation_ids == ()
    assert result.investment_implication == "insufficient_evidence"
    assert result.causal_hypothesis == "No causal mechanism is established."
    assert result.missing_reason == (
        "point_in_time is insufficient because fed.g17.IP.B50001.S is not a vintage panel"
    )
    assert "2.0000" not in result.narrative
    assert "104.0400" not in result.narrative
    _assert_no_gdp_figure(result.narrative)


def _point(period: str, value: str) -> EconomicObservation:
    return EconomicObservation(
        observation_id=f"g17-{period}",
        dataset_id=INDUSTRIAL_PRODUCTION_DATASET_ID,
        provider_id="federal_reserve_board",
        source_id="federal_reserve_g17_total_ip",
        rights_record_id="federal_reserve_g17_total_ip",
        period_start=date.fromisoformat(period),
        frequency=Frequency.MONTHLY,
        geography="US",
        unit="index_2017_100",
        seasonal_adjustment=SeasonalAdjustment.SEASONALLY_ADJUSTED,
        raw_value=value,
        quality_status=QualityStatus.OBSERVED,
        series_provenance=SeriesProvenance.LATEST_REVISED,
        provider_vintage_date=VINTAGE,
        availability_precision=AvailabilityPrecision.UNKNOWN,
        retrieved_at=RETRIEVED,
        first_seen_at=RETRIEVED,
        adapter_version="industrial_production_activity_fixture_v1",
    )


def test_trending_level_change_rank_is_not_the_level_rank() -> None:
    points = (
        ("2024-09-01", "100.0000"),
        ("2025-09-01", "200.0000"),
        ("2026-09-01", "300.0000"),
    )
    series = {date.fromisoformat(period): _point(period, value) for period, value in points}
    result = _run(series)
    assert result.sufficiency == "sufficient"
    calculation = result.calculation
    assert calculation is not None
    levels = [Decimal(value) for _, value in points]
    level_rank = 1 + sum(1 for level in levels if level < levels[-1])
    assert level_rank == 3
    assert calculation["historical_rank"] == 1
    assert calculation["stored_change_count"] == 2
    assert calculation["historical_rank"] != level_rank
    assert calculation["twelve_month_percent_change"] == "50.0000"
    assert calculation["endpoints_only"] is True
    assert INDUSTRIAL_PRODUCTION_DATASET_ID in str(calculation["ranked_series"])
    assert "overlapping 12-month percent changes" in result.narrative
    assert "today's revised file" in result.narrative
    assert "not what was known on each past date" in result.narrative
    assert "endpoints only" in result.narrative.casefold()
    assert "not treated as observed" in result.narrative.casefold()
    assert "2025-10" not in result.narrative
    assert "composite" not in json.dumps(calculation).casefold()
    assert "spread" not in result.narrative.casefold()
    assert "real rate" not in result.narrative.casefold()
    _assert_no_gdp_figure(result.narrative)


def test_missing_endpoint_returns_insufficient() -> None:
    result = _run({date(2026, 9, 1): _point("2026-09-01", "300.0000")})
    assert result.sufficiency == "insufficient"
    assert result.calculation is None
    assert result.observation_ids == ()
    assert result.investment_implication == "insufficient_evidence"
    assert result.causal_hypothesis == "No causal mechanism is established."
    assert result.missing_reason == "missing endpoint for window 2025-09-01 to 2026-09-01"
    assert "interpolat" not in (result.missing_reason or "")
    assert "2025-10-01 was observed" not in result.narrative.casefold()
    _assert_no_gdp_figure(result.narrative)


def test_narrative_does_not_claim_a_gdp_figure() -> None:
    result = _run(_series())
    _assert_no_gdp_figure(result.narrative)
    assert "industrial production" in result.narrative.casefold()
    assert "not gdp" in result.narrative.casefold()
    assert "Census advance orders were not collected." in result.narrative
