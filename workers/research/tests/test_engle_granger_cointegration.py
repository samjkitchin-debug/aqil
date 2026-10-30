"""Engle-Granger cointegration on log levels. Fixture series only."""

from __future__ import annotations

import json
import math
from datetime import UTC, date, datetime
from pathlib import Path

import numpy as np
import pytest
from statsmodels.regression.linear_model import OLS
from statsmodels.tsa.adfvalues import mackinnoncrit
from statsmodels.tsa.stattools import adfuller, coint

from aqil_research.contracts.observation import (
    AnalysisMode,
    AvailabilityPrecision,
    EconomicObservation,
    Frequency,
    QualityStatus,
    SeasonalAdjustment,
    SeriesProvenance,
)
from aqil_research.methods.autoregressive_benchmark import (
    PUBLISHED_CONFIG as AUTOREGRESSIVE_PUBLISHED,
)
from aqil_research.methods.autoregressive_benchmark import (
    AutoregressiveBenchmarkMethod,
)
from aqil_research.methods.bai_perron_mean_shifts import (
    PUBLISHED_CONFIG as BAI_PERRON_PUBLISHED,
)
from aqil_research.methods.bai_perron_mean_shifts import (
    BaiPerronMeanShiftsMethod,
)
from aqil_research.methods.engle_granger_cointegration import (
    CRITICAL_VALUE_SOURCE,
    ENGLE_GRANGER_COINTEGRATION,
    INDUSTRIAL_PRODUCTION_DATASET_ID,
    LABELS,
    MINIMUM_OVERLAP_MONTHS,
    NO_CAUSAL_CLAIM,
    NOT_A_LEADING_INDICATOR,
    PAYROLL_DATASET_ID,
    PAYROLL_UNIT,
    PUBLICATION_ALLOWED,
    PUBLISHED_CONFIG,
    UNITS,
    EngleGrangerCointegrationMethod,
    engle_granger_from_log_levels,
    longest_contiguous_overlap,
    schwert_max_lag,
)
from aqil_research.methods.hamilton_monthly import (
    HAMILTON_MONTHLY_PUBLISHED,
    HamiltonMonthlyMethod,
)
from aqil_research.methods.lead_lag import (
    PUBLISHED_CONFIG as LEAD_LAG_PUBLISHED,
)
from aqil_research.methods.lead_lag import (
    LeadLagCrossCorrelationMethod,
)
from aqil_research.methods.protocol import MethodContext
from aqil_research.methods.registry import default_method_registry
from aqil_research.methods.restricted_coincident_diffusion import (
    PUBLISHED_CONFIG as DIFFUSION_PUBLISHED,
)
from aqil_research.methods.restricted_coincident_diffusion import (
    RestrictedCoincidentDiffusionMethod,
)
from aqil_research.methods.stock_watson_1988_fit import (
    ACCEPTED_CONFIG,
    MULTISTART_CONFIG,
    StockWatsonModernRefitMethod,
)
from aqil_research.persistence.reproduce import reproduction_config

STORED_CONFIGS = (
    (
        "restricted-coincident-diffusion",
        RestrictedCoincidentDiffusionMethod,
        DIFFUSION_PUBLISHED,
        None,
    ),
    (
        "sw1988-modern-1997-2026m07",
        StockWatsonModernRefitMethod,
        ACCEPTED_CONFIG,
        None,
    ),
    ("sw1988-modern-multistart", StockWatsonModernRefitMethod, MULTISTART_CONFIG, None),
    (
        "hamilton_monthly_ip_v1",
        HamiltonMonthlyMethod,
        HAMILTON_MONTHLY_PUBLISHED,
        "ac35490e07a1020cdffcde486f87d4d41f83e16e5709c0f8a62a944ccf8824ee",
    ),
    (
        "bai_perron_mean_shifts_v1",
        BaiPerronMeanShiftsMethod,
        BAI_PERRON_PUBLISHED,
        "3efce19ca7f8fbfc6182907600eccc331d5489c8427abab7e2889fb657f27f75",
    ),
    (
        "autoregressive-benchmark-v1",
        AutoregressiveBenchmarkMethod,
        AUTOREGRESSIVE_PUBLISHED,
        "d059e97c16a8cae36df5e4e272742f180fb6c8aafd8fd3ee43bdca3649e94bfd",
    ),
    (
        "lead-lag-cross-correlation-v1",
        LeadLagCrossCorrelationMethod,
        LEAD_LAG_PUBLISHED,
        "42247425902cc9b0bf95a167f67064e13fe89c0f452ebcea350aed527dfd8f40",
    ),
)


def test_predeclared_pair_uses_mackinnon_critical_values() -> None:
    assert ENGLE_GRANGER_COINTEGRATION == "ENGLE_GRANGER_COINTEGRATION"
    assert PUBLICATION_ALLOWED is False
    assert PUBLISHED_CONFIG["config_id"] == "engle-granger-cointegration-v1"
    assert MINIMUM_OVERLAP_MONTHS == 120
    assert schwert_max_lag(240) == int(math.ceil(12.0 * (240 / 100.0) ** 0.25))
    text = Path(engle_granger_from_log_levels.__code__.co_filename).read_text(encoding="utf-8")
    lowered = text.lower()
    assert "johansen" not in lowered
    assert "vecm" not in lowered
    assert "granger_causality" not in lowered
    assert "natural_log_levels" in text
    assert "MacKinnon (2010)" in CRITICAL_VALUE_SOURCE
    assert "Not the Engle and Granger (1987) table" in CRITICAL_VALUE_SOURCE


