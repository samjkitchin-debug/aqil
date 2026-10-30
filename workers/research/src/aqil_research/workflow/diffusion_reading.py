"""Store the restricted coincident diffusion on the modern refit panel."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date, datetime
from uuid import uuid4

import psycopg

from aqil_research.contracts.observation import AnalysisMode
from aqil_research.methods.restricted_coincident_diffusion import (
    DATASETS,
    METHOD_ID,
    METHOD_VERSION,
    NOT_INDEPENDENT_CONFIRMATION,
    NOT_THE_CHICAGO_FED_INDEX,
    PERSISTENCE_RULE,
    PUBLICATION_ALLOWED,
    correlate_with_filtered_factor,
    diffusion_implementation_hash,
    restricted_coincident_diffusion,
)
from aqil_research.methods.stock_watson_1988_fit import NOT_THE_CITIBASE_SPECIFICATION
from aqil_research.persistence.runs import save_research_run
from aqil_research.pipeline.models import ResearchRun
from aqil_research.workflow.stock_watson_reading import (
    PRESERVED_ESTIMATION_RUN_ID,
    load_coincident_levels,
    parameter_row_is_adopted,
)


@dataclass(frozen=True, slots=True)
class DiffusionRecord:
    run_id: str
    correlation: float | None
    overlap_months: int
    stock_watson_run_id: str | None
    publication_allowed: bool


def record_restricted_diffusion(
    conn: psycopg.Connection, *, decision_at: datetime
) -> DiffusionRecord:
    """Append one diffusion run. publication_allowed stays false."""
    if PUBLICATION_ALLOWED:
        raise RuntimeError("publication_allowed must stay false")
    loaded = load_coincident_levels(conn)
    if loaded is None:
        raise RuntimeError("the balanced modern panel is unavailable")
    ordered, series = loaded
    levels = {
        dataset: {date.fromisoformat(period): value for period, value in series[dataset].items()}
        for dataset in DATASETS
    }
    result = restricted_coincident_diffusion(levels)
    factor_run_id, factor_by_period = _filtered_factor_by_period(conn)
    correlation: float | None = None
    overlap = 0
    correlation_note = NOT_INDEPENDENT_CONFIRMATION
    if factor_by_period is None:
        correlation_note = (
            "The Stock–Watson filtered factor was not available, "
            "so the correlation was not computed. " + NOT_INDEPENDENT_CONFIRMATION
        )
    else:
        try:
            correlation, overlap = correlate_with_filtered_factor(result.months, factor_by_period)
        except ValueError as exc:
            correlation_note = f"{exc}. {NOT_INDEPENDENT_CONFIRMATION}"
    run_id = str(uuid4())
    payload = {
        "method_id": METHOD_ID,
        "publication_allowed": False,
        "real_time": False,
        "input_vintage": "latest_revised",
        "not_chicago_fed_85_indicator_index": True,
        "change": "three_month_arithmetic_level_change",
        "improvement": "strictly_positive_change",
        "persistence_rule": PERSISTENCE_RULE,
        "balanced_start": ordered[0],
        "balanced_end": ordered[-1],
        "months": [
            {
                "period": month.period.isoformat(),
                "improving": month.improving,
                "denominator": month.denominator,
                "share": month.share,
                "persistence_months": month.persistence_months,
            }
            for month in result.months
            if month.period.isoformat() in set(ordered)
        ],
        "correlation_with_stock_watson_filtered_factor": correlation,
        "correlation_overlap_months": overlap,
        "correlation_is_not_independent_confirmation": True,
        "stock_watson_run_id": factor_run_id,
        "sources": list(DATASETS),
    }
    preserved = conn.execute(
        """
        select source_id, rights_record_id
        from research.research_runs
        where run_id = %s
        """,
        (PRESERVED_ESTIMATION_RUN_ID,),
    ).fetchone()
    if preserved is None:
        raise RuntimeError("preserved Stock–Watson run is not available for source identity")
    run = ResearchRun(
        run_id=run_id,
        executed_at=decision_at,
        execution_status="completed",
        dataset_id=DATASETS[0],
        input_dataset_ids=list(DATASETS),
        source_id=preserved[0],
        rights_record_id=preserved[1],
        analysis_mode=AnalysisMode.LATEST_REVISED,
        analysis_type="coincident_diffusion",
        decision_at=decision_at,
        evaluation_period=ordered[-1],
        method_id=METHOD_ID,
        method_version=METHOD_VERSION,
        implementation_hash=diffusion_implementation_hash(),
        config_id="restricted-coincident-diffusion",
        config_hash=hashlib.sha256(b"restricted-coincident-diffusion").hexdigest(),
        input_snapshot_hash=hashlib.sha256(repr(ordered).encode("utf-8")).hexdigest(),
        data_sufficiency="sufficient",
        calculation=payload,
        statistical_interpretation=(
            "Share of four procyclical levels that rose over three months. "
            f"{NOT_THE_CHICAGO_FED_INDEX} {correlation_note} "
            f"{NOT_THE_CITIBASE_SPECIFICATION}"
        ),
        causal_hypothesis="none",
        investment_implication="no_action",
        assumptions=[
            "Each series enters as a three-month arithmetic change.",
            "An increase is an improvement.",
            "There is no interpolation.",
            PERSISTENCE_RULE,
        ],
        limitations=[
            "publication_allowed is false.",
            NOT_THE_CHICAGO_FED_INDEX,
            "The path is latest revised.",
            correlation_note,
        ],
        observation_ids=[],
        reproduction={
            "update_kind": "restricted_coincident_diffusion",
            "publication_allowed": "false",
            "stock_watson_run_id": factor_run_id or "",
        },
        narrative=(
            "Restricted coincident diffusion on the balanced panel from January 1997. "
            f"{NOT_THE_CHICAGO_FED_INDEX} publication_allowed is false."
        ),
        publication_allowed=False,
    )
    if run.publication_allowed:
        raise RuntimeError("publication_allowed must stay false")
    save_research_run(conn, run)
    return DiffusionRecord(
        run_id=run_id,
        correlation=correlation,
        overlap_months=overlap,
        stock_watson_run_id=factor_run_id,
        publication_allowed=False,
    )


def _filtered_factor_by_period(
    conn: psycopg.Connection,
) -> tuple[str | None, dict[date, float] | None]:
    row = conn.execute(
        """
        select run_id::text, calculation
        from research.research_runs
        where method_id = 'STOCK_WATSON_COINCIDENT_1988_MODERN_REFIT'
          and execution_status = 'completed'
          and calculation ? 'filtered_factor'
          and calculation ? 'growth_start'
          and coalesce(calculation->>'adopted_parameter_version', 'true') = 'true'
        order by executed_at desc
        limit 1
        """,
        (),
    ).fetchone()
    if row is None or not parameter_row_is_adopted(row[1]):
        return None, None
    calculation = row[1]
    start = date.fromisoformat(str(calculation["growth_start"]))
    values = calculation["filtered_factor"]
    factor: dict[date, float] = {}
    for index, value in enumerate(values):
        factor[_shift(start, index)] = float(value)
    return str(row[0]), factor


def _shift(period: date, months: int) -> date:
    index = period.month - 1 + months
    year = period.year + index // 12
    month = index % 12 + 1
    return date(year, month, 1)
