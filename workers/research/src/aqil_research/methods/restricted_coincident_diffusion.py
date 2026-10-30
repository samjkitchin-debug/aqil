"""Restricted four-series coincident diffusion.

Each series enters as a three-month arithmetic change in its level. An increase
is an improvement for all four series, because each is a procyclical level.
This is not the Chicago Fed 85-indicator index. A correlation with the
Stock–Watson filtered factor is not independent confirmation.
"""

from __future__ import annotations

import hashlib
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from aqil_research.contracts.observation import AnalysisMode, SeriesProvenance
from aqil_research.methods.parameters import MethodParameterDocument
from aqil_research.methods.protocol import MethodContext, MethodExecutionResult
from aqil_research.methods.stock_watson_1988_fit import MODERN_REFIT_DATASETS

METHOD_ID = "RESTRICTED_COINCIDENT_DIFFUSION"
METHOD_VERSION = "0.1.0"
PUBLICATION_ALLOWED = False
SAMPLE_START = date(1997, 1, 1)
CHANGE_HORIZON_MONTHS = 3
PERSISTENCE_SHARE_FLOOR = 0.5
DATASETS = MODERN_REFIT_DATASETS
NOT_THE_CHICAGO_FED_INDEX = "This is not the Chicago Fed 85-indicator index."
NOT_INDEPENDENT_CONFIRMATION = (
    "The correlation with the Stock–Watson filtered factor is not independent confirmation."
)
PERSISTENCE_RULE = (
    "Persistence counts consecutive months, ending this month, "
    "for which the diffusion share is at or above one half. "
    "A share below one half, or a month with no observed series, resets the count to zero. "
    "A zero change is not an improvement."
)


@dataclass(frozen=True, slots=True)
class DiffusionMonth:
    period: date
    improving: int
    denominator: int
    share: float | None
    persistence_months: int


@dataclass(frozen=True, slots=True)
class DiffusionResult:
    months: tuple[DiffusionMonth, ...]
    balanced_months: tuple[date, ...]


class RestrictedCoincidentDiffusionConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    config_id: str = Field(min_length=1)
    label: str = Field(min_length=1)


def shift_month(period: date, months: int) -> date:
    index = period.month - 1 + months
    year = period.year + index // 12
    month = index % 12 + 1
    return date(year, month, 1)


def balanced_level_months(
    levels: Mapping[str, Mapping[date, float]],
) -> tuple[date, ...]:
    """Months from January 1997 on which every series is observed. No interpolation."""
    present = []
    for dataset_id in DATASETS:
        series = levels.get(dataset_id)
        if series is None:
            return ()
        present.append({period for period in series if period >= SAMPLE_START})
    if any(not months for months in present):
        return ()
    return tuple(sorted(set.intersection(*present)))


def restricted_coincident_diffusion(
    levels: Mapping[str, Mapping[date, float]],
) -> DiffusionResult:
    """Share of series whose level rose over three months.

    A series is omitted from that month's denominator when either endpoint is
    missing. Missing months are not interpolated.
    """
    balanced = balanced_level_months(levels)
    streak = 0
    rows: list[DiffusionMonth] = []
    for period in balanced:
        improving = 0
        denominator = 0
        prior = shift_month(period, -CHANGE_HORIZON_MONTHS)
        for dataset_id in DATASETS:
            series = levels[dataset_id]
            if period not in series or prior not in series:
                continue
            denominator += 1
            if series[period] - series[prior] > 0:
                improving += 1
        if denominator == 0:
            share = None
            streak = 0
            persistence = 0
        else:
            share = improving / denominator
            if share >= PERSISTENCE_SHARE_FLOOR:
                streak += 1
            else:
                streak = 0
            persistence = streak
        rows.append(
            DiffusionMonth(
                period=period,
                improving=improving,
                denominator=denominator,
                share=share,
                persistence_months=persistence,
            )
        )
    return DiffusionResult(months=tuple(rows), balanced_months=balanced)


def pearson_correlation(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right) or len(left) < 3:
        raise ValueError("correlation needs at least three paired months")
    mean_left = sum(left) / len(left)
    mean_right = sum(right) / len(right)
    variance_left = sum((value - mean_left) ** 2 for value in left)
    variance_right = sum((value - mean_right) ** 2 for value in right)
    if variance_left <= 0 or variance_right <= 0:
        raise ValueError("correlation is undefined when a series does not vary")
    covariance = sum(
        (first - mean_left) * (second - mean_right)
        for first, second in zip(left, right, strict=True)
    )
    return covariance / math.sqrt(variance_left * variance_right)


def correlate_with_filtered_factor(
    months: Sequence[DiffusionMonth],
    factor_by_period: Mapping[date, float],
) -> tuple[float, int]:
    """Pair the diffusion share with the filtered factor. Not a second identification."""
    shares: list[float] = []
    factor: list[float] = []
    for month in months:
        if month.share is None or month.period not in factor_by_period:
            continue
        shares.append(month.share)
        factor.append(factor_by_period[month.period])
    return pearson_correlation(shares, factor), len(shares)


