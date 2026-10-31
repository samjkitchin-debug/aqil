"""Four-quarter probit of the NBER classification on the constant-maturity spread.

The spread indicator remains ``ESTRELLA_MISHKIN_TERM_SPREAD``. This method has
its own id. It estimates a probit of the stored NBER quarterly classification
four quarters ahead. The short rate is the H.15 three-month constant-maturity
yield, not the three-month Treasury bill in the June 1996 article. The fit is
not the New York Fed parameterisation.

Estimation ends with the spread quarter 2005 Q4. Evaluation starts with the
spread quarter 2006 Q1. Those windows are fixed. A fit that does not converge,
separates, or has no variation is stored as not accepted. The windows are not
widened to produce a result.
"""

from __future__ import annotations

import csv
import hashlib
import warnings
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, model_validator
from scipy.stats import norm
from statsmodels.discrete.discrete_model import Probit
from statsmodels.tools.sm_exceptions import (
    ConvergenceWarning,
    PerfectSeparationError,
    PerfectSeparationWarning,
)

from aqil_research.contracts.observation import (
    AnalysisMode,
    EconomicObservation,
    Frequency,
    SeriesProvenance,
)
from aqil_research.methods.parameters import MethodParameterDocument
from aqil_research.methods.protocol import (
    MethodContext,
    MethodDependency,
    MethodExecutionResult,
    bind_dependency,
)

METHOD_ID = "CONSTANT_MATURITY_SPREAD_RECESSION_PROBIT"
METHOD_VERSION = "1.0.0"
PUBLICATION_ALLOWED = False

TEN_YEAR_DATASET_ID = "fed.h15.RIFLGFCY10_N.M"
THREE_MONTH_DATASET_ID = "fed.h15.RIFLGFCM03_N.M"
FEDERAL_FUNDS_DATASET_ID = "fed.h15.RIFSPFF_N.M"
CHRONOLOGY_DATASET_ID = "nber.bcdc.us_business_cycle_chronology"
CHRONOLOGY_SOURCE_URL = (
    "https://www.nber.org/research/data/us-business-cycle-expansions-and-contractions"
)
CHRONOLOGY_PUBLICATION_DATE = date(2023, 3, 14)
HORIZON_QUARTERS = 4
ESTIMATION_LAST_SPREAD_QUARTER = date(2005, 10, 1)
EVALUATION_FIRST_SPREAD_QUARTER = date(2006, 1, 1)

INSTRUMENT_MISMATCH = (
    "The stored short rate is fed.h15.RIFLGFCM03_N.M, the H.15 three-month "
    "constant-maturity yield quoted on an investment basis. It is not the "
    "three-month Treasury bill in the June 1996 Current Issues article. "
    "This fit is not the New York Fed parameterisation."
)
CONTRACTION_QUARTER_RULE = (
    "A contraction quarter is strictly after the published peak quarter and "
    "up to and including the published trough quarter. The published quarter "
    "is used when it does not contain the turning-point month. The first "
    "printed trough has no peak and does not open a contraction."
)
_NOT_REAL_TIME = "This is a latest-revised fit. It is not a real-time recession probability."

ACCEPTED_CONFIG = {
    "config_id": "constant_maturity_spread_recession_probit_v1",
    "label": "Four-quarter probit of the NBER classification on the constant-maturity spread",
    "horizon_quarters": HORIZON_QUARTERS,
    "estimation_last_spread_quarter": ESTIMATION_LAST_SPREAD_QUARTER.isoformat(),
    "evaluation_first_spread_quarter": EVALUATION_FIRST_SPREAD_QUARTER.isoformat(),
}


class ChronologyError(ValueError):
    """Raised when the stored chronology is not the dated reference file."""


class ProbitConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    config_id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    horizon_quarters: int
    estimation_last_spread_quarter: date
    evaluation_first_spread_quarter: date

    @model_validator(mode="after")
    def windows_stay_predeclared(self) -> ProbitConfig:
        if self.horizon_quarters != HORIZON_QUARTERS:
            raise ValueError("the horizon stays at four quarters")
        if self.estimation_last_spread_quarter != ESTIMATION_LAST_SPREAD_QUARTER:
            raise ValueError("the estimation window is predeclared and is not widened")
        if self.evaluation_first_spread_quarter != EVALUATION_FIRST_SPREAD_QUARTER:
            raise ValueError("the evaluation window is predeclared and is not moved earlier")
        if self.estimation_last_spread_quarter >= self.evaluation_first_spread_quarter:
            raise ValueError("estimation and evaluation windows must be separate")
        return self


