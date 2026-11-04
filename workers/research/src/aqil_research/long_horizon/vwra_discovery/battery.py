"""EIMI battery and matched excess scores. Thresholds come from comparison.py."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal

from aqil_research.long_horizon.etf_protocol.rules import (
    conjunction_status,
    control_increment_status,
)
from aqil_research.long_horizon.money import decimal_text, sha256_document
from aqil_research.long_horizon.state_atlas.specification import SESSION_STEPS
from aqil_research.long_horizon.vwra_discovery.align import partial_linear, partial_rank
from aqil_research.long_horizon.vwra_discovery.comparison import (
    CASE_CLASSES,
    CASE_STATE_FEATURES,
    DIVERGENCE_STEPS,
    EXCLUSIVE_CLASSES,
    HYPOTHESES,
    PRICE_CONTROL,
    REAL_GDP_FEATURE,
    RELATIVE_CONTROL,
    UNEMPLOYMENT_FEATURE,
    approximately_neutral,
    association_relation,
    divergent_eimi,
    divergent_vwra,
    excess_return,
    exclusive_class,
    is_advance,
    is_decline,
    leadership_reversal,
    mapped_status,
)
from aqil_research.long_horizon.vwra_discovery.dossier import CaseRow, Finding, Trial
from aqil_research.long_horizon.vwra_discovery.sequence import (
    deceleration_flags,
    sequence_counts,
    sequence_flags,
)
from aqil_research.long_horizon.vwra_discovery.specification import (
    INTERSECTION_PAIRS,
    LOGISTIC_NON_OVERLAPPING,
    SEQUENCE,
    sequence_finding,
)
from aqil_research.long_horizon.vwra_discovery.statistics import (
    bh_flags,
    fit_binary,
    frequency_association,
    linear_association,
    model_allowed,
    parse_decimal,
    positive_flag,
    rank_association,
    split_kind,
)


@dataclass
class ScoredTrial:
    symbol: str
    trial: Trial


def experiment_id(
    hypothesis_id: str,
    hypotheses: tuple[dict[str, object], ...] | None = None,
) -> str:
    rows = HYPOTHESES if hypotheses is None else hypotheses
    row = next(item for item in rows if item["hypothesis_id"] == hypothesis_id)
    return str(row["experiment_id"])


def score_features(
    *,
    hypothesis_id: str,
    symbol: str,
    panel: dict[str, dict[str, str]],
    units: dict[str, str],
    row_ids: list[str],
    outcomes: dict[str, Decimal | None],
    positive_labels: dict[str, bool | None],
    negative_labels: dict[str, bool | None],
    thinned_ids: list[str],
    non_overlapping: int,
    numeric_outcome: str,
    positive_statistic: str,
    positive_outcome: str,
    negative_statistic: str,
    negative_outcome: str,
    logistic_outcome: str,
    apply_bh: bool = True,
    hypotheses: tuple[dict[str, object], ...] | None = None,
) -> list[ScoredTrial]:
    """Spearman, Pearson, conditional labels, and logistic under the frozen floors."""
    features = sorted({feature for row in panel.values() for feature in row})
    labelled = [row_id for row_id in row_ids if outcomes.get(row_id) is not None]
    allowed = model_allowed(len(labelled), len(thinned_ids))
    trials: list[ScoredTrial] = []
    experiment = experiment_id(hypothesis_id, hypotheses)
    for feature in features:
        unit = units.get(feature, "stored")
        kind = split_kind(feature, unit)
        pairs: list[tuple[Decimal, Decimal]] = []
        flags: list[bool] = []
        positive: list[bool] = []
        negative: list[bool] = []
        for row_id in labelled:
            left = parse_decimal(panel[row_id].get(feature))
            right = outcomes.get(row_id)
            if left is None or right is None:
                continue
            pairs.append((left, right))
            flag = positive_flag(left, kind)
            pos = positive_labels.get(row_id)
            neg = negative_labels.get(row_id)
            if flag is not None and pos is not None and neg is not None:
                flags.append(flag)
                positive.append(pos)
                negative.append(neg)
        note = (
            f"unit={unit}. Retrospective latest-revised output is not a decision input. "
            "Overlapping month-ends are not independent trials."
        )
        rank = rank_association(pairs)
        linear = linear_association(pairs)
        trials.append(
            _from(
                symbol,
                experiment,
                feature,
                None,
                "spearman",
                numeric_outcome,
                non_overlapping,
                rank,
                note,
            )
        )
        trials.append(
            _from(
                symbol,
                experiment,
                feature,
                None,
                "pearson",
                numeric_outcome,
                non_overlapping,
                linear,
                note,
            )
        )
        if kind == "none":
            trials.append(
                _raw(
                    symbol,
                    experiment,
                    feature,
                    None,
                    "conditional_frequency",
                    positive_outcome,
                    len(pairs),
                    non_overlapping,
                    None,
                    "no predeclared split",
                    "insufficient_sample",
                    note + " No median split was applied.",
                )
            )
        else:
            trials.append(
                _from(
                    symbol,
                    experiment,
                    feature,
                    None,
                    positive_statistic,
                    positive_outcome,
                    non_overlapping,
                    frequency_association(flags, positive, positive_statistic),
                    note,
                )
            )
            trials.append(
                _from(
                    symbol,
                    experiment,
                    feature,
                    None,
                    negative_statistic,
                    negative_outcome,
                    non_overlapping,
                    frequency_association(flags, negative, negative_statistic),
                    note,
                )
            )
        trials.append(
            _logistic(
                symbol,
                experiment,
                feature,
                panel,
                thinned_ids,
                positive_labels,
                allowed,
                non_overlapping,
                logistic_outcome,
                note,
            )
        )
    if apply_bh:
        _apply_bh(trials, experiment, symbol)
    return trials


def score_pairs(
    *,
    hypothesis_id: str,
    symbol: str,
    panel: dict[str, dict[str, str]],
    row_ids: list[str],
    positive_labels: dict[str, bool | None],
    negative_labels: dict[str, bool | None],
    non_overlapping: int,
    reasons: dict[str, str],
    positive_statistic: str,
    positive_outcome: str,
    negative_statistic: str,
    negative_outcome: str,
    hypotheses: tuple[dict[str, object], ...] | None = None,
) -> list[ScoredTrial]:
    experiment = experiment_id(hypothesis_id, hypotheses)
    trials: list[ScoredTrial] = []
    for pair in INTERSECTION_PAIRS:
        left_id = str(pair["left_feature"])
        right_id = str(pair["right_feature"])
        present_left = any(panel[row_id].get(left_id) for row_id in row_ids)
        present_right = any(panel[row_id].get(right_id) for row_id in row_ids)
        if not present_left or not present_right:
            missing = left_id if not present_left else right_id
            method_id = missing.split(":")[1] if missing.startswith("method:") else ""
            reason = reasons.get(method_id) or f"{missing} is not stored"
            trials.append(
                _raw(
                    symbol,
                    experiment,
                    left_id,
                    right_id,
                    "intersection",
                    positive_outcome,
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
        positive: list[bool] = []
        negative: list[bool] = []
        for row_id in row_ids:
            left = parse_decimal(panel[row_id].get(left_id))
            right = parse_decimal(panel[row_id].get(right_id))
            pos = positive_labels.get(row_id)
            neg = negative_labels.get(row_id)
            if left is None or right is None or pos is None or neg is None:
                continue
            both.append((left, right))
            flags.append(
                _pair_flag(left, str(pair["left_sign"]))
                and _pair_flag(right, str(pair["right_sign"]))
            )
            positive.append(pos)
            negative.append(neg)
        detail = (
            f"pair={pair['pair_id']}. independent_confirmation is false. "
            "Overlapping month-ends are not independent trials."
        )
        trials.append(
            _from(
                symbol,
                experiment,
                left_id,
                right_id,
                "spearman_between_legs",
                "not_an_outcome",
                non_overlapping,
                rank_association(both),
                detail,
            )
        )
        trials.append(
            _from(
                symbol,
                experiment,
                left_id,
                right_id,
                positive_statistic,
                positive_outcome,
                non_overlapping,
                frequency_association(flags, positive, positive_statistic),
                detail,
            )
        )
        trials.append(
            _from(
                symbol,
                experiment,
                left_id,
                right_id,
                negative_statistic,
                negative_outcome,
                non_overlapping,
                frequency_association(flags, negative, negative_statistic),
                detail,
            )
        )
    return trials


def score_sequence(
    *,
    hypothesis_id: str,
    symbol: str,
    panel: dict[str, dict[str, str]],
    row_ids: list[str],
    labels: list[bool | None],
    non_overlapping: int,
    outcome_name: str,
    label_note: str,
    hypotheses: tuple[dict[str, object], ...] | None = None,
) -> tuple[dict[str, object], list[ScoredTrial]]:
    """The stored sequence. Momentum remains strictly positive."""
    experiment = experiment_id(hypothesis_id, hypotheses)
    inflation = str(SEQUENCE["inflation_feature"])
    momentum = str(SEQUENCE["momentum_feature"])
    yoy = [panel[row_id].get(inflation) for row_id in row_ids]
    mom = [panel[row_id].get(momentum) for row_id in row_ids]
    slowed = deceleration_flags(yoy)
    confirmed = sequence_flags(yoy, mom)
    moving = [value is not None and Decimal(value) > 0 for value in mom]
    counts = sequence_counts(
        sequence=confirmed,
        deceleration=slowed,
        momentum_positive=moving,
        advances=labels,
    )
    finding = sequence_finding(str(counts["comparison_status"]))
    note = (
        f"{label_note} The stored sequence uses a strictly positive 63-session return. "
        "The ETF-PROT-001 binary of 0.05 is not substituted. "
        "Overlapping month-ends are not independent trials."
    )
    trials = [
        _count(symbol, experiment, "false_positives", counts, non_overlapping, outcome_name, note),
        _count(symbol, experiment, "missed_advances", counts, non_overlapping, outcome_name, note),
        _rate(
            symbol,
            experiment,
            "sequence",
            "pair_advances",
            "pair_count",
            counts,
            non_overlapping,
            outcome_name,
            note,
        ),
        _rate(
            symbol,
            experiment,
            "deceleration",
            "deceleration_advances",
            "deceleration_count",
            counts,
            non_overlapping,
            outcome_name,
            note,
        ),
        _rate(
            symbol,
            experiment,
            "momentum",
            "momentum_advances",
            "momentum_count",
            counts,
            non_overlapping,
            outcome_name,
            note,
        ),
        _raw(
            symbol,
            experiment,
            "SEQ-INF-MOM-001",
            None,
            "conjunction_comparison",
            outcome_name,
            int(counts["eligible"]),
            non_overlapping,
            str(counts["comparison_status"]),
            None,
            finding,
            note + " The comparison uses the frozen ETF-PROT-001 conjunction floors.",
        ),
    ]
    return counts, trials


def score_horizons(
    rows: list[dict[str, Decimal | None]],
    *,
    peer: str = "EIMI",
    pair_symbol: str = "EIMI-VWRA",
    hypothesis_id: str = "LH-H-016",
    hypotheses: tuple[dict[str, object], ...] | None = None,
    class_names: tuple[str, ...] | None = None,
    rename: dict[str, str] | None = None,
) -> list[ScoredTrial]:
    """Five exclusive classes at each horizon. A missing leg is censored, not zero."""
    experiment = experiment_id(hypothesis_id, hypotheses)
    names = EXCLUSIVE_CLASSES if class_names is None else class_names
    trials: list[ScoredTrial] = []
    for label, steps in SESSION_STEPS.items():
        counts = dict.fromkeys(names, 0)
        censored = 0
        for row in rows:
            peer_return = row.get(f"{peer}:{steps}")
            vwra = row.get(f"VWRA:{steps}")
            if peer_return is None or vwra is None:
                censored += 1
                continue
            raw_label = exclusive_class(peer_return, vwra)
            mapped = raw_label if rename is None else rename[raw_label]
            counts[mapped] += 1
        observed = sum(counts.values())
        for name in names:
            trials.append(
                _raw(
                    pair_symbol,
                    experiment,
                    name,
                    None,
                    "class_count",
                    f"excess_{steps}",
                    observed,
                    0,
                    str(counts[name]),
                    None,
                    "descriptive",
                    (
                        f"horizon={label}. steps={steps}. observed={observed}. "
                        f"censored={censored}. Relative outperformance is not an absolute advance. "
                        "The classes are exclusive at zero."
                    ),
                )
            )
        trials.append(
            _raw(
                pair_symbol,
                experiment,
                "censored",
                None,
                "class_count",
                f"excess_{steps}",
                observed + censored,
                0,
                str(censored),
                None,
                "descriptive",
                f"horizon={label}. A missing session is censored and is not filled.",
            )
        )
    return trials


def score_named_associations(
    panel: dict[str, dict[str, str]],
    row_ids: list[str],
    outcomes: dict[str, dict[str, Decimal | None]],
    non_overlapping: int,
    *,
    peer: str = "EIMI",
    peer_outcome: str = "eimi_return_126",
    control_outcome: str = "vwra_return_126",
    excess_outcome: str = "excess_126",
    pair_symbol: str = "EIMI-VWRA",
    relation_outcome: str = "eimi_minus_vwra",
    peer_label: str = "eimi",
    hypothesis_id: str = "LH-H-016",
    hypotheses: tuple[dict[str, object], ...] | None = None,
    price_control: str = PRICE_CONTROL,
    relative_control: str = RELATIVE_CONTROL,
) -> list[ScoredTrial]:
    """Unemployment and real GDP on both legs and the excess, then the price controls."""
    experiment = experiment_id(hypothesis_id, hypotheses)
    trials: list[ScoredTrial] = []
    features = (UNEMPLOYMENT_FEATURE, REAL_GDP_FEATURE)
    outcome_names = (peer_outcome, control_outcome, excess_outcome)
    stored: dict[tuple[str, str, str], Decimal | None] = {}
    for feature in features:
        for outcome_name in outcome_names:
            pairs = _feature_pairs(panel, row_ids, outcomes, feature, outcome_name)
            for statistic, association in (
                ("spearman", rank_association(pairs)),
                ("pearson", linear_association(pairs)),
            ):
                stored[(feature, outcome_name, statistic)] = parse_decimal(association.result_text)
        for statistic in ("spearman", "pearson"):
            left = stored[(feature, peer_outcome, statistic)]
            right = stored[(feature, control_outcome, statistic)]
            relation = association_relation(left, right)
            difference = None if left is None or right is None else left - right
            trials.append(
                _raw(
                    pair_symbol,
                    experiment,
                    feature,
                    "VWRA",
                    statistic + "_relation",
                    relation_outcome,
                    len(row_ids),
                    non_overlapping,
                    relation,
                    None,
                    "descriptive" if relation != "not_comparable" else "insufficient_sample",
                    (
                        f"{peer_label}={_text(left)}; vwra={_text(right)}; "
                        f"difference={_text(difference)}. "
                        "Signs differ only when both coefficients are strictly opposite. "
                        "A refusal is not_comparable."
                    ),
                )
            )
        for outcome_name in outcome_names:
            for control in (price_control, relative_control):
                target, feature_values, control_values = _controlled(
                    panel, row_ids, outcomes, feature, outcome_name, control
                )
                for statistic, association in (
                    ("partial_pearson", partial_linear(target, feature_values, control_values)),
                    ("partial_spearman", partial_rank(target, feature_values, control_values)),
                ):
                    if outcome_name == excess_outcome:
                        symbol = pair_symbol
                    elif outcome_name == control_outcome:
                        symbol = "VWRA"
                    else:
                        symbol = peer
                    trials.append(
                        _from(
                            symbol,
                            experiment,
                            feature,
                            control,
                            statistic,
                            outcome_name,
                            non_overlapping,
                            association,
                            "The price control was declared before the score. "
                            "No new macro cut was added.",
                        )
                    )
    return trials


def score_excess_pairs(
    panel: dict[str, dict[str, str]],
    row_ids: list[str],
    outcomes: dict[str, dict[str, Decimal | None]],
    non_overlapping: int,
    reasons: dict[str, str],
    *,
    pair_symbol: str = "EIMI-VWRA",
    hypothesis_id: str = "LH-H-016",
    hypotheses: tuple[dict[str, object], ...] | None = None,
    positive_statistic: str = "conditional_eimi_ahead",
    positive_outcome: str = "eimi_ahead_126",
    negative_statistic: str = "conditional_vwra_ahead",
    negative_outcome: str = "vwra_ahead_126",
    conjunction_outcome: str = "eimi_ahead_126",
    relative_control: str = RELATIVE_CONTROL,
) -> list[ScoredTrial]:
    """The eight pairs against the excess, each leg, and price-only relative momentum."""
    experiment = experiment_id(hypothesis_id, hypotheses)
    trials: list[ScoredTrial] = []
    excess_labels = {
        row_id: None
        if outcomes[row_id].get("excess_126") is None
        else outcomes[row_id]["excess_126"] > 0
        for row_id in row_ids
    }
    vwra_labels = {
        row_id: None
        if outcomes[row_id].get("excess_126") is None
        else outcomes[row_id]["excess_126"] < 0
        for row_id in row_ids
    }
    trials.extend(
        score_pairs(
            hypothesis_id=hypothesis_id,
            hypotheses=hypotheses,
            symbol=pair_symbol,
            panel=panel,
            row_ids=row_ids,
            positive_labels=excess_labels,
            negative_labels=vwra_labels,
            non_overlapping=non_overlapping,
            reasons=reasons,
            positive_statistic=positive_statistic,
            positive_outcome=positive_outcome,
            negative_statistic=negative_statistic,
            negative_outcome=negative_outcome,
        )
    )
    momentum_flags: list[bool] = []
    momentum_hits: list[bool] = []
    for row_id in row_ids:
        excess = outcomes[row_id].get("excess_126")
        momentum = parse_decimal(panel[row_id].get(relative_control))
        if excess is None or momentum is None:
            continue
        momentum_flags.append(momentum > 0)
        momentum_hits.append(excess > 0)
    pair_abs: list[Decimal] = []
    control_pairs = _feature_pairs(panel, row_ids, outcomes, relative_control, "excess_126")
    control_rank = rank_association(control_pairs)
    control_value = parse_decimal(control_rank.result_text)
    any_estimated = False
    any_beats = False
    for pair in INTERSECTION_PAIRS:
        left_id = str(pair["left_feature"])
        right_id = str(pair["right_feature"])
        eligible = pair_count = pair_hits = 0
        left_count = left_hits = right_count = right_hits = 0
        advance_count = 0
        flag_pairs: list[tuple[Decimal, Decimal]] = []
        for row_id in row_ids:
            excess = outcomes[row_id].get("excess_126")
            if excess is None:
                continue
            eligible += 1
            ahead = excess > 0
            if ahead:
                advance_count += 1
            left = parse_decimal(panel[row_id].get(left_id))
            right = parse_decimal(panel[row_id].get(right_id))
            if left is not None and _pair_flag(left, str(pair["left_sign"])):
                left_count += 1
                left_hits += int(ahead)
            if right is not None and _pair_flag(right, str(pair["right_sign"])):
                right_count += 1
                right_hits += int(ahead)
            if left is not None and right is not None:
                both = _pair_flag(left, str(pair["left_sign"])) and _pair_flag(
                    right, str(pair["right_sign"])
                )
                if both:
                    pair_count += 1
                    pair_hits += int(ahead)
                flag_pairs.append((Decimal(int(both)), excess))
        status = conjunction_status(
            eligible=eligible,
            pair_count=pair_count,
            pair_advances=pair_hits,
            drawdown_count=left_count,
            drawdown_advances=left_hits,
            volatility_count=right_count,
            volatility_advances=right_hits,
            advances=advance_count,
        )
        trials.append(
            _raw(
                pair_symbol,
                experiment,
                left_id,
                right_id,
                "conjunction_comparison",
                conjunction_outcome,
                eligible,
                non_overlapping,
                status,
                None,
                mapped_status(status),
                (
                    f"pair={pair['pair_id']}. Compared with each leg under the frozen floors. "
                    "The label is excess greater than zero, which is not an absolute advance. "
                    f"pair={pair_count}/{pair_hits}; left={left_count}/{left_hits}; "
                    f"right={right_count}/{right_hits}."
                ),
            )
        )
        association = rank_association(flag_pairs)
        trials.append(
            _from(
                pair_symbol,
                experiment,
                left_id,
                right_id,
                "spearman_flag",
                "excess_126",
                non_overlapping,
                association,
                f"pair={pair['pair_id']}. Binary flag against the excess.",
            )
        )
        flag_value = parse_decimal(association.result_text)
        if flag_value is not None:
            any_estimated = True
            pair_abs.append(abs(flag_value))
            if control_value is not None and abs(flag_value) > abs(control_value):
                any_beats = True
    momentum_rate = frequency_association(momentum_flags, momentum_hits, "relative_momentum")
    trials.append(
        _from(
            pair_symbol,
            experiment,
            relative_control,
            None,
            positive_statistic,
            positive_outcome,
            non_overlapping,
            momentum_rate,
            "Price-only relative momentum against excess greater than zero.",
        )
    )
    increment = control_increment_status(
        control_estimated=control_value is not None,
        any_candidate_beats_control=any_beats,
        any_candidate_estimated=any_estimated,
    )
    trials.append(
        _raw(
            pair_symbol,
            experiment,
            relative_control,
            "eight_pairs",
            "control_increment",
            "excess_126",
            len(row_ids),
            non_overlapping,
            increment,
            None,
            mapped_status(increment),
            (
                "A larger absolute Spearman than the price-only control is inconclusive, "
                "not a promotion. The history has already been inspected. "
                f"control={_text(control_value)}; pair_absolute_coefficients={len(pair_abs)}."
            ),
        )
    )
    trials.append(
        _raw(
            pair_symbol,
            experiment,
            "fx_observations",
            None,
            "currency_intersection",
            "excess_126",
            0,
            non_overlapping,
            None,
            "blocked_no_foreign_exchange",
            "insufficient_sample",
            "fx_observations is empty. No conversion and no SGD return was invented.",
        )
    )
    return trials


def casebook_rows(
    matched: list[dict[str, object]],
    panel: dict[str, dict[str, str]],
) -> list[CaseRow]:
    """Counts and pre-event states. Classes may overlap. Neutral anchors are kept."""
    previous: Decimal | None = None
    membership: dict[str, list[str]] = {name: [] for name in CASE_CLASSES}
    for row in matched:
        row_id = str(row["row_id"])
        eimi = row.get("eimi_126")
        vwra = row.get("vwra_126")
        assert isinstance(eimi, Decimal) or eimi is None
        assert isinstance(vwra, Decimal) or vwra is None
        current = excess_return(eimi, vwra)
        if current is not None and eimi is not None and vwra is not None:
            if divergent_eimi(current):
                membership["eimi_ahead"].append(row_id)
            if divergent_vwra(current):
                membership["vwra_ahead"].append(row_id)
            if is_advance(eimi) and is_advance(vwra):
                membership["both_advance"].append(row_id)
            if is_decline(eimi) and is_decline(vwra):
                membership["both_decline"].append(row_id)
            if leadership_reversal(previous, current):
                membership["leadership_reversal"].append(row_id)
            if approximately_neutral(current):
                membership["approximately_neutral"].append(row_id)
        previous = current
    features = list(CASE_STATE_FEATURES)
    named = {feature_id for _name, feature_id in CASE_STATE_FEATURES}
    method_features = sorted(
        {
            feature
            for row in panel.values()
            for feature in row
            if feature.startswith("method:") and feature not in named
        }
    )
    rows: list[CaseRow] = []
    for name in CASE_CLASSES:
        ids = membership[name]
        rows.append(
            CaseRow(
                name,
                "anchor_count",
                None,
                None,
                DIVERGENCE_STEPS,
                None,
                len(ids),
                (
                    f"anchors={len(ids)}. window_steps={DIVERGENCE_STEPS}. "
                    "Classes may overlap. Non-divergent anchors remain in approximately_neutral. "
                    "A relative excess is not an absolute advance."
                ),
            )
        )
        for state_name, feature_id in (*features, *((item, item) for item in method_features)):
            values = [
                parsed
                for row_id in ids
                if (parsed := parse_decimal(panel.get(row_id, {}).get(feature_id))) is not None
            ]
            positive = sum(1 for value in values if value > 0)
            share = None if not values else Decimal(positive) / Decimal(len(values))
            rows.append(
                CaseRow(
                    name,
                    state_name,
                    None,
                    None,
                    DIVERGENCE_STEPS,
                    _median(values),
                    len(values),
                    (
                        f"feature={feature_id}. observed={len(values)}. "
                        f"class_anchors={len(ids)}. positive_share={_text(share)}. "
                        "The state is the value on or before the shared date."
                    ),
                )
            )
    return rows


def findings_for(trials: list[ScoredTrial], sequence_status: str) -> list[Finding]:
    """One finding per new hypothesis. None of them is a promotion."""
    by_experiment: dict[str, list[ScoredTrial]] = defaultdict(list)
    for row in trials:
        by_experiment[row.trial.experiment_id].append(row)
    built: list[Finding] = []
    for hypothesis in HYPOTHESES:
        if hypothesis["hypothesis_id"] == "LH-H-018":
            continue
        experiment = str(hypothesis["experiment_id"])
        rows = by_experiment.get(experiment, [])
        executed = sum(1 for row in rows if row.trial.result_text is not None)
        if hypothesis["hypothesis_id"] == "LH-H-015":
            finding_class = sequence_finding(sequence_status)
            statement = (
                f"The EIMI sequence comparison is {sequence_status}, stored as {finding_class}. "
                "The thresholds were not retuned and the sequence is not an executable strategy."
            )
        elif executed:
            finding_class = "descriptive"
            statement = (
                f"{experiment} stores {executed} descriptive or comparison rows and "
                f"{sum(1 for row in rows if row.trial.refusal_reason)} refusals. "
                "Overlapping month-ends are not independent replications. "
                "Nothing in this row is statistically supported, economically useful, "
                "or forward-validated."
            )
        else:
            finding_class = "insufficient_sample"
            statement = f"{experiment} has no stored result."
        if finding_class == "no_incremental_information":
            finding_class = mapped_status(finding_class)
        built.append(
            Finding(
                f"CMP-F-{hypothesis['hypothesis_id'][-3:]}",
                str(hypothesis["hypothesis_id"]),
                experiment,
                finding_class,
                statement,
            )
        )
    return built


def assign_ids(trials: list[ScoredTrial], cases: list[CaseRow]) -> None:
    trials.sort(
        key=lambda row: (
            row.trial.experiment_id,
            row.symbol,
            row.trial.feature,
            row.trial.paired_feature or "",
            row.trial.statistic,
            row.trial.outcome,
        )
    )
    for index, row in enumerate(trials, start=1):
        row.trial.trial_id = f"CMP-T-{index:05d}"
        digest = sha256_document({**row.trial.canonical(), "symbol": row.symbol})
        row.trial.detail = f"row_hash={digest}. " + row.trial.detail
    for index, case in enumerate(cases, start=1):
        case.case_id = f"CMP-C-{index:05d}"


def grid_holds(trials: list[ScoredTrial]) -> bool:
    executed = sum(1 for row in trials if row.trial.result_text is not None)
    refused = sum(1 for row in trials if row.trial.refusal_reason is not None)
    return executed + refused == len(trials) and all(row.trial.trial_id for row in trials)


def _feature_pairs(
    panel: dict[str, dict[str, str]],
    row_ids: list[str],
    outcomes: dict[str, dict[str, Decimal | None]],
    feature: str,
    outcome_name: str,
) -> list[tuple[Decimal, Decimal]]:
    pairs: list[tuple[Decimal, Decimal]] = []
    for row_id in row_ids:
        left = parse_decimal(panel[row_id].get(feature))
        right = outcomes[row_id].get(outcome_name)
        if left is None or right is None:
            continue
        pairs.append((left, right))
    return pairs


def _controlled(
    panel: dict[str, dict[str, str]],
    row_ids: list[str],
    outcomes: dict[str, dict[str, Decimal | None]],
    feature: str,
    outcome_name: str,
    control: str,
) -> tuple[list[Decimal], list[Decimal], list[Decimal]]:
    target: list[Decimal] = []
    feature_values: list[Decimal] = []
    control_values: list[Decimal] = []
    for row_id in row_ids:
        outcome = outcomes[row_id].get(outcome_name)
        left = parse_decimal(panel[row_id].get(feature))
        held = parse_decimal(panel[row_id].get(control))
        if outcome is None or left is None or held is None:
            continue
        target.append(outcome)
        feature_values.append(left)
        control_values.append(held)
    return target, feature_values, control_values


def _pair_flag(value: Decimal, sign: str) -> bool:
    if sign == "positive":
        return value > 0
    if sign == "negative":
        return value < 0
    if sign == "drawdown_0_10":
        return value <= Decimal("-0.10")
    raise ValueError(sign)


def _logistic(
    symbol: str,
    experiment: str,
    feature: str,
    panel: dict[str, dict[str, str]],
    thinned_ids: list[str],
    labels: dict[str, bool | None],
    allowed: bool,
    non_overlapping: int,
    outcome_name: str,
    note: str,
) -> ScoredTrial:
    values: list[Decimal] = []
    binary: list[int] = []
    for row_id in thinned_ids:
        left = parse_decimal(panel[row_id].get(feature))
        label = labels.get(row_id)
        if left is None or label is None:
            continue
        values.append(left)
        binary.append(1 if label else 0)
    if not allowed or len(binary) < LOGISTIC_NON_OVERLAPPING or len(set(binary)) < 2:
        return _raw(
            symbol,
            experiment,
            feature,
            None,
            "logistic_probit",
            outcome_name,
            len(binary),
            non_overlapping,
            None,
            "not_estimable_effective_sample",
            "insufficient_sample",
            note + " Descriptive rows are stored separately.",
        )
    logistic = fit_binary("logistic", values, binary)
    probit = fit_binary("probit", values, binary)
    if logistic.result_text is None and probit.result_text is None:
        return _raw(
            symbol,
            experiment,
            feature,
            None,
            "logistic_probit",
            outcome_name,
            len(binary),
            non_overlapping,
            None,
            logistic.refusal_reason or probit.refusal_reason,
            "insufficient_sample",
            logistic.detail + " " + probit.detail,
        )
    return _raw(
        symbol,
        experiment,
        feature,
        None,
        "logistic_probit",
        outcome_name,
        len(binary),
        non_overlapping,
        f"logistic={logistic.result_text}; probit={probit.result_text}",
        None,
        "descriptive",
        logistic.detail + " " + probit.detail,
    )


def _from(
    symbol: str,
    experiment: str,
    feature: str,
    paired: str | None,
    statistic: str,
    outcome: str,
    non_overlapping: int,
    association: object,
    note: str,
) -> ScoredTrial:
    result = association.result_text
    refusal = association.refusal_reason
    finding = "descriptive" if result is not None else "insufficient_sample"
    trial = _raw(
        symbol,
        experiment,
        feature,
        paired,
        statistic,
        outcome,
        association.sample_count,
        non_overlapping,
        result,
        refusal,
        finding,
        note + " " + association.detail,
    )
    trial.trial.p_value_text = association.p_value_text
    return trial


def _raw(
    symbol: str,
    experiment: str,
    feature: str,
    paired: str | None,
    statistic: str,
    outcome: str,
    sample_count: int,
    non_overlapping: int,
    result: str | None,
    refusal: str | None,
    finding: str,
    detail: str,
) -> ScoredTrial:
    if (result is None) == (refusal is None):
        raise ValueError("a trial needs a result or a refusal, not both")
    if finding in {"statistically_supported", "economically_useful", "forward_validated"}:
        raise ValueError("a retrospective trial cannot be promoted")
    return ScoredTrial(
        symbol,
        Trial(
            experiment,
            feature,
            paired,
            statistic,
            outcome,
            sample_count,
            non_overlapping,
            result,
            refusal,
            None,
            finding,
            None,
            detail,
        ),
    )


def _count(
    symbol: str,
    experiment: str,
    name: str,
    counts: dict[str, object],
    non_overlapping: int,
    outcome: str,
    note: str,
) -> ScoredTrial:
    return _raw(
        symbol,
        experiment,
        "SEQ-INF-MOM-001",
        None,
        name,
        outcome,
        int(counts["eligible"]),
        non_overlapping,
        str(counts[name]),
        None,
        "descriptive",
        note,
    )


def _rate(
    symbol: str,
    experiment: str,
    name: str,
    numerator: str,
    denominator: str,
    counts: dict[str, object],
    non_overlapping: int,
    outcome: str,
    note: str,
) -> ScoredTrial:
    count = int(counts[denominator])
    if count == 0:
        return _raw(
            symbol,
            experiment,
            "SEQ-INF-MOM-001",
            name,
            "advance_rate",
            outcome,
            0,
            non_overlapping,
            None,
            "one conditional side is empty",
            "insufficient_sample",
            note,
        )
    rate = decimal_text(Decimal(int(counts[numerator])) / Decimal(count))
    return _raw(
        symbol,
        experiment,
        "SEQ-INF-MOM-001",
        name,
        "advance_rate",
        outcome,
        count,
        non_overlapping,
        rate,
        None,
        "descriptive",
        note,
    )


def _apply_bh(trials: list[ScoredTrial], experiment: str, symbol: str) -> None:
    scored = [
        row.trial
        for row in trials
        if row.trial.statistic == "spearman"
        and row.trial.p_value_text
        and row.trial.finding_class == "descriptive"
    ]
    flags = bh_flags([trial.p_value_text or "1" for trial in scored])
    flagged = 0
    for trial, flag in zip(scored, flags, strict=True):
        trial.bh_diagnostic = flag
        if flag:
            flagged += 1
    trials.append(
        _raw(
            symbol,
            experiment,
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
                "Overlapping month-ends are not independent trials."
            ),
        )
    )


def _median(values: list[Decimal]) -> str | None:
    if not values:
        return None
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2 == 1:
        return decimal_text(ordered[middle])
    return decimal_text((ordered[middle - 1] + ordered[middle]) / Decimal(2))


def _text(value: Decimal | None) -> str:
    if value is None:
        return "absent"
    return decimal_text(value)
