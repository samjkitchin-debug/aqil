"""VWRA month-end dossier. Outcomes stay off the state rows."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from aqil_research.long_horizon.money import decimal_text, sha256_document
from aqil_research.long_horizon.state_atlas.features import trailing_return
from aqil_research.long_horizon.state_atlas.specification import SESSION_STEPS
from aqil_research.long_horizon.vwra_discovery.guards import assert_state_feature, latest_period
from aqil_research.long_horizon.vwra_discovery.market import downside_volatility, trend_persistence
from aqil_research.long_horizon.vwra_discovery.replay import MethodRun, StoredPoint
from aqil_research.long_horizon.vwra_discovery.sequence import (
    deceleration_flags,
    sequence_counts,
    sequence_flags,
)
from aqil_research.long_horizon.vwra_discovery.specification import (
    ADVANCE_MINIMUM,
    DECLINE_MAXIMUM,
    EPISODE_GROUP,
    INTERSECTION_PAIRS,
    LOGISTIC_NON_OVERLAPPING,
    NOT_A_MONTHLY_STATE,
    PRE_EVENT_STEPS,
    SEQUENCE,
    VWRA_FIRST_SESSION,
    intersection_finding,
    method_finding,
    univariate_finding,
)
from aqil_research.long_horizon.vwra_discovery.statistics import (
    Association,
    atlas_unit,
    bh_flags,
    decline_label,
    fit_binary,
    frequency_association,
    linear_association,
    model_allowed,
    parse_decimal,
    positive_flag,
    rank_association,
    session_on_or_before,
    split_kind,
    thin_indexes,
)

EPISODE_ORDER = (
    "advances",
    "declines",
    "bulls",
    "bears",
    "recoveries",
    "failed_recoveries",
    "reversals",
    "volatility_transitions",
    "stagnation",
)


@dataclass(frozen=True)
class Anchor:
    anchor_id: str
    session: date


@dataclass(frozen=True)
class Outcome:
    status: str
    value_text: str | None
    labelled_advance: bool | None


@dataclass(frozen=True)
class MarketEvent:
    event_id: str
    definition_id: str
    family: str
    start_date: date
    end_date: date


@dataclass
class Trial:
    experiment_id: str
    feature: str
    paired_feature: str | None
    statistic: str
    outcome: str
    sample_count: int
    non_overlapping_count: int
    result_text: str | None
    refusal_reason: str | None
    p_value_text: str | None
    finding_class: str
    bh_diagnostic: bool | None
    detail: str
    trial_id: str = ""

    def canonical(self) -> dict[str, object]:
        return {
            "trial_id": self.trial_id,
            "experiment_id": self.experiment_id,
            "feature": self.feature,
            "paired_feature": self.paired_feature,
            "statistic": self.statistic,
            "outcome": self.outcome,
            "sample_count": self.sample_count,
            "non_overlapping_count": self.non_overlapping_count,
            "result_text": self.result_text,
            "refusal_reason": self.refusal_reason,
            "p_value_text": self.p_value_text,
            "finding_class": self.finding_class,
            "bh_diagnostic": self.bh_diagnostic,
            "detail": self.detail,
        }


@dataclass
class AnchorFeature:
    anchor_id: str
    feature_id: str
    anchor_session: date
    period_end: date
    value_text: str | None
    state_label: str | None
    unit: str
    source: str
    method_id: str | None
    reconstruction: str


@dataclass
class CaseRow:
    episode_group: str
    family: str
    event_id: str | None
    anchor_session: date | None
    window_steps: int | None
    value_text: str | None
    sample_count: int | None
    detail: str
    case_id: str = ""


@dataclass
class Finding:
    finding_id: str
    hypothesis_id: str
    experiment_id: str
    finding_class: str
    statement: str


@dataclass
class Dossier:
    features: list[AnchorFeature]
    trials: list[Trial]
    cases: list[CaseRow]
    findings: list[Finding]
    coverage: dict[str, object]
    sequence: dict[str, object]
    runs: list[MethodRun] = field(repr=False)


def build_dossier(
    *,
    anchors: list[Anchor],
    atlas: dict[tuple[str, str], tuple[str, str, str]],
    outcomes: dict[str, Outcome],
    events: list[MarketEvent],
    sessions: tuple[date, ...],
    closes: tuple[Decimal, ...],
    runs: list[MethodRun],
    macro_periods: int,
    macro_series_periods: int,
) -> Dossier:
    """Assemble the dossier from stored rows and reconstructed points."""
    usable = [anchor for anchor in anchors if anchor.session >= VWRA_FIRST_SESSION]
    usable.sort(key=lambda item: item.session)
    index_by_session = {session: index for index, session in enumerate(sessions)}
    features = _added_market(usable, sessions, closes, index_by_session)
    features.extend(_joined_methods(usable, runs))
    panel, units, skipped = _panel(usable, atlas, features)
    trials: list[Trial] = []
    trials.extend(_method_trials(runs))
    trials.extend(_skipped_trials(skipped))
    labelled = [anchor for anchor in usable if _observed(outcomes.get(anchor.anchor_id))]
    thinned = _thinned(labelled, index_by_session)
    allowed = model_allowed(len(labelled), len(thinned))
    non_overlapping = len(thinned)
    trials.extend(
        _univariate(usable, panel, units, outcomes, labelled, thinned, allowed, non_overlapping)
    )
    trials.extend(_intersections(usable, panel, outcomes, non_overlapping, runs))
    sequence, sequence_trials = _sequence(usable, panel, outcomes, non_overlapping)
    trials.extend(sequence_trials)
    _apply_bh(trials)
    cases = _casebook(usable, events, sessions, closes, panel)
    findings = _findings(runs, trials, sequence)
    _assign_ids(trials, cases)
    coverage = _coverage(
        usable,
        events,
        runs,
        trials,
        labelled,
        non_overlapping,
        macro_periods,
        macro_series_periods,
        sequence,
    )
    return Dossier(features, trials, cases, findings, coverage, sequence, runs)


def _observed(outcome: Outcome | None) -> bool:
    return outcome is not None and outcome.status == "observed" and outcome.value_text is not None


def _added_market(
    anchors: list[Anchor],
    sessions: tuple[date, ...],
    closes: tuple[Decimal, ...],
    index_by_session: dict[date, int],
) -> list[AnchorFeature]:
    rows: list[AnchorFeature] = []
    for anchor in anchors:
        if anchor.session not in index_by_session:
            continue
        index = index_by_session[anchor.session]
        for steps in SESSION_STEPS.values():
            downside = downside_volatility(closes, index, steps)
            persistence = trend_persistence(closes, index, steps)
            if downside is not None:
                rows.append(
                    _feature(
                        anchor,
                        f"downside_volatility_{steps}",
                        anchor.session,
                        downside,
                        None,
                        "ratio",
                        "added_transform",
                        None,
                        "stored_sessions",
                    )
                )
            if persistence is not None:
                rows.append(
                    _feature(
                        anchor,
                        f"trend_persistence_{steps}",
                        anchor.session,
                        persistence,
                        None,
                        "sessions",
                        "added_transform",
                        None,
                        "stored_sessions",
                    )
                )
    return rows


def _joined_methods(anchors: list[Anchor], runs: list[MethodRun]) -> list[AnchorFeature]:
    grouped: dict[tuple[str, str], list[StoredPoint]] = defaultdict(list)
    reconstruction: dict[str, str] = {}
    for run in runs:
        if run.status != "succeeded" or run.method_id in NOT_A_MONTHLY_STATE:
            continue
        reconstruction[run.method_id] = run.reconstruction or "retrospective_reconstruction"
        for point in run.points:
            if point.value_text is None:
                continue
            grouped[(run.method_id, point.series_key)].append(point)
    rows: list[AnchorFeature] = []
    for anchor in anchors:
        for (method_id, series_key), points in grouped.items():
            ends = tuple(point.period_end for point in points)
            chosen_end = latest_period(ends, anchor.session)
            if chosen_end is None:
                continue
            chosen = max(
                (point for point in points if point.period_end == chosen_end),
                key=lambda point: point.period_start,
            )
            rows.append(
                _feature(
                    anchor,
                    f"method:{method_id}:{series_key}",
                    chosen.period_end,
                    chosen.value_text,
                    chosen.state_label,
                    chosen.unit,
                    "reconstructed_method",
                    method_id,
                    reconstruction[method_id],
                )
            )
    return rows


def _feature(
    anchor: Anchor,
    feature_id: str,
    period_end: date,
    value_text: str | None,
    state_label: str | None,
    unit: str,
    source: str,
    method_id: str | None,
    reconstruction: str,
) -> AnchorFeature:
    assert_state_feature(feature_id)
    if period_end > anchor.session:
        raise ValueError("a later period cannot be a state at this anchor")
    return AnchorFeature(
        anchor.anchor_id,
        feature_id,
        anchor.session,
        period_end,
        value_text,
        state_label,
        unit,
        source,
        method_id,
        reconstruction,
    )


def _panel(
    anchors: list[Anchor],
    atlas: dict[tuple[str, str], tuple[str, str, str]],
    features: list[AnchorFeature],
) -> tuple[dict[str, dict[str, str]], dict[str, str], dict[str, int]]:
    panel: dict[str, dict[str, str]] = {anchor.anchor_id: {} for anchor in anchors}
    units: dict[str, str] = {}
    skipped: dict[str, int] = defaultdict(int)
    for (anchor_id, feature_id), (availability, value, _clock) in atlas.items():
        if anchor_id not in panel or availability != "observed" or value is None:
            continue
        assert_state_feature(feature_id)
        if parse_decimal(value) is None:
            if feature_id.endswith(":direction") or value in {"up", "down", "flat"}:
                skipped[feature_id] += 1
            continue
        panel[anchor_id][feature_id] = value
        units[feature_id] = atlas_unit(feature_id)
    for feature in features:
        if feature.value_text is None:
            continue
        panel[feature.anchor_id][feature.feature_id] = feature.value_text
        units[feature.feature_id] = feature.unit
    return panel, units, skipped


def _skipped_trials(skipped: dict[str, int]) -> list[Trial]:
    trials: list[Trial] = []
    for feature, count in sorted(skipped.items()):
        trials.append(
            _result(
                "LH-E-009",
                feature,
                None,
                "not_continuous",
                "return_126",
                count,
                0,
                None,
                "not a continuous series",
                "insufficient_sample",
                f"Observed direction labels={count}. No score was invented for the label.",
            )
        )
    return trials


def _method_trials(runs: list[MethodRun]) -> list[Trial]:
    trials: list[Trial] = []
    overlaps = 0
    succeeded = [run for run in runs if run.status == "succeeded"]
    for left in range(len(succeeded)):
        for right in range(left + 1, len(succeeded)):
            shared = set(succeeded[left].required_datasets) & set(
                succeeded[right].required_datasets
            )
            if shared:
                overlaps += 1
    for run in runs:
        if run.status == "succeeded":
            detail = (
                f"class={run.method_class}; reconstruction={run.reconstruction}; "
                f"points={len(run.points)}. Not point-in-time and not a signal."
            )
            if run.method_id in NOT_A_MONTHLY_STATE:
                detail += " The summary is not joined to earlier month-ends as a state."
            trials.append(
                _result(
                    "LH-E-008",
                    run.method_id,
                    None,
                    "method_timeline",
                    "not_an_outcome",
                    run.numeric_count,
                    0,
                    str(run.numeric_count),
                    None,
                    "descriptive",
                    detail,
                )
            )
        else:
            trials.append(
                _result(
                    "LH-E-008",
                    run.method_id,
                    None,
                    "method_timeline",
                    "not_an_outcome",
                    0,
                    0,
                    None,
                    run.reason or run.status,
                    "insufficient_sample",
                    f"class={run.method_class}; status={run.status}.",
                )
            )
    trials.append(
        _result(
            "LH-E-008",
            "reconstructed_methods",
            None,
            "shared_input_pairs",
            "not_an_outcome",
            overlaps,
            0,
            str(overlaps),
            None,
            "descriptive",
            "Pairs of reconstructed methods whose required datasets intersect. "
            "independent_confirmation is false.",
        )
    )
    return trials


def _thinned(anchors: list[Anchor], index_by_session: dict[date, int]) -> list[Anchor]:
    ordered = [anchor for anchor in anchors if anchor.session in index_by_session]
    indexes = [index_by_session[anchor.session] for anchor in ordered]
    kept = set(thin_indexes(indexes))
    return [anchor for anchor in ordered if index_by_session[anchor.session] in kept]


def _univariate(
    anchors: list[Anchor],
    panel: dict[str, dict[str, str]],
    units: dict[str, str],
    outcomes: dict[str, Outcome],
    labelled: list[Anchor],
    thinned: list[Anchor],
    allowed: bool,
    non_overlapping: int,
) -> list[Trial]:
    features = sorted({feature for row in panel.values() for feature in row})
    trials: list[Trial] = []
    for feature in features:
        unit = units.get(feature, "stored")
        pairs: list[tuple[Decimal, Decimal]] = []
        advance_flags: list[bool] = []
        decline_flags: list[bool] = []
        feature_flags: list[bool] = []
        kind = split_kind(feature, unit)
        for anchor in labelled:
            raw = panel[anchor.anchor_id].get(feature)
            outcome = outcomes[anchor.anchor_id]
            left = parse_decimal(raw)
            right = parse_decimal(outcome.value_text)
            if left is None or right is None or outcome.labelled_advance is None:
                continue
            pairs.append((left, right))
            flag = positive_flag(left, kind)
            if flag is not None:
                feature_flags.append(flag)
                advance_flags.append(outcome.labelled_advance)
                decline_flags.append(decline_label(outcome.value_text or ""))
        note = f"unit={unit}. reconstruction is retrospective and is not a decision input."
        if "lower_mean" in feature:
            note += " This series is the complement of higher_mean and is not independent."
        if feature.startswith("method:") and "smoothed_" in feature:
            note += " The smoother uses the full sample."
        rank = rank_association(pairs)
        trials.append(
            _from_association(
                "LH-E-009", feature, "spearman", "return_126", non_overlapping, rank, note
            )
        )
        linear = linear_association(pairs)
        trials.append(
            _from_association(
                "LH-E-009", feature, "pearson", "return_126", non_overlapping, linear, note
            )
        )
        if kind == "none":
            trials.append(
                _result(
                    "LH-E-009",
                    feature,
                    None,
                    "conditional_frequency",
                    "advance_126",
                    len(pairs),
                    non_overlapping,
                    None,
                    "no predeclared split",
                    "insufficient_sample",
                    note + f" Complete anchors={len(pairs)}. No median split was applied.",
                )
            )
        else:
            trials.append(
                _from_association(
                    "LH-E-009",
                    feature,
                    "conditional_advance",
                    "advance_126",
                    non_overlapping,
                    frequency_association(feature_flags, advance_flags, "advance"),
                    note,
                )
            )
            trials.append(
                _from_association(
                    "LH-E-009",
                    feature,
                    "conditional_decline",
                    "decline_126",
                    non_overlapping,
                    frequency_association(feature_flags, decline_flags, "decline"),
                    note,
                )
            )
        trials.append(
            _model_trial(feature, thinned, panel, outcomes, allowed, non_overlapping, note)
        )
    return trials


def _model_trial(
    feature: str,
    thinned: list[Anchor],
    panel: dict[str, dict[str, str]],
    outcomes: dict[str, Outcome],
    allowed: bool,
    non_overlapping: int,
    note: str,
) -> Trial:
    values: list[Decimal] = []
    labels: list[int] = []
    for anchor in thinned:
        raw = panel[anchor.anchor_id].get(feature)
        outcome = outcomes.get(anchor.anchor_id)
        left = parse_decimal(raw)
        if left is None or outcome is None or outcome.labelled_advance is None:
            continue
        values.append(left)
        labels.append(1 if outcome.labelled_advance else 0)
    if not allowed or len(labels) < LOGISTIC_NON_OVERLAPPING or len(set(labels)) < 2:
        return _result(
            "LH-E-009",
            feature,
            None,
            "logistic_probit",
            "advance_126",
            len(labels),
            non_overlapping,
            None,
            "not_estimable_effective_sample",
            "insufficient_sample",
            note + " Descriptive rank and frequency rows are stored separately.",
        )
    logistic = fit_binary("logistic", values, labels)
    probit = fit_binary("probit", values, labels)
    if logistic.result_text is None and probit.result_text is None:
        return _result(
            "LH-E-009",
            feature,
            None,
            "logistic_probit",
            "advance_126",
            len(labels),
            non_overlapping,
            None,
            logistic.refusal_reason or probit.refusal_reason,
            "insufficient_sample",
            logistic.detail + " " + probit.detail,
        )
    text = f"logistic={logistic.result_text}; probit={probit.result_text}"
    return _result(
        "LH-E-009",
        feature,
        None,
        "logistic_probit",
        "advance_126",
        len(labels),
        non_overlapping,
        text,
        None,
        "descriptive",
        logistic.detail + " " + probit.detail,
    )


def _intersections(
    anchors: list[Anchor],
    panel: dict[str, dict[str, str]],
    outcomes: dict[str, Outcome],
    non_overlapping: int,
    runs: list[MethodRun],
) -> list[Trial]:
    reasons = {run.method_id: run.reason for run in runs if run.status != "succeeded"}
    trials: list[Trial] = []
    for pair in INTERSECTION_PAIRS:
        left_id = str(pair["left_feature"])
        right_id = str(pair["right_feature"])
        left_values = [panel[anchor.anchor_id].get(left_id) for anchor in anchors]
        right_values = [panel[anchor.anchor_id].get(right_id) for anchor in anchors]
        if not any(left_values) or not any(right_values):
            missing = left_id if not any(left_values) else right_id
            method_id = missing.split(":")[1] if missing.startswith("method:") else ""
            reason = reasons.get(method_id) or f"{missing} is not stored on any VWRA anchor"
            trials.append(
                _result(
                    "LH-E-010",
                    left_id,
                    right_id,
                    "intersection",
                    "advance_126",
                    0,
                    non_overlapping,
                    None,
                    reason,
                    "insufficient_sample",
                    "The pair is skipped because an input is absent. "
                    "No substitute series was used.",
                )
            )
            continue
        both: list[tuple[Decimal, Decimal]] = []
        flags: list[bool] = []
        advances: list[bool] = []
        declines: list[bool] = []
        for anchor in anchors:
            outcome = outcomes.get(anchor.anchor_id)
            left = parse_decimal(panel[anchor.anchor_id].get(left_id))
            right = parse_decimal(panel[anchor.anchor_id].get(right_id))
            if left is None or right is None or not _observed(outcome):
                continue
            assert outcome is not None and outcome.value_text is not None
            both.append((left, right))
            flags.append(
                _pair_flag(left, str(pair["left_sign"]))
                and _pair_flag(right, str(pair["right_sign"]))
            )
            advances.append(bool(outcome.labelled_advance))
            declines.append(decline_label(outcome.value_text))
        detail = (
            f"pair={pair['pair_id']}. independent_confirmation is false. "
            "Overlapping month-ends are not independent trials."
        )
        trials.append(
            _from_association(
                "LH-E-010",
                left_id,
                "spearman_between_legs",
                "not_an_outcome",
                non_overlapping,
                rank_association(both),
                detail,
                right_id,
            )
        )
        trials.append(
            _from_association(
                "LH-E-010",
                left_id,
                "conditional_advance",
                "advance_126",
                non_overlapping,
                frequency_association(flags, advances, "advance"),
                detail,
                right_id,
            )
        )
        trials.append(
            _from_association(
                "LH-E-010",
                left_id,
                "conditional_decline",
                "decline_126",
                non_overlapping,
                frequency_association(flags, declines, "decline"),
                detail,
                right_id,
            )
        )
    return trials


def _pair_flag(value: Decimal, sign: str) -> bool:
    if sign == "positive":
        return value > 0
    if sign == "negative":
        return value < 0
    if sign == "drawdown_0_10":
        return value <= Decimal("-0.10")
    raise ValueError(sign)


def _sequence(
    anchors: list[Anchor],
    panel: dict[str, dict[str, str]],
    outcomes: dict[str, Outcome],
    non_overlapping: int,
) -> tuple[dict[str, object], list[Trial]]:
    inflation = str(SEQUENCE["inflation_feature"])
    momentum = str(SEQUENCE["momentum_feature"])
    yoy = [panel[anchor.anchor_id].get(inflation) for anchor in anchors]
    mom = [panel[anchor.anchor_id].get(momentum) for anchor in anchors]
    slowed = deceleration_flags(yoy)
    confirmed = sequence_flags(yoy, mom)
    moving = [value is not None and Decimal(value) > 0 for value in mom]
    advances = []
    for anchor in anchors:
        outcome = outcomes.get(anchor.anchor_id)
        if not _observed(outcome) or outcome is None:
            advances.append(None)
        else:
            advances.append(bool(outcome.labelled_advance))
    counts = sequence_counts(
        sequence=confirmed,
        deceleration=slowed,
        momentum_positive=moving,
        advances=advances,
    )
    finding = str(counts["finding_class"])
    trials = [
        _count_trial("false_positives", counts, non_overlapping),
        _count_trial("missed_advances", counts, non_overlapping),
        _rate_trial("sequence", "pair_advances", "pair_count", counts, non_overlapping),
        _rate_trial(
            "deceleration",
            "deceleration_advances",
            "deceleration_count",
            counts,
            non_overlapping,
        ),
        _rate_trial("momentum", "momentum_advances", "momentum_count", counts, non_overlapping),
        _result(
            "LH-E-011",
            "SEQ-INF-MOM-001",
            None,
            "conjunction_comparison",
            "advance_126",
            int(counts["eligible"]),
            non_overlapping,
            str(counts["comparison_status"]),
            None,
            finding,
            "The comparison uses the frozen ETF-PROT-001 conjunction floors. "
            "It is not an executable strategy and the thresholds were not retuned.",
        ),
    ]
    return counts, trials


def _count_trial(name: str, counts: dict[str, object], non_overlapping: int) -> Trial:
    return _result(
        "LH-E-011",
        "SEQ-INF-MOM-001",
        None,
        name,
        "advance_126",
        int(counts["eligible"]),
        non_overlapping,
        str(counts[name]),
        None,
        "descriptive",
        "The count uses the frozen sequence. Overlapping month-ends are not independent trials.",
    )


def _rate_trial(
    name: str,
    numerator: str,
    denominator: str,
    counts: dict[str, object],
    non_overlapping: int,
) -> Trial:
    count = int(counts[denominator])
    if count == 0:
        return _result(
            "LH-E-011",
            "SEQ-INF-MOM-001",
            name,
            "advance_rate",
            "advance_126",
            0,
            non_overlapping,
            None,
            "one conditional side is empty",
            "insufficient_sample",
            f"{name} has no month-end in the eligible sample.",
        )
    rate = decimal_text(Decimal(int(counts[numerator])) / Decimal(count))
    return _result(
        "LH-E-011",
        "SEQ-INF-MOM-001",
        name,
        "advance_rate",
        "advance_126",
        count,
        non_overlapping,
        rate,
        None,
        "descriptive",
        f"{name} advance rate on {count} month-ends. Not an independent trial set.",
    )


def _casebook(
    anchors: list[Anchor],
    events: list[MarketEvent],
    sessions: tuple[date, ...],
    closes: tuple[Decimal, ...],
    panel: dict[str, dict[str, str]],
) -> list[CaseRow]:
    rows: list[CaseRow] = []
    for family in EPISODE_GROUP:
        matched = [event for event in events if event.family == family]
        if matched:
            continue
        rows.append(
            CaseRow(
                EPISODE_GROUP[family],
                family,
                None,
                None,
                None,
                None,
                0,
                "No VWRA event is stored for this family.",
            )
        )
    for group in EPISODE_ORDER:
        group_events = [event for event in events if EPISODE_GROUP.get(event.family) == group]
        occupied = [
            anchor.anchor_id
            for anchor in anchors
            if any(event.start_date <= anchor.session <= event.end_date for event in group_events)
        ]
        controls = [anchor for anchor in anchors if anchor.anchor_id not in occupied]
        for event in group_events:
            if event.start_date < VWRA_FIRST_SESSION:
                rows.append(
                    CaseRow(
                        group,
                        event.family,
                        event.event_id,
                        event.start_date,
                        None,
                        None,
                        0,
                        "The event starts before the VWRA listing and is refused.",
                    )
                )
                continue
            index = session_on_or_before(sessions, event.start_date)
            for steps in PRE_EVENT_STEPS:
                value = None if index is None else trailing_return(closes, index, steps).value
                rows.append(
                    CaseRow(
                        group,
                        event.family,
                        event.event_id,
                        event.start_date,
                        steps,
                        value,
                        None if value is None else 1,
                        "Pre-event trailing return from closes on or before the event start.",
                    )
                )
        for steps in PRE_EVENT_STEPS:
            event_values = [
                Decimal(row.value_text)
                for row in rows
                if row.episode_group == group
                and row.window_steps == steps
                and row.value_text is not None
                and row.event_id is not None
            ]
            control_values = []
            feature = f"trailing_return_{steps}"
            for anchor in controls:
                raw = panel[anchor.anchor_id].get(feature)
                parsed = parse_decimal(raw)
                if parsed is not None:
                    control_values.append(parsed)
            rows.append(
                CaseRow(
                    group,
                    group,
                    None,
                    None,
                    steps,
                    _median(event_values),
                    len(event_values),
                    (
                        f"event_count={len(event_values)}; control_count={len(control_values)}; "
                        f"control_median={_median(control_values)}. "
                        "Controls are month-ends outside the event interval, "
                        "not chosen by later returns."
                    ),
                )
            )
    return rows


def _median(values: list[Decimal]) -> str | None:
    if not values:
        return None
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2 == 1:
        return decimal_text(ordered[middle])
    return decimal_text((ordered[middle - 1] + ordered[middle]) / 2)


def _apply_bh(trials: list[Trial]) -> None:
    scored = [trial for trial in trials if trial.statistic == "spearman" and trial.p_value_text]
    flags = bh_flags([trial.p_value_text or "1" for trial in scored])
    flagged = 0
    for trial, flag in zip(scored, flags, strict=True):
        trial.bh_diagnostic = flag
        if trial.finding_class != "descriptive":
            raise ValueError("a BH flag cannot change the finding class")
        if flag:
            flagged += 1
    trials.append(
        _result(
            "LH-E-009",
            "benjamini_hochberg",
            None,
            "bh_flag_count",
            "diagnostic",
            len(scored),
            0,
            str(flagged),
            None,
            "descriptive",
            (
                f"p_values={len(scored)}. The flag count cannot promote a claim. "
                "Overlapping month-ends are not independent trials, "
                "so the p-values are a diagnostic."
            ),
        )
    )


def _findings(
    runs: list[MethodRun],
    trials: list[Trial],
    sequence: dict[str, object],
) -> list[Finding]:
    numeric = sum(1 for run in runs if run.status == "succeeded")
    descriptive = sum(
        1
        for trial in trials
        if trial.experiment_id == "LH-E-009"
        and trial.result_text is not None
        and trial.statistic == "spearman"
    )
    estimated = sum(
        1 for trial in trials if trial.experiment_id == "LH-E-010" and trial.result_text is not None
    )
    method_class = method_finding(numeric)
    univariate_class = univariate_finding(descriptive)
    pair_class = intersection_finding(estimated)
    sequence_class = str(sequence["finding_class"])
    return [
        Finding(
            "DIS-F-008",
            "LH-H-008",
            "LH-E-008",
            method_class,
            (
                f"{numeric} registered methods produced a numerical timeline. "
                "The output is retrospective_reconstruction or retrospective_latest_revised. "
                "It is not point-in-time and it is not an investment signal."
            ),
        ),
        Finding(
            "DIS-F-009",
            "LH-H-009",
            "LH-E-009",
            univariate_class,
            (
                f"{descriptive} features have a stored Spearman coefficient against the later "
                f"126-session return. Advance minimum is {ADVANCE_MINIMUM} and decline maximum "
                f"is {DECLINE_MAXIMUM}. Overlapping month-ends are not independent trials. "
                "Point-in-time eligibility is empty."
            ),
        ),
        Finding(
            "DIS-F-010",
            "LH-H-010",
            "LH-E-010",
            pair_class,
            (
                f"{estimated} intersection rows have a stored result. "
                "A missing input is a refusal. Shared inputs are not independent confirmation."
            ),
        ),
        Finding(
            "DIS-F-011",
            "LH-H-011",
            "LH-E-011",
            sequence_class,
            (
                f"The frozen sequence comparison is {sequence['comparison_status']}. "
                f"False positives {sequence['false_positives']}. "
                f"Missed advances {sequence['missed_advances']}. "
                "The sequence is not an executable strategy."
            ),
        ),
    ]


def _coverage(
    anchors: list[Anchor],
    events: list[MarketEvent],
    runs: list[MethodRun],
    trials: list[Trial],
    labelled: list[Anchor],
    non_overlapping: int,
    macro_periods: int,
    macro_series_periods: int,
    sequence: dict[str, object],
) -> dict[str, object]:
    executed = sum(1 for trial in trials if trial.result_text is not None)
    refused = sum(1 for trial in trials if trial.refusal_reason is not None)
    return {
        "decision_dates": len(anchors),
        "macro_periods": macro_periods,
        "macro_series_periods": macro_series_periods,
        "market_episodes": len(events),
        "outcome_anchors": len(labelled),
        "non_overlapping_126": non_overlapping,
        "declared_trials": len(trials),
        "executed_trials": executed,
        "refused_trials": refused,
        "methods_registered": len(runs),
        "methods_with_numbers": sum(1 for run in runs if run.status == "succeeded"),
        "methods_unavailable": sum(1 for run in runs if run.status == "unavailable"),
        "methods_failed": sum(1 for run in runs if run.status == "failed"),
        "portfolio_simulations": 0,
        "point_in_time_results": 0,
        "sequence_status": sequence["comparison_status"],
        "first_anchor": anchors[0].session.isoformat() if anchors else None,
        "last_anchor": anchors[-1].session.isoformat() if anchors else None,
    }


def _assign_ids(trials: list[Trial], cases: list[CaseRow]) -> None:
    trials.sort(
        key=lambda trial: (
            trial.experiment_id,
            trial.feature,
            trial.paired_feature or "",
            trial.statistic,
            trial.outcome,
        )
    )
    for index, trial in enumerate(trials, start=1):
        trial.trial_id = f"DIS-T-{index:05d}"
        digest = sha256_document(trial.canonical())
        trial.detail = f"row_hash={digest}. " + trial.detail
    for index, case in enumerate(cases, start=1):
        case.case_id = f"DIS-C-{index:05d}"


def _from_association(
    experiment_id: str,
    feature: str,
    statistic: str,
    outcome: str,
    non_overlapping: int,
    association: Association,
    note: str,
    paired: str | None = None,
) -> Trial:
    finding = "descriptive" if association.result_text is not None else "insufficient_sample"
    trial = _result(
        experiment_id,
        feature,
        paired,
        statistic,
        outcome,
        association.sample_count,
        non_overlapping,
        association.result_text,
        association.refusal_reason,
        finding,
        note + " " + association.detail,
    )
    trial.p_value_text = association.p_value_text
    return trial


def _result(
    experiment_id: str,
    feature: str,
    paired: str | None,
    statistic: str,
    outcome: str,
    sample_count: int,
    non_overlapping: int,
    result_text: str | None,
    refusal: str | None,
    finding_class: str,
    detail: str,
) -> Trial:
    if (result_text is None) == (refusal is None):
        raise ValueError("a trial needs a result or a refusal, not both and not neither")
    if finding_class in {"statistically_supported", "economically_useful", "forward_validated"}:
        raise ValueError("a retrospective trial cannot be promoted")
    return Trial(
        experiment_id,
        feature,
        paired,
        statistic,
        outcome,
        sample_count,
        non_overlapping,
        result_text,
        refusal,
        None,
        finding_class,
        None,
        detail,
    )
