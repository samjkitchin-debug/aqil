"""Counts that keep a design register distinct from a scientific conclusion.

Registered scenarios are not executed simulations. A reconciled ledger is not
a scientifically supported conclusion. Shared data is not independent
confirmation.
"""

from __future__ import annotations

SHARED_RELATIONS = frozenset(
    {
        "shares_dataset",
        "overlaps_period",
        "shares_instrument",
        "shares_indicator",
        "same_contribution_schedule",
        "matched_control",
    }
)

SPEC_FIELDS = (
    "hypothesis_id",
    "research_question",
    "methodology_version",
    "portfolio_decision_policy",
    "baseline_strategy",
    "starting_capital",
    "contribution_amount",
    "contribution_schedule",
    "simulation_window_rule",
    "investability_rules",
    "statistical_tests",
    "macro_vintage_ids",
    "publication_allowed",
)

EXECUTION_FIELDS = (
    "git_commit",
    "code_hash",
    "reproduction_command",
    "simulation_start",
    "simulation_end",
    "macro_vintage_ids",
    "price_series_versions",
    "artifact_sha256",
)

EVIDENCE_BODY_FIELDS = ("fills", "cash_flows", "snapshots", "forgone")


def missing_fields(document: dict[str, object], required: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(name for name in required if name not in document or document[name] in (None, ""))


def classify_progress(row: dict[str, int]) -> dict[str, int]:
    """Keep dossier executions out of the portfolio-simulation count.

    Succeeded executions are not portfolio simulations. A claim that is
    inconclusive or rejected is not a scientifically validated finding.
    """
    supported = (
        row["claims_statistically_supported"]
        + row["claims_economically_useful"]
        + row["claims_forward_validated"]
    )
    return {
        "registered_scenarios": row["candidate_scenario_ids"],
        "registered_signals": row["candidate_signal_ids"],
        "registered_comparisons": row["registered_comparisons"],
        "executed_comparisons": row["executed_comparisons"],
        "refused_comparisons": row["refused_comparisons"],
        "retrospective_results": row["retrospective_results"],
        "point_in_time_results": row["point_in_time_results"],
        "portfolio_simulations": row["portfolio_simulations"],
        "scientifically_validated_findings": row["scientifically_validated_findings"],
        "scientifically_supported_conclusions": supported,
        "candidate_rows_marked_as_results": row["candidate_rows_marked_as_results"],
    }


def progress_paragraph(counts: dict[str, int]) -> str:
    return (
        f"Registered scenarios: {counts['registered_scenarios']}. "
        f"Registered comparisons: {counts['registered_comparisons']}. "
        f"Executed comparisons: {counts['executed_comparisons']}. "
        f"Refused comparisons: {counts['refused_comparisons']}. "
        f"Retrospective results: {counts['retrospective_results']}. "
        f"Point-in-time results: {counts['point_in_time_results']}. "
        f"Portfolio simulations: {counts['portfolio_simulations']}. "
        f"Scientifically validated findings: {counts['scientifically_validated_findings']}. "
        f"Scientifically supported conclusions: {counts['scientifically_supported_conclusions']}."
    )


def shared_rows_are_independent(rows: list[dict[str, object]]) -> bool:
    """True only if a shared-data link was marked as independent confirmation."""
    for row in rows:
        if row["relation"] in SHARED_RELATIONS and row["independent_confirmation"] is True:
            return True
    return False
