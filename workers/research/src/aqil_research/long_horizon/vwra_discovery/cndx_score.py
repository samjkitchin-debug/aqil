"""CNDX casebook counts. Classes may overlap. Thresholds come from the frozen spec."""

from __future__ import annotations

from decimal import Decimal

from aqil_research.long_horizon.money import sha256_document
from aqil_research.long_horizon.vwra_discovery.battery import ScoredTrial, _median
from aqil_research.long_horizon.vwra_discovery.cndx_comparison import (
    CASE_CLASSES,
    CASE_STATE_FEATURES,
    DIVERGENCE_EXCESS,
    DIVERGENCE_STEPS,
    HYPOTHESES,
)
from aqil_research.long_horizon.vwra_discovery.comparison import (
    excess_return,
    is_advance,
    is_decline,
    leadership_reversal,
)
from aqil_research.long_horizon.vwra_discovery.dossier import CaseRow, Finding
from aqil_research.long_horizon.vwra_discovery.specification import sequence_finding
from aqil_research.long_horizon.vwra_discovery.statistics import parse_decimal

CASE_LABELS = (
    ("cndx_ahead", "CNDX ahead"),
    ("vwra_ahead", "VWRA ahead"),
    ("both_advance", "both advance"),
    ("both_decline", "both decline"),
    ("cndx_up_vwra_down", "CNDX up and VWRA down"),
    ("cndx_down_vwra_up", "CNDX down and VWRA up"),
    ("leadership_reversal", "leadership reversal"),
    ("approximately_neutral", "approximately neutral"),
)


def casebook_sentence(cases: list[CaseRow]) -> str:
    """Quote every class count. A missing count is not a sentence."""
    counts: dict[str, int] = {}
    for case in cases:
        if case.family != "anchor_count" or case.sample_count is None:
            continue
        counts[case.episode_group] = case.sample_count
    missing = [key for key, _label in CASE_LABELS if key not in counts]
    if missing:
        raise ValueError("the casebook sentence is missing " + ", ".join(missing))
    parts = [f"{label} {counts[key]}" for key, label in CASE_LABELS]
    return "LH-E-024 casebook counts, which may overlap: " + ", ".join(parts) + "."


def casebook_rows(
    matched: list[dict[str, object]],
    panel: dict[str, dict[str, str]],
) -> list[CaseRow]:
    """Counts and pre-event states. Neutral anchors are kept."""
    floor = Decimal(DIVERGENCE_EXCESS)
    previous: Decimal | None = None
    membership: dict[str, list[str]] = {name: [] for name in CASE_CLASSES}
    for row in matched:
        row_id = str(row["row_id"])
        cndx = row.get("cndx_126")
        vwra = row.get("vwra_126")
        if not isinstance(cndx, Decimal) and cndx is not None:
            raise TypeError("CNDX return is not a stored decimal")
        if not isinstance(vwra, Decimal) and vwra is not None:
            raise TypeError("VWRA return is not a stored decimal")
        current = excess_return(cndx, vwra)
        if current is not None and cndx is not None and vwra is not None:
            if current >= floor:
                membership["cndx_ahead"].append(row_id)
            if current <= -floor:
                membership["vwra_ahead"].append(row_id)
            if is_advance(cndx) and is_advance(vwra):
                membership["both_advance"].append(row_id)
            if is_decline(cndx) and is_decline(vwra):
                membership["both_decline"].append(row_id)
            if cndx > 0 and vwra < 0:
                membership["cndx_up_vwra_down"].append(row_id)
            if cndx < 0 and vwra > 0:
                membership["cndx_down_vwra_up"].append(row_id)
            if leadership_reversal(previous, current):
                membership["leadership_reversal"].append(row_id)
            if abs(current) < floor:
                membership["approximately_neutral"].append(row_id)
        previous = current
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
        for state_name, feature_id in (
            *CASE_STATE_FEATURES,
            *((item, item) for item in method_features),
        ):
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
                        f"class_anchors={len(ids)}. positive_share={_share(share)}. "
                        "The state is the value on or before the shared date."
                    ),
                )
            )
    return rows


def _share(value: Decimal | None) -> str:
    if value is None:
        return "absent"
    return format(value, "f")


def findings_for_cndx(
    trials: list[ScoredTrial],
    sequence_status: str,
    classification: str,
    cases: list[CaseRow],
) -> list[Finding]:
    """One finding per hypothesis. The casebook sentence quotes the counts."""
    by_experiment: dict[str, list[ScoredTrial]] = {}
    for row in trials:
        by_experiment.setdefault(row.trial.experiment_id, []).append(row)
    built: list[Finding] = []
    for hypothesis in HYPOTHESES:
        if hypothesis["hypothesis_id"] == "LH-H-025":
            continue
        experiment = str(hypothesis["experiment_id"])
        rows = by_experiment.get(experiment, [])
        executed = sum(1 for row in rows if row.trial.result_text is not None)
        refused = sum(1 for row in rows if row.trial.refusal_reason is not None)
        if hypothesis["hypothesis_id"] == "LH-H-022":
            finding_class = sequence_finding(sequence_status)
            statement = (
                f"The CNDX sequence comparison is {sequence_status}, stored as {finding_class}. "
                "The stored sign is strictly positive. The 0.05 binary was not substituted. "
                "The thresholds were not retuned and the sequence is not an executable strategy."
            )
        elif hypothesis["hypothesis_id"] == "LH-H-024":
            finding_class = "descriptive"
            statement = casebook_sentence(cases)
        elif hypothesis["hypothesis_id"] == "LH-H-023" and executed:
            finding_class = "descriptive"
            statement = (
                f"{experiment} stores {executed} descriptive or comparison rows and "
                f"{refused} refusals. The relative classification is {classification}. "
                "Overlapping month-ends are not independent replications. "
                "Nothing in this row is statistically supported, economically useful, "
                "or forward-validated."
            )
        elif executed:
            finding_class = "descriptive"
            statement = (
                f"{experiment} stores {executed} descriptive or comparison rows and "
                f"{refused} refusals. Overlapping month-ends are not independent replications. "
                "Nothing in this row is statistically supported, economically useful, "
                "or forward-validated."
            )
        else:
            finding_class = "insufficient_sample"
            statement = f"{experiment} has no stored result."
        built.append(
            Finding(
                f"CNDX-F-{str(hypothesis['hypothesis_id'])[-3:]}",
                str(hypothesis["hypothesis_id"]),
                experiment,
                finding_class,
                statement,
            )
        )
    return built


def assign_cndx_ids(trials: list[ScoredTrial], cases: list[CaseRow]) -> None:
    """Stable CNDX trial and case identifiers. They do not reuse the EIMI CMP-T series."""
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
        row.trial.trial_id = f"CNDX-T-{index:05d}"
        digest = sha256_document({**row.trial.canonical(), "symbol": row.symbol})
        row.trial.detail = f"row_hash={digest}. " + row.trial.detail
    for index, case in enumerate(cases, start=1):
        case.case_id = f"CNDX-C-{index:05d}"
