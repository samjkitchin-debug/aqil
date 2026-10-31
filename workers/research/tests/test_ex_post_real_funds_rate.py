"""Ex-post real federal funds rate. Synthetic series only."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from aqil_research.contracts.observation import (
    AnalysisMode,
    AvailabilityPrecision,
    EconomicObservation,
    Frequency,
    QualityStatus,
    SeasonalAdjustment,
    SeriesProvenance,
)
from aqil_research.methods.ex_post_real_funds_rate import (
    CPI_DATASET_ID,
    CPI_UNIT,
    EX_POST_REAL_FUNDS_RATE,
    FED_FUNDS_DATASET_ID,
    HORIZON_MONTHS,
    INFLATION_EQUATION,
    PUBLICATION_ALLOWED,
    RATE_UNIT,
    REAL_RATE_EQUATION,
    ExPostRealFundsRateMethod,
    ex_post_real_rate,
)
from aqil_research.methods.protocol import MethodContext
from aqil_research.pipeline.execute_method import execution_refusal


def test_contract_is_latest_revised_and_refit_is_rejected() -> None:
    method = ExPostRealFundsRateMethod()
    dependency = method.dependency()
    assert method.method_id == EX_POST_REAL_FUNDS_RATE
    assert PUBLICATION_ALLOWED is False
    assert method.required_dataset_ids() == (FED_FUNDS_DATASET_ID, CPI_DATASET_ID)
    assert dependency.source_series == (FED_FUNDS_DATASET_ID, CPI_DATASET_ID)
    assert dependency.frequency == ("monthly",)
    assert dependency.vintage_class == "latest_revised"
    assert dependency.parameter_policy == "none"
    assert dependency.depends_on_method_ids == ()
    assert "INFLATION_AUTOREGRESSION" not in dependency.depends_on_method_ids
    assert dependency.new_observation_requires_recalculation is True
    assert dependency.refit_is_different_command is False
    assert execution_refusal(method, refit=True) is not None
    assert execution_refusal(method, refit=False) is None
    assert len(method.implementation_hash()) == 64
    payload = method.accepted_config_payload()
    assert "output_gap" not in payload
    assert "inflation_target" not in payload
    config = method.parse_config(payload)
    assert method.config_hash(config)
    with pytest.raises(ValidationError):
        method.parse_config({**payload, "execution_mode": "refit"})


def test_real_rate_is_funds_minus_subsequent_twelve_month_inflation() -> None:
    inflation, real_rate = ex_post_real_rate(Decimal("5.5000"), Decimal("100"), Decimal("110"))
    assert inflation == Decimal("10")
    assert real_rate == Decimal("-4.5")
    method = ExPostRealFundsRateMethod()
    config = method.parse_config(method.accepted_config_payload())
    cpi = {
        date(2018, 1, 1): _cpi(date(2018, 1, 1), "100"),
        date(2019, 1, 1): _cpi(date(2019, 1, 1), "110"),
        date(2019, 6, 1): _cpi(date(2019, 6, 1), "999"),
        date(2020, 1, 1): _cpi(date(2020, 1, 1), "121"),
    }
    funds = {
        date(2018, 1, 1): _funds(date(2018, 1, 1), "1.0000"),
        date(2019, 1, 1): _funds(date(2019, 1, 1), "5.5000"),
        date(2020, 1, 1): _funds(date(2020, 1, 1), "99.0000"),
    }
    result = method.run(_context(cpi, funds, date(2020, 1, 1)), config)
    assert result.sufficiency == "sufficient"
    calculation = result.calculation
    assert calculation is not None
    assert calculation["equation"] == REAL_RATE_EQUATION
    assert calculation["inflation_equation"] == INFLATION_EQUATION
    assert calculation["horizon_months"] == HORIZON_MONTHS == 12
    assert calculation["endpoints_only"] is True
    assert calculation["funds_month"] == "2019-01-01"
    assert calculation["inflation_end_month"] == "2020-01-01"
    assert calculation["federal_funds_percent_per_year"] == "5.5000"
    assert calculation["cpi_index_at_t"] == "110"
    assert calculation["cpi_index_at_t_plus_horizon"] == "121"
    assert calculation["inflation_percent"] == "10.0000"
    assert calculation["real_funds_rate_percent_per_year"] == "-4.5000"
    assert calculation["computable_month_count"] == 2
    assert calculation["twelve_month_price_rank"] is False
    assert "rank" not in calculation
    assert set(result.observation_ids) == {
        "cpi-2018-01-01",
        "cpi-2019-01-01",
        "cpi-2020-01-01",
        "funds-2018-01-01",
        "funds-2019-01-01",
    }
    assert "cpi-2019-06-01" not in result.observation_ids
    earlier = method.run(_context(cpi, funds, date(2019, 1, 1)), config)
    assert earlier.calculation["funds_month"] == "2018-01-01"
    assert earlier.calculation["inflation_end_month"] == "2019-01-01"
    assert earlier.calculation["federal_funds_percent_per_year"] == "1.0000"
    assert earlier.calculation["real_funds_rate_percent_per_year"] == "-9.0000"
    assert earlier.calculation["computable_month_count"] == 1
    _assert_not_a_taylor_rule_or_qualified_forecast(result)
    _assert_not_a_taylor_rule_or_qualified_forecast(earlier)
    json.dumps(calculation, allow_nan=False)


def test_display_rounding_uses_the_exact_difference() -> None:
    inflation, real_rate = ex_post_real_rate(Decimal("5.2500"), Decimal("300"), Decimal("310"))
    assert inflation == (Decimal("310") / Decimal("300") - 1) * 100
    assert real_rate == Decimal("5.2500") - inflation
    method = ExPostRealFundsRateMethod()
    config = method.parse_config(method.accepted_config_payload())
    cpi = {
        date(2019, 1, 1): _cpi(date(2019, 1, 1), "300"),
        date(2020, 1, 1): _cpi(date(2020, 1, 1), "310"),
    }
    funds = {date(2019, 1, 1): _funds(date(2019, 1, 1), "5.2500")}
    result = method.run(_context(cpi, funds, date(2020, 1, 1)), config)
    assert result.sufficiency == "sufficient"
    assert result.calculation["inflation_percent"] == "3.3333"
    assert result.calculation["real_funds_rate_percent_per_year"] == "1.9167"


def test_a_missing_intermediate_month_does_not_block_the_endpoints() -> None:
    method = ExPostRealFundsRateMethod()
    config = method.parse_config(method.accepted_config_payload())
    months = _months(date(2019, 1, 1), 13)
    cpi = {month: _cpi(month, "100" if month < months[-1] else "103") for month in months}
    del cpi[date(2019, 6, 1)]
    funds = {months[0]: _funds(months[0], "2.0000")}
    result = method.run(_context(cpi, funds, months[-1]), config)
    assert result.sufficiency == "sufficient"
    assert result.calculation["inflation_percent"] == "3.0000"
    assert result.calculation["real_funds_rate_percent_per_year"] == "-1.0000"
    assert result.calculation["endpoints_only"] is True
    assert date(2019, 6, 1).isoformat() not in result.observation_ids


def test_empty_and_short_samples_do_not_invent_a_rate() -> None:
    method = ExPostRealFundsRateMethod()
    config = method.parse_config(method.accepted_config_payload())
    empty = method.run(_context({}, {}, date(2020, 1, 1)), config)
    assert empty.sufficiency == "insufficient"
    assert empty.observation_ids == ()
    _assert_not_a_taylor_rule_or_qualified_forecast(empty)
    short_months = _months(date(2019, 1, 1), 6)
    short_cpi = {month: _cpi(month, "100") for month in short_months}
    short_funds = {month: _funds(month, "1.0000") for month in short_months}
    short = method.run(_context(short_cpi, short_funds, short_months[-1]), config)
    assert short.sufficiency == "insufficient"
    assert "real_funds_rate_percent_per_year" not in short.calculation
    _assert_not_a_taylor_rule_or_qualified_forecast(short)
    cpi_only = method.run(
        _context({date(2020, 1, 1): _cpi(date(2020, 1, 1), "100")}, {}, date(2020, 1, 1)),
        config,
    )
    funds_only = method.run(
        _context({}, {date(2020, 1, 1): _funds(date(2020, 1, 1), "1.0000")}, date(2020, 1, 1)),
        config,
    )
    assert cpi_only.sufficiency == "insufficient"
    assert funds_only.sufficiency == "insufficient"
    end_only_funds = {
        date(2019, 1, 1): _cpi(date(2019, 1, 1), "100"),
        date(2020, 1, 1): _cpi(date(2020, 1, 1), "110"),
    }
    funds_at_end = {date(2020, 1, 1): _funds(date(2020, 1, 1), "5.0000")}
    missing_start_rate = method.run(
        _context(end_only_funds, funds_at_end, date(2020, 1, 1)),
        config,
    )
    assert missing_start_rate.sufficiency == "insufficient"
    zero_price = {
        date(2019, 1, 1): _cpi(date(2019, 1, 1), "0"),
        date(2020, 1, 1): _cpi(date(2020, 1, 1), "110"),
    }
    assert (
        method.run(
            _context(
                zero_price,
                {date(2019, 1, 1): _funds(date(2019, 1, 1), "5")},
                date(2020, 1, 1),
            ),
            config,
        ).sufficiency
        == "insufficient"
    )


def test_point_in_time_and_the_wrong_vintage_are_not_used() -> None:
    method = ExPostRealFundsRateMethod()
    config = method.parse_config(method.accepted_config_payload())
    cpi = {
        date(2019, 1, 1): _cpi(date(2019, 1, 1), "100"),
        date(2020, 1, 1): _cpi(date(2020, 1, 1), "110"),
    }
    funds = {date(2019, 1, 1): _funds(date(2019, 1, 1), "5.5000")}
    refused = method.run(
        _context(cpi, funds, date(2020, 1, 1), analysis_mode=AnalysisMode.POINT_IN_TIME),
        config,
    )
    assert refused.sufficiency == "insufficient"
    _assert_not_a_taylor_rule_or_qualified_forecast(refused)
    vintage_cpi = {
        date(2019, 1, 1): _cpi(
            date(2019, 1, 1),
            "100",
            provenance=SeriesProvenance.PROVIDER_VINTAGE,
        ),
        date(2020, 1, 1): _cpi(
            date(2020, 1, 1),
            "110",
            provenance=SeriesProvenance.PROVIDER_VINTAGE,
        ),
    }
    assert (
        method.run(_context(vintage_cpi, funds, date(2020, 1, 1)), config).sufficiency
        == "insufficient"
    )


def _assert_not_a_taylor_rule_or_qualified_forecast(result) -> None:
    calculation = result.calculation
    assert calculation["publication_allowed"] is False
    assert calculation["product_forecast"] is False
    assert calculation["taylor_rule"] is False
    assert calculation["output_gap_used"] is False
    assert calculation["inflation_target_used"] is False
    assert calculation["recommended_policy_rate_computed"] is False
    assert calculation["empirically_qualified_as_forecast"] is False
    assert calculation["retrospective"] is True
    assert calculation["input_vintage"] == "latest_revised"
    assert calculation["parameter_policy"] == "none"
    assert calculation["refit_rejected"] is True
    assert "output_gap" not in calculation
    assert "inflation_target" not in calculation
    assert "recommended_policy_rate" not in calculation
    narrative = result.narrative.lower()
    assert "not a taylor rule" in narrative
    assert "not a qualified forecast" in narrative
    assert "output gap" in narrative
    assert result.causal_hypothesis == "none"
    assert result.investment_implication in {"no_action", "insufficient_evidence"}


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


def _cpi(
    period: date,
    raw_value: str,
    *,
    provenance: SeriesProvenance = SeriesProvenance.LATEST_REVISED,
) -> EconomicObservation:
    return _observation(
        period,
        raw_value,
        dataset_id=CPI_DATASET_ID,
        unit=CPI_UNIT,
        seasonal_adjustment=SeasonalAdjustment.SEASONALLY_ADJUSTED,
        provenance=provenance,
        observation_id=f"cpi-{period.isoformat()}",
    )


def _funds(period: date, raw_value: str) -> EconomicObservation:
    return _observation(
        period,
        raw_value,
        dataset_id=FED_FUNDS_DATASET_ID,
        unit=RATE_UNIT,
        seasonal_adjustment=SeasonalAdjustment.UNKNOWN,
        provenance=SeriesProvenance.LATEST_REVISED,
        observation_id=f"funds-{period.isoformat()}",
    )


def _observation(
    period: date,
    raw_value: str,
    *,
    dataset_id: str,
    unit: str,
    seasonal_adjustment: SeasonalAdjustment,
    provenance: SeriesProvenance,
    observation_id: str,
) -> EconomicObservation:
    retrieved = datetime(2026, 8, 1, tzinfo=UTC)
    precision = (
        AvailabilityPrecision.UNKNOWN
        if provenance == SeriesProvenance.LATEST_REVISED
        else AvailabilityPrecision.DATE
    )
    return EconomicObservation(
        observation_id=observation_id,
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
        series_provenance=provenance,
        provider_vintage_date=period,
        availability_precision=precision,
        retrieved_at=retrieved,
        first_seen_at=retrieved,
        adapter_version="test",
    )


def _months(start: date, count: int) -> list[date]:
    months: list[date] = []
    year, month = start.year, start.month
    for _ in range(count):
        months.append(date(year, month, 1))
        month += 1
        if month == 13:
            month = 1
            year += 1
    return months
