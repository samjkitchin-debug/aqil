"""Readable rendering for Sahm-rule research results."""

from __future__ import annotations

from aqil_research.contracts.observation import AnalysisMode
from aqil_research.methods.sahm import SahmOutput


def render_sahm_narrative(
    output: SahmOutput,
    analysis_mode: AnalysisMode,
    config_label: str,
) -> str:
    mode_label = (
        "Point-in-time reconstruction"
        if analysis_mode == AnalysisMode.POINT_IN_TIME
        else "Latest-revised retrospective view"
    )
    trigger_text = (
        "meets or exceeds the configured threshold"
        if output.triggered
        else "is below the configured threshold"
    )
    return (
        f"{mode_label} for US seasonally adjusted unemployment (Sahm rule, {config_label}).\n"
        f"Three-month average: {output.three_month_average}%.\n"
        f"Lowest three-month average in the prior 12 months (excluding the evaluation month): "
        f"{output.prior_twelve_month_low_of_average}%.\n"
        f"Gap: {output.gap_percentage_points} percentage points; this {trigger_text} "
        f"({output.threshold_percentage_points} points).\n"
        "Observation: these are calculated unemployment averages from the cited inputs.\n"
        "Statistical interpretation: the published Sahm rule is a recession-association indicator, "
        "not an NBER recession call.\n"
        "Causal hypothesis: unresolved here; no investment action is implied.\n"
        "Market pricing: unknown. Investment implication: no action."
    )
