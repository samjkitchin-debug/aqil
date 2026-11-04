"""Descriptive associations. A model is fit only under the frozen sample rule."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from aqil_research.long_horizon.etf_protocol.rules import (
    _p_value,
    _pearson,
    benjamini_hochberg,
    conditional_frequency,
    spearman,
)
from aqil_research.long_horizon.money import decimal_text
from aqil_research.long_horizon.vwra_discovery.specification import (
    DECLINE_MAXIMUM,
    DRAWDOWN_SPLIT,
    LOGISTIC_DECISION_POINTS,
    LOGISTIC_NON_OVERLAPPING,
    NON_OVERLAP_SESSION_GAP,
    RATE_DATASETS,
)


@dataclass(frozen=True)
class Association:
    result_text: str | None
    refusal_reason: str | None
    p_value_text: str | None
    sample_count: int
    detail: str


def parse_decimal(value: str | None) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(value)
    except ArithmeticError:
        return None


def split_kind(feature_id: str, unit: str) -> str:
    """A predeclared split. A level has none, so no median is invented."""
    if feature_id.startswith("drawdown_"):
        return "drawdown_0_10"
    if feature_id.startswith(("volatility_", "downside_volatility_", "trend_persistence")):
        return "none"
    if feature_id.endswith((":persistence", ":trailing_percentile", ":level")):
        return "none"
    if unit in {"probability", "share", "months", "mae", "adf_statistic", "cusum", "correlation"}:
        return "none"
    if "lower_mean" in feature_id:
        return "none"
    if feature_id.endswith(":phase") or feature_id.endswith(
        (
            ":difference",
            ":percent_change",
            ":year_on_year",
            ":acceleration",
            ":trailing_standardisation",
        )
    ):
        return "sign"
    if feature_id.startswith(("trailing_return", "relative_performance", "recovery_")):
        return "sign"
    if unit in {
        "percentage_points",
        "percent",
        "ratio",
        "log_growth",
        "spread_percentage_points",
        "coincident_factor",
        "percent_per_year",
        "percent_net_tightening",
    }:
        return "sign"
    return "none"


def atlas_unit(feature_id: str) -> str:
    dataset = feature_id.split(":", 1)[0]
    if feature_id.endswith((":percent_change", ":year_on_year", ":acceleration")):
        return "ratio"
    if feature_id.endswith(":difference"):
        if dataset in RATE_DATASETS:
            return "percentage_points"
        return "level_difference"
    if feature_id.endswith(":trailing_standardisation"):
        return "standardised"
    if feature_id.startswith("trailing_return") or feature_id.startswith("relative_"):
        return "ratio"
    if feature_id.startswith("drawdown_") or feature_id.startswith("recovery_"):
        return "ratio"
    if feature_id.startswith("volatility_"):
        return "ratio"
    return "stored"


def positive_flag(value: Decimal, kind: str) -> bool | None:
    if kind == "none":
        return None
    if kind == "sign":
        return value > 0
    if kind == "negative":
        return value < 0
    if kind == "drawdown_0_10":
        return value <= Decimal(DRAWDOWN_SPLIT)
    raise ValueError(f"unknown split {kind}")


def rank_association(pairs: list[tuple[Decimal, Decimal]]) -> Association:
    score = spearman(pairs)
    detail = (
        f"n={len(pairs)}. Overlapping month-ends are not independent trials. "
        "The rank coefficient is descriptive."
    )
    if score.refusal:
        return Association(None, score.refusal, None, len(pairs), detail)
    return Association(score.result, None, score.p_value, len(pairs), detail)


def linear_association(pairs: list[tuple[Decimal, Decimal]]) -> Association:
    detail = (
        f"n={len(pairs)}. Pearson uses the anchor set. "
        "Overlapping month-ends are not independent trials."
    )
    if len(pairs) < 3:
        return Association(None, "insufficient_effective_sample", None, len(pairs), detail)
    rho = _pearson([item[0] for item in pairs], [item[1] for item in pairs])
    if rho is None:
        return Association(None, "variance is zero", None, len(pairs), detail)
    return Association(decimal_text(rho), None, _p_value(rho, len(pairs)), len(pairs), detail)


def frequency_association(flags: list[bool], outcomes: list[bool], label: str) -> Association:
    true_count = sum(1 for flag in flags if flag)
    false_count = len(flags) - true_count
    outcome_true = sum(1 for flag, outcome in zip(flags, outcomes, strict=True) if flag and outcome)
    outcome_false = sum(
        1 for flag, outcome in zip(flags, outcomes, strict=True) if not flag and outcome
    )
    detail = (
        f"{label}. flag_true={true_count}, flag_false={false_count}, "
        f"outcome_when_true={outcome_true}, outcome_when_false={outcome_false}. "
        "Overlapping month-ends are not independent trials."
    )
    if not flags or true_count == 0 or false_count == 0:
        return Association(None, "one conditional side is empty", None, len(flags), detail)
    score = conditional_frequency(flags, outcomes)
    if score.refusal:
        return Association(None, score.refusal, None, len(flags), detail)
    return Association(score.result, None, None, len(flags), detail)


def thin_indexes(indexes: list[int], gap: int = NON_OVERLAP_SESSION_GAP) -> list[int]:
    """Keep a session only when it is at least `gap` sessions after the previous keep."""
    kept: list[int] = []
    last: int | None = None
    for index in indexes:
        if last is None or index - last >= gap:
            kept.append(index)
            last = index
    return kept


def model_allowed(decision_points: int, non_overlapping: int) -> bool:
    return (
        decision_points >= LOGISTIC_DECISION_POINTS and non_overlapping >= LOGISTIC_NON_OVERLAPPING
    )


def fit_binary(kind: str, features: list[Decimal], labels: list[int]) -> Association:
    """Logistic or probit. A separation or a failed fit is stored as a failure."""
    detail = (
        f"n={len(labels)}. Fit on the non-overlapping subset only. "
        "This coefficient is not a confidence score and is not a strategy."
    )
    if len(set(labels)) < 2:
        return Association(None, "not_estimable_effective_sample", None, len(labels), detail)
    if len(labels) < LOGISTIC_NON_OVERLAPPING:
        return Association(None, "not_estimable_effective_sample", None, len(labels), detail)
    try:
        import statsmodels.api as sm

        exog = sm.add_constant([float(item) for item in features], has_constant="add")
        model = sm.Logit(labels, exog) if kind == "logistic" else sm.Probit(labels, exog)
        fitted = model.fit(disp=False, maxiter=100)
    except Exception as exc:
        return Association(None, f"fit_failed: {exc}", None, len(labels), detail)
    converged = True
    retvals = getattr(fitted, "mle_retvals", None)
    if isinstance(retvals, dict):
        converged = bool(retvals.get("converged", False))
    if not converged:
        return Association(None, "fit_failed: not converged", None, len(labels), detail)
    params = list(fitted.params)
    if len(params) < 2:
        return Association(None, "fit_failed: no slope", None, len(labels), detail)
    slope = Decimal(str(params[1]))
    bse = list(getattr(fitted, "bse", []))
    pvalues = list(getattr(fitted, "pvalues", []))
    extra = ""
    if len(bse) > 1 and len(pvalues) > 1:
        extra = f" model_standard_error={bse[1]} model_p_value={pvalues[1]}."
    return Association(decimal_text(slope), None, None, len(labels), detail + extra)


def decline_label(value: str) -> bool:
    return Decimal(value) <= Decimal(DECLINE_MAXIMUM)


def bh_flags(p_values: list[str]) -> tuple[bool, ...]:
    return benjamini_hochberg(p_values)


def session_on_or_before(dates: tuple[date, ...], day: date) -> int | None:
    eligible = [index for index, session in enumerate(dates) if session <= day]
    if not eligible:
        return None
    return eligible[-1]
