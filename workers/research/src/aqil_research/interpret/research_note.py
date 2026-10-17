"""Deterministic readable research notes from ResearchRun output."""

from __future__ import annotations

from aqil_research.pipeline.models import ResearchRun
from aqil_research.sources.attribution import (
    BLS_LATEST_REVISED_LIMITATION,
    bls_unemployment_attribution,
)


def render_bls_sahm_research_note(run: ResearchRun) -> str:
    lines = [
        "Aqil macro research note (deterministic; not for public publication).",
        "",
        "What was measured",
        "The Sahm rule gap on US seasonally adjusted U-3 unemployment (percent).",
        "",
        "Why it matters",
        "The published Sahm rule is a recession-association indicator used in policy "
        "discussion. It is not an NBER recession determination.",
        "",
        "Analysis mode",
        f"{run.analysis_mode.value} - {BLS_LATEST_REVISED_LIMITATION}",
        "",
        "Method and configuration",
        (
            f"{run.method_id} v{run.method_version} "
            f"(implementation {run.implementation_hash[:12]}...)."
        ),
        f"Configuration: {run.config_id} (hash {run.config_hash[:12]}...).",
        f"Input snapshot: {run.input_snapshot_hash[:12]}...",
        "",
        "Result",
    ]
    if run.data_sufficiency != "sufficient" or run.calculation is None:
        lines.append(f"Insufficient data: {run.missing_data_reason or 'unknown reason'}.")
    else:
        calc = run.calculation
        lines.extend(
            [
                f"Evaluation month: {calc.get('evaluation_period')}.",
                f"Three-month average: {calc.get('three_month_average')}%.",
                (
                    "Lowest three-month average in the prior 12 months "
                    "(excluding evaluation month): "
                    f"{calc.get('prior_twelve_month_low_of_average')}%."
                ),
                f"Gap: {calc.get('gap_percentage_points')} percentage points.",
                f"Published 0.50 threshold met: {calc.get('triggered')}.",
            ],
        )
    lines.extend(
        [
            "",
            "What this establishes",
            "A reproducible arithmetic summary from cited BLS observations for this run.",
            "",
            "What this does not establish",
            "A confirmed recession, a forward recession forecast, market mispricing, "
            "or any investment action.",
            f"Investment implication: {run.investment_implication}. "
            f"Market pricing: {run.market_pricing}.",
            "",
            "Attribution",
            bls_unemployment_attribution(run.executed_at.date().isoformat()),
            "",
            "Observation references",
            ", ".join(run.observation_ids[:5]) + ("..." if len(run.observation_ids) > 5 else ""),
            "",
            "Limitations",
            *run.limitations,
            BLS_LATEST_REVISED_LIMITATION,
        ],
    )
    return "\n".join(lines)
