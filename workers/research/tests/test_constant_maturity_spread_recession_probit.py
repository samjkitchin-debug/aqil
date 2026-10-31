"""Four-quarter probit on the stored NBER classification.

The spread method stays a spread. This file does not open the preserved database.
"""

from __future__ import annotations

import csv
import math
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import numpy as np
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
from aqil_research.methods.constant_maturity_spread_recession_probit import (
    CHRONOLOGY_DATASET_ID,
    CHRONOLOGY_PUBLICATION_DATE,
    CHRONOLOGY_SOURCE_URL,
    ESTIMATION_LAST_SPREAD_QUARTER,
    EVALUATION_FIRST_SPREAD_QUARTER,
    FEDERAL_FUNDS_DATASET_ID,
    HORIZON_QUARTERS,
    INSTRUMENT_MISMATCH,
    METHOD_ID,
    PUBLICATION_ALLOWED,
    TEN_YEAR_DATASET_ID,
    THREE_MONTH_DATASET_ID,
    ChronologyError,
    ConstantMaturitySpreadRecessionProbitMethod,
    ProbitQuarter,
    contraction_quarters,
    estimate_split_probit,
    load_chronology,
)
from aqil_research.methods.estrella_mishkin import METHOD_ID as SPREAD_METHOD_ID
from aqil_research.methods.protocol import MethodContext
from aqil_research.methods.registry import default_method_registry
from aqil_research.sources.rights import (
    AttributionRequirement,
    M1Role,
    OperationalStatus,
    RightsDecision,
    load_source_rights,
)

ROOT = Path(__file__).resolve().parents[3]
COVERAGE = ROOT / "docs" / "sources" / "MACRO_COVERAGE.csv"
RETRIEVED = datetime(2026, 11, 1, 12, 0, tzinfo=UTC)


def test_chronology_is_the_dated_nber_page_and_not_a_yield_vintage() -> None:
    turns = load_chronology()
    assert len(turns) == 35
    assert turns[0].peak_month is None
    assert turns[0].trough_month == date(1854, 12, 1)
    assert turns[0].trough_quarter == date(1854, 10, 1)
    assert all(turn.publication_date == CHRONOLOGY_PUBLICATION_DATE for turn in turns)
    assert all(turn.source_url == CHRONOLOGY_SOURCE_URL for turn in turns)
    assert turns[-1].peak_month == date(2020, 2, 1)
    assert turns[-1].peak_quarter == date(2019, 10, 1)
    assert turns[-1].trough_month == date(2020, 4, 1)
    assert turns[-1].trough_quarter == date(2020, 4, 1)
    january_1912 = next(turn for turn in turns if turn.trough_month == date(1912, 1, 1))
    assert january_1912.trough_quarter == date(1911, 10, 1)
    quarters = contraction_quarters(turns)
    assert date(2019, 10, 1) not in quarters
    assert date(2020, 1, 1) in quarters
    assert date(2020, 4, 1) in quarters
    assert date(2020, 7, 1) not in quarters
    assert date(1980, 1, 1) not in quarters
    assert date(1980, 4, 1) in quarters
    assert date(1980, 7, 1) in quarters
    assert date(1868, 1, 1) in quarters
    assert "fred" not in CHRONOLOGY_SOURCE_URL
    with pytest.raises(ChronologyError):
        load_chronology(ROOT / "docs" / "sources" / "SOURCE_RIGHTS.csv")


