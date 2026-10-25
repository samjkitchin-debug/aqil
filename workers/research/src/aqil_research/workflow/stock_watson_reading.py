"""Replay the stored 1988 factor when the database panel is unchanged."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

import psycopg

from aqil_research.contracts.observation import AnalysisMode
from aqil_research.methods.stock_watson_1988 import gaussian_log_likelihood
from aqil_research.methods.stock_watson_1988_fit import (
    _filtered_factor,
    log_difference,
    standardise,
)
from aqil_research.persistence.runs import save_research_run
from aqil_research.pipeline.models import ResearchRun

METHOD_ID = "STOCK_WATSON_COINCIDENT_1988_MODERN_REFIT"
FACTOR_LOCK = 410221002
DATASETS = (
    "fed.g17.IP.B50001.S",
    "bea.nipa.T20600.W875RX",
    "bea.nipa.U002BU.KPMT",
    "bls.ce.CES0000000001",
)


@dataclass(frozen=True, slots=True)
class FilterUpdate:
    status: str
    detail: str


def record_filter_update(conn: psycopg.Connection, *, decision_at: datetime) -> FilterUpdate:
    """Do not insert a run when the filtered path still matches the stored one."""
    del decision_at
    locked = conn.execute("select pg_try_advisory_lock(%s)", (FACTOR_LOCK,)).fetchone()
    if locked is None or not locked[0]:
        return FilterUpdate("locked", "another filter update holds the lock")
    try:
        return _filter_update_locked(conn)
    finally:
        conn.execute("select pg_advisory_unlock(%s)", (FACTOR_LOCK,))


def _filter_update_locked(conn: psycopg.Connection) -> FilterUpdate:
    row = conn.execute(
        """
        select calculation from research.research_runs
        where method_id = %s
          and execution_status = 'completed'
          and calculation ? 'loadings_ip_income_sales_payroll'
        order by executed_at desc
        limit 1
        """,
        (METHOD_ID,),
    ).fetchone()
    if row is None or row[0] is None:
        return FilterUpdate("absent", "no stored 1988 refit")
    calculation = row[0]
    try:
        panel = _panel(conn, calculation.get("moments"))
    except (ValueError, ZeroDivisionError) as exc:
        _store_failure(conn, f"panel rejected: {exc}")
        return FilterUpdate("failed", f"panel rejected: {exc}")
    if panel is None:
        return FilterUpdate("insufficient", "the four series do not share 36 months")
    observations = tuple(
        tuple(panel[series][time] for series in range(4)) for time in range(len(panel[0]))
    )
    loadings = tuple(calculation["loadings_ip_income_sales_payroll"])
    factor_ar = tuple(calculation["factor_ar"])
    idiosyncratic = tuple(tuple(pair) for pair in calculation["idiosyncratic_ar"])
    scales = tuple(calculation["idiosyncratic_scale"])
    likelihood = gaussian_log_likelihood(
        observations,
        loadings=loadings,
        factor_ar=factor_ar,
        idiosyncratic_ar=idiosyncratic,
        idiosyncratic_innovation_scale=scales,
    )
    path = _filtered_factor(
        observations,
        loadings=loadings,
        factor_ar=factor_ar,
        idiosyncratic_ar=idiosyncratic,
        idiosyncratic_innovation_scale=scales,
    )
    if not math.isfinite(likelihood) or any(not math.isfinite(value) for value in path):
        _store_failure(conn, "non-finite likelihood or filtered state")
        return FilterUpdate("failed", "non-finite likelihood or filtered state")
    stored = calculation["filtered_factor"]
    gap = None
    if len(path) == len(stored):
        gap = max(abs(left - right) for left, right in zip(path, stored, strict=True))
    likelihood_gap = abs(likelihood - float(calculation["log_likelihood"]))
    if gap is not None and gap <= 1e-6 and likelihood_gap <= 1e-4:
        return FilterUpdate("unchanged", "filtered path matches the stored run")
    _store_filter_update(conn, calculation, path, likelihood)
    return FilterUpdate(
        "filter_update",
        "stored a new filtered path with the existing fitted parameters and frozen standardisation",
    )


def _store_filter_update(conn, calculation, path, likelihood) -> None:
    """Persist a filter update. Parameters and training moments stay frozen."""
    now = datetime.now(UTC)
    payload = dict(calculation)
    payload["filtered_factor"] = list(path)
    payload["log_likelihood"] = likelihood
    payload["update_kind"] = "filter_update"
    payload["real_time"] = False
    payload["publication_allowed"] = False
    run = ResearchRun(
        run_id=str(uuid4()),
        executed_at=now,
        execution_status="completed",
        dataset_id=DATASETS[0],
        input_dataset_ids=list(DATASETS),
        source_id="bea_real_manufacturing_trade_sales",
        rights_record_id="bea_real_manufacturing_trade_sales",
        analysis_mode=AnalysisMode.LATEST_REVISED,
        analysis_type="coincident_factor",
        decision_at=now,
        evaluation_period=str(calculation.get("sample_levels", ["2026-07-01", "2026-07-01"])[-1]),
        method_id=METHOD_ID,
        method_version="0.1.0",
        implementation_hash="filter-update",
        config_id="sw1988-modern-frozen-moments",
        config_hash="frozen-moments",
        input_snapshot_hash="filter-update",
        data_sufficiency="sufficient",
        calculation=payload,
        statistical_interpretation=(
            "Filter update using the stored 1988 parameters and the training-sample "
            "mean and scale. Not a re-estimation and not a real-time vintage."
        ),
        causal_hypothesis="none",
        investment_implication="no_action",
        assumptions=["Training-sample standardisation is frozen."],
        limitations=["publication_allowed is false.", "Not a re-estimated model."],
        observation_ids=[],
        reproduction={"update_kind": "filter_update"},
        narrative="Filter update. Re-estimation is manual.",
        publication_allowed=False,
    )
    save_research_run(conn, run)


def _store_failure(conn, reason: str) -> None:
    """Record a failed filter attempt without replacing the last completed factor."""
    now = datetime.now(UTC)
    previous = conn.execute(
        """
        select evaluation_period::text
        from research.research_runs
        where method_id = %s and execution_status = 'completed'
        order by executed_at desc
        limit 1
        """,
        (METHOD_ID,),
    ).fetchone()
    evaluation_period = previous[0] if previous is not None else "1997-01-01"
    run = ResearchRun(
        run_id=str(uuid4()),
        executed_at=now,
        execution_status="failed_method",
        dataset_id=DATASETS[0],
        input_dataset_ids=list(DATASETS),
        source_id="bea_real_manufacturing_trade_sales",
        rights_record_id="bea_real_manufacturing_trade_sales",
        analysis_mode=AnalysisMode.LATEST_REVISED,
        analysis_type="coincident_factor",
        decision_at=now,
        evaluation_period=evaluation_period,
        method_id=METHOD_ID,
        method_version="0.1.0",
        implementation_hash="filter-failure",
        config_id="sw1988-modern-frozen-moments",
        config_hash="frozen-moments",
        input_snapshot_hash="filter-failure",
        data_sufficiency="insufficient",
        missing_data_reason=reason,
        calculation={"update_kind": "filter_failure", "publication_allowed": False},
        statistical_interpretation=(
            "Filter update failed. The last completed factor was not replaced."
        ),
        causal_hypothesis="none",
        investment_implication="insufficient_evidence",
        assumptions=["A failed update does not change fitted parameters."],
        limitations=["publication_allowed is false.", reason],
        observation_ids=[],
        reproduction={"update_kind": "filter_failure", "reason": reason},
        narrative="Filter update failed. No new factor was stored.",
        publication_allowed=False,
    )
    save_research_run(conn, run)


def _panel(
    conn: psycopg.Connection,
    moments: dict[str, dict[str, float]] | None,
) -> list[list[float]] | None:
    series: dict[str, dict[str, float]] = {}
    for dataset in DATASETS:
        series[dataset] = {}
        for period, value in conn.execute(
            """
            SELECT o.period_start::text, o.raw_value::float
            FROM research.economic_observations o
            JOIN research.source_retrievals r ON r.retrieval_id = o.retrieval_id
            WHERE o.dataset_id = %s
              AND r.collection_mode = 'live'
              AND o.series_provenance = 'latest_revised'
              AND o.period_start >= DATE '1997-01-01'
            ORDER BY o.retrieved_at
            """,
            (dataset,),
        ):
            series[dataset][period] = value
    months = set.intersection(*(set(series[dataset]) for dataset in DATASETS))
    if len(months) < 36:
        return None
    ordered = sorted(months)
    names = ("production", "income", "sales", "payroll")
    panel = []
    for dataset, name in zip(DATASETS, names, strict=True):
        levels = [series[dataset][month] for month in ordered]
        growth = log_difference(levels)
        if moments and name in moments:
            mean = float(moments[name]["mean"])
            scale = float(moments[name]["scale"])
            standardised = [(value - mean) / scale for value in growth]
        else:
            standardised, _mean, _scale = standardise(growth)
        panel.append(standardised)
    return panel
