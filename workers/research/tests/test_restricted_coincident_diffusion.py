"""Restricted coincident diffusion on the four modern series."""

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
from aqil_research.methods.protocol import MethodContext
from aqil_research.methods.restricted_coincident_diffusion import (
    DATASETS,
    METHOD_ID,
    NOT_INDEPENDENT_CONFIRMATION,
    NOT_THE_CHICAGO_FED_INDEX,
    PERSISTENCE_SHARE_FLOOR,
    PUBLICATION_ALLOWED,
    RestrictedCoincidentDiffusionMethod,
    correlate_with_filtered_factor,
    pearson_correlation,
    restricted_coincident_diffusion,
    shift_month,
)
from aqil_research.methods.stock_watson_1988_fit import MODERN_REFIT_DATASETS


def _months(count: int, start: date = date(1997, 1, 1)) -> list[date]:
    months: list[date] = []
    year, month = start.year, start.month
    for _ in range(count):
        months.append(date(year, month, 1))
        month += 1
        if month == 13:
            month = 1
            year += 1
    return months


def test_definition_constants() -> None:
    assert METHOD_ID == "RESTRICTED_COINCIDENT_DIFFUSION"
    assert DATASETS == MODERN_REFIT_DATASETS
    assert PUBLICATION_ALLOWED is False
    assert PERSISTENCE_SHARE_FLOOR == 0.5
    assert shift_month(date(1997, 1, 1), -3) == date(1996, 10, 1)
    assert "Chicago Fed 85-indicator" in NOT_THE_CHICAGO_FED_INDEX
    assert "not independent confirmation" in NOT_INDEPENDENT_CONFIRMATION


def test_three_month_change_share_denominator_and_persistence() -> None:
    periods = _months(8)
    levels = {dataset: {} for dataset in DATASETS}
    for index, period in enumerate(periods):
        for series_index, dataset in enumerate(DATASETS):
            # January–March stay at 100. From April, two series rise and two fall,
            # except May where all four rise, and July where exactly two rise.
            if index < 3:
                value = 100.0
            elif period == date(1997, 5, 1):
                value = 110.0
            elif period == date(1997, 7, 1) and series_index < 2:
                value = 120.0
            elif period == date(1997, 7, 1):
                value = 90.0
            elif series_index < 2:
                value = 101.0
            else:
                value = 99.0
            levels[dataset][period] = value
    result = restricted_coincident_diffusion(levels)
    by_period = {month.period: month for month in result.months}
    january = by_period[date(1997, 1, 1)]
    assert january.denominator == 0
    assert january.share is None
    assert january.persistence_months == 0
    april = by_period[date(1997, 4, 1)]
    assert april.denominator == 4
    assert april.improving == 2
    assert april.share == 0.5
    assert april.persistence_months == 1
    may = by_period[date(1997, 5, 1)]
    assert may.improving == 4
    assert may.share == 1.0
    assert may.persistence_months == 2
    june = by_period[date(1997, 6, 1)]
    assert june.improving == 2
    assert june.share == 0.5
    assert june.persistence_months == 3
    july = by_period[date(1997, 7, 1)]
    assert july.improving == 2
    assert july.share == 0.5
    assert july.persistence_months == 4


def test_missing_endpoint_is_omitted_and_not_interpolated() -> None:
    periods = _months(6)
    levels = {
        dataset: {period: 100.0 + index for index, period in enumerate(periods)}
        for dataset in DATASETS
    }
    sales = DATASETS[2]
    del levels[sales][date(1997, 1, 1)]
    # A gap is not filled from the neighbouring months.
    assert date(1997, 1, 1) not in levels[sales]
    result = restricted_coincident_diffusion(levels)
    assert date(1997, 1, 1) not in result.balanced_months
    april = next(month for month in result.months if month.period == date(1997, 4, 1))
    assert april.denominator == 3
    assert april.improving == 3
    assert april.share == 1.0


def test_zero_change_is_not_an_improvement() -> None:
    periods = _months(4)
    levels = {dataset: {period: 50.0 for period in periods} for dataset in DATASETS}
    result = restricted_coincident_diffusion(levels)
    april = next(month for month in result.months if month.period == date(1997, 4, 1))
    assert april.denominator == 4
    assert april.improving == 0
    assert april.share == 0.0
    assert april.persistence_months == 0


def test_correlation_with_the_factor_is_labelled_as_not_independent() -> None:
    periods = _months(8)
    levels = {dataset: {} for dataset in DATASETS}
    for index, period in enumerate(periods):
        for series_index, dataset in enumerate(DATASETS):
            if index < 3:
                value = 100.0
            elif period == date(1997, 5, 1):
                value = 110.0
            elif series_index < 2:
                value = 101.0
            else:
                value = 99.0
            levels[dataset][period] = value
    result = restricted_coincident_diffusion(levels)
    defined = [month for month in result.months if month.share is not None]
    factor = {month.period: 0.1 * offset for offset, month in enumerate(defined)}
    correlation, overlap = correlate_with_filtered_factor(result.months, factor)
    assert overlap == len(defined)
    assert overlap >= 3
    assert correlation == pearson_correlation(
        [month.share for month in defined],
        [factor[month.period] for month in defined],
    )
    assert "not independent confirmation" in NOT_INDEPENDENT_CONFIRMATION


def test_method_stays_unpublished_on_latest_revised_levels() -> None:
    periods = _months(40)
    when = datetime(2026, 8, 1, tzinfo=UTC)
    inputs = {}
    for dataset in DATASETS:
        inputs[dataset] = {
            period: EconomicObservation(
                observation_id=f"{dataset}-{period.isoformat()}",
                dataset_id=dataset,
                provider_id="test",
                source_id="test",
                rights_record_id="test",
                period_start=period,
                frequency=Frequency.MONTHLY,
                geography="US",
                unit="level",
                seasonal_adjustment=SeasonalAdjustment.SEASONALLY_ADJUSTED,
                raw_value=str(100 + index),
                quality_status=QualityStatus.OBSERVED,
                series_provenance=SeriesProvenance.LATEST_REVISED,
                provider_vintage_date=period,
                source_release_at=when,
                availability_precision=AvailabilityPrecision.UNKNOWN,
                retrieved_at=when,
                first_seen_at=when,
                source_locator="diffusion-test",
                adapter_version="test",
            )
            for index, period in enumerate(periods)
        }
    method = RestrictedCoincidentDiffusionMethod()
    config = method.parse_config(
        {"config_id": "restricted-coincident-diffusion", "label": "Restricted coincident diffusion"}
    )
    context = MethodContext(
        inputs_by_dataset=inputs,
        evaluation_period=periods[-1],
        analysis_mode=AnalysisMode.LATEST_REVISED,
        primary_dataset_id=DATASETS[0],
    )
    result = method.run(context, config)
    assert result.sufficiency == "sufficient"
    assert result.calculation is not None
    assert result.calculation["publication_allowed"] is False
    assert result.calculation["not_chicago_fed_85_indicator_index"] is True
    assert result.investment_implication == "no_action"
    april = next(month for month in result.calculation["months"] if month["period"] == "1997-04-01")
    assert april["denominator"] == 4
    assert april["share"] == 1.0
    refused = method.run(
        MethodContext(
            inputs_by_dataset=inputs,
            evaluation_period=periods[-1],
            analysis_mode=AnalysisMode.POINT_IN_TIME,
            primary_dataset_id=DATASETS[0],
        ),
        config,
    )
    assert refused.sufficiency == "insufficient"
    assert refused.calculation is None
