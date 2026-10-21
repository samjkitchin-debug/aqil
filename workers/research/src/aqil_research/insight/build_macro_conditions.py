"""Structured macro conditions insight from a MACRO_CONDITIONS_PANEL run."""

from __future__ import annotations

from datetime import UTC, datetime

from aqil_research.insight.models import ChartPoint, ResearchInsight
from aqil_research.pipeline.models import ResearchRun
from aqil_research.sources.attribution import (
    BLS_LATEST_REVISED_LIMITATION,
    bls_unemployment_attribution,
    census_adv_orders_attribution,
    fed_sloos_attribution,
)


def build_macro_conditions_insight(run: ResearchRun) -> ResearchInsight:
    generated_at = datetime.now(tz=UTC)
    retrieval_date = generated_at.date().isoformat()
    calc = run.calculation or {}
    labour = calc.get("labour", {})
    credit = calc.get("business_credit", {})
    manufacturing = calc.get("manufacturing_demand", {})
    labour_result = labour.get("result") if isinstance(labour, dict) else None
    credit_result = credit.get("result") if isinstance(credit, dict) else None
    mfg_result = manufacturing.get("result") if isinstance(manufacturing, dict) else None

    sufficient = run.data_sufficiency == "sufficient" and run.calculation is not None
    if not sufficient:
        headline = "Macro conditions panel is incomplete for the configured evaluation windows."
    else:
        headline = (
            "US labour, business credit and manufacturing demand — combined conditions read"
        )

    what_changed = _what_changed(labour_result, credit_result, mfg_result, sufficient)
    why_it_matters = (
        "Together, labour-market deterioration, bank lending standards and advance factory "
        "orders describe three distinct parts of the business cycle. Each series has its own "
        "revision behaviour and evidence limits. This panel is not a unified forecast, an "
        "earnings predictor, or an ETF allocation model."
    )
    historical_context = (
        "The Sahm component applies the published unemployment-gap rule. The credit component "
        "uses the Federal Reserve Senior Loan Officer Survey net tightening share for C&I loans. "
        "The manufacturing component uses Census advance durable goods new orders. "
        "Near-term forward spread remains blocked and is not approximated with a conventional "
        "yield spread."
    )
    investor_implications = (
        "Long-horizon investors may monitor these conditions alongside inflation and policy. "
        "The engine records investment_implication as no_action and does not generate ETF "
        "allocation changes from these outputs."
    )
    confidence_and_limitations = (
        f"Data sufficiency: {run.data_sufficiency}. Analysis mode: {run.analysis_mode.value}. "
        f"{BLS_LATEST_REVISED_LIMITATION} "
        "SLOOS zero means balanced net tightening and easing, not unanimous unchanged standards. "
        "Census advance orders distinguish initial-estimate from official month-on-month changes. "
        f"Verification: {run.verification_status}. "
        f"Evidence: {', '.join(run.evidence_reasons) if run.evidence_reasons else 'fail-closed'}."
    )
    what_comes_next = (
        "Monitor the Employment Situation release, the quarterly SLOOS publication and the "
        "Census advance M3 release. Resolve near-term forward spread formula and rights before "
        "enabling that slot."
    )
    attribution = (
        f"{bls_unemployment_attribution(retrieval_date)} "
        f"{fed_sloos_attribution(retrieval_date)} "
        f"{census_adv_orders_attribution(retrieval_date)}"
    )

    chart_points = _unemployment_chart(labour_result)

    return ResearchInsight(
        insight_id=f"insight-{run.run_id}",
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
        publication_status="internal_preview",
        verification_status=run.verification_status,
        calculation_summary=calc,
        source_attribution=attribution,
        observation_ids=list(run.observation_ids),
        analytical_payload_hash=run.analytical_payload_hash,
        evidence_reasons=list(run.evidence_reasons),
        chart_points=chart_points,
    )


def _what_changed(
    labour: dict[str, object] | None,
    credit: dict[str, object] | None,
    manufacturing: dict[str, object] | None,
    sufficient: bool,
) -> str:
    if not sufficient:
        return "One or more panel inputs were insufficient for the configured evaluation dates."
    parts: list[str] = []
    if labour:
        parts.append(
            "Labour (Sahm): gap "
            f"{labour.get('gap_percentage_points')} percentage points; threshold met: "
            f"{labour.get('threshold_met')}."
        )
    if credit:
        parts.append(
            "Business credit (SLOOS C&I): net tightening share "
            f"{credit.get('net_tightening_share_percent')}% ({credit.get('direction_label')})."
        )
    if manufacturing:
        parts.append(
            "Manufacturing (Census advance new orders): initial-estimate m/m "
            f"{manufacturing.get('initial_estimate_to_initial_estimate_pct_change')}% versus "
            f"official m/m {manufacturing.get('official_month_on_month_pct_change')}%."
        )
    blocked = calc_blocked_note()
    return " ".join(parts) + " " + blocked


def calc_blocked_note() -> str:
    return (
        "Near-term forward spread: blocked (no substitute spread used)."
    )


def _unemployment_chart(labour: dict[str, object] | None) -> list[ChartPoint]:
    if not labour:
        return []
    gap = labour.get("gap_percentage_points")
    if gap is None:
        return []
    try:
        value = float(gap)
    except (TypeError, ValueError):
        return []
    period = str(labour.get("evaluation_period", ""))
    if not period:
        return []
    return [ChartPoint(period=period, value=value)]