def test_constant_is_in_the_cointegrating_regression_and_not_in_the_residual_test() -> None:
    left, right = _cointegrated_logs(seed=7, count=240)
    result = engle_granger_from_log_levels(left, right)
    exog = np.column_stack((right, np.ones(len(right))))
    independent = np.linalg.lstsq(exog, left, rcond=None)
    library = OLS(left, exog).fit()
    assert result["first_stage"]["constant_included"] is True
    assert result["first_stage"]["slope"] == pytest.approx(float(independent[0][0]))
    assert result["first_stage"]["intercept"] == pytest.approx(float(independent[0][1]))
    assert result["first_stage"]["slope"] == pytest.approx(float(library.params[0]))
    assert result["first_stage"]["intercept"] == pytest.approx(float(library.params[1]), rel=1e-6)
    without_constant = np.linalg.lstsq(right.reshape(-1, 1), left, rcond=None)
    assert result["first_stage"]["slope"] != pytest.approx(float(without_constant[0][0]), rel=1e-4)
    assert result["second_stage"]["regression"] == "no_constant_no_trend"
    assert result["growth_rates_used"] is False
    assert result["publication_allowed"] is False


def test_failure_to_reject_is_kept_when_an_ordinary_adf_would_reject() -> None:
    left, right = _independent_logs(seed=11, count=240)
    result = engle_granger_from_log_levels(left, right)
    library_stat, library_p, library_crit = coint(
        left,
        right,
        trend="c",
        method="aeg",
        autolag="aic",
        return_results=False,
    )
    exog = np.column_stack((right, np.ones(len(right))))
    residual = OLS(left, exog).fit().resid
    ordinary = adfuller(
        residual,
        maxlag=schwert_max_lag(len(residual)),
        regression="n",
        autolag="aic",
        result_object=False,
    )
    mackinnon = mackinnoncrit(N=2, regression="c", nobs=len(left) - 1)
    assert result["statistic"] == pytest.approx(float(library_stat))
    assert result["p_value"] == pytest.approx(float(library_p))
    assert result["critical_value_five_percent"] == pytest.approx(float(library_crit[1]))
    assert result["critical_value_five_percent"] == pytest.approx(float(mackinnon[1]))
    assert result["statistic"] == pytest.approx(float(ordinary[0]))
    assert result["statistic"] < float(ordinary[4]["5%"])
    assert result["statistic"] > float(library_crit[1])
    assert result["p_value"] != pytest.approx(float(ordinary[1]), rel=0.05)
    assert (float(library_stat) < float(library_crit[1])) is False
    assert result["rejects_no_cointegration_at_five_percent"] is False
    assert result["second_stage"]["ordinary_adf_critical_values_used"] is False
    assert result["second_stage"]["critical_value_source"] == CRITICAL_VALUE_SOURCE
    encoded = json.dumps(result)
    assert "NaN" not in encoded
    assert "Infinity" not in encoded


def test_a_constructed_cointegrating_pair_rejects_no_cointegration() -> None:
    left, right = _cointegrated_logs(seed=7, count=240)
    result = engle_granger_from_log_levels(left, right)
    library_stat, _library_p, library_crit = coint(
        left,
        right,
        trend="c",
        autolag="aic",
        return_results=False,
    )
    assert result["statistic"] == pytest.approx(float(library_stat))
    assert float(library_stat) < float(library_crit[1])
    assert result["rejects_no_cointegration_at_five_percent"] is True
    assert result["second_stage"]["max_lag"] == schwert_max_lag(240)
    assert result["second_stage"]["used_lag"] >= 0
    assert result["first_stage"]["slope"] == pytest.approx(0.4, abs=0.05)
    assert result["first_stage"]["intercept"] == pytest.approx(1.5, abs=0.15)


def test_a_gap_is_not_interpolated() -> None:
    months = _months(date(2000, 1, 1), 8)
    left = {month: float(index + 10) for index, month in enumerate(months)}
    right = {month: float(index + 20) for index, month in enumerate(months)}
    del left[months[4]]
    chosen, left_logs, right_logs, excluded = longest_contiguous_overlap(left, right)
    assert chosen == tuple(months[:4])
    assert excluded == 3
    assert left_logs == tuple(math.log(left[month]) for month in chosen)
    assert right_logs == tuple(math.log(right[month]) for month in chosen)


