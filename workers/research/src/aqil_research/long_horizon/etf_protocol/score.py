"""Score the frozen grid from caller-supplied anchor values.

This module does not read a database and does not fit a logistic, probit,
or regularized model.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from aqil_research.long_horizon.etf_protocol.rules import (
    Score,
    assert_effect_null,
    assert_pair_status,
    benjamini_hochberg,
    binary_flag,
    conditional_frequency,
    conjunction_status,
    control_increment_status,
    method_refusal,
    outcome_flag,
    promotion_decision,
    search_refusal,
    spearman,
)
from aqil_research.long_horizon.etf_protocol.specification import (
    PRIMARY_CONTROL,
    PRIMARY_HORIZON,
    PROTOCOL,
    SEARCH_REFUSAL_REASON,
    ProtocolError,
    TrialKey,
)


@dataclass(frozen=True)
class AnchorState:
    session: date
    values: dict[str, Decimal | None]
    outcomes: dict[str, Decimal | None]
    classes: dict[str, str | None]
    volatility_median: Decimal | None


@dataclass(frozen=True)
class TrialRecord:
    key: TrialKey
    effect: str | None
    result: str | None
    refusal: str | None
    p_value: str | None
    result_status: str | None
    detail: str


@dataclass(frozen=True)
class DossierScore:
    records: tuple[TrialRecord, ...]
    status: str
    bh_tested: int
    bh_flagged: int
    class_counts: dict[str, int]
    conjunction_counts: dict[str, int]
    policy: str


def _conjunction_rule() -> dict[str, object]:
    rule = PROTOCOL["conjunction"]
    if not isinstance(rule, dict):
        raise ProtocolError("the conjunction rule is missing")
    return rule


def _complete(
    anchors: Sequence[AnchorState], feature: str, horizon: str
) -> list[tuple[Decimal, Decimal]]:
    pairs: list[tuple[Decimal, Decimal]] = []
    for anchor in anchors:
        predictor = anchor.values.get(feature)
        outcome = anchor.outcomes.get(horizon)
        if predictor is None or outcome is None:
            continue
        pairs.append((predictor, outcome))
    return pairs


def _binary_pairs(
    anchors: Sequence[AnchorState],
    feature: str,
    horizon: str,
    outcome: str,
) -> tuple[list[bool], list[bool], bool]:
    flags: list[bool] = []
    labels: list[bool] = []
    any_outcome = False
    for anchor in anchors:
        raw = anchor.outcomes.get(horizon)
        if raw is None:
            continue
        any_outcome = True
        flag = binary_flag(feature, anchor.values.get(feature))
        label = outcome_flag(outcome, raw)
        if flag is None or label is None:
            continue
        flags.append(flag)
        labels.append(label)
    return flags, labels, any_outcome


def _any_outcome(anchors: Sequence[AnchorState], horizon: str) -> bool:
    return any(anchor.outcomes.get(horizon) is not None for anchor in anchors)


def _spearman_record(
    key: TrialKey,
    anchors: Sequence[AnchorState],
) -> tuple[Score, str]:
    if not _any_outcome(anchors, key.horizon_label):
        return Score(None, None, "censored_horizon"), "No complete outcome at this horizon."
    raw_pairs = _complete(anchors, key.feature, key.horizon_label)
    if key.outcome == "excess":
        scored = spearman(raw_pairs)
        return scored, f"Complete pairs {len(raw_pairs)}."
    labelled: list[tuple[Decimal, Decimal]] = []
    for predictor, outcome in raw_pairs:
        flag = outcome_flag(key.outcome, outcome)
        if flag is None:
            continue
        labelled.append((predictor, Decimal(int(flag))))
    scored = spearman(labelled)
    return scored, f"Complete pairs {len(labelled)}."


def _frequency_record(key: TrialKey, anchors: Sequence[AnchorState]) -> tuple[Score, str]:
    flags, labels, any_outcome = _binary_pairs(anchors, key.feature, key.horizon_label, key.outcome)
    if not any_outcome:
        return Score(None, None, "censored_horizon"), "No complete outcome at this horizon."
    scored = conditional_frequency(flags, labels)
    return scored, f"Complete pairs {len(flags)}. Non-events stay in the denominator."


def _conjunction_counts(anchors: Sequence[AnchorState]) -> dict[str, int]:
    rule = _conjunction_rule()
    magnitude = Decimal(str(rule["drawdown_magnitude"]))
    eligible = pair_count = pair_advances = 0
    drawdown_count = drawdown_advances = 0
    volatility_count = volatility_advances = 0
    advances = 0
    for anchor in anchors:
        outcome = anchor.outcomes.get(PRIMARY_HORIZON)
        drawdown = anchor.values.get("drawdown_252")
        volatility = anchor.values.get("volatility_63")
        if (
            outcome is None
            or drawdown is None
            or volatility is None
            or anchor.volatility_median is None
        ):
            continue
        eligible += 1
        advance = outcome >= Decimal("0.10")
        if advance:
            advances += 1
        drawdown_on = drawdown <= -magnitude
        volatility_on = volatility > anchor.volatility_median
        if drawdown_on:
            drawdown_count += 1
            drawdown_advances += int(advance)
        if volatility_on:
            volatility_count += 1
            volatility_advances += int(advance)
        if drawdown_on and volatility_on:
            pair_count += 1
            pair_advances += int(advance)
    return {
        "eligible": eligible,
        "pair_count": pair_count,
        "pair_advances": pair_advances,
        "drawdown_count": drawdown_count,
        "drawdown_advances": drawdown_advances,
        "volatility_count": volatility_count,
        "volatility_advances": volatility_advances,
        "advances": advances,
    }


def _status_from_counts(counts: Mapping[str, int]) -> str:
    status = conjunction_status(
        eligible=counts["eligible"],
        pair_count=counts["pair_count"],
        pair_advances=counts["pair_advances"],
        drawdown_count=counts["drawdown_count"],
        drawdown_advances=counts["drawdown_advances"],
        volatility_count=counts["volatility_count"],
        volatility_advances=counts["volatility_advances"],
        advances=counts["advances"],
    )
    assert_pair_status(status)
    return status


def _control_status(records: Sequence[TrialRecord]) -> str:
    control: TrialRecord | None = None
    candidates: list[TrialRecord] = []
    for record in records:
        key = record.key
        if (
            key.statistic != "spearman"
            or key.horizon_label != PRIMARY_HORIZON
            or key.outcome != "excess"
        ):
            continue
        if key.feature == PRIMARY_CONTROL:
            control = record
        elif key.kind == "score":
            candidates.append(record)
    if control is None or control.effect is None:
        return "insufficient_data"
    control_abs = abs(Decimal(control.effect))
    estimated = False
    beats = False
    for record in candidates:
        if record.effect is None:
            continue
        estimated = True
        if abs(Decimal(record.effect)) - control_abs > 0:
            beats = True
    status = control_increment_status(
        control_estimated=True,
        any_candidate_beats_control=beats,
        any_candidate_estimated=estimated,
    )
    assert_pair_status(status)
    return status


def _class_counts(anchors: Sequence[AnchorState]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for anchor in anchors:
        label = anchor.classes.get(PRIMARY_HORIZON)
        if label is None:
            counts["censored"] = counts.get("censored", 0) + 1
            continue
        counts[label] = counts.get(label, 0) + 1
    return counts


def score_dossier(
    keys: Sequence[TrialKey],
    anchors: Sequence[AnchorState],
    *,
    method_replay: Mapping[str, str],
    citations: Mapping[str, str],
    kind: str,
) -> DossierScore:
    """Return one record per declared key. Refusals keep a null effect."""
    counts = _conjunction_counts(anchors) if kind == "single" else None
    single_status = _status_from_counts(counts) if counts is not None else None
    built: list[TrialRecord] = []
    for key in keys:
        status: str | None = None
        if key.kind == "method_refusal":
            score = method_refusal(method_replay[key.feature])
            assert_effect_null(score)
            detail = "Inventory only. No historical method output was written."
        elif key.kind == "search_refusal":
            score = search_refusal()
            assert_effect_null(score)
            detail = f"Named in the protocol and not estimated. Refusal {SEARCH_REFUSAL_REASON}."
        elif key.kind == "citation":
            text = citations.get(key.feature)
            if text is None:
                score = Score(None, None, "not_in_stored_evidence")
                detail = "The stored evidence has no row for this citation."
            else:
                score = Score(None, text, None)
                detail = "Cited from stored evidence. Not re-estimated."
        elif key.kind == "conjunction":
            if counts is None or single_status is None:
                raise ProtocolError("the conjunction is only scored for one symbol")
            status = single_status
            score = Score(None, status, None)
            detail = "Predeclared conjunction. The effect is the status, not a fitted coefficient."
        elif key.statistic == "spearman":
            score, detail = _spearman_record(key, anchors)
        elif key.statistic == "conditional_frequency":
            score, detail = _frequency_record(key, anchors)
        else:
            raise ProtocolError(f"{key.kind} is not a frozen trial kind")
        if score.refusal is not None:
            assert_effect_null(score)
        built.append(
            TrialRecord(
                key,
                score.effect,
                score.result,
                score.refusal,
                score.p_value,
                status,
                detail,
            )
        )
    if kind == "pair":
        dossier_status = _control_status(built)
        assert_pair_status(dossier_status)
    else:
        if single_status is None:
            raise ProtocolError("a single-name dossier has no conjunction status")
        dossier_status = single_status
    tested = [
        index
        for index, record in enumerate(built)
        if record.key.statistic == "spearman"
        and record.key.horizon_label == PRIMARY_HORIZON
        and record.p_value is not None
    ]
    flags = benjamini_hochberg([built[index].p_value or "1" for index in tested])
    flagged = 0
    for flag, index in zip(flags, tested, strict=True):
        if not flag:
            continue
        flagged += 1
        record = built[index]
        built[index] = TrialRecord(
            record.key,
            record.effect,
            record.result,
            record.refusal,
            record.p_value,
            record.result_status,
            record.detail + " Benjamini-Hochberg diagnostic flag. It cannot promote a claim.",
        )
    policy = promotion_decision(
        point_in_time=False,
        uninspected_evaluation=False,
        incremental_information=False,
    )
    if policy != "no_policy_registered":
        raise ProtocolError("this inspected history must not register a policy")
    return DossierScore(
        tuple(built),
        dossier_status,
        len(tested),
        flagged,
        _class_counts(anchors) if kind == "pair" else {},
        counts or {},
        policy,
    )