@dataclass(frozen=True, slots=True)
class ChronologyTurn:
    publication_date: date
    source_url: str
    peak_month: date | None
    peak_quarter: date | None
    trough_month: date
    trough_quarter: date


@dataclass(frozen=True, slots=True)
class ProbitQuarter:
    spread_quarter: date
    outcome_quarter: date
    spread: float
    spread_text: str
    contraction: int
    window: str
    observation_ids: tuple[str, ...]


class ConstantMaturitySpreadRecessionProbitMethod:
    """Analytical method for one fixed-window probit.

    Registered on the default method registry. The spread indicator stays a
    separate method. This fit is not the New York Fed parameterisation.
    """

    method_id = METHOD_ID
    method_version = METHOD_VERSION

    def implementation_hash(self) -> str:
        chronology = chronology_path().read_bytes()
        digest = hashlib.sha256(chronology).hexdigest()
        payload = (
            f"{self.method_id}:{self.method_version}:{HORIZON_QUARTERS}:"
            f"{ESTIMATION_LAST_SPREAD_QUARTER.isoformat()}:"
            f"{EVALUATION_FIRST_SPREAD_QUARTER.isoformat()}:{digest}"
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def required_dataset_ids(self) -> tuple[str, ...]:
        return (TEN_YEAR_DATASET_ID, THREE_MONTH_DATASET_ID)

    def dependency(self) -> MethodDependency:
        return bind_dependency(
            self.required_dataset_ids(),
            frequency=("monthly",),
            minimum_history=(
                "three complete months in each spread quarter, with the "
                "predeclared estimation window before the evaluation window"
            ),
            parameter_policy="none",
            depends_on_method_ids=(),
            new_observation_requires_recalculation=True,
            refit_is_different_command=False,
        )

    def accepted_config_payload(self) -> dict[str, object]:
        return dict(ACCEPTED_CONFIG)

    def parse_config(self, payload: dict[str, object]) -> ProbitConfig:
        return ProbitConfig.model_validate(payload)

    def config_hash(self, config: BaseModel) -> str:
        if not isinstance(config, ProbitConfig):
            raise TypeError("expected ProbitConfig")
        return MethodParameterDocument(
            config_id=config.config_id,
            label=config.label,
            scalars={
                "horizon_quarters": str(config.horizon_quarters),
                "estimation_last_spread_quarter": (
                    config.estimation_last_spread_quarter.isoformat()
                ),
                "evaluation_first_spread_quarter": (
                    config.evaluation_first_spread_quarter.isoformat()
                ),
            },
        ).config_hash()

    def run(self, context: MethodContext, config: BaseModel) -> MethodExecutionResult:
        if not isinstance(config, ProbitConfig):
            raise TypeError("expected ProbitConfig")
        if context.analysis_mode != AnalysisMode.LATEST_REVISED:
            return _insufficient(
                "latest_revised is required. This probit is not a real-time probability.",
            )
        try:
            turns = load_chronology()
        except ChronologyError as exc:
            return _insufficient(str(exc))
        built = _quarter_rows(context, contraction_quarters(turns))
        if isinstance(built, str):
            return _insufficient(built)
        quarters, omitted = built
        if not quarters:
            return _insufficient("no complete spread quarter is available")
        fitted = estimate_split_probit(quarters)
        fitted["incomplete_quarters_omitted"] = omitted
        return _result(fitted, quarters)


def chronology_path() -> Path:
    for parent in Path(__file__).resolve().parents:
        candidate = (
            parent / "docs" / "sources" / "reference" / "nber_us_business_cycle_chronology.csv"
        )
        if candidate.is_file():
            return candidate
    raise ChronologyError("the NBER chronology file was not found")


def load_chronology(path: Path | None = None) -> tuple[ChronologyTurn, ...]:
    """Load the attributed copy. Dates stay as published."""
    source = path if path is not None else chronology_path()
    with source.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        raw_rows = list(reader)
    if not raw_rows:
        raise ChronologyError("the NBER chronology file has no rows")
    turns: list[ChronologyTurn] = []
    for index, row in enumerate(raw_rows):
        publication = _require_date(row.get("publication_date", ""), "publication_date")
        if publication != CHRONOLOGY_PUBLICATION_DATE:
            raise ChronologyError("the chronology publication date is not 14 March 2023")
        if row.get("source_url") != CHRONOLOGY_SOURCE_URL:
            raise ChronologyError("the chronology source is not the official NBER page")
        peak_month = _optional_month(row.get("peak_month", ""), "peak_month")
        peak_quarter = _optional_quarter(row.get("peak_quarter", ""), "peak_quarter")
        trough_month = _require_month(row.get("trough_month", ""), "trough_month")
        trough_quarter = _require_quarter(row.get("trough_quarter", ""), "trough_quarter")
        if (peak_month is None) != (peak_quarter is None):
            raise ChronologyError("a peak month and peak quarter must be stored together")
        if peak_month is None and index != 0:
            raise ChronologyError("only the first printed trough has no peak")
        if peak_quarter is not None and peak_quarter >= trough_quarter:
            raise ChronologyError("a published peak quarter is not before its trough quarter")
        turns.append(
            ChronologyTurn(
                publication_date=publication,
                source_url=CHRONOLOGY_SOURCE_URL,
                peak_month=peak_month,
                peak_quarter=peak_quarter,
                trough_month=trough_month,
                trough_quarter=trough_quarter,
            ),
        )
    return tuple(turns)


def contraction_quarters(turns: tuple[ChronologyTurn, ...]) -> frozenset[date]:
    quarters: set[date] = set()
    for turn in turns:
        if turn.peak_quarter is None:
            continue
        cursor = _add_quarters(turn.peak_quarter, 1)
        while cursor <= turn.trough_quarter:
            quarters.add(cursor)
            cursor = _add_quarters(cursor, 1)
    return frozenset(quarters)


def estimate_split_probit(rows: tuple[ProbitQuarter, ...]) -> dict[str, object]:
    """Fit on the estimation rows and score only the later rows."""
    estimation = tuple(row for row in rows if row.window == "estimation")
    evaluation = tuple(row for row in rows if row.window == "evaluation")
    if estimation and evaluation:
        if max(row.spread_quarter for row in estimation) >= min(
            row.spread_quarter for row in evaluation
        ):
            raise ValueError("estimation and evaluation windows overlap")
    payload = _empty_fit(estimation, evaluation)
    if not _both_classes(estimation):
        payload["fit_status"] = "not_estimated"
        payload["fit_failure"] = (
            "estimation window does not contain both a contraction quarter and an expansion quarter"
        )
        return payload
    spreads = np.array([row.spread for row in estimation], dtype=float)
    if float(np.nanmax(spreads) - np.nanmin(spreads)) == 0.0:
        payload["fit_status"] = "not_estimated"
        payload["fit_failure"] = "estimation spreads do not vary"
        return payload
    endog = np.array([row.contraction for row in estimation], dtype=float)
    exog = np.column_stack([np.ones(len(estimation)), spreads])
    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", PerfectSeparationWarning)
            warnings.simplefilter("always", ConvergenceWarning)
            fitted = Probit(endog, exog).fit(disp=False, maxiter=200)
    except PerfectSeparationError:
        payload["fit_status"] = "unstable"
        payload["fit_failure"] = "perfect_separation"
        return payload
    except (FloatingPointError, np.linalg.LinAlgError, ValueError) as exc:
        payload["fit_status"] = "unstable"
        payload["fit_failure"] = type(exc).__name__
        return payload
    separated = any(issubclass(item.category, PerfectSeparationWarning) for item in caught)
    converged = bool(fitted.mle_retvals.get("converged", False))
    params = [float(value) for value in fitted.params]
    errors = [float(value) for value in fitted.bse]
    payload["statsmodels_converged"] = converged
    if len(params) != 2 or len(errors) != 2 or not all(np.isfinite(params + errors)):
        payload["fit_status"] = "unstable"
        payload["fit_failure"] = "coefficients or standard errors are not finite"
        return payload
    payload["intercept"] = _text(params[0])
    payload["spread_coefficient"] = _text(params[1])
    payload["intercept_standard_error"] = _text(errors[0])
    payload["spread_coefficient_standard_error"] = _text(errors[1])
    probabilities = _probability_rows(rows, params[0], params[1])
    payload["probabilities"] = probabilities
    if separated or not converged:
        payload["fit_status"] = "unstable"
        payload["fit_failure"] = (
            "perfect_separation" if separated else "the probit optimiser did not converge"
        )
        payload["probabilities_accepted"] = False
        return payload
    payload["fit_status"] = "estimated"
    payload["fit_stable"] = True
    payload["fit_failure"] = None
    payload["probabilities_accepted"] = True
    _record_evaluation_metrics(payload, probabilities)
    return payload


def _empty_fit(
    estimation: tuple[ProbitQuarter, ...],
    evaluation: tuple[ProbitQuarter, ...],
) -> dict[str, object]:
    return {
        "method_id": METHOD_ID,
        "publication_allowed": PUBLICATION_ALLOWED,
        "input_vintage": "latest_revised",
        "real_time_probability": False,
        "new_york_fed_parameterisation": False,
        "paper_coefficients_reproduced": False,
        "instrument_mismatch": INSTRUMENT_MISMATCH,
        "short_rate_dataset_id": THREE_MONTH_DATASET_ID,
        "ten_year_dataset_id": TEN_YEAR_DATASET_ID,
        "chronology_dataset_id": CHRONOLOGY_DATASET_ID,
        "chronology_source_url": CHRONOLOGY_SOURCE_URL,
        "classification_publication_date": CHRONOLOGY_PUBLICATION_DATE.isoformat(),
        "classification_kind": "reference_classification",
        "chronology_is_yield_vintage": False,
        "horizon_quarters": HORIZON_QUARTERS,
        "contraction_quarter_rule": CONTRACTION_QUARTER_RULE,
        "estimation_last_spread_quarter": ESTIMATION_LAST_SPREAD_QUARTER.isoformat(),
        "evaluation_first_spread_quarter": EVALUATION_FIRST_SPREAD_QUARTER.isoformat(),
        "estimation_quarter_count": len(estimation),
        "estimation_contraction_count": sum(row.contraction for row in estimation),
        "evaluation_quarter_count": len(evaluation),
        "evaluation_contraction_count": sum(row.contraction for row in evaluation),
        "fit_status": "not_estimated",
        "fit_stable": False,
        "fit_failure": None,
        "statsmodels_converged": None,
        "intercept": None,
        "spread_coefficient": None,
        "intercept_standard_error": None,
        "spread_coefficient_standard_error": None,
        "probabilities": [],
        "probabilities_accepted": False,
        "procedure": "statsmodels.discrete.discrete_model.Probit",
        "discrimination_status": "not_computed",
        "auroc": None,
        "discrimination_quarter_count": None,
        "calibration_status": "not_computed",
        "brier_score": None,
        "calibration_intercept": None,
        "calibration_slope": None,
        "calibration_quarter_count": None,
        "metric_note": None,
    }


def _record_evaluation_metrics(
    payload: dict[str, object],
    probabilities: list[dict[str, object]],
) -> None:
    evaluation = tuple(row for row in probabilities if row["window"] == "evaluation")
    if not evaluation:
        payload["metric_note"] = "evaluation window has no complete spread quarter"
        return
    labels = {int(row["nber_contraction"]) for row in evaluation}
    payload["discrimination_quarter_count"] = len(evaluation)
    payload["calibration_quarter_count"] = len(evaluation)
    if labels != {0, 1}:
        payload["metric_note"] = (
            "evaluation window does not contain both a contraction quarter and an expansion quarter"
        )
        return
    scored = [(float(row["probability"]), int(row["nber_contraction"])) for row in evaluation]
    payload["discrimination_status"] = "computed"
    payload["auroc"] = _text(_auroc(scored))
    payload["brier_score"] = _text(sum((prob - label) ** 2 for prob, label in scored) / len(scored))
    slope = _calibration_slope(scored)
    if slope is None:
        payload["calibration_status"] = "not_identified"
        return
    payload["calibration_status"] = "computed"
    payload["calibration_intercept"] = _text(slope[0])
    payload["calibration_slope"] = _text(slope[1])


def _probability_rows(
    rows: tuple[ProbitQuarter, ...],
    intercept: float,
    slope: float,
) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for row in rows:
        probability = float(norm.cdf(intercept + slope * row.spread))
        records.append(
            {
                "spread_quarter": row.spread_quarter.isoformat(),
                "outcome_quarter": row.outcome_quarter.isoformat(),
                "window": row.window,
                "spread": row.spread_text,
                "nber_contraction": row.contraction,
                "probability": _text(probability),
            },
        )
    return records


def _auroc(scored: list[tuple[float, int]]) -> float:
    positives = [prob for prob, label in scored if label == 1]
    negatives = [prob for prob, label in scored if label == 0]
    wins = 0.0
    for positive in positives:
        for negative in negatives:
            if positive > negative:
                wins += 1.0
            elif positive == negative:
                wins += 0.5
    return wins / (len(positives) * len(negatives))


def _calibration_slope(scored: list[tuple[float, int]]) -> tuple[float, float] | None:
    probs = np.array([prob for prob, _label in scored], dtype=float)
    labels = np.array([label for _prob, label in scored], dtype=float)
    if float(np.nanmax(probs) - np.nanmin(probs)) == 0.0:
        return None
    design = np.column_stack([np.ones(len(probs)), probs])
    coef, _residuals, rank, _singular = np.linalg.lstsq(design, labels, rcond=None)
    if rank < 2 or not np.all(np.isfinite(coef)):
        return None
    return float(coef[0]), float(coef[1])


def _both_classes(rows: tuple[ProbitQuarter, ...]) -> bool:
    return {row.contraction for row in rows} == {0, 1}


def _quarter_rows(
    context: MethodContext,
    contractions: frozenset[date],
) -> tuple[tuple[ProbitQuarter, ...], int] | str:
    monthly = _monthly_spreads(context)
    if isinstance(monthly, str):
        return monthly
    by_quarter: dict[date, dict[date, tuple[Decimal, tuple[str, str]]]] = {}
    for month, value, observation_id in monthly:
        quarter = _quarter_start(month)
        by_quarter.setdefault(quarter, {})[month] = (value, observation_id)
    rows: list[ProbitQuarter] = []
    omitted = 0
    for quarter in sorted(by_quarter):
        months = (
            quarter,
            _add_months(quarter, 1),
            _add_months(quarter, 2),
        )
        present = by_quarter[quarter]
        if any(month not in present for month in months):
            omitted += 1
            continue
        if any(month > context.evaluation_period for month in months):
            omitted += 1
            continue
        window = _window_for(quarter)
        if window is None:
            continue
        values = [present[month][0] for month in months]
        mean = sum(values, Decimal(0)) / Decimal(3)
        outcome = _add_quarters(quarter, HORIZON_QUARTERS)
        observation_ids = tuple(
            observation_id for month in months for observation_id in present[month][1]
        )
        rows.append(
            ProbitQuarter(
                spread_quarter=quarter,
                outcome_quarter=outcome,
                spread=float(mean),
                spread_text=format(mean, "f"),
                contraction=1 if outcome in contractions else 0,
                window=window,
                observation_ids=observation_ids,
            ),
        )
    return tuple(rows), omitted


def _monthly_spreads(
    context: MethodContext,
) -> tuple[tuple[date, Decimal, tuple[str, str]], ...] | str:
    ten_year = context.inputs_by_dataset.get(TEN_YEAR_DATASET_ID, {})
    three_month = context.inputs_by_dataset.get(THREE_MONTH_DATASET_ID, {})
    if not ten_year or not three_month:
        return "missing constant-maturity yield"
    rows: list[tuple[date, Decimal, tuple[str, str]]] = []
    for period in sorted(set(ten_year) & set(three_month)):
        if period > context.evaluation_period:
            continue
        long_rate = _eligible(ten_year[period], TEN_YEAR_DATASET_ID)
        short_rate = _eligible(three_month[period], THREE_MONTH_DATASET_ID)
        if long_rate is None or short_rate is None:
            continue
        rows.append(
            (
                period,
                long_rate.decimal_value() - short_rate.decimal_value(),
                (long_rate.observation_id, short_rate.observation_id),
            ),
        )
    if not rows:
        return "missing constant-maturity yield"
    return tuple(rows)


def _eligible(observation: EconomicObservation, dataset_id: str) -> EconomicObservation | None:
    if observation.dataset_id != dataset_id:
        return None
    if observation.dataset_id == FEDERAL_FUNDS_DATASET_ID:
        return None
    if observation.series_provenance != SeriesProvenance.LATEST_REVISED:
        return None
    if observation.frequency != Frequency.MONTHLY:
        return None
    try:
        observation.decimal_value()
    except (InvalidOperation, ValueError):
        return None
    return observation


def _window_for(quarter: date) -> str | None:
    if quarter <= ESTIMATION_LAST_SPREAD_QUARTER:
        return "estimation"
    if quarter >= EVALUATION_FIRST_SPREAD_QUARTER:
        return "evaluation"
    return None


def _result(
    fitted: dict[str, object],
    quarters: tuple[ProbitQuarter, ...],
) -> MethodExecutionResult:
    observation_ids = tuple(
        sorted({item for row in quarters for item in row.observation_ids}),
    )
    status = str(fitted["fit_status"])
    if fitted["fit_stable"] is True:
        interpretation = (
            "The four-quarter probit was estimated on the predeclared window and "
            f"scored on the later window. {_NOT_REAL_TIME} {INSTRUMENT_MISMATCH}"
        )
    else:
        interpretation = (
            f"The four-quarter probit was not accepted ({status}). "
            "The estimation and evaluation windows were not widened. "
            f"{_NOT_REAL_TIME} {INSTRUMENT_MISMATCH}"
        )
    return MethodExecutionResult(
        sufficiency="sufficient",
        calculation=fitted,
        observation_ids=observation_ids,
        assumptions=_assumptions(),
        limitations=_limitations(fitted),
        missing_reason=None,
        statistical_interpretation=interpretation,
        causal_hypothesis="No causal mechanism is established.",
        investment_implication="no_action",
        narrative=(f"{interpretation} publication_allowed is false."),
    )


def _assumptions() -> tuple[str, ...]:
    return (
        "The outcome is the NBER quarterly classification published on 14 March 2023.",
        CONTRACTION_QUARTER_RULE,
        "The horizon is four quarters.",
        "The spread is the quarterly mean of the monthly 10-year constant-maturity "
        "yield minus the monthly 3-month constant-maturity yield.",
        "A quarter with a missing month is omitted. No month is interpolated.",
        "Estimation uses spread quarters through 2005 Q4. Evaluation uses spread "
        "quarters from 2006 Q1 onward. Coefficients are not refit on the evaluation window.",
        INSTRUMENT_MISMATCH,
        "The chronology is a reference classification. It is not a vintage of the yields.",
    )


def _limitations(fitted: dict[str, object]) -> tuple[str, ...]:
    limits = [
        "publication_allowed is false.",
        _NOT_REAL_TIME,
        INSTRUMENT_MISMATCH,
        "Quarters after the last published trough are not contraction quarters on "
        "the 14 March 2023 chronology, because that page has no later peak.",
        "An unstable or unidentified fit is stored. The windows are not widened.",
    ]
    failure = fitted["fit_failure"]
    if isinstance(failure, str):
        limits.append(failure)
    note = fitted["metric_note"]
    if isinstance(note, str):
        limits.append(note)
    return tuple(limits)


def _insufficient(reason: str) -> MethodExecutionResult:
    return MethodExecutionResult(
        sufficiency="insufficient",
        calculation=None,
        observation_ids=(),
        assumptions=(),
        limitations=(
            "publication_allowed is false.",
            _NOT_REAL_TIME,
            INSTRUMENT_MISMATCH,
        ),
        missing_reason=reason,
        statistical_interpretation="The probit was not estimated.",
        causal_hypothesis="No causal mechanism is established.",
        investment_implication="insufficient_evidence",
        narrative=f"Probit incomplete. Reason: {reason} publication_allowed is false.",
    )


def _require_date(value: str, field: str) -> date:
    parsed = _optional_date(value, field)
    if parsed is None:
        raise ChronologyError(f"the chronology {field} is missing")
    return parsed


def _require_month(value: str, field: str) -> date:
    parsed = _require_date(value, field)
    if parsed.day != 1:
        raise ChronologyError(f"the chronology {field} is not stored on the first of the month")
    return parsed


def _require_quarter(value: str, field: str) -> date:
    parsed = _require_month(value, field)
    if parsed.month not in {1, 4, 7, 10}:
        raise ChronologyError(f"the chronology {field} is not a quarter start")
    return parsed


def _optional_month(value: str, field: str) -> date | None:
    parsed = _optional_date(value, field)
    if parsed is not None and parsed.day != 1:
        raise ChronologyError(f"the chronology {field} is not stored on the first of the month")
    return parsed


def _optional_quarter(value: str, field: str) -> date | None:
    parsed = _optional_month(value, field)
    if parsed is not None and parsed.month not in {1, 4, 7, 10}:
        raise ChronologyError(f"the chronology {field} is not a quarter start")
    return parsed


def _optional_date(value: str, field: str) -> date | None:
    text = value.strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError as exc:
        raise ChronologyError(f"the chronology {field} is not a date") from exc


def _quarter_start(month: date) -> date:
    quarter_month = ((month.month - 1) // 3) * 3 + 1
    return date(month.year, quarter_month, 1)


def _add_months(anchor: date, count: int) -> date:
    index = anchor.year * 12 + (anchor.month - 1) + count
    return date(index // 12, index % 12 + 1, 1)


def _add_quarters(anchor: date, count: int) -> date:
    return _add_months(anchor, 3 * count)


def _text(value: float) -> str:
    return format(value, ".12g")
