"""UK English records for the CNDX comparison. Numbers come from the stored run."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from aqil_research.long_horizon.vwra_discovery.battery import ScoredTrial
from aqil_research.long_horizon.vwra_discovery.cndx_comparison import (
    REAL_GDP_FEATURE,
    REPRODUCTION_COMMAND,
    SPECIFICATION_ID,
    UNEMPLOYMENT_FEATURE,
    specification_hash,
)
from aqil_research.long_horizon.vwra_discovery.cndx_score import casebook_sentence
from aqil_research.long_horizon.vwra_discovery.dossier import CaseRow, Finding


def write_documents(prepared: dict[str, Any], *, git_commit: str, folder: Path) -> None:
    """Write the CNDX record. The return audit is left in place."""
    folder.mkdir(parents=True, exist_ok=True)
    trials: list[ScoredTrial] = prepared["trials"]
    cases: list[CaseRow] = prepared["cases"]
    findings: list[Finding] = prepared["findings"]
    coverage: dict[str, Any] = prepared["coverage"]
    portfolio: dict[str, Any] = prepared["portfolio"]
    hashes: dict[str, str] = prepared["hashes"]
    records: dict[str, Any] = prepared["records"]
    (folder / "method-coverage.md").write_text(str(records["census_markdown"]), encoding="utf-8")
    (folder / "README.md").write_text(
        _readme(coverage, portfolio, hashes, git_commit, findings), encoding="utf-8"
    )
    (folder / "dossier.md").write_text(_dossier(trials, coverage), encoding="utf-8")
    (folder / "comparison.md").write_text(_comparison(trials, coverage), encoding="utf-8")
    (folder / "casebooks.md").write_text(_casebooks(cases), encoding="utf-8")
    (folder / "intersections.md").write_text(_intersections(trials), encoding="utf-8")
    (folder / "sequence.md").write_text(_sequence(trials, coverage), encoding="utf-8")
    (folder / "portfolio.md").write_text(_portfolio(portfolio), encoding="utf-8")
    (folder / "trials.md").write_text(_trials(trials), encoding="utf-8")
    (folder / "multiple-testing.md").write_text(
        _multiple_testing(trials, records), encoding="utf-8"
    )
    (folder / "vintage-blocker.md").write_text(_vintage(records), encoding="utf-8")
    (folder / "next-etf.md").write_text(_next_etf(records), encoding="utf-8")


def _readme(
    coverage: dict[str, Any],
    portfolio: dict[str, Any],
    hashes: dict[str, str],
    git_commit: str,
    findings: list[Finding],
) -> str:
    lines = [
        "# CNDX and VWRA comparison",
        "",
        "Retrospective latest-revised research. It is not a point-in-time signal and not a "
        "historically executable allocation. The 2019 to 2026 overlap was already inspected "
        "by the VWRA and EIMI programmes and is not an untouched holdout. "
        "`publication_allowed` stays false. This record is not Verified.",
        "",
        f"Specification `{SPECIFICATION_ID}` version 1. Hash `{specification_hash()}`.",
        f"Stored git commit `{git_commit}`.",
        f"Reproduction: `{REPRODUCTION_COMMAND}`.",
        "",
        (
            f"CNDX month-end anchors: {coverage['cndx_anchors']}, "
            f"{coverage['cndx_first_anchor']} to {coverage['cndx_last_anchor']}."
        ),
        (
            f"First stored CNDX session: {coverage['cndx_first_session']}. "
            f"Stored sessions: {coverage['cndx_sessions']}."
        ),
        (
            f"VWRA month-end anchors: {coverage['vwra_anchors']}, "
            f"{coverage['vwra_first_anchor']} to {coverage['vwra_last_anchor']}."
        ),
        (
            f"First stored VWRA session: {coverage['vwra_first_session']}. "
            f"Stored sessions: {coverage['vwra_sessions']}."
        ),
        (
            f"Matched anchors on or after 2019-07-25: {coverage['matched_anchors']}, "
            f"{coverage['matched_first']} to {coverage['matched_last']}. "
            f"Widest day gap: {coverage['matched_max_gap_days']}."
        ),
        (
            f"Executed trials {coverage['executed_trials']}. "
            f"Refused trials {coverage['refused_trials']}."
        ),
        (
            f"Relative classification: {coverage['relative_classification']}. "
            "A higher terminal wealth is not economically useful or forward-validated."
        ),
        "",
        "## Artefacts",
        "",
    ]
    for execution_id, digest in sorted(hashes.items()):
        lines.append(f"- `{execution_id}` `{digest}`")
    lines.extend(["", "## Findings", ""])
    for finding in findings:
        lines.append(f"- `{finding.finding_id}` `{finding.finding_class}`. {finding.statement}")
    lines.extend(
        [
            "",
            "## Portfolio",
            "",
            str(portfolio["statement"]),
            "",
            "The prices are split-adjusted closes. They are not distribution-adjusted total "
            "returns. See `return-audit.md`.",
            "",
        ]
    )
    return "\n".join(lines)


def _dossier(trials: list[ScoredTrial], coverage: dict[str, Any]) -> str:
    lines = [
        "# CNDX dossier",
        "",
        "Descriptive associations on CNDX month-ends. Sessions before the first stored "
        "CNDX session are refused. No earlier price was manufactured. Logistic and probit "
        f"are allowed on this sample: {coverage['cndx_logistic_allowed']}. "
        f"Non-overlapping 126-session keeps: {coverage['cndx_non_overlapping_126']}.",
        "",
        "Stored outcome counts, observed then censored:",
        "",
    ]
    for steps, counts in coverage["outcomes"]["CNDX"].items():
        lines.append(
            f"- {steps} sessions: observed {counts['observed']}, censored {counts['censored']}."
        )
    lines.extend(["", "## Named rows", ""])
    lines.extend(_named_lines(trials, "LH-E-020"))
    lines.extend(["", "## Eight pairs", ""])
    lines.extend(_named_lines(trials, "LH-E-021"))
    lines.append("")
    return "\n".join(lines)


def _comparison(trials: list[ScoredTrial], coverage: dict[str, Any]) -> str:
    lines = [
        "# Matched comparison",
        "",
        "Anchors require a CNDX month-end and a VWRA month-end within five days, on or after "
        "2019-07-25. The shared date is the earlier session. A state after that date is dropped. "
        "The excess is the CNDX session-step return minus the VWRA session-step return. "
        "No excess model was selected from two separately fitted absolute models. "
        f"Matched logistic allowed: {coverage['matched_logistic_allowed']}. "
        f"Non-overlapping keeps: {coverage['matched_non_overlapping_126']}.",
        "",
        f"Relative classification: {coverage['relative_classification']}.",
        (
            "Unemployment excess partial survives the price control: "
            f"{coverage['unemployment_excess_partial_survives']}."
        ),
        (
            "Real GDP excess partial survives the price control: "
            f"{coverage['real_gdp_excess_partial_survives']}."
        ),
        "",
        "The price control is `VWRA:trailing_return_252`. The price-only relative control is "
        "`CNDX:relative_performance_vs_vwra_252`. An excess partial survives only when its "
        "absolute partial Spearman is strictly greater than the absolute Spearman of that "
        "relative control. Otherwise the relative result is structural exposure or price "
        "momentum, not macroeconomic information.",
        "",
        "## Unemployment and real GDP",
        "",
    ]
    for feature in (UNEMPLOYMENT_FEATURE, REAL_GDP_FEATURE):
        lines.append(f"### `{feature}`")
        lines.append("")
        lines.extend(
            _select(
                trials,
                experiment="LH-E-023",
                feature=feature,
            )
        )
        lines.append("")
    lines.append("## Classification row")
    lines.append("")
    lines.extend(_select(trials, experiment="LH-E-023", feature="relative_classification"))
    lines.append("")
    return "\n".join(lines)


def _casebooks(cases: list[CaseRow]) -> str:
    lines = [
        "# Casebooks",
        "",
        casebook_sentence(cases),
        "",
        "Classes may overlap. The counts below are the stored anchor counts.",
        "",
        "| Class | Anchors |",
        "| --- | ---: |",
    ]
    for case in cases:
        if case.family == "anchor_count":
            lines.append(f"| {case.episode_group} | {case.sample_count} |")
    lines.extend(["", "## Pre-event states", ""])
    for case in cases:
        if case.family == "anchor_count":
            continue
        lines.append(
            f"- {case.episode_group} / {case.family}: median {case.value_text}, "
            f"observed {case.sample_count}. {case.detail}"
        )
    lines.append("")
    return "\n".join(lines)


def _intersections(trials: list[ScoredTrial]) -> str:
    lines = [
        "# Intersections",
        "",
        "Each row is the frozen pair against the excess, compared with each leg and with "
        "price-only relative momentum. Foreign-exchange intersections stay blocked. "
        "A status is descriptive, retrospective exploratory, inconclusive, insufficient, "
        "rejected, or no incremental information. None of those statuses is a promotion.",
        "",
    ]
    for statistic in (
        "conjunction_comparison",
        "control_increment",
        "currency_intersection",
        "conditional_cndx_ahead",
        "conditional_vwra_ahead",
    ):
        rows = [
            row
            for row in trials
            if row.trial.experiment_id == "LH-E-023" and row.trial.statistic == statistic
        ]
        if not rows:
            continue
        lines.append(f"## {statistic}")
        lines.append("")
        for row in rows:
            lines.append(
                f"- `{row.trial.feature}` / `{row.trial.outcome}`: "
                f"result {row.trial.result_text or 'refused'}, "
                f"class {row.trial.finding_class}, "
                f"refusal {row.trial.refusal_reason or 'none'}, "
                f"sample {row.trial.sample_count}."
            )
        lines.append("")
    return "\n".join(lines)


def _sequence(trials: list[ScoredTrial], coverage: dict[str, Any]) -> str:
    lines = [
        "# Sequence",
        "",
        "The sequence is a negative change in year-on-year CPI inflation, then within one to "
        "three month-ends a strictly positive 63-session trailing return. The stored sign is "
        "greater than zero. The separate 0.05 binary was not substituted.",
        "",
        f"Full-sample comparison status: {coverage['sequence_status']}.",
        f"Stored finding class: {coverage['sequence_finding']}.",
        "",
        "Counts:",
        "",
    ]
    for key, value in coverage["sequence_counts"].items():
        lines.append(f"- {key}: {value}.")
    lines.extend(["", "## Stored sequence rows", ""])
    for row in trials:
        if row.trial.experiment_id not in {"LH-E-022", "LH-E-023"}:
            continue
        if row.trial.feature not in {
            "SEQ-INF-MOM-001",
            "sequence",
            "deceleration",
            "momentum",
        }:
            continue
        lines.append(
            f"- `{row.trial.experiment_id}` `{row.symbol}` `{row.trial.feature}` "
            f"`{row.trial.statistic}`: {row.trial.result_text or row.trial.refusal_reason} "
            f"({row.trial.finding_class})."
        )
    lines.append("")
    return "\n".join(lines)


def _portfolio(portfolio: dict[str, Any]) -> str:
    lines = [
        "# Price-only portfolio",
        "",
        str(portfolio["statement"]),
        "",
        "The contribution is 1000 US dollars, the cost rate is 0.001, and cash interest is 0. "
        "The start is no earlier than both instruments' first stored sessions. "
        "Macroeconomic states were not passed to the simulator. The 618 catalogue scenarios "
        "were not run. These paths are provisional split-adjusted price paths, not total returns.",
        "",
        f"Blocked paths: {', '.join(portfolio.get('blocked_paths', []))}.",
        "",
    ]
    wealth = portfolio.get("wealth") or {}
    if wealth:
        lines.append("| Path | Terminal wealth |")
        lines.append("| --- | ---: |")
        for name, value in wealth.items():
            lines.append(f"| {name} | {value} |")
        lines.append("")
        lines.append(f"Sessions: {portfolio.get('session_count')}.")
        lines.append(f"Contributions: {portfolio.get('contribution_count')}.")
        lines.append(f"Window: {portfolio.get('start')} to {portfolio.get('end')}.")
        lines.append(
            f"Momentum choices: CNDX {portfolio.get('cndx_choices')}, "
            f"VWRA {portfolio.get('vwra_choices')}, "
            f"fallbacks {portfolio.get('fallbacks')}, ties {portfolio.get('ties')}."
        )
    else:
        lines.append(f"Block reason: {portfolio.get('reason')}.")
    lines.extend(
        [
            "",
            "A higher terminal wealth is not economically useful and not forward-validated.",
            "",
        ]
    )
    return "\n".join(lines)


def _trials(trials: list[ScoredTrial]) -> str:
    executed = sum(1 for row in trials if row.trial.result_text is not None)
    refused = sum(1 for row in trials if row.trial.refusal_reason is not None)
    lines = [
        "# Trial counts",
        "",
        f"Executed rows: {executed}. Refused rows: {refused}. Total: {len(trials)}.",
        "",
        "Month-ends and overlapping forward windows are not independent replications. "
        "Component counts are not independent dates.",
        "",
        "| Experiment | Executed | Refused |",
        "| --- | ---: | ---: |",
    ]
    grouped: dict[str, list[ScoredTrial]] = defaultdict(list)
    for row in trials:
        grouped[row.trial.experiment_id].append(row)
    for experiment in sorted(grouped):
        rows = grouped[experiment]
        done = sum(1 for row in rows if row.trial.result_text is not None)
        stopped = sum(1 for row in rows if row.trial.refusal_reason is not None)
        lines.append(f"| {experiment} | {done} | {stopped} |")
    lines.extend(["", "## Refusal reasons", ""])
    reasons: dict[str, int] = defaultdict(int)
    for row in trials:
        if row.trial.refusal_reason:
            reasons[row.trial.refusal_reason] += 1
    for reason, count in sorted(reasons.items()):
        lines.append(f"- {reason}: {count}.")
    lines.append("")
    return "\n".join(lines)


def _multiple_testing(trials: list[ScoredTrial], records: dict[str, Any]) -> str:
    executed = sum(1 for row in trials if row.trial.result_text is not None)
    refused = sum(1 for row in trials if row.trial.refusal_reason is not None)
    lines = [
        "# Multiple testing",
        "",
        "The 2019 to 2026 overlap has already been inspected by the VWRA discovery and the "
        "EIMI comparison. It is not an untouched holdout. Month-ends and overlapping forward "
        "windows are not independent replications. Component counts are not independent dates. "
        "A Benjamini-Hochberg flag may be stored and cannot promote a claim.",
        "",
        "Earlier programmes, counted from the stored trial rows before this comparison:",
        "",
    ]
    for row in records["earlier"]:
        lines.append(
            f"- `{row['specification_id']}`: executed {row['executed']}, refused {row['refused']}."
        )
    lines.extend(
        [
            "",
            f"This CNDX comparison: executed {executed}, refused {refused}.",
            "",
            "Those three programmes are one inspected history. A coefficient in this file does "
            "not become statistically supported because an earlier programme used the same months.",
            "",
        ]
    )
    return "\n".join(lines)


def _vintage(records: dict[str, Any]) -> str:
    vintage = records["vintage"]
    blocker = records["assessment_blocker"]
    return "\n".join(
        [
            "# Vintage blocker",
            "",
            "The single method inspected for a point-in-time replay is `SAHM_UNEMPLOYMENT_GAP`. "
            "Its only required dataset is `bls.ln.LNS14000000`. The registered dependency binds "
            "that series as `latest_revised`. The rule uses a three-month average and a "
            "12-month lookback. `PERIOD_LEVEL_CHANGE` uses the same series and is not a second "
            "candidate for this note.",
            "",
            "The stored BEA real-GDP vintage, `bea.vintage.real_gdp.pct_preceding`, is not an "
            "input of the 26 registered methods. It was not substituted.",
            "",
            "ALFRED retention is prohibited. No ALFRED file was read and none was stored.",
            "",
            (
                "Stored provider-vintage rows for `bls.ln.LNS14000000`: "
                f"{vintage['unemployment_provider_vintage_rows']}, "
                f"{vintage['unemployment_provider_vintage_first']} to "
                f"{vintage['unemployment_provider_vintage_last']}. "
                "Those rows are not an original-vintage lookback long enough to replay the "
                "Sahm average and the 12-month window. The current LN file has no vintage "
                "column. The Employment Situation archive may have been revised."
            ),
            "",
            "Blocker: the method cannot be replayed as point-in-time from a rights-cleared "
            "source already in the repository. Latest-revised unemployment was not relabelled "
            "as point-in-time. No new source was ingested. The search stops at this one method.",
            "",
            "Registered gate assessment:",
            "",
            str(blocker),
            "",
        ]
    )


def _next_etf(records: dict[str, Any]) -> str:
    lines = [
        "# Next ETF",
        "",
        "This recommendation is not executed. No score was run for it.",
        "",
        "Stored adjusted-close coverage for the three candidates:",
        "",
    ]
    by_ticker = {str(row["ticker"]): row for row in records["next_etf"]}
    for ticker in ("CSPX", "IWDA", "IUIT"):
        row = by_ticker.get(ticker)
        if row is None:
            lines.append(f"- {ticker}: no stored adjusted close in this query.")
            continue
        lines.append(
            f"- {ticker}: {row['sessions']} {row['currency']} sessions, "
            f"{row['first']} to {row['last']}."
        )
    anchors = records["vintage"]["cspx_month_end_anchors"]
    lines.extend(
        [
            "",
            f"CSPX month-end anchors already stored: {anchors}.",
            "",
            "CSPX is the next listing. It is a stored US-dollar London line, the category C "
            "pilot already prices it with VWRA, and this programme does not open a discovery "
            "dossier for it. IWDA is the closer world-equity listing. IUIT overlaps the "
            "technology exposure already described for CNDX. Neither is scored here.",
            "",
        ]
    )
    return "\n".join(lines)


def _named_lines(trials: list[ScoredTrial], experiment: str) -> list[str]:
    rows = [row for row in trials if row.trial.experiment_id == experiment]
    kept = [
        row
        for row in rows
        if row.trial.statistic
        in {"spearman", "pearson", "conditional_advance", "conditional_decline"}
        and row.trial.feature
        in {UNEMPLOYMENT_FEATURE, REAL_GDP_FEATURE, "trailing_return_252", "cpi_year_on_year"}
    ]
    if not kept:
        return ["No named battery row was selected for this short list."]
    return [_line(row) for row in kept]


def _select(trials: list[ScoredTrial], *, experiment: str, feature: str) -> list[str]:
    rows = [
        row
        for row in trials
        if row.trial.experiment_id == experiment and row.trial.feature == feature
    ]
    if not rows:
        return [f"`{feature}` has no stored row."]
    return [_line(row) for row in rows]


def _line(row: ScoredTrial) -> str:
    paired = row.trial.paired_feature or "none"
    return (
        f"- `{row.symbol}` `{row.trial.statistic}` outcome `{row.trial.outcome}` "
        f"paired `{paired}`: result {row.trial.result_text or 'refused'}, "
        f"class {row.trial.finding_class}, sample {row.trial.sample_count}, "
        f"non-overlapping {row.trial.non_overlapping_count}, "
        f"refusal {row.trial.refusal_reason or 'none'}."
    )
