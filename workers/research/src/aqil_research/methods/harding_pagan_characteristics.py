"""Phase, amplitude, and concordance from the Spencer-15 dates.

This is not quarterly Harding–Pagan BBQ and it is not a second monthly dating
engine. Turning points come from ``date_spencer15_variant``. A series is dated
only when it is an eligible level input under the same structural rules as the
G.17 kernel: live retrieval, the series' own level unit, seasonal adjustment
already applied, monthly, latest_revised, observed, a month start, a finite
value, no duplicate month, and no gap. A failed series is recorded and is not
given a date.

The phase rule: after a trough, and up to the next peak, the phase is
expansion. After a peak, and up to the next trough, the phase is contraction.
The peak month is the last month of expansion. The trough month is the last
month of contraction. Months before the first turn and after the last turn
are unclassified.

Concordance is the Harding–Pagan index: the share of compared months in which
both series are in expansion or both are in contraction. Payroll, income, and
sales turns are specific-cycle phases in those series. They are not NBER
recession dates.

Dates are retrospective_full_sample on latest_revised levels. The Spencer
smoother is centred, so the dates are not a contemporaneous recession call.
publication_allowed stays false.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from itertools import combinations
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from aqil_research.contracts.observation import (
    AnalysisMode,
    EconomicObservation,
    Frequency,
    QualityStatus,
    SeasonalAdjustment,
    SeriesProvenance,
)
from aqil_research.methods.bry_boschan_monthly import (
    G17_DATASET_ID,
    G17_LEVEL_UNIT,
    LEVEL_REPRESENTATION,
    G17InputPoint,
    assess_g17_level_input,
)
from aqil_research.methods.bry_boschan_spencer15 import (
    BRY_BOSCHAN_SPENCER15_VARIANT,
    CHRONOLOGY_CLASS,
    PUBLICATION_ALLOWED,
    date_spencer15_variant,
    variant_implementation_hash,
)
from aqil_research.methods.parameters import MethodParameterDocument
from aqil_research.methods.protocol import MethodContext, MethodExecutionResult

HARDING_PAGAN_CHARACTERISTICS = "HARDING_PAGAN_CHARACTERISTICS"
CHARACTERISTICS_VERSION = "1.0.0"
AMPLITUDE_QUANTUM = Decimal("0.0001")
CONCORDANCE_QUANTUM = Decimal("0.000001")

PHASE_RULE = (
    "After a trough, and up to the next peak, the phase is expansion. "
    "After a peak, and up to the next trough, the phase is contraction. "
    "The peak month is the last month of expansion. The trough month is the "
    "last month of contraction. Months before the first turn and after the "
    "last turn are unclassified."
)
CONCORDANCE_DEFINITION = (
    "Concordance is the Harding-Pagan index: the share of compared months in "
    "which both series are in expansion or both are in contraction. The "
    "denominator is the months where both series have a classified phase."
)
NOT_NBER_RECESSION = (
    "These are specific-cycle phases in this series. They are not NBER recession dates."
)
NOT_BBQ = (
    "Quarterly Harding-Pagan BBQ is not implemented and is not run on monthly "
    "industrial production."
)
CAUSAL_HYPOTHESIS = "No causal mechanism is established."

HARDING_PAGAN_CHARACTERISTICS_PUBLISHED = {
    "config_id": "harding_pagan_characteristics_v1",
    "label": "Phase duration, amplitude, and concordance from Spencer-15 dates",
}


class HardingPaganCharacteristicsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    config_id: str = Field(min_length=1)
    label: str = Field(min_length=1)


@dataclass(frozen=True, slots=True)
class LevelSeriesContract:
    dataset_id: str
    level_unit: str
    series_label: str


@dataclass(frozen=True, slots=True)
class LevelInputPoint:
    observation: EconomicObservation
    collection_mode: str


@dataclass(frozen=True, slots=True)
class LevelInputAssessment:
    eligible: bool
    reasons: tuple[str, ...]
    sample_start: date | None
    sample_end: date | None
    month_count: int


COINCIDENT_LEVEL_SERIES: tuple[LevelSeriesContract, ...] = (
    LevelSeriesContract(
        G17_DATASET_ID,
        G17_LEVEL_UNIT,
        "industrial production",
    ),
    LevelSeriesContract(
        "bea.nipa.T20600.W875RX",
        "millions_chained_2017_dollars",
        "real personal income excluding transfers",
    ),
    LevelSeriesContract(
        "bea.nipa.U002BU.KPMT",
        "millions_chained_2017_dollars",
        "real manufacturing and trade sales",
    ),
    LevelSeriesContract(
        "bls.ce.CES0000000001",
        "thousands",
        "total nonfarm payroll employment",
    ),
)

_CONTRACTS = {spec.dataset_id: spec for spec in COINCIDENT_LEVEL_SERIES}


def characteristics_implementation_hash() -> str:
    payload = "|".join(
        (
            HARDING_PAGAN_CHARACTERISTICS,
            CHARACTERISTICS_VERSION,
            variant_implementation_hash(),
            "phase=after-trough-through-peak",
            "concordance=same-phase-share",
            "bbq=not-implemented",
        ),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def assess_coincident_level_input(
    dataset_id: str,
    points: tuple[LevelInputPoint, ...] | list[LevelInputPoint],
    *,
    representation: str = LEVEL_REPRESENTATION,
) -> LevelInputAssessment:
    """Apply the kernel's level-input rules to one coincident series.

    G.17 uses ``assess_g17_level_input`` unchanged. The other series use the
    same checks with their own dataset id and level unit. A growth rate, a
    gap, or a fixture retrieval is ineligible. Nothing is interpolated.
    """
    spec = _CONTRACTS.get(dataset_id)
    if spec is None:
        return LevelInputAssessment(
            False,
            (f"{dataset_id} is not one of the coincident level series",),
            None,
            None,
            0,
        )
    if dataset_id == G17_DATASET_ID:
        assessment = assess_g17_level_input(
            tuple(
                G17InputPoint(
                    observation=point.observation,
                    collection_mode=point.collection_mode,
                )
                for point in points
            ),
            representation=representation,
        )
        return LevelInputAssessment(
            assessment.eligible,
            assessment.reasons,
            assessment.sample_start,
            assessment.sample_end,
            assessment.month_count,
        )
    return _assess_level_input(spec, points, representation=representation)


def expansion_contraction_states(
    peaks: tuple[date, ...],
    troughs: tuple[date, ...],
) -> dict[date, Literal["expansion", "contraction"]] | None:
    """Map each classified month to expansion or contraction.

    Returns None when the turns do not alternate. Phases are not forced.
    """
    turns = sorted(
        [("peak", item) for item in peaks] + [("trough", item) for item in troughs],
        key=lambda item: item[1],
    )
    for index in range(len(turns) - 1):
        if turns[index][0] == turns[index + 1][0]:
            return None
    states: dict[date, Literal["expansion", "contraction"]] = {}
    for index in range(len(turns) - 1):
        kind, start = turns[index]
        _next_kind, end = turns[index + 1]
        phase: Literal["expansion", "contraction"] = (
            "expansion" if kind == "trough" else "contraction"
        )
        cursor = _next_month(start)
        while cursor <= end:
            states[cursor] = phase
            cursor = _next_month(cursor)
    return states


def phase_rows(
    levels: tuple[tuple[date, Decimal], ...] | list[tuple[date, Decimal]],
    peaks: tuple[date, ...],
    troughs: tuple[date, ...],
) -> tuple[dict[str, object], ...] | None:
    """Duration in months and percent change between consecutive turns."""
    states = expansion_contraction_states(peaks, troughs)
    if states is None:
        return None
    by_period = {period: value for period, value in levels}
    turns = sorted(
        [("peak", item) for item in peaks] + [("trough", item) for item in troughs],
        key=lambda item: item[1],
    )
    rows: list[dict[str, object]] = []
    for index in range(len(turns) - 1):
        start_kind, start = turns[index]
        end_kind, end = turns[index + 1]
        phase = "expansion" if start_kind == "trough" else "contraction"
        start_level = by_period.get(start)
        end_level = by_period.get(end)
        amplitude: str | None = None
        amplitude_reason: str | None = None
        if start_level is None or end_level is None:
            amplitude_reason = "A turning-point month has no stored level."
        elif start_level == 0:
            amplitude_reason = "The starting level is zero, so the percent change is undefined."
        else:
            change = ((end_level - start_level) / start_level) * Decimal(100)
            amplitude = format(change.quantize(AMPLITUDE_QUANTUM, rounding=ROUND_HALF_UP), "f")
        row: dict[str, object] = {
            "phase": phase,
            "start_kind": start_kind,
            "end_kind": end_kind,
            "start": start.isoformat(),
            "end": end.isoformat(),
            "duration_months": _month_gap(start, end),
            "start_level": None if start_level is None else format(start_level, "f"),
            "end_level": None if end_level is None else format(end_level, "f"),
            "amplitude_percent": amplitude,
        }
        if amplitude_reason is not None:
            row["amplitude_reason"] = amplitude_reason
        rows.append(row)
    return tuple(rows)


def concordance_index(
    left: dict[date, str],
    right: dict[date, str],
) -> dict[str, object]:
    """Share of months in which both series are in the same phase."""
    months = sorted(set(left) & set(right))
    same = sum(1 for month in months if left[month] == right[month])
    compared = len(months)
    share: str | None = None
    if compared:
        ratio = (Decimal(same) / Decimal(compared)).quantize(
            CONCORDANCE_QUANTUM,
            rounding=ROUND_HALF_UP,
        )
        share = format(ratio, "f")
    return {
        "compared_months": compared,
        "same_phase_months": same,
        "concordance": share,
        "definition": CONCORDANCE_DEFINITION,
    }


class HardingPaganCharacteristicsMethod:
    method_id = HARDING_PAGAN_CHARACTERISTICS
    method_version = CHARACTERISTICS_VERSION

    def implementation_hash(self) -> str:
        return characteristics_implementation_hash()

    def required_dataset_ids(self) -> tuple[str, ...]:
        return tuple(spec.dataset_id for spec in COINCIDENT_LEVEL_SERIES)

    def parse_config(self, payload: dict[str, object]) -> HardingPaganCharacteristicsConfig:
        return HardingPaganCharacteristicsConfig.model_validate(payload)

    def config_hash(self, config: BaseModel) -> str:
        if not isinstance(config, HardingPaganCharacteristicsConfig):
            raise TypeError("expected HardingPaganCharacteristicsConfig")
        return MethodParameterDocument(
            config_id=config.config_id,
            label=config.label,
            scalars={"dating_method": BRY_BOSCHAN_SPENCER15_VARIANT},
        ).config_hash()

    def run(self, context: MethodContext, config: BaseModel) -> MethodExecutionResult:
        if not isinstance(config, HardingPaganCharacteristicsConfig):
            raise TypeError("expected HardingPaganCharacteristicsConfig")
        if context.analysis_mode != AnalysisMode.LATEST_REVISED:
            return _insufficient(
                "These series are dated on latest_revised levels. "
                "A point-in-time request was not dated.",
            )
        points_by_dataset = {
            spec.dataset_id: tuple(
                LevelInputPoint(observation=observation, collection_mode="live")
                for observation in context.inputs_by_dataset.get(spec.dataset_id, {}).values()
            )
            for spec in COINCIDENT_LEVEL_SERIES
        }
        calculation = build_characteristics(points_by_dataset)
        series_rows = calculation["series"]
        if not isinstance(series_rows, list):
            raise TypeError("characteristics series rows must be a list")
        dated_count = sum(1 for row in series_rows if row["eligible"] is True)
        observation_ids = tuple(
            sorted(
                point.observation.observation_id
                for points in points_by_dataset.values()
                for point in points
            ),
        )
        if dated_count == 0:
            reasons = [
                f"{row['dataset_id']}: {'; '.join(row['reasons'])}"
                for row in series_rows
                if row["reasons"]
            ]
            reason = "; ".join(reasons) or "no coincident level series was eligible"
            failed = _insufficient(reason)
            return MethodExecutionResult(
                sufficiency=failed.sufficiency,
                calculation=calculation,
                observation_ids=observation_ids,
                assumptions=failed.assumptions,
                limitations=failed.limitations,
                missing_reason=reason,
                statistical_interpretation=failed.statistical_interpretation,
                causal_hypothesis=failed.causal_hypothesis,
                investment_implication=failed.investment_implication,
                narrative=failed.narrative,
            )
        return MethodExecutionResult(
            sufficiency="sufficient",
            calculation=calculation,
            observation_ids=observation_ids,
            assumptions=(
                PHASE_RULE,
                CONCORDANCE_DEFINITION,
                (
                    "Turning points come from the Spencer-15 variant. The chronology "
                    "is retrospective_full_sample on latest_revised levels."
                ),
                (
                    "The Spencer smoother is centred, so these dates are not a "
                    "contemporaneous recession call."
                ),
                NOT_BBQ,
                NOT_NBER_RECESSION,
            ),
            limitations=(
                NOT_BBQ,
                NOT_NBER_RECESSION,
                (
                    "Revision sensitivity is blocked because the inputs are "
                    "latest_revised. No vintage panel was invented."
                ),
                "publication_allowed stays false.",
                ("An ineligible series is recorded and is not given a turning point."),
            ),
            missing_reason=None,
            statistical_interpretation=(
                "Phase duration, amplitude, and pairwise concordance from "
                "Spencer-15 specific-cycle dates. This is not a quarterly BBQ "
                "dating, not an NBER recession chronology, and not a forecast."
            ),
            causal_hypothesis=CAUSAL_HYPOTHESIS,
            investment_implication="no_action",
            narrative=_narrative(series_rows),
        )


def build_characteristics(
    points_by_dataset: dict[str, tuple[LevelInputPoint, ...] | list[LevelInputPoint]],
) -> dict[str, object]:
    """Date each eligible series and compute phases, amplitudes, and concordance."""
    prepared: list[dict[str, object]] = []
    states_by_dataset: dict[str, dict[date, str]] = {}
    for spec in COINCIDENT_LEVEL_SERIES:
        points = tuple(points_by_dataset.get(spec.dataset_id, ()))
        assessment = assess_coincident_level_input(spec.dataset_id, points)
        row = _series_row(spec, points, assessment)
        prepared.append(row)
        states = row.get("phase_states")
        if assessment.eligible and isinstance(states, dict):
            states_by_dataset[spec.dataset_id] = states
        row.pop("phase_states", None)
    pairs = _pairs(prepared, states_by_dataset)
    dated = sum(1 for row in prepared if row["eligible"] is True)
    return {
        "method_id": HARDING_PAGAN_CHARACTERISTICS,
        "dating_method": BRY_BOSCHAN_SPENCER15_VARIANT,
        "chronology_class": CHRONOLOGY_CLASS,
        "input_revision": AnalysisMode.LATEST_REVISED.value,
        "centred_spencer_smoother": True,
        "contemporaneous_recession_call": False,
        "publication_allowed": PUBLICATION_ALLOWED,
        "quarterly_bbq_implemented": False,
        "bbq_run_on_monthly_g17": False,
        "phase_rule": PHASE_RULE,
        "concordance_definition": CONCORDANCE_DEFINITION,
        "nber_recession_chronology": False,
        "series_dated": dated,
        "series": prepared,
        "concordance": pairs,
        "revision_sensitivity": {
            "status": "blocked",
            "reason": (
                "Inputs are latest_revised. Revision sensitivity needs a vintage "
                "panel, and none was invented."
            ),
        },
    }


def _series_row(
    spec: LevelSeriesContract,
    points: tuple[LevelInputPoint, ...],
    assessment: LevelInputAssessment,
) -> dict[str, object]:
    base: dict[str, object] = {
        "dataset_id": spec.dataset_id,
        "series_label": spec.series_label,
        "level_unit": spec.level_unit,
        "eligible": assessment.eligible,
        "reasons": list(assessment.reasons),
        "nber_recession_chronology": False,
        "description": NOT_NBER_RECESSION,
        "peaks": [],
        "troughs": [],
        "phases": [],
    }
    if not assessment.eligible or assessment.sample_start is None or assessment.sample_end is None:
        base["dated"] = False
        return base
    chosen = [
        point.observation
        for point in points
        if assessment.sample_start <= point.observation.period_start <= assessment.sample_end
    ]
    chosen.sort(key=lambda observation: observation.period_start)
    levels = tuple(
        (observation.period_start, observation.decimal_value()) for observation in chosen
    )
    dated = date_spencer15_variant(levels)
    phases = phase_rows(levels, dated.peaks, dated.troughs)
    states = expansion_contraction_states(dated.peaks, dated.troughs)
    base.update(
        {
            "dated": True,
            "sample_start": assessment.sample_start.isoformat(),
            "sample_end": assessment.sample_end.isoformat(),
            "month_count": assessment.month_count,
            "mcd_months": dated.mcd_months,
            "peak_count": len(dated.peaks),
            "trough_count": len(dated.troughs),
            "peaks": [item.isoformat() for item in dated.peaks],
            "troughs": [item.isoformat() for item in dated.troughs],
            "phases": [] if phases is None else list(phases),
            "phase_states": states,
        },
    )
    if phases is None:
        base["phase_reason"] = "Turns do not alternate, so phases were not forced."
    return base


def _pairs(
    series_rows: list[dict[str, object]],
    states_by_dataset: dict[str, dict[date, str]],
) -> list[dict[str, object]]:
    by_id = {str(row["dataset_id"]): row for row in series_rows}
    pairs: list[dict[str, object]] = []
    dataset_ids = [spec.dataset_id for spec in COINCIDENT_LEVEL_SERIES]
    for left_id, right_id in combinations(dataset_ids, 2):
        left = by_id[left_id]
        right = by_id[right_id]
        pair: dict[str, object] = {
            "left_dataset_id": left_id,
            "right_dataset_id": right_id,
            "left_label": left["series_label"],
            "right_label": right["series_label"],
        }
        if left["eligible"] is not True or right["eligible"] is not True:
            blocked = [
                str(row["dataset_id"]) for row in (left, right) if row["eligible"] is not True
            ]
            pair["computed"] = False
            pair["reason"] = (
                "Concordance was not computed because "
                + " and ".join(blocked)
                + " failed the level-input rules."
            )
            pairs.append(pair)
            continue
        left_states = states_by_dataset.get(left_id)
        right_states = states_by_dataset.get(right_id)
        if left_states is None or right_states is None:
            pair["computed"] = False
            pair["reason"] = "Phases were not available, so concordance was not computed."
            pairs.append(pair)
            continue
        measured = concordance_index(left_states, right_states)
        pair["computed"] = True
        pair.update(measured)
        if measured["compared_months"] == 0:
            pair["reason"] = "No month has a classified phase in both series."
        pairs.append(pair)
    return pairs


def _assess_level_input(
    spec: LevelSeriesContract,
    points: tuple[LevelInputPoint, ...] | list[LevelInputPoint],
    *,
    representation: str,
) -> LevelInputAssessment:
    """Same structural checks as ``assess_g17_level_input``, for one other series."""
    reasons: list[str] = []
    if representation != LEVEL_REPRESENTATION:
        reasons.append(
            "non-level input is ineligible; the procedure dates the level, not a growth rate"
        )
    if not points:
        reasons.append("no observations")
        return LevelInputAssessment(False, tuple(reasons), None, None, 0)

    periods: dict[date, LevelInputPoint] = {}
    for point in points:
        observation = point.observation
        if point.collection_mode != "live":
            reasons.append(
                f"{observation.period_start.isoformat()} retrieval is "
                f"{point.collection_mode}, not live"
            )
        if observation.dataset_id != spec.dataset_id:
            reasons.append(f"dataset {observation.dataset_id} is not {spec.dataset_id}")
        if observation.unit != spec.level_unit:
            reasons.append(
                f"{observation.period_start.isoformat()} unit {observation.unit} "
                f"is not the level unit {spec.level_unit}"
            )
        if observation.seasonal_adjustment is not SeasonalAdjustment.SEASONALLY_ADJUSTED:
            reasons.append(
                f"{observation.period_start.isoformat()} is not seasonally adjusted; "
                "this procedure does not seasonally adjust"
            )
        if observation.frequency is not Frequency.MONTHLY:
            reasons.append(f"{observation.period_start.isoformat()} is not monthly")
        if observation.series_provenance is not SeriesProvenance.LATEST_REVISED:
            reasons.append(f"{observation.period_start.isoformat()} is not latest_revised")
        if observation.quality_status is not QualityStatus.OBSERVED:
            reasons.append(f"{observation.period_start.isoformat()} is not observed")
        if observation.period_start.day != 1:
            reasons.append(f"{observation.period_start.isoformat()} is not a month start")
        if not observation.decimal_value().is_finite():
            reasons.append(f"{observation.period_start.isoformat()} is not finite")
        if observation.period_start in periods:
            reasons.append(f"duplicate month {observation.period_start.isoformat()}")
        periods[observation.period_start] = point

    if not periods:
        return LevelInputAssessment(False, tuple(reasons), None, None, 0)

    ordered = tuple(sorted(periods))
    start = ordered[0]
    end = ordered[-1]
    cursor = start
    missing: list[str] = []
    while cursor <= end:
        if cursor not in periods:
            missing.append(cursor.isoformat())
        cursor = _next_month(cursor)
    if missing:
        shown = ", ".join(missing[:6])
        extra = len(missing) - 6
        if extra > 0:
            shown = f"{shown}, and {extra} more"
        reasons.append(f"gap in monthly index: {shown}")

    unique_reasons = tuple(dict.fromkeys(reasons))
    return LevelInputAssessment(
        eligible=not unique_reasons,
        reasons=unique_reasons,
        sample_start=start,
        sample_end=end,
        month_count=len(periods),
    )


def _narrative(series_rows: list[dict[str, object]]) -> str:
    dated = [str(row["series_label"]) for row in series_rows if row["eligible"] is True]
    refused = [str(row["series_label"]) for row in series_rows if row["eligible"] is not True]
    dated_text = ", ".join(dated) if dated else "no series"
    sentence = (
        f"Harding-Pagan characteristics dated specific cycles in {dated_text}. "
        "Concordance is the share of months in the same phase. "
        "The chronology is retrospective full sample on latest-revised levels. "
        "The centred Spencer smoother means these dates are not a contemporaneous "
        "recession call. Publication allowed is false."
    )
    if refused:
        sentence += " Eligibility failed for " + ", ".join(refused) + "."
    sentence += " " + NOT_NBER_RECESSION
    return sentence


def _insufficient(reason: str) -> MethodExecutionResult:
    return MethodExecutionResult(
        sufficiency="insufficient",
        calculation={
            "method_id": HARDING_PAGAN_CHARACTERISTICS,
            "publication_allowed": PUBLICATION_ALLOWED,
            "quarterly_bbq_implemented": False,
            "nber_recession_chronology": False,
        },
        observation_ids=(),
        assumptions=(NOT_BBQ,),
        limitations=(NOT_BBQ, "publication_allowed stays false."),
        missing_reason=reason,
        statistical_interpretation="Characteristics were not completed.",
        causal_hypothesis="Unresolved because inputs were insufficient.",
        investment_implication="insufficient_evidence",
        narrative=f"Characteristics incomplete. Reason: {reason}",
    )


def _next_month(month_start: date) -> date:
    if month_start.month == 12:
        return date(month_start.year + 1, 1, 1)
    return date(month_start.year, month_start.month + 1, 1)


def _month_gap(left: date, right: date) -> int:
    return abs((left.year - right.year) * 12 + (left.month - right.month))
