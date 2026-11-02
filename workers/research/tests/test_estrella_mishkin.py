"""The Estrella–Mishkin spread is a latest revised difference, not a probability."""

from __future__ import annotations

from datetime import UTC, date, datetime

from aqil_research.contracts.observation import (
    AnalysisMode,
    AvailabilityPrecision,
    EconomicObservation,
    Frequency,
    QualityStatus,
    SeasonalAdjustment,
    SeriesProvenance,
)
from aqil_research.methods.estrella_mishkin import (
    FEDERAL_FUNDS_DATASET_ID,
    METHOD_ID,
    PAPER_PROBIT_EXAMPLE,
    PAPER_STATED_HORIZON,
    PUBLICATION_ALLOWED,
    TEN_YEAR_DATASET_ID,
    THREE_MONTH_DATASET_ID,
    EstrellaMishkinSpreadMethod,
)
from aqil_research.methods.protocol import MethodContext

RETRIEVED = datetime(2026, 10, 31, 12, 0, tzinfo=UTC)
PERIOD = date(2020, 1, 1)


def test_spread_is_ten_year_minus_three_month_and_is_not_a_probability() -> None:
    method = EstrellaMishkinSpreadMethod()
    assert METHOD_ID == "ESTRELLA_MISHKIN_TERM_SPREAD"
    assert method.method_id == METHOD_ID
    assert method.dependency().parameter_policy == "none"
    assert method.dependency().refit_is_different_command is False
    assert method.dependency().vintage_class == "latest_revised"
    assert FEDERAL_FUNDS_DATASET_ID not in method.required_dataset_ids()
    assert PAPER_STATED_HORIZON == "two to six quarters ahead"
    assert PAPER_PROBIT_EXAMPLE == "four quarters ahead"
    result = method.run(
        _context(AnalysisMode.LATEST_REVISED),
        method.parse_config(method.accepted_config_payload()),
    )
    assert result.sufficiency == "sufficient"
    assert result.calculation is not None
    assert result.calculation["spread"] == "2.75"
    assert result.calculation["ten_year_yield"] == "4.00"
    assert result.calculation["three_month_yield"] == "1.25"
    assert result.calculation["publication_allowed"] is PUBLICATION_ALLOWED
    assert result.calculation["publication_allowed"] is False
    assert result.calculation["real_time_probability"] is False
    assert result.calculation["input_vintage"] == "latest_revised"
    assert result.calculation["paper_stated_horizon"] == PAPER_STATED_HORIZON
    assert result.calculation["coefficients_estimated"] is False
    assert result.calculation["paper_coefficients_reproduced"] is False
    assert result.calculation["probit_estimated"] is False
    assert "probability" not in result.calculation["spread"]
    assert result.investment_implication == "no_action"
    assert "publication_allowed is false." in result.limitations


def test_point_in_time_and_a_missing_short_rate_are_insufficient() -> None:
    method = EstrellaMishkinSpreadMethod()
    config = method.parse_config(method.accepted_config_payload())
    point_in_time = method.run(_context(AnalysisMode.POINT_IN_TIME), config)
    assert point_in_time.sufficiency == "insufficient"
    assert point_in_time.calculation is None
    assert "publication_allowed is false." in point_in_time.limitations
    inputs = _inputs()
    del inputs[THREE_MONTH_DATASET_ID][PERIOD]
    missing = method.run(
        MethodContext(
            inputs_by_dataset=inputs,
            evaluation_period=PERIOD,
            analysis_mode=AnalysisMode.LATEST_REVISED,
            primary_dataset_id=TEN_YEAR_DATASET_ID,
        ),
        config,
    )
    assert missing.sufficiency == "insufficient"
    assert missing.calculation is None


def test_federal_funds_observations_are_not_accepted_as_the_short_rate() -> None:
    method = EstrellaMishkinSpreadMethod()
    inputs = _inputs()
    inputs[THREE_MONTH_DATASET_ID] = {
        PERIOD: _row(FEDERAL_FUNDS_DATASET_ID, "ff-2020-01", "1.25"),
    }
    result = method.run(
        MethodContext(
            inputs_by_dataset=inputs,
            evaluation_period=PERIOD,
            analysis_mode=AnalysisMode.LATEST_REVISED,
            primary_dataset_id=TEN_YEAR_DATASET_ID,
        ),
        method.parse_config(method.accepted_config_payload()),
    )
    assert result.sufficiency == "insufficient"


def test_method_is_registered_and_refit_stays_closed() -> None:
    from aqil_research.methods.registry import default_method_registry
    from aqil_research.pipeline.execute_method import execution_refusal

    registered = default_method_registry().get(METHOD_ID)
    assert isinstance(registered, EstrellaMishkinSpreadMethod)
    assert registered.method_id == METHOD_ID
    assert execution_refusal(registered, refit=True) is not None
    assert execution_refusal(registered, refit=False) is None
    assert "probability" not in str(registered.accepted_config_payload()["label"])


def _context(mode: AnalysisMode) -> MethodContext:
    return MethodContext(
        inputs_by_dataset=_inputs(),
        evaluation_period=PERIOD,
        analysis_mode=mode,
        primary_dataset_id=TEN_YEAR_DATASET_ID,
    )


def _inputs() -> dict[str, dict[date, EconomicObservation]]:
    return {
        TEN_YEAR_DATASET_ID: {
            PERIOD: _row(TEN_YEAR_DATASET_ID, "cm10-2020-01", "4.00"),
        },
        THREE_MONTH_DATASET_ID: {
            PERIOD: _row(THREE_MONTH_DATASET_ID, "cm03-2020-01", "1.25"),
        },
    }


def _row(dataset_id: str, observation_id: str, value: str) -> EconomicObservation:
    return EconomicObservation(
        observation_id=observation_id,
        dataset_id=dataset_id,
        provider_id="federal_reserve_board",
        source_id="fixture",
        rights_record_id="fixture",
        period_start=PERIOD,
        frequency=Frequency.MONTHLY,
        geography="US",
        unit="percent_per_year",
        seasonal_adjustment=SeasonalAdjustment.UNKNOWN,
        raw_value=value,
        quality_status=QualityStatus.OBSERVED,
        series_provenance=SeriesProvenance.LATEST_REVISED,
        provider_vintage_date=date(2026, 10, 31),
        availability_precision=AvailabilityPrecision.UNKNOWN,
        retrieved_at=RETRIEVED,
        first_seen_at=RETRIEVED,
        adapter_version="test",
    )
