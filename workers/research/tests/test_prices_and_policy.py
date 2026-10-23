"""Fixture tests for the prices and policy reading. No database."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
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
    PRICES_AND_POLICY_METHOD_ID,
    PRICES_AND_POLICY_METHOD_VERSION,
    PricesAndPolicyMethod,
)
from aqil_research.methods.protocol import MethodContext, MethodExecutionResult

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "prices_and_policy.json"
FRAGMENT_PATH = (
    Path(__file__).resolve().parents[3]
    / "docs"
    / "sources"
    / "fragments"
    / "PRICES_AND_POLICY.json"
)
CONFIG = {
    "config_id": "prices_and_policy_fixture_v1",
    "label": "Prices and policy fixture",
}
RETRIEVED_AT = datetime(2026, 10, 22, 12, 0, tzinfo=UTC)
VINTAGE = date(2026, 10, 22)
HICP_OBSERVATION_ID = "hicp-2025-12"
CHANGE_SCALE = Decimal("0.0001")
_SOURCES = {
    "bls.cu.CUSR0000SA0": ("bls", "bls_cpi_u_all_items"),
    "fed.h15.RIFSPFF_N.M": (
        "federal_reserve_board",
        "federal_reserve_h15_federal_funds_effective",
    ),
    "fed.h15.RIFLGFCY10_N.M": (
        "federal_reserve_board",
        "federal_reserve_h15_treasury_10y_constant_maturity",
    ),
    "ecb.icp.M.U2.Y.000000.3.INX": ("ecb", "ecb_sdw_hicp_sa"),
}


def test_sufficient_cpi_12_month_change() -> None:
    method = PricesAndPolicyMethod()
    result = _run(method, date(2026, 9, 1), AnalysisMode.LATEST_REVISED)
    fragment = json.loads(FRAGMENT_PATH.read_text(encoding="utf-8"))
    cpi = result.calculation["cpi_u"]
    later = Decimal("312.000")
    earlier = Decimal("300.000")
    expected = ((later / earlier) - 1) * Decimal(100)
    expected = expected.quantize(CHANGE_SCALE, rounding=ROUND_HALF_UP)

    assert method.method_id == PRICES_AND_POLICY_METHOD_ID == fragment["method_id"]
    assert method.method_version == PRICES_AND_POLICY_METHOD_VERSION == fragment["method_version"]
    assert "ecb.icp.M.U2.Y.000000.3.INX" not in method.required_dataset_ids()
    assert result.sufficiency == "sufficient"
    assert result.investment_implication == "no_action"
    assert result.causal_hypothesis == "No causal mechanism is established."
    assert cpi["window_start"] == "2025-09-01"
    assert cpi["window_end"] == "2026-09-01"
    assert cpi["unit"] == "percent"
    assert cpi["formula"] == "(later_index / earlier_index - 1) * 100"
    assert Decimal(cpi["percent_change"]) == expected
    assert cpi["earlier_observation_id"] == "cpi-u-2025-09"
    assert cpi["later_observation_id"] == "cpi-u-2026-09"
    assert cpi["latest_value_rank"] == _rank_from_fixture("bls.cu.CUSR0000SA0", later)
    assert result.calculation["federal_funds"]["latest_value_rank"] == _rank_from_fixture(
        "fed.h15.RIFSPFF_N.M",
        Decimal("5.13"),
    )
    assert result.calculation["treasury_10_year_yield"]["latest_value_rank"] == _rank_from_fixture(
        "fed.h15.RIFLGFCY10_N.M",
        Decimal("4.27"),
    )
    assert HICP_OBSERVATION_ID not in result.observation_ids
    assert any("ends December 2025 and is excluded" in item for item in result.limitations)
    _assert_fragment(result, fragment)


def test_missing_cpi_endpoint_is_insufficient() -> None:
    result = _run(PricesAndPolicyMethod(), date(2025, 10, 1), AnalysisMode.LATEST_REVISED)
    assert result.sufficiency == "insufficient"
    assert result.calculation is None
    assert result.observation_ids == ()
    assert result.investment_implication == "insufficient_evidence"
    assert result.causal_hypothesis == "No causal mechanism is established."
    assert result.missing_reason == (
        "Missing CPI-U 12-month endpoint 2025-10-01 for window 2024-10-01 to 2025-10-01."
    )
    assert any("ends December 2025 and is excluded" in item for item in result.limitations)


def test_does_not_emit_funds_minus_yield() -> None:
    result = _run(PricesAndPolicyMethod(), date(2026, 9, 1), AnalysisMode.LATEST_REVISED)
    funds = result.calculation["federal_funds"]
    treasury = result.calculation["treasury_10_year_yield"]
    funds_level = Decimal(funds["level"])
    yield_level = Decimal(treasury["level"])
    cpi_change = Decimal(result.calculation["cpi_u"]["percent_change"])
    present = _decimals(result.calculation)
    forbidden = (
        funds_level - yield_level,
        funds_level - cpi_change,
        yield_level - cpi_change,
    )

    assert Decimal(funds["one_month_change"]) == funds_level - Decimal(funds["prior_level"])
    assert Decimal(treasury["one_month_change"]) == yield_level - Decimal(treasury["prior_level"])
    for figure in forbidden:
        assert figure.quantize(CHANGE_SCALE, rounding=ROUND_HALF_UP) not in present
    for key in _keys(result.calculation):
        lowered = key.lower()
        assert "spread" not in lowered
        assert "minus" not in lowered
        assert "real_rate" not in lowered
        assert "forward" not in lowered
    blob = json.dumps(
        {
            "calculation": result.calculation,
            "narrative": result.narrative,
            "assumptions": result.assumptions,
            "limitations": result.limitations,
            "statistical_interpretation": result.statistical_interpretation,
        },
    ).lower()
    assert "near-term forward spread" not in blob
    assert "near_term_forward_spread" not in blob


def test_point_in_time_is_insufficient() -> None:
    result = _run(PricesAndPolicyMethod(), date(2026, 9, 1), AnalysisMode.POINT_IN_TIME)
    assert result.sufficiency == "insufficient"
    assert result.calculation is None
    assert result.observation_ids == ()
    assert result.investment_implication == "insufficient_evidence"
    assert result.causal_hypothesis == "No causal mechanism is established."
    assert result.missing_reason == (
        "Point-in-time is insufficient because these files are not vintage panels."
    )
    assert "4.0000" not in (result.missing_reason or "")
    assert any("ends December 2025 and is excluded" in item for item in result.limitations)


def _run(
    method: PricesAndPolicyMethod,
    evaluation_period: date,
    analysis_mode: AnalysisMode,
) -> MethodExecutionResult:
    observations = _load_observations()
    observations.append(_hicp_observation())
    inputs: dict[str, dict[date, EconomicObservation]] = {}
    for obs in observations:
        inputs.setdefault(obs.dataset_id, {})[obs.period_start] = obs
    context = MethodContext(
        inputs_by_dataset=inputs,
        evaluation_period=evaluation_period,
        analysis_mode=analysis_mode,
        primary_dataset_id="bls.cu.CUSR0000SA0",
    )
    return method.run(context, method.parse_config(CONFIG))


def _assert_fragment(result: MethodExecutionResult, fragment: dict[str, object]) -> None:
    assert result.sufficiency == fragment["sufficiency"]
    assert result.calculation == fragment["calculation"]
    assert list(result.observation_ids) == fragment["observation_ids"]
    assert list(result.assumptions) == fragment["assumptions"]
    assert list(result.limitations) == fragment["limitations"]
    assert result.missing_reason == fragment["missing_reason"]
    assert result.statistical_interpretation == fragment["statistical_interpretation"]
    assert result.causal_hypothesis == fragment["causal_hypothesis"]
    assert result.investment_implication == fragment["investment_implication"]
    assert result.narrative == fragment["narrative"]


def _rank_from_fixture(dataset_id: str, latest: Decimal) -> int:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    values = [
        Decimal(row["raw_value"])
        for row in payload["observations"]
        if row["dataset_id"] == dataset_id
    ]
    return 1 + sum(1 for value in values if value < latest)


def _load_observations() -> list[EconomicObservation]:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return [_observation(row) for row in payload["observations"]]


def _observation(row: dict[str, str]) -> EconomicObservation:
    provider_id, source_id = _SOURCES[row["dataset_id"]]
    return EconomicObservation(
        observation_id=row["observation_id"],
        dataset_id=row["dataset_id"],
        provider_id=provider_id,
        source_id=source_id,
        rights_record_id=source_id,
        period_start=date.fromisoformat(row["period_start"]),
        frequency=Frequency.MONTHLY,
        geography="US" if provider_id != "ecb" else "EA",
        unit=row["unit"],
        seasonal_adjustment=SeasonalAdjustment(row["seasonal_adjustment"]),
        raw_value=row["raw_value"],
        quality_status=QualityStatus.OBSERVED,
        series_provenance=SeriesProvenance.LATEST_REVISED,
        provider_vintage_date=VINTAGE,
        availability_precision=AvailabilityPrecision.UNKNOWN,
        earliest_model_available_at=None,
        retrieved_at=RETRIEVED_AT,
        first_seen_at=RETRIEVED_AT,
        adapter_version="prices_and_policy_fixture_v1",
    )


def _hicp_observation() -> EconomicObservation:
    return _observation(
        {
            "observation_id": HICP_OBSERVATION_ID,
            "dataset_id": "ecb.icp.M.U2.Y.000000.3.INX",
            "period_start": "2025-12-01",
            "raw_value": "128.50",
            "unit": "index, 2015 = 100",
            "seasonal_adjustment": "seasonally_adjusted",
        },
    )


def _keys(value: object) -> list[str]:
    keys: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            keys.append(str(key))
            keys.extend(_keys(item))
    elif isinstance(value, list):
        for item in value:
            keys.extend(_keys(item))
    return keys


def _decimals(value: object) -> set[Decimal]:
    found: list[Decimal] = []
    if isinstance(value, dict):
        for item in value.values():
            found.extend(_decimals(item))
    elif isinstance(value, list):
        for item in value:
            found.extend(_decimals(item))
    elif isinstance(value, bool) or value is None:
        return set(found)
    elif isinstance(value, int):
        found.append(Decimal(value))
    elif isinstance(value, str):
        try:
            found.append(Decimal(value))
        except InvalidOperation:
            pass
    return set(found)