def test_rights_permit_one_attributed_copy_and_block_a_collector() -> None:
    record = next(row for row in load_source_rights() if row.dataset_id == CHRONOLOGY_DATASET_ID)
    assert record.source_id == "nber_us_business_cycle_chronology"
    assert record.terms_url == "https://www.nber.org/terms-and-conditions"
    assert CHRONOLOGY_SOURCE_URL in record.evidence_urls
    assert record.terms_url in record.evidence_urls
    assert record.automated_access is RightsDecision.PROHIBITED
    assert record.internal_computation is RightsDecision.PERMITTED
    assert record.raw_data_retention is RightsDecision.PERMITTED
    assert record.historical_archiving is RightsDecision.PERMITTED
    assert record.redistribution is RightsDecision.UNKNOWN
    assert record.commercial_publication is RightsDecision.PROHIBITED
    assert record.ai_processing is RightsDecision.UNKNOWN
    assert record.ai_model_training is RightsDecision.UNKNOWN
    assert record.attribution is AttributionRequirement.REQUIRED
    assert record.m1_role is M1Role.UNRESOLVED
    assert record.operational_status is OperationalStatus.ENABLED
    assert record.assessed_on.isoformat() == "2026-11-01"
    assert "Permission to copy is granted, provided attribution of source is given." in (
        record.evidence_note
    )
    coverage = next(
        row
        for row in csv.DictReader(COVERAGE.open(encoding="utf-8"))
        if row["dataset_id"] == CHRONOLOGY_DATASET_ID
    )
    assert coverage["status"] == "reference"
    assert coverage["collection_mode"] == "local_file"
    assert coverage["vintage_class"] == ""
    assert coverage["distinct_periods"] == "35"
    assert coverage["source_id"] == record.source_id
    assert "Not a vintage of the H.15 yields." in coverage["note"]
    assert "Not FRED." in coverage["note"]


def test_method_is_separate_and_registered() -> None:
    method = ConstantMaturitySpreadRecessionProbitMethod()
    assert METHOD_ID == "CONSTANT_MATURITY_SPREAD_RECESSION_PROBIT"
    assert METHOD_ID != SPREAD_METHOD_ID
    assert FEDERAL_FUNDS_DATASET_ID not in method.required_dataset_ids()
    assert method.required_dataset_ids() == (TEN_YEAR_DATASET_ID, THREE_MONTH_DATASET_ID)
    assert method.dependency().vintage_class == "latest_revised"
    assert method.dependency().parameter_policy == "none"
    assert method.dependency().refit_is_different_command is False
    assert PUBLICATION_ALLOWED is False
    registered = default_method_registry().get(METHOD_ID)
    assert registered.method_id == METHOD_ID
    assert registered.dependency().parameter_policy == "none"
    widened = method.accepted_config_payload()
    widened["estimation_last_spread_quarter"] = "2012-10-01"
    with pytest.raises(ValidationError):
        method.parse_config(widened)
    shorter = method.accepted_config_payload()
    shorter["horizon_quarters"] = 2
    with pytest.raises(ValidationError):
        method.parse_config(shorter)


def test_known_probit_recovers_on_a_later_window_only() -> None:
    rng = np.random.default_rng(7)
    intercept = -0.3
    slope = -0.9
    rows: list[ProbitQuarter] = []
    quarter = date(1981, 10, 1)
    while quarter <= date(2015, 10, 1):
        window = "estimation" if quarter <= ESTIMATION_LAST_SPREAD_QUARTER else "evaluation"
        spread = float(rng.normal())
        latent = intercept + slope * spread + float(rng.normal())
        outcome_year = quarter.year + 1
        outcome = date(outcome_year, quarter.month, 1)
        rows.append(
            ProbitQuarter(
                spread_quarter=quarter,
                outcome_quarter=outcome,
                spread=spread,
                spread_text=format(spread, ".6f"),
                contraction=1 if latent > 0 else 0,
                window=window,
                observation_ids=(),
            ),
        )
        quarter = _add_quarters(quarter, 1)
    fitted = estimate_split_probit(tuple(rows))
    assert fitted["fit_stable"] is True
    assert fitted["fit_status"] == "estimated"
    assert fitted["horizon_quarters"] == HORIZON_QUARTERS
    assert float(fitted["intercept"]) == pytest.approx(intercept, abs=0.45)
    assert float(fitted["spread_coefficient"]) == pytest.approx(slope, abs=0.45)
    assert fitted["discrimination_status"] == "computed"
    assert fitted["calibration_status"] == "computed"
    assert fitted["discrimination_quarter_count"] == fitted["evaluation_quarter_count"]
    assert fitted["auroc"] is not None
    assert fitted["brier_score"] is not None
    estimation = [row for row in fitted["probabilities"] if row["window"] == "estimation"]
    evaluation = [row for row in fitted["probabilities"] if row["window"] == "evaluation"]
    assert estimation
    assert evaluation
    assert max(row["spread_quarter"] for row in estimation) <= "2005-10-01"
    assert min(row["spread_quarter"] for row in evaluation) >= "2006-01-01"
    assert fitted["new_york_fed_parameterisation"] is False
    assert fitted["instrument_mismatch"] == INSTRUMENT_MISMATCH


