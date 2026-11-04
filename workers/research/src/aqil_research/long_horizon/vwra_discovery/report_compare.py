"""UK English records for the EIMI comparison. Numbers come from the stored run."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from aqil_research.long_horizon.vwra_discovery.battery import ScoredTrial
from aqil_research.long_horizon.vwra_discovery.comparison import (
    REAL_GDP_FEATURE,
    REPRODUCTION_COMMAND,
    SPECIFICATION_ID,
    UNEMPLOYMENT_FEATURE,
    specification_hash,
)
from aqil_research.long_horizon.vwra_discovery.dossier import CaseRow, Finding
from aqil_research.long_horizon.vwra_discovery.lh017_correction import sentence_from_cases


def write_documents(
    prepared: dict[str, Any],
    *,
    census_markdown: str,
    git_commit: str,
    folder: Path,
) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    trials: list[ScoredTrial] = prepared["trials"]
    cases: list[CaseRow] = prepared["cases"]
    findings: list[Finding] = prepared["findings"]
    coverage: dict[str, Any] = prepared["coverage"]
    portfolio: dict[str, Any] = prepared["portfolio"]
    hashes: dict[str, str] = prepared["hashes"]
    (folder / "method-coverage.md").write_text(census_markdown, encoding="utf-8")
    (folder / "README.md").write_text(
        _readme(coverage, portfolio, hashes, git_commit, findings, cases),
        encoding="utf-8",
    )
    (folder / "dossier.md").write_text(_dossier(trials, coverage), encoding="utf-8")
    (folder / "comparison.md").write_text(_comparison(trials, coverage), encoding="utf-8")
    (folder / "casebooks.md").write_text(_casebooks(cases), encoding="utf-8")
    (folder / "trials.md").write_text(_trials(trials), encoding="utf-8")
    (folder / "limitations.md").write_text(
        _limitations(trials, coverage, portfolio), encoding="utf-8"
    )


def _readme(
    coverage: dict[str, Any],
    portfolio: dict[str, Any],
    hashes: dict[str, str],
    git_commit: str,
    findings: list[Finding],
    cases: list[CaseRow],
) -> str:
    lines = [
        "# EIMI and VWRA comparison",
        "",
        "Retrospective latest-revised research. It is not a point-in-time signal and not a "
        "historically executable allocation. `publication_allowed` stays false. This record "
        "is not Verified.",
        "",
        f"Specification `{SPECIFICATION_ID}` version 1. Hash `{specification_hash()}`.",
        f"Stored git commit `{git_commit}`.",
        f"Reproduction: `{REPRODUCTION_COMMAND}`.",
        "",
        f"EIMI month-end anchors: {coverage['eimi_anchors']}, "
        f"{coverage['eimi_first_anchor']} to {coverage['eimi_last_anchor']}.",
        f"First stored EIMI session: {coverage['eimi_first_session']}. "
        f"Stored sessions: {coverage['eimi_sessions']}.",
        f"Matched anchors on or after 2019-07-25: {coverage['matched_anchors']}, "
        f"{coverage['matched_first']} to {coverage['matched_last']}.",
        f"Executed trials {coverage['executed_trials']}. "
        f"Refused trials {coverage['refused_trials']}.",
        "",
        "## Artefacts",
        "",
    ]
    for execution_id, digest in sorted(hashes.items()):
        lines.append(f"- `{execution_id}` `{digest}`")
    lines.extend(["", "## Findings", ""])
    for finding in findings:
        statement = finding.statement
        if finding.experiment_id == "LH-E-017":
            statement = sentence_from_cases(cases)
        lines.append(f"- `{finding.finding_id}` `{finding.finding_class}`. {statement}")
    lines.extend(
        [
            "",
            "The portfolio result is "
            + (
                "blocked. No wealth path was stored."
                if portfolio["blocked"]
                else f"`{portfolio['claim_status']}` on a provisional price-return path."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def _dossier(trials: list[ScoredTrial], coverage: dict[str, Any]) -> str:
    rows = [
        row for row in trials if row.trial.experiment_id in {"LH-E-013", "LH-E-014", "LH-E-015"}
    ]
    lines = [
        "# EIMI dossier",
        "",
        "The battery is the stored VWRA battery with the symbol set to EIMI. "
        "Thresholds were not retuned. A later 126-session return is the outcome, not a state.",
        "",
        f"Anchors: {coverage['eimi_anchors']}. "
        f"Non-overlapping 126-session keeps: {coverage['eimi_non_overlapping_126']}. "
        f"Logistic and probit floors met: {coverage['eimi_logistic_allowed']}.",
        "",
        "Observed and censored outcomes:",
        "",
        "| Steps | Observed | Censored |",
        "| ---: | ---: | ---: |",
    ]
    for steps, counts in coverage["outcomes"]["EIMI"].items():
        lines.append(f"| {steps} | {counts['observed']} | {counts['censored']} |")
    lines.extend(
        [
            "",
            f"Sequence comparison: `{coverage['sequence_status']}`, "
            f"stored as `{coverage['sequence_finding']}`.",
            "",
        ]
    )
    lines.extend(_trial_lines(rows, "LH-E-015", "conjunction_comparison"))
    lines.extend(["", "## Pairs", ""])
    lines.extend(_trial_lines(rows, "LH-E-014", "spearman_between_legs"))
    bh = _select(rows, experiment_id="LH-E-013", statistic="bh_flag_count")
    if bh:
        lines.extend(
            [
                "",
                f"Benjamini–Hochberg flag count on the EIMI Spearman rows: "
                f"{bh[0].trial.result_text}. The flag cannot promote a claim.",
                "",
            ]
        )
    return "\n".join(lines)


def _comparison(trials: list[ScoredTrial], coverage: dict[str, Any]) -> str:
    rows = [row for row in trials if row.trial.experiment_id == "LH-E-016"]
    lines = [
        "# Matched comparison",
        "",
        "Both listings are US-dollar London lines. The outcome is the EIMI session-step "
        "return minus the VWRA session-step return. A missing session is censored. "
        "Relative outperformance is not a positive absolute return. "
        f"Matched anchors: {coverage['matched_anchors']}. "
        f"Non-overlapping 126-session keeps: {coverage['matched_non_overlapping_126']}. "
        f"Logistic floors met on the excess: {coverage['matched_logistic_allowed']}.",
        "",
        "## Exclusive classes",
        "",
        "The five classes are exclusive at zero. Censored rows are counted separately.",
        "",
        "| Outcome | Class | Count | Sample |",
        "| --- | --- | ---: | ---: |",
    ]
    for row in sorted(
        (item for item in rows if item.trial.statistic == "class_count"),
        key=lambda item: (item.trial.outcome, item.trial.feature),
    ):
        lines.append(
            f"| {row.trial.outcome} | {row.trial.feature} | "
            f"{row.trial.result_text} | {row.trial.sample_count} |"
        )
    lines.extend(["", "## Unemployment and real GDP", ""])
    lines.append(
        "The original feature definitions are scored again on the matched sample. "
        "Signs differ only when both Spearman coefficients are strictly opposite."
    )
    lines.append("")
    for feature in (UNEMPLOYMENT_FEATURE, REAL_GDP_FEATURE):
        lines.append(f"### `{feature}`")
        lines.append("")
        for statistic in ("spearman", "pearson", "partial_pearson", "partial_spearman"):
            selected = [
                row
                for row in rows
                if row.trial.feature == feature and row.trial.statistic == statistic
            ]
            for row in selected:
                lines.append(
                    f"- {row.symbol} {row.trial.statistic} {row.trial.outcome}: "
                    f"{row.trial.result_text or row.trial.refusal_reason} "
                    f"(n={row.trial.sample_count})"
                    + (
                        f", control `{row.trial.paired_feature}`"
                        if row.trial.paired_feature
                        else ""
                    )
                )
        relation = [
            row
            for row in rows
            if row.trial.feature == feature and row.trial.statistic.endswith("_relation")
        ]
        for row in relation:
            lines.append(f"- {row.trial.statistic}: {row.trial.result_text}.")
        lines.append("")
    lines.extend(["## Excess against the eight pairs and price-only momentum", ""])
    for row in rows:
        if row.trial.statistic in {
            "conjunction_comparison",
            "control_increment",
            "currency_intersection",
        }:
            lines.append(
                f"- `{row.trial.feature}` / `{row.trial.paired_feature or 'none'}` "
                f"{row.trial.statistic}: {row.trial.result_text or row.trial.refusal_reason}."
            )
    lines.append("")
    return "\n".join(lines)


def _casebooks(cases: list[CaseRow]) -> str:
    lines = [
        "# Casebooks",
        "",
        "Classes may overlap. Approximately neutral keeps the non-divergent anchors, "
        "where the absolute 126-session excess is below 0.10. "
        "A class without a count is not used.",
        "",
        "| Class | State | Anchors or observations | Median | Positive share is in the detail |",
        "| --- | --- | ---: | --- | --- |",
    ]
    for case in cases:
        if (
            case.family != "anchor_count"
            and not case.family.startswith(("unemployment", "cpi", "industrial", "term", "credit"))
            and not case.family.startswith("method:")
        ):
            continue
        lines.append(
            f"| {case.episode_group} | {case.family} | {case.sample_count} | "
            f"{case.value_text or 'absent'} | {case.detail} |"
        )
    lines.append("")
    return "\n".join(lines)


def _trials(trials: list[ScoredTrial]) -> str:
    lines = [
        "# Trials executed and refused",
        "",
        "Every row has a result or a refusal. A Benjamini–Hochberg flag is a diagnostic "
        "and cannot promote a claim. `statistically_supported`, `economically_useful`, "
        "and `forward_validated` are absent.",
        "",
        "| Experiment | Symbol | Executed | Refused |",
        "| --- | --- | ---: | ---: |",
    ]
    groups: dict[tuple[str, str], list[int]] = {}
    for row in trials:
        key = (row.trial.experiment_id, row.symbol)
        groups.setdefault(key, [0, 0])
        if row.trial.result_text is not None:
            groups[key][0] += 1
        if row.trial.refusal_reason is not None:
            groups[key][1] += 1
    for key in sorted(groups):
        executed, refused = groups[key]
        lines.append(f"| {key[0]} | {key[1]} | {executed} | {refused} |")
    executed = sum(item[0] for item in groups.values())
    refused = sum(item[1] for item in groups.values())
    lines.extend(
        ["", f"Total executed {executed}. Total refused {refused}. Total rows {len(trials)}.", ""]
    )
    refused_rows = [row for row in trials if row.trial.refusal_reason]
    reasons: dict[str, int] = {}
    for row in refused_rows:
        reason = row.trial.refusal_reason or ""
        reasons[reason] = reasons.get(reason, 0) + 1
    lines.append("Refusal reasons:")
    lines.append("")
    for reason, count in sorted(reasons.items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"- {count}: {reason}")
    lines.append("")
    return "\n".join(lines)


def _limitations(
    trials: list[ScoredTrial],
    coverage: dict[str, Any],
    portfolio: dict[str, Any],
) -> str:
    promoted = [
        row.trial.finding_class
        for row in trials
        if row.trial.finding_class
        in {"statistically_supported", "economically_useful", "forward_validated"}
    ]
    return "\n".join(
        [
            "# Limitations",
            "",
            "The inputs are latest revised. A retrospective association is not a figure that "
            "was knowable on the anchor date, and it is not a point-in-time signal.",
            "",
            "The overlap has already been inspected. It is not an untouched holdout. "
            "Month-ends and overlapping forward windows are not independent replications. "
            f"Method components total {coverage['method_components']}. "
            f"The sum of distinct output dates is {coverage['method_distinct_dates_sum']}. "
            "Those counts are not the same thing.",
            "",
            "EIMI is an emerging-market overweight relative to VWRA, "
            "not an independent diversifier. "
            "Both listings are US-dollar London lines. A US-dollar price-return comparison is not "
            "a total-return study and not an SGD investor-return study. "
            "Split-adjusted closes stay split-adjusted closes.",
            "",
            "The stored sequence confirms on a strictly positive 63-session return. "
            "The ETF-PROT-001 binary of 0.05 was not substituted. "
            f"`fx_observations` has {coverage['fx_observations']} rows, "
            "so no currency intersection was calculated.",
            "",
            "No monthly state was filled from a sample-end statistic. "
            "No forward outcome was written into a state. "
            f"Point-in-time methodology outputs: {coverage['point_in_time_methodology_outputs']}.",
            "",
            "Portfolio paths, when stored, use the category C contribution, cost rate, and cash "
            "interest rate. A higher terminal wealth is not economically useful "
            "or forward-validated. "
            + (
                "This run stored no wealth path."
                if portfolio["blocked"]
                else "The stored path is a provisional split-adjusted price return."
            ),
            "",
            f"Promoted trial classes found: {len(promoted)}. "
            "Catalogue scenarios executed: 0. `publication_allowed` stays false.",
            "",
        ]
    )


def _trial_lines(rows: list[ScoredTrial], experiment: str, statistic: str) -> list[str]:
    selected = _select(rows, experiment_id=experiment, statistic=statistic)
    if not selected:
        return ["No row of that statistic was stored.", ""]
    lines = []
    for row in selected:
        lines.append(
            f"- `{row.trial.feature}` / `{row.trial.paired_feature or 'none'}`: "
            f"{row.trial.result_text or row.trial.refusal_reason} "
            f"(n={row.trial.sample_count}, class `{row.trial.finding_class}`)."
        )
    return lines


def _select(rows: list[ScoredTrial], **expected: str) -> list[ScoredTrial]:
    found = []
    for row in rows:
        if all(getattr(row.trial, key) == value for key, value in expected.items()):
            found.append(row)
    return found
