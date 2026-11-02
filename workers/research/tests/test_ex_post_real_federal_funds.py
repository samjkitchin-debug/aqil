"""Ex-post real federal funds rate. Hand-checked percent-change identity."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from decimal import Decimal

from aqil_research.contracts.observation import (
    AnalysisMode,
    AvailabilityPrecision,
    EconomicObservation,
    Frequency,
    QualityStatus,
    SeasonalAdjustment,
    SeriesProvenance,
)
from aqil_research.methods.ex_post_real_federal_funds import (
    EX_POST_REAL_FEDERAL_FUNDS_RATE,
    HORIZON_MONTHS,
    INFLATION_FORMULA,
    PUBLICATION_ALLOWED,
    PUBLISHED_CONFIG,
    QUALIFICATION_STATEMENT,
    ExPostRealFederalFundsRateMethod,
    ex_post_real_rate,
    twelve_month_percent_change,
)
from aqil_research.methods.prices_and_policy import (
    CPI_DATASET_ID,
    CPI_UNIT,
    FED_FUNDS_DATASET_ID,
    RATE_UNIT,
)
from aqil_research.methods.protocol import MethodContext
from aqil_research.methods.registry import default_method_registry


def test_percent_change_identity_is_not_a_log_change() -> None:
    # 110 / 100 - 1 = 0.10, times 100 = 10 percentage points.
    # 100 * log(110 / 100) is about 9.53 and is not the transformation used here.
    inflation = twelve_month_percent_change(Decimal("110"), Decimal("100"))
    assert inflation == Decimal("10")
    assert ex_post_real_rate(Decimal("6"), inflation) == Decimal("-4.0000")
    # 203 / 200 - 1 = 0.015, times 100 = 1.5. 5.25 - 1.5 = 3.75.
    second = twelve_month_percent_change(Decimal("203"), Decimal("200"))
    assert second == Decimal("1.5")
    assert ex_post_real_rate(Decimal("5.25"), second) == Decimal("3.7500")


def test_method_uses_trailing_endpoints_and_stays_unpublished() -> None:
    method = ExPostRealFederalFundsRateMethod()
    config = method.parse_config(dict(PUBLISHED_CONFIG))
    assert method.method_id == EX_POST_REAL_FEDERAL_FUNDS_RATE
    assert PUBLICATION_ALLOWED is False
    assert HORIZON_MONTHS == 12
    assert method.accepted_config_payload()["config_id"] == "ex-post-real-federal-funds-rate-v1"
    dependency = method.dependency()
    assert dependency.source_series == (FED_FUNDS_DATASET_ID, CPI_DATASET_ID)
    assert dependency.vintage_class == "latest_revised"
    assert dependency.minimum_history.startswith("1 aligned month")
    assert dependency.parameter_policy == "none"
    assert dependency.refit_is_different_command is False
    assert default_method_registry().get(EX_POST_REAL_FEDERAL_FUNDS_RATE).method_id == (
        EX_POST_REAL_FEDERAL_FUNDS_RATE
    )

    cpi = {
        date(2000, 1, 1): _cpi(date(2000, 1, 1), "100"),
        date(2000, 2, 1): _cpi(date(2000, 2, 1), "200"),
        date(2001, 1, 1): _cpi(date(2001, 1, 1), "110"),
        date(2001, 2, 1): _cpi(date(2001, 2, 1), "203"),
    }
    funds = {
        date(2001, 1, 1): _funds(date(2001, 1, 1), "6"),
        date(2001, 2, 1): _funds(date(2001, 2, 1), "5.25"),
    }
    result = method.run(_context(cpi, funds, date(2001, 2, 1)), config)
    assert result.sufficiency == "sufficient"
    assert result.investment_implication == "no_action"
    assert result.causal_hypothesis == "none"
    calculation = result.calculation
    assert calculation is not None
    assert calculation["publication_allowed"] is False
    assert calculation["real_time_claim"] is False
    assert calculation["empirically_qualified_as_forecast"] is False
    assert calculation["qualification_statement"] == QUALIFICATION_STATEMENT
    assert calculation["inflation_transformation"] == "twelve_month_percent_change"
    assert calculation["inflation_formula"] == INFLATION_FORMULA
    assert calculation["monthly_log_change_used"] is False
    assert calculation["alignment"] == "trailing_same_month"
    assert calculation["not_taylor_rule"] is True
    assert calculation["not_ex_ante"] is True
    assert calculation["output_gap_estimated"] is False
    assert calculation["persistence_estimated"] is False
    assert calculation["andrews_chen_median_unbiased"] is False
    assert calculation["policy_prescription"] == "none"
    assert calculation["aligned_month_count"] == 2
    assert calculation["latest_period"] == "2001-02-01"
    assert calculation["latest_federal_funds_rate_percent"] == "5.2500"
    assert calculation["latest_cpi_u_inflation_percent"] == "1.5000"
    assert calculation["latest_ex_post_real_rate_percentage_points"] == "3.7500"
    january = calculation["months"][0]
    assert january["cpi_u_inflation_percent"] == "10.0000"
    assert january["ex_post_real_rate_percentage_points"] == "-4.0000"
    assert january["cpi_comparison_period"] == "2000-01-01"
    encoded = json.dumps(calculation)
    assert "NaN" not in encoded

    refused = method.run(
        _context(cpi, funds, date(2001, 2, 1), analysis_mode=AnalysisMode.POINT_IN_TIME),
        config,
    )
    assert refused.sufficiency == "insufficient"
    assert refused.investment_implication == "insufficient_evidence"
    assert refused.calculation is not None
    assert refused.calculation["publication_allowed"] is False

    missing_endpoint = method.run(
        _context(
            {date(2001, 2, 1): cpi[date(2001, 2, 1)]},
            funds,
            date(2001, 2, 1),
        ),
        config,
    )
    assert missing_endpoint.sufficiency == "insufficient"


def _context(
    cpi: dict[date, EconomicObservation],
    funds: dict[date, EconomicObservation],
    evaluation: date,
    *,
    analysis_mode: AnalysisMode = AnalysisMode.LATEST_REVISED,
) -> MethodContext:
    return MethodContext(
        inputs_by_dataset={CPI_DATASET_ID: cpi, FED_FUNDS_DATASET_ID: funds},
        evaluation_period=evaluation,
        analysis_mode=analysis_mode,
        primary_dataset_id=FED_FUNDS_DATASET_ID,
    )


def _cpi(period: date, raw_value: str) -> EconomicObservation:
    return _observation(
        period,
        raw_value,
        dataset_id=CPI_DATASET_ID,
        unit=CPI_UNIT,
        seasonal_adjustment=SeasonalAdjustment.SEASONALLY_ADJUSTED,
    )


def _funds(period: date, raw_value: str) -> EconomicObservation:
    return _observation(
        period,
        raw_value,
        dataset_id=FED_FUNDS_DATASET_ID,
        unit=RATE_UNIT,
        seasonal_adjustment=SeasonalAdjustment.UNKNOWN,
    )


def _observation(
    period: date,
    raw_value: str,
    *,
    dataset_id: str,
    unit: str,
    seasonal_adjustment: SeasonalAdjustment,
) -> EconomicObservation:
    retrieved = datetime(2026, 8, 1, tzinfo=UTC)
    return EconomicObservation(
        observation_id=f"{dataset_id}-{period.isoformat()}",
        dataset_id=dataset_id,
        provider_id="test",
        source_id="test",
        rights_record_id="test",
        period_start=period,
        frequency=Frequency.MONTHLY,
        geography="US",
        unit=unit,
        seasonal_adjustment=seasonal_adjustment,
        raw_value=raw_value,
        quality_status=QualityStatus.OBSERVED,
        series_provenance=SeriesProvenance.LATEST_REVISED,
        provider_vintage_date=period,
        availability_precision=AvailabilityPrecision.UNKNOWN,
        retrieved_at=retrieved,
        first_seen_at=retrieved,
        adapter_version="test",
    )