def diffusion_implementation_hash() -> str:
    payload = "|".join(
        (
            METHOD_ID,
            METHOD_VERSION,
            f"change-{CHANGE_HORIZON_MONTHS}",
            f"floor-{PERSISTENCE_SHARE_FLOOR}",
            "strictly-positive",
            "no-interpolation",
            "not-cfnai",
        )
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class RestrictedCoincidentDiffusionMethod:
    """Breadth on the same four series as the modern refit.

    Registration, for the integrator, inside ``default_method_registry``::

        registry.register(RestrictedCoincidentDiffusionMethod())
    """

    method_id = METHOD_ID
    method_version = METHOD_VERSION

    def implementation_hash(self) -> str:
        return diffusion_implementation_hash()

    def required_dataset_ids(self) -> tuple[str, ...]:
        return DATASETS

    def parse_config(self, payload: dict[str, object]) -> RestrictedCoincidentDiffusionConfig:
        return RestrictedCoincidentDiffusionConfig.model_validate(payload)

    def config_hash(self, config: BaseModel) -> str:
        if not isinstance(config, RestrictedCoincidentDiffusionConfig):
            raise TypeError("expected RestrictedCoincidentDiffusionConfig")
        return MethodParameterDocument(
            config_id=config.config_id,
            label=config.label,
        ).config_hash()

    def run(self, context: MethodContext, config: BaseModel) -> MethodExecutionResult:
        if not isinstance(config, RestrictedCoincidentDiffusionConfig):
            raise TypeError("expected RestrictedCoincidentDiffusionConfig")
        if context.analysis_mode != AnalysisMode.LATEST_REVISED:
            return _insufficient("diffusion reads a latest-revised panel, not a real-time vintage")
        levels, observation_ids = _levels(context.inputs_by_dataset)
        if levels is None:
            return _insufficient(
                "the four coincident series are not all available from January 1997"
            )
        result = restricted_coincident_diffusion(levels)
        if len(result.balanced_months) < 36:
            return _insufficient("the four series do not share 36 months from January 1997")
        return MethodExecutionResult(
            sufficiency="sufficient",
            calculation=_calculation(result),
            observation_ids=tuple(observation_ids),
            assumptions=(
                "Each series enters as a three-month arithmetic change in the level.",
                "An increase is an improvement for all four series.",
                "A zero change is not an improvement.",
                PERSISTENCE_RULE,
                "A missing endpoint omits that series from the denominator.",
                "There is no interpolation.",
            ),
            limitations=(
                "publication_allowed is false.",
                NOT_THE_CHICAGO_FED_INDEX,
                "The path is latest revised. It is not a real-time vintage.",
                NOT_INDEPENDENT_CONFIRMATION,
            ),
            missing_reason=None,
            statistical_interpretation=(
                "Share of the four coincident series that rose over three months. "
                f"{NOT_THE_CHICAGO_FED_INDEX} {NOT_INDEPENDENT_CONFIRMATION}"
            ),
            causal_hypothesis="none",
            investment_implication="no_action",
            narrative=(
                "Restricted coincident diffusion on the four latest revised series. "
                f"{NOT_THE_CHICAGO_FED_INDEX} publication_allowed is false."
            ),
        )


def _calculation(result: DiffusionResult) -> dict[str, object]:
    return {
        "method_id": METHOD_ID,
        "publication_allowed": PUBLICATION_ALLOWED,
        "real_time": False,
        "input_vintage": "latest_revised",
        "not_chicago_fed_85_indicator_index": True,
        "change": "three_month_arithmetic_level_change",
        "improvement": "strictly_positive_change",
        "persistence_rule": PERSISTENCE_RULE,
        "balanced_start": result.balanced_months[0].isoformat(),
        "balanced_end": result.balanced_months[-1].isoformat(),
        "months": [
            {
                "period": month.period.isoformat(),
                "improving": month.improving,
                "denominator": month.denominator,
                "share": month.share,
                "persistence_months": month.persistence_months,
            }
            for month in result.months
        ],
        "correlation_is_not_independent_confirmation": True,
        "sources": list(DATASETS),
    }


def _levels(inputs_by_dataset: dict) -> tuple[dict[str, dict[date, float]] | None, list[str]]:
    levels: dict[str, dict[date, float]] = {}
    observation_ids: list[str] = []
    for dataset_id in DATASETS:
        rows = inputs_by_dataset.get(dataset_id)
        if not rows:
            return None, []
        levels[dataset_id] = {}
        for period, observation in rows.items():
            if observation.series_provenance != SeriesProvenance.LATEST_REVISED:
                continue
            levels[dataset_id][period] = float(observation.decimal_value())
            if period >= SAMPLE_START:
                observation_ids.append(observation.observation_id)
    return levels, observation_ids


def _insufficient(reason: str) -> MethodExecutionResult:
    return MethodExecutionResult(
        sufficiency="insufficient",
        calculation=None,
        observation_ids=(),
        assumptions=(),
        limitations=(
            "publication_allowed is false.",
            NOT_THE_CHICAGO_FED_INDEX,
        ),
        missing_reason=reason,
        statistical_interpretation="Restricted coincident diffusion was not calculated.",
        causal_hypothesis="none",
        investment_implication="insufficient_evidence",
        narrative=f"Diffusion incomplete. Reason: {reason}",
    )
