"""Markdown dossier. Numbers come from the stored result, not from a chart library."""

from __future__ import annotations

from pathlib import Path

from aqil_research.long_horizon.vwra_discovery.dossier import Dossier
from aqil_research.long_horizon.vwra_discovery.specification import REPRODUCTION_COMMAND


def write_documents(
    dossier: Dossier,
    digests: dict[str, str],
    eimi: dict[str, object],
    directory: Path,
) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    files = {
        "README.md": _readme(dossier, digests),
        "coverage.md": _coverage(dossier),
        "methods.md": _methods(dossier, digests["LH-X-008"]),
        "casebook.md": _casebook(dossier),
        "associations.md": _associations(dossier, digests),
        "intersections.md": _named(dossier, "LH-E-010", digests["LH-X-010"]),
        "sequence.md": _sequence(dossier, digests["LH-X-011"]),
        "failures.md": _failures(dossier),
        "limits.md": _limits(dossier),
        "reproduction.md": _reproduction(digests),
        "eimi-readiness.md": _eimi(eimi),
    }
    for name, text in files.items():
        (directory / name).write_text(text, encoding="utf-8")


def _readme(dossier: Dossier, digests: dict[str, str]) -> str:
    lines = [
        "# VWRA discovery",
        "",
        "This note records a retrospective reconstruction on stored latest-revised inputs.",
        "It is not a point-in-time study and it is not an investment signal.",
        "No portfolio simulation was run. Nothing here is cleared for publication.",
        "",
        f"Specification hash `{dossier.coverage['specification_hash']}`.",
        "",
        "| Execution | Artifact hash |",
        "| --- | --- |",
    ]
    for execution_id, digest in sorted(digests.items()):
        lines.append(f"| {execution_id} | `{digest}` |")
    lines.extend(
        [
            "",
            "Decision dates, macro periods, and market episodes are separate counts.",
            "Overlapping month-ends are not independent trials.",
            "",
            f"Reproduction: `{REPRODUCTION_COMMAND}`.",
            "",
            "A second run inserts nothing when the artifact hash matches.",
        ]
    )
    return "\n".join(lines) + "\n"


def _coverage(dossier: Dossier) -> str:
    lines = ["# Coverage", "", "| Count | Value |", "| --- | ---: |"]
    for key, value in dossier.coverage.items():
        lines.append(f"| {key} | {value} |")
    lines.extend(
        [
            "",
            "Macro periods are distinct economic period ends inside the VWRA window.",
            "Series-periods count a dataset and a period together, so one month is not "
            "twenty-eight independent trials.",
            "Market episodes are stored VWRA events under EVT-DEF-001 and EVT-DEF-002.",
        ]
    )
    return "\n".join(lines) + "\n"


def _methods(dossier: Dossier, digest: str) -> str:
    lines = [
        "# Reconstructed methods",
        "",
        f"Experiment LH-E-008. Artifact hash `{digest}`.",
        "",
        "| Method | Class | Status | Points | Reconstruction | Reason |",
        "| --- | --- | --- | ---: | --- | --- |",
    ]
    for run in dossier.runs:
        lines.append(
            "| {method} | {klass} | {status} | {count} | {clock} | {reason} |".format(
                method=run.method_id,
                klass=run.method_class,
                status=run.status,
                count=run.numeric_count,
                clock=run.reconstruction or "",
                reason=(run.reason or "").replace("|", "/"),
            )
        )
    return "\n".join(lines) + "\n"


def _casebook(dossier: Dossier) -> str:
    lines = [
        "# Episode casebook",
        "",
        "Pre-event windows use session steps 21, 63, 126, and 252.",
        "The control month-ends are the listing month-end grid outside the event interval.",
        "They are not chosen by the later return.",
        "",
        "| Group | Window | Event median | Events | Detail |",
        "| --- | ---: | --- | ---: | --- |",
    ]
    for row in dossier.cases:
        if row.event_id is not None:
            continue
        lines.append(
            f"| {row.episode_group} | {row.window_steps or ''} | {row.value_text or ''} | "
            f"{row.sample_count if row.sample_count is not None else ''} | {row.detail} |"
        )
    lines.append("")
    lines.append(
        f"Event-level rows stored: {sum(1 for row in dossier.cases if row.event_id is not None)}."
    )
    lines.append("Those rows are in `research.discovery_v2_casebook`.")
    return "\n".join(lines) + "\n"


def _associations(dossier: Dossier, digests: dict[str, str]) -> str:
    lines = [
        "# Associations",
        "",
        "Each row names its experiment and the hash of that row.",
        "The execution artifact hashes are below.",
        "",
    ]
    for execution_id, digest in sorted(digests.items()):
        lines.append(f"- {execution_id}: `{digest}`")
    lines.extend(
        [
            "",
            "| Experiment | Statistic | Feature | Result | Sample | Row hash |",
            "| --- | --- | --- | --- | ---: | --- |",
        ]
    )
    for trial in dossier.trials:
        if trial.experiment_id != "LH-E-009" or trial.statistic not in {"spearman", "pearson"}:
            continue
        if trial.result_text is None:
            continue
        lines.append(
            f"| {trial.experiment_id} | {trial.statistic} | {trial.feature} | "
            f"{trial.result_text} | {trial.sample_count} | `{_hash(trial.detail)}` |"
        )
    return "\n".join(lines) + "\n"