def test_a_separating_sample_is_stored_as_unstable() -> None:
    rows = (
        _row(date(2004, 1, 1), -2.0, 0, "estimation"),
        _row(date(2004, 4, 1), -1.0, 0, "estimation"),
        _row(date(2004, 7, 1), 1.0, 1, "estimation"),
        _row(date(2004, 10, 1), 2.0, 1, "estimation"),
        _row(date(2006, 1, 1), -1.0, 0, "evaluation"),
        _row(date(2006, 4, 1), 1.0, 1, "evaluation"),
    )
    fitted = estimate_split_probit(rows)
    assert fitted["fit_stable"] is False
    assert fitted["fit_status"] == "unstable"
    assert fitted["fit_failure"] == "perfect_separation"
    assert fitted["probabilities_accepted"] is False
    assert fitted["estimation_last_spread_quarter"] == "2005-10-01"
    assert fitted["evaluation_first_spread_quarter"] == "2006-01-01"
    assert fitted["discrimination_status"] == "not_computed"
    assert fitted["auroc"] is None


def test_a_flat_spread_is_not_given_a_slope() -> None:
    rows = (
        _row(date(2004, 1, 1), 1.5, 0, "estimation"),
        _row(date(2004, 4, 1), 1.5, 1, "estimation"),
        _row(date(2004, 7, 1), 1.5, 0, "estimation"),
        _row(date(2006, 1, 1), 0.2, 1, "evaluation"),
        _row(date(2006, 4, 1), -0.4, 0, "evaluation"),
    )
    fitted = estimate_split_probit(rows)
    assert fitted["fit_stable"] is False
    assert fitted["fit_status"] == "not_estimated"
    assert fitted["fit_failure"] == "estimation spreads do not vary"
    assert fitted["spread_coefficient"] is None
    assert fitted["estimation_last_spread_quarter"] == ESTIMATION_LAST_SPREAD_QUARTER.isoformat()
    assert fitted["evaluation_first_spread_quarter"] == EVALUATION_FIRST_SPREAD_QUARTER.isoformat()


def test_method_run_records_the_fixed_split_and_the_instrument() -> None:
    method = ConstantMaturitySpreadRecessionProbitMethod()
    result = method.run(
        _context(date(2010, 12, 1)),
        method.parse_config(method.accepted_config_payload()),
    )
    assert result.sufficiency == "sufficient"
    assert result.investment_implication == "no_action"
    calculation = result.calculation
    assert calculation is not None
    assert calculation["publication_allowed"] is False
    assert calculation["input_vintage"] == "latest_revised"
    assert calculation["real_time_probability"] is False
    assert calculation["chronology_is_yield_vintage"] is False
    assert calculation["classification_kind"] == "reference_classification"
    assert calculation["classification_publication_date"] == "2023-03-14"
    assert calculation["short_rate_dataset_id"] == THREE_MONTH_DATASET_ID
    assert calculation["horizon_quarters"] == 4
    assert calculation["estimation_last_spread_quarter"] == "2005-10-01"
    assert calculation["evaluation_first_spread_quarter"] == "2006-01-01"
    assert "New York Fed parameterisation" in calculation["instrument_mismatch"]
    assert "RIFSGFSM03" not in str(calculation)
    estimation = [row for row in calculation["probabilities"] if row["window"] == "estimation"]
    evaluation = [row for row in calculation["probabilities"] if row["window"] == "evaluation"]
    if calculation["fit_stable"] is True:
        assert calculation["spread_coefficient"] is not None
        assert calculation["intercept"] is not None
        assert calculation["intercept_standard_error"] is not None
        assert calculation["spread_coefficient_standard_error"] is not None
        if calculation["discrimination_status"] == "computed":
            assert (
                calculation["discrimination_quarter_count"]
                == calculation["evaluation_quarter_count"]
            )
            assert calculation["auroc"] is not None
        assert max(row["spread_quarter"] for row in estimation) <= "2005-10-01"
        assert min(row["spread_quarter"] for row in evaluation) >= "2006-01-01"
    else:
        assert calculation["fit_status"] in {"unstable", "not_estimated"}
        assert calculation["estimation_last_spread_quarter"] == "2005-10-01"
    assert "publication_allowed is false." in result.limitations
    point_in_time = method.run(
        _context(date(2010, 12, 1), AnalysisMode.POINT_IN_TIME),
        method.parse_config(method.accepted_config_payload()),
    )
    assert point_in_time.sufficiency == "insufficient"
    assert point_in_time.calculation is None


