"""Deterministic Sahm research insight from a validated ResearchRun."""

from __future__ import annotations

from datetime import UTC, datetime

from aqil_research.insight.models import ChartPoint, ResearchInsight
from aqil_research.pipeline.models import ResearchRun
from aqil_research.sources.attribution import (
    BLS_LATEST_REVISED_LIMITATION,
    bls_unemployment_attribution,
)


def build_sahm_insight(
    run: ResearchRun,
    *,
    chart_points: list[ChartPoint] | None = None,
) -> ResearchInsight:
    generated_at = datetime.now(tz=UTC)
    insight_id = f"insight-{run.run_id}"

    calc = run.calculation or {}
    threshold_met = bool(calc.get("threshold_met", calc.get("triggered")))
    threshold_crossed = bool(calc.get("threshold_crossed"))
    gap = calc.get("gap_percentage_points")
    sufficient = run.data_sufficiency == "sufficient" and run.calculation is not None

    if not sufficient:
        headline = "Latest data does not support a complete Sahm assessment."
    elif threshold_crossed:
        headline = "The Sahm recession indicator has crossed its conventional threshold."
    elif threshold_met:
        headline = "The Sahm recession indicator meets its conventional threshold."
    elif gap is not None and float(gap) > 0:
        headline = "US unemployment deterioration has increased."
    else:
        headline = "Latest data does not satisfy the Sahm threshold."

    if sufficient:
        crossing_note = f"Threshold crossed (prior month below threshold): {threshold_crossed}."
        what_changed = (
            f"Evaluation month {calc.get('evaluation_period')}: three-month average "
            f"{calc.get('three_month_average')}% versus a prior 12-month low of "
            f"{calc.get('prior_twelve_month_low_of_average')}% (gap "
            f"{calc.get('gap_percentage_points')} percentage points). "
            f"Published 0.50 threshold met: {threshold_met}. {crossing_note}"
        )
    else:
        what_changed = run.missing_data_reason or "Insufficient observations for Sahm window."

    why_it_matters = (
        "The Sahm rule measures how far the three-month average unemployment rate has risen "
        "above its recent low. It is associated with recessions already under way in US history. "
        "It is not an NBER recession call, a guaranteed forward forecast, or a market-timing rule."
    )

    historical_context = (
        "The Sahm rule was proposed by Claudia Sahm as a real-time recession indicator based on "
        "labour-market deterioration. Aqil applies the published arithmetic only; this run does "
        "not claim an academic replication certificate or a validated "
        "point-in-time historical study."
    )

    investor_implications = (
        "For a long-horizon investor, this is one labour-market signal to monitor alongside "
        "inflation, policy and portfolio goals. Economic conditions, market pricing, asset "
        "allocation and specific trades remain distinct. "
        f"Investment implication from the engine: {run.investment_implication}. "
        f"Market pricing assessed here: {run.market_pricing}."
    )

    confidence_and_limitations = (
        f"Data sufficiency: {run.data_sufficiency}. "
        f"Analysis mode: {run.analysis_mode.value}. "
        f"{BLS_LATEST_REVISED_LIMITATION} "
        f"Verification: {run.verification_status}. "
        f"Publication allowed: {run.publication_allowed}. "
        "Evidence: "
        f"{', '.join(run.evidence_reasons) if run.evidence_reasons else 'fail-closed defaults'}."
    )

    what_comes_next = (
        "Monitor the monthly BLS employment situation release for revised unemployment rates. "
        "Related measures include payroll growth and participation; they are not substituted here."
    )

    publication_status = (
        "internal_preview"
        if not run.publication_allowed and run.execution_status == "completed"
        else ("blocked" if not run.publication_allowed else "not_eligible")
    )

    return ResearchInsight(
        insight_id=insight_id,
        run_id=run.run_id,
        generated_at=generated_at,
        headline=headline,
        what_changed=what_changed,
        why_it_matters=why_it_matters,
        historical_context=historical_context,
        investor_implications=investor_implications,
        confidence_and_limitations=confidence_and_limitations,
        what_comes_next=what_comes_next,
        method_id=run.method_id,
        method_version=run.method_version,
        dataset_id=run.dataset_id,
        analysis_mode=run.analysis_mode.value,
        data_provenance="latest_revised",
        publication_status=publication_status,
        verification_status=run.verification_status,
        calculation_summary=dict(calc),
        source_attribution=bls_unemployment_attribution(run.executed_at.date().isoformat()),
        observation_ids=list(run.observation_ids),
        analytical_payload_hash=run.analytical_payload_hash,
        evidence_reasons=list(run.evidence_reasons),
        chart_points=chart_points or [],
    )