def test_method_stores_the_log_level_result_and_registers_last_but_one() -> None:
    method = EngleGrangerCointegrationMethod()
    config = method.parse_config(dict(PUBLISHED_CONFIG))
    assert method.required_dataset_ids() == (INDUSTRIAL_PRODUCTION_DATASET_ID, PAYROLL_DATASET_ID)
    dependency = method.dependency()
    assert dependency.vintage_class == "latest_revised"
    assert dependency.parameter_policy == "none"
    assert dependency.depends_on_method_ids == ()
    assert dependency.refit_is_different_command is False
    assert method.config_hash(config)
    registered = [item.method_id for item in default_method_registry().registered()]
    assert registered[-3] == "LEAD_LAG_CROSS_CORRELATION"
    assert registered[-2] == ENGLE_GRANGER_COINTEGRATION
    assert registered[-1] == "CUSUM_RECURSIVE_RESIDUALS"
    left, right = _cointegrated_logs(seed=7, count=150)
    result = method.run(_context(_levels(left, right)), config)
    assert result.sufficiency == "sufficient"
    assert result.calculation is not None
    assert result.calculation["publication_allowed"] is False
    assert result.calculation["transformation"] == "natural_log_levels"
    assert result.calculation["rejects_no_cointegration_at_five_percent"] is True
    assert result.investment_implication == "no_action"
    assert result.causal_hypothesis == NO_CAUSAL_CLAIM
    text = " ".join(
        (
            result.narrative,
            result.statistical_interpretation,
            *result.assumptions,
            *result.limitations,
        ),
    )
    assert NOT_A_LEADING_INDICATOR in text
    assert "MacKinnon (2010)" in text
    assert "1987" in text
    assert "growth-rate" not in text.lower()
    assert "leading indicator is assigned" in text
    refused = method.run(
        _context(_levels(left, right), analysis_mode=AnalysisMode.POINT_IN_TIME),
        config,
    )
    assert refused.sufficiency == "insufficient"
    assert refused.investment_implication == "insufficient_evidence"
    assert refused.calculation["publication_allowed"] is False
    short_left, short_right = _cointegrated_logs(seed=1, count=24)
    short = method.run(_context(_levels(short_left, short_right)), config)
    assert short.sufficiency == "insufficient"


def test_the_seven_stored_config_ids_are_unchanged() -> None:
    for config_id, method_type, published, stored_hash in STORED_CONFIGS:
        payload = reproduction_config(config_id)
        assert payload["config_id"] == config_id
        method = method_type()
        parsed = method.parse_config(payload)
        assert parsed.config_id == config_id
        if stored_hash is not None:
            assert method.config_hash(parsed) == stored_hash
        assert published["config_id"] == config_id
    added = reproduction_config("engle-granger-cointegration-v1")
    assert added["config_id"] == "engle-granger-cointegration-v1"
    cusum = reproduction_config("cusum-recursive-residuals-v1")
    assert cusum["config_id"] == "cusum-recursive-residuals-v1"


def _cointegrated_logs(seed: int, count: int) -> tuple[np.ndarray, np.ndarray]:
    generator = np.random.default_rng(seed)
    right = np.cumsum(generator.normal(0.0, 1.0, size=count))
    left = 1.5 + 0.4 * right + generator.normal(0.0, 0.15, size=count)
    return left, right


def _independent_logs(seed: int, count: int) -> tuple[np.ndarray, np.ndarray]:
    generator = np.random.default_rng(seed)
    left = np.cumsum(generator.normal(size=count))
    right = np.cumsum(generator.normal(size=count))
    return left, right


def _levels(left: np.ndarray, right: np.ndarray) -> dict[str, dict[date, EconomicObservation]]:
    months = _months(date(1990, 1, 1), int(left.size))
    return {
        INDUSTRIAL_PRODUCTION_DATASET_ID: {
            month: _observation(
                INDUSTRIAL_PRODUCTION_DATASET_ID,
                month,
                math.exp(float(left[index])),
            )
            for index, month in enumerate(months)
        },
        PAYROLL_DATASET_ID: {
            month: _observation(PAYROLL_DATASET_ID, month, math.exp(float(right[index]) + 10.0))
            for index, month in enumerate(months)
        },
    }


def _context(
    inputs: dict[str, dict[date, EconomicObservation]],
    *,
    analysis_mode: AnalysisMode = AnalysisMode.LATEST_REVISED,
) -> MethodContext:
    return MethodContext(
        inputs_by_dataset=inputs,
        evaluation_period=max(inputs[INDUSTRIAL_PRODUCTION_DATASET_ID]),
        analysis_mode=analysis_mode,
        primary_dataset_id=INDUSTRIAL_PRODUCTION_DATASET_ID,
    )


def _observation(dataset_id: str, period: date, value: float) -> EconomicObservation:
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
        unit=UNITS[dataset_id],
        seasonal_adjustment=SeasonalAdjustment.SEASONALLY_ADJUSTED,
        raw_value=format(value, ".10f"),
        quality_status=QualityStatus.OBSERVED,
        series_provenance=SeriesProvenance.LATEST_REVISED,
        provider_vintage_date=period,
        availability_precision=AvailabilityPrecision.UNKNOWN,
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


def test_payroll_unit_matches_the_stored_series() -> None:
    assert PAYROLL_UNIT == "thousands"
    assert LABELS[PAYROLL_DATASET_ID] == "Total nonfarm payroll employment"