def test_federal_funds_and_a_missing_yield_do_not_estimate() -> None:
    method = ConstantMaturitySpreadRecessionProbitMethod()
    config = method.parse_config(method.accepted_config_payload())
    inputs = _inputs(date(2010, 12, 1))
    inputs[THREE_MONTH_DATASET_ID] = {
        period: _observation(FEDERAL_FUNDS_DATASET_ID, f"ff-{period.isoformat()}", "1.00", period)
        for period in inputs[TEN_YEAR_DATASET_ID]
    }
    refused = method.run(
        MethodContext(
            inputs_by_dataset=inputs,
            evaluation_period=date(2010, 12, 1),
            analysis_mode=AnalysisMode.LATEST_REVISED,
            primary_dataset_id=TEN_YEAR_DATASET_ID,
        ),
        config,
    )
    assert refused.sufficiency == "insufficient"
    missing = method.run(
        MethodContext(
            inputs_by_dataset={TEN_YEAR_DATASET_ID: inputs[TEN_YEAR_DATASET_ID]},
            evaluation_period=date(2010, 12, 1),
            analysis_mode=AnalysisMode.LATEST_REVISED,
            primary_dataset_id=TEN_YEAR_DATASET_ID,
        ),
        config,
    )
    assert missing.sufficiency == "insufficient"


def _row(quarter: date, spread: float, contraction: int, window: str) -> ProbitQuarter:
    return ProbitQuarter(
        spread_quarter=quarter,
        outcome_quarter=_add_quarters(quarter, 4),
        spread=spread,
        spread_text=format(spread, "f"),
        contraction=contraction,
        window=window,
        observation_ids=(),
    )


def _context(
    evaluation: date,
    mode: AnalysisMode = AnalysisMode.LATEST_REVISED,
) -> MethodContext:
    return MethodContext(
        inputs_by_dataset=_inputs(evaluation),
        evaluation_period=evaluation,
        analysis_mode=mode,
        primary_dataset_id=TEN_YEAR_DATASET_ID,
    )


def _inputs(evaluation: date) -> dict[str, dict[date, EconomicObservation]]:
    ten_year: dict[date, EconomicObservation] = {}
    three_month: dict[date, EconomicObservation] = {}
    cursor = date(1981, 10, 1)
    index = 0
    while cursor <= evaluation:
        spread = Decimal("1.25") + Decimal(str(round(math.sin(index / 5.0), 4)))
        ten_year[cursor] = _observation(
            TEN_YEAR_DATASET_ID,
            f"cm10-{cursor.isoformat()}",
            "5.00",
            cursor,
        )
        three_month[cursor] = _observation(
            THREE_MONTH_DATASET_ID,
            f"cm03-{cursor.isoformat()}",
            str(Decimal("5.00") - spread),
            cursor,
        )
        index += 1
        cursor = _add_months(cursor, 1)
    return {TEN_YEAR_DATASET_ID: ten_year, THREE_MONTH_DATASET_ID: three_month}


def _observation(
    dataset_id: str,
    observation_id: str,
    value: str,
    period: date,
) -> EconomicObservation:
    return EconomicObservation(
        observation_id=observation_id,
        dataset_id=dataset_id,
        provider_id="fixture",
        source_id="fixture",
        rights_record_id="fixture",
        period_start=period,
        frequency=Frequency.MONTHLY,
        geography="US",
        unit="percent_per_year",
        seasonal_adjustment=SeasonalAdjustment.UNKNOWN,
        raw_value=value,
        quality_status=QualityStatus.OBSERVED,
        series_provenance=SeriesProvenance.LATEST_REVISED,
        provider_vintage_date=date(2026, 11, 1),
        availability_precision=AvailabilityPrecision.UNKNOWN,
        retrieved_at=RETRIEVED,
        first_seen_at=RETRIEVED,
        adapter_version="test",
    )


def _add_months(anchor: date, count: int) -> date:
    index = anchor.year * 12 + (anchor.month - 1) + count
    return date(index // 12, index % 12 + 1, 1)


def _add_quarters(anchor: date, count: int) -> date:
    return _add_months(anchor, 3 * count)