def _named(dossier: Dossier, experiment_id: str, digest: str) -> str:
    lines = [
        "# Intersections",
        "",
        f"Experiment {experiment_id}. Artifact hash `{digest}`.",
        "",
        "A missing input is a refusal. Methods that share inputs are not independent.",
        "",
        "| Feature | Paired feature | Statistic | Result or refusal | Sample | Row hash |",
        "| --- | --- | --- | --- | ---: | --- |",
    ]
    for trial in dossier.trials:
        if trial.experiment_id != experiment_id:
            continue
        shown = trial.result_text or trial.refusal_reason
        lines.append(
            f"| {trial.feature} | {trial.paired_feature or ''} | {trial.statistic} | "
            f"{shown} | {trial.sample_count} | `{_hash(trial.detail)}` |"
        )
    return "\n".join(lines) + "\n"


def _sequence(dossier: Dossier, digest: str) -> str:
    sequence = dossier.sequence
    lines = [
        "# Sequence",
        "",
        f"Experiment LH-E-011. Artifact hash `{digest}`.",
        "",
        "Inflation deceleration is a negative change in the atlas year-on-year ratio.",
        "It is not a percentage-point change. Positive 63-session momentum must follow",
        "within one to three month-ends. The 126-session advance is the later outcome.",
        "The thresholds were not retuned on VWRA.",
        "",
        "```mermaid",
        "flowchart LR",
        "  decel[Year-on-year inflation change is negative]",
        "  wait[Within 1 to 3 month-ends]",
        "  mom[63-session return is positive]",
        "  outcome[Later 126-session advance is the outcome]",
        "  decel --> wait --> mom --> outcome",
        "```",
        "",
        "| Item | Value |",
        "| --- | ---: |",
    ]
    for key, value in sequence.items():
        lines.append(f"| {key} | {value} |")
    lines.extend(["", "| Statistic | Result or refusal | Row hash |", "| --- | --- | --- |"])
    for trial in dossier.trials:
        if trial.experiment_id != "LH-E-011":
            continue
        shown = trial.result_text or trial.refusal_reason
        lines.append(f"| {trial.statistic} | {shown} | `{_hash(trial.detail)}` |")
    lines.append("")
    lines.append("The sequence is not an executable strategy.")
    return "\n".join(lines) + "\n"


def _failures(dossier: Dossier) -> str:
    counts: dict[str, int] = {}
    for trial in dossier.trials:
        if trial.refusal_reason is None:
            continue
        counts[trial.refusal_reason.split(":", 1)[0]] = (
            counts.get(trial.refusal_reason.split(":", 1)[0], 0) + 1
        )
    lines = ["# Failures and refusals", "", "| Reason | Rows |", "| --- | ---: |"]
    for reason, count in sorted(counts.items()):
        lines.append(f"| {reason} | {count} |")
    lines.extend(["", "## Methods that did not produce a number", ""])
    for run in dossier.runs:
        if run.status == "succeeded":
            continue
        lines.append(f"- {run.method_id}: {run.reason}")
    return "\n".join(lines) + "\n"


def _limits(dossier: Dossier) -> str:
    coverage = dossier.coverage
    return "\n".join(
        [
            "# Sample limits",
            "",
            f"Decision dates: {coverage['decision_dates']}.",
            f"Anchors with an observed 126-session return: {coverage['outcome_anchors']}.",
            f"Non-overlapping 126-session keeps: {coverage['non_overlapping_126']}.",
            "Logistic and probit use the frozen floors of 60 decision points and "
            "15 non-overlapping keeps. When those floors are not met the model is "
            "not_estimable_effective_sample and the descriptive rows are still stored.",
            "Overlapping month-ends are not independent trials.",
            "Latest-revised rows are not decision inputs.",
            "A Benjamini-Hochberg flag cannot promote a claim.",
            "Point-in-time eligible results: 0.",
            "Independently validated results: 0.",
            "Portfolio simulations from this dossier: 0.",
            "",
        ]
    )


def _reproduction(digests: dict[str, str]) -> str:
    lines = [
        "# Reproduction",
        "",
        "From `workers/research`:",
        "",
        "```text",
        REPRODUCTION_COMMAND,
        "```",
        "",
        "The command reads the local research database and `aqil_etf`.",
        "It does not apply a hosted migration and it does not call the portfolio simulator.",
        "A second run that reproduces the same artifact inserts nothing.",
        "",
        "| Execution | Artifact hash |",
        "| --- | --- |",
    ]
    for execution_id, digest in sorted(digests.items()):
        lines.append(f"| {execution_id} | `{digest}` |")
    return "\n".join(lines) + "\n"


def _eimi(eimi: dict[str, object]) -> str:
    return "\n".join(
        [
            "# EIMI readiness",
            "",
            "The same battery was not scored for EIMI. This note stops after the stored facts.",
            "",
            f"Stored EIMI month-end anchors: {eimi['anchor_count']}.",
            f"First anchor: {eimi['first_anchor']}.",
            f"Last anchor: {eimi['last_anchor']}.",
            f"First stored session: {eimi['first_stored_session']}.",
            f"Stored sessions: {eimi['stored_sessions']}.",
            "",
            "No EIMI association, intersection, sequence, or method score was written.",
            "",
        ]
    )


def _hash(detail: str) -> str:
    prefix = "row_hash="
    if detail.startswith(prefix):
        return detail.split(".", 1)[0].removeprefix(prefix)
    return ""
