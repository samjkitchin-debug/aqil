"""PRICES_AND_POLICY 1.0.0 on a small latest-revised fixture. No database."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
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
from aqil_research.methods.prices_and_policy import (
    CAUSAL_HYPOTHESIS,
    CPI_DATASET_ID,
    FED_FUNDS_DATASET_ID,
    PRICES_AND_POLICY_METHOD_ID,
    PRICES_AND_POLICY_METHOD_VERSION,
    TREASURY_10Y_DATASET_ID,
    PricesAndPolicyMethod,
)
from aqil_research.methods.protocol import MethodContext
from aqil_research.methods.registry import default_method_registry

FIXTURE = Path(__file__).parent / "fixtures" / "prices_and_policy.json"
FRAGMENT = (
    Path(__file__).resolve().parents[3]
    / "docs"
    / "sources"
    / "fragments"
    / "PRICES_AND_POLICY.json"
)
HICP_DATASET_ID = "ecb.icp.M.U2.Y.000000.3.INX"
RETRIEVED = datetime(2026, 10, 16, 12, 0, tzinfo=UTC)
CONFIG = {"config_id": "prices-and-policy-fixture", "label": "Prices and policy fixture"}

SEPTEMBER_2026_CALCULATION = {
    "evaluation_period": "2026-09-01",
    "analysis_mode": "latest_revised",
    "cpi_u": {
        "dataset_id": CPI_DATASET_ID,
        "unit": "1982-84=100",
        "seasonal_adjustment": "seasonally_adjusted",
        "transformation": "twelve_month_percent_change",
        "formula": "(index_t / index_t-12 - 1) * 100",
        "period": "2026-09-01",
        "comparison_period": "2025-09-01",
        "index_level": "275.000",
        "comparison_index_level": "250.000",
        "twelve_month_percent_change": "10.0000",
        "values_strictly_below": 4,
        "rank": 5,
    },
    "federal_funds": {
        "dataset_id": FED_FUNDS_DATASET_ID,
        "unit": "percent_per_year",
        "seasonal_adjustment": "unknown",
        "transformation": "level_and_one_month_change",
        "period": "2026-09-01",
        "prior_period": "2026-08-01",
        "level_percent_per_year": "4.22",
        "prior_level_percent_per_year": "4.33",
        "one_month_change_percentage_points": "-0.1100",
        "values_strictly_below": 1,
        "rank": 2,
    },
    "treasury_10_year": {
        "dataset_id": TREASURY_10Y_DATASET_ID,
        "unit": "percent_per_year",
        "seasonal_adjustment": "unknown",
        "transformation": "level_and_one_month_change",
        "period": "2026-09-01",
        "prior_period": "2026-08-01",
        "level_percent_per_year": "4.14",
        "prior_level_percent_per_year": "4.26",
        "one_month_change_percentage_points": "-0.1200",
        "values_strictly_below": 2,
        "rank": 3,
    },
}

SEPTEMBER_2026_OBSERVATION_IDS = (
    "cpi-2024-09",
    "cpi-2025-09",
    "cpi-2026-07",
    "cpi-2026-08",
    "cpi-2026-09",
    "ff-2025-08",
    "ff-2025-09",
    "ff-2025-10",
    "ff-2026-08",
    "ff-2026-09",
    "t10-2025-08",
    "t10-2025-09",
    "t10-2025-10",
    "t10-2026-08",
    "t10-2026-09",
)


def _load_inputs() -> dict[str, dict[date, EconomicObservation]]:
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    inputs: dict[str, dict[date, EconomicObservation]] = {}
    for series in payload["series"]:
        rows: dict[date, EconomicObservation] = {}
        for item in series["observations"]:
            observation = _observation(series, item)
            rows[observation.period_start] = observation
        inputs[series["dataset_id"]] = rows
    return inputs


def _observation(series: dict[str, object], item: dict[str, str]) -> EconomicObservation:
    return EconomicObservation(
        observation_id=item["observation_id"],
        dataset_id=str(series["dataset_id"]),
        provider_id=str(series["provider_id"]),
        source_id=str(series["source_id"]),
        rights_record_id=str(series["source_id"]),
        period_start=date.fromisoformat(item["period_start"]),
        frequency=Frequency.MONTHLY,
        geography="US",
        unit=str(series["unit"]),
        seasonal_adjustment=SeasonalAdjustment(str(series["seasonal_adjustment"])),
        raw_value=item["raw_value"],
        quality_status=QualityStatus.OBSERVED,
        series_provenance=SeriesProvenance.LATEST_REVISED,
        provider_vintage_date=date(2026, 10, 16),
        availability_precision=AvailabilityPrecision.UNKNOWN,
        retrieved_at=RETRIEVED,
        first_seen_at=RETRIEVED,
        adapter_version="prices_and_policy_fixture_v1",
    )


def _run(
    inputs: dict[str, dict[date, EconomicObservation]],
    evaluation: date,
    analysis_mode: AnalysisMode = AnalysisMode.LATEST_REVISED,
):
    method = PricesAndPolicyMethod()
    context = MethodContext(
        inputs_by_dataset=inputs,
        evaluation_period=evaluation,
        analysis_mode=analysis_mode,
        primary_dataset_id=CPI_DATASET_ID,
    )
    return method.run(context, method.parse_config(CONFIG))


def test_method_identity_and_inputs() -> None:
    method = PricesAndPolicyMethod()
    assert method.method_id == PRICES_AND_POLICY_METHOD_ID
    assert method.method_version == PRICES_AND_POLICY_METHOD_VERSION
    assert method.required_dataset_ids() == (
        CPI_DATASET_ID,
        FED_FUNDS_DATASET_ID,
        TREASURY_10Y_DATASET_ID,
    )
    assert HICP_DATASET_ID not in method.required_dataset_ids()
    registered = default_method_registry().get(PRICES_AND_POLICY_METHOD_ID)
    assert registered.method_id == PRICES_AND_POLICY_METHOD_ID
    assert registered.method_version == "1.0.0"


def test_september_2025_to_september_2026_fixture_calculation() -> None:
    result = _run(_load_inputs(), date(2026, 9, 1))
    assert result.sufficiency == "sufficient"
    assert result.calculation == SEPTEMBER_2026_CALCULATION
    assert result.observation_ids == SEPTEMBER_2026_OBSERVATION_IDS
    assert result.investment_implication == "no_action"
    assert result.causal_hypothesis == CAUSAL_HYPOTHESIS
    assert result.missing_reason is None
    assert "cpi-2026-10" not in result.observation_ids
    assert "ff-2026-10" not in result.observation_ids
    assert "t10-2026-10" not in result.observation_ids

    cpi = SEPTEMBER_2026_CALCULATION["cpi_u"]
    expected_change = (
        Decimal(cpi["index_level"]) / Decimal(cpi["comparison_index_level"]) - 1
    ) * 100
    assert Decimal(cpi["twelve_month_percent_change"]) == expected_change
    funds = SEPTEMBER_2026_CALCULATION["federal_funds"]
    treasury = SEPTEMBER_2026_CALCULATION["treasury_10_year"]
    assert Decimal(funds["one_month_change_percentage_points"]) == (
        Decimal(funds["level_percent_per_year"]) - Decimal(funds["prior_level_percent_per_year"])
    )
    assert Decimal(treasury["one_month_change_percentage_points"]) == (
        Decimal(treasury["level_percent_per_year"])
        - Decimal(treasury["prior_level_percent_per_year"])
    )
    rate_gap = Decimal(treasury["level_percent_per_year"]) - Decimal(
        funds["level_percent_per_year"]
    )
    rendered = json.dumps(result.calculation)
    assert f"{rate_gap:.4f}" not in rendered
    assert "spread" not in rendered.lower()
    assert "real rate" not in rendered.lower()
    assert "real_rate" not in rendered.lower()
    assert "forward" not in rendered.lower()
    assert HICP_DATASET_ID not in rendered
    assert "HICP" not in result.narrative
    hicp = " ".join(result.limitations)
    assert "HICP (ecb.icp.M.U2.Y.000000.3.INX) is a separate series ending 2025-12-01" in hicp
    assert "index, 2015 = 100" in hicp


def test_rank_one_is_the_lowest_stored_level() -> None:
    result = _run(_load_inputs(), date(2025, 9, 1))
    assert result.sufficiency == "sufficient"
    calculation = result.calculation or {}
    assert calculation["cpi_u"]["twelve_month_percent_change"] == "0.0000"
    assert calculation["cpi_u"]["values_strictly_below"] == 0
    assert calculation["cpi_u"]["rank"] == 1
    assert calculation["federal_funds"]["rank"] == 1
    assert calculation["treasury_10_year"]["rank"] == 1
    assert calculation["federal_funds"]["one_month_change_percentage_points"] == "-0.2800"
    assert calculation["treasury_10_year"]["one_month_change_percentage_points"] == "-0.1500"


def test_window_that_needs_missing_october_2025_cpi_endpoint_is_insufficient() -> None:
    as_start = _run(_load_inputs(), date(2026, 10, 1))
    assert as_start.sufficiency == "insufficient"
    assert as_start.calculation is None
    assert as_start.observation_ids == ()
    assert as_start.investment_implication == "insufficient_evidence"
    assert as_start.causal_hypothesis == CAUSAL_HYPOTHESIS
    assert as_start.missing_reason == (
        "missing CPI-U endpoint 2025-10-01 for the 12-month window 2025-10-01 to 2026-10-01"
    )

    as_end = _run(_load_inputs(), date(2025, 10, 1))
    assert as_end.sufficiency == "insufficient"
    assert as_end.calculation is None
    assert as_end.observation_ids == ()
    assert as_end.missing_reason == (
        "missing CPI-U endpoint 2024-10-01 and 2025-10-01 "
        "for the 12-month window 2024-10-01 to 2025-10-01"
    )


def test_missing_federal_funds_prior_month_fails_that_window() -> None:
    inputs = _load_inputs()
    del inputs[FED_FUNDS_DATASET_ID][date(2026, 8, 1)]
    result = _run(inputs, date(2026, 9, 1))
    assert result.sufficiency == "insufficient"
    assert result.calculation is None
    assert result.observation_ids == ()
    assert result.missing_reason == (
        "missing federal funds endpoint 2026-08-01 for the one-month window "
        "2026-08-01 to 2026-09-01"
    )


def test_point_in_time_is_insufficient() -> None:
    result = _run(_load_inputs(), date(2026, 9, 1), AnalysisMode.POINT_IN_TIME)
    assert result.sufficiency == "insufficient"
    assert result.calculation is None
    assert result.observation_ids == ()
    assert result.investment_implication == "insufficient_evidence"
    assert result.causal_hypothesis == CAUSAL_HYPOTHESIS
    assert result.missing_reason is not None
    assert result.missing_reason.startswith("point_in_time is insufficient")
    assert "HICP" in " ".join(result.limitations)
    assert HICP_DATASET_ID not in result.narrative


def test_fragment_names_hicp_only_as_a_separate_series() -> None:
    fragment = json.loads(FRAGMENT.read_text(encoding="utf-8"))
    input_ids = [row["dataset_id"] for row in fragment["inputs"]]
    assert input_ids == [CPI_DATASET_ID, FED_FUNDS_DATASET_ID, TREASURY_10Y_DATASET_ID]
    separate = fragment["separate_series"]
    assert separate["name"] == "HICP"
    assert separate["dataset_id"] == HICP_DATASET_ID
    assert separate["latest_period_start"] == "2025-12-01"
    assert separate["unit"] == "index, 2015 = 100"
    assert separate["role"] == "limitation_only"
    assert fragment["causal_hypothesis"] == CAUSAL_HYPOTHESIS
    assert fragment["analysis_mode"] == "latest_revised"
    assert fragment["point_in_time"] == "insufficient"
