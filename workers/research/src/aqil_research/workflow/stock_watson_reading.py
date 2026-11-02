"""Replay the stored 1988 factor when the database panel is unchanged."""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

import psycopg

from aqil_research.contracts.observation import AnalysisMode
from aqil_research.methods.stock_watson_1988 import gaussian_log_likelihood
from aqil_research.methods.stock_watson_1988_fit import (
    GRADIENT_STEP,
    MODERN_REFIT_DATASETS,
    NOT_THE_CITIBASE_SPECIFICATION,
    _filtered_factor,
    fit_coincident_factor,
    log_difference,
    modern_refit_implementation_hash,
    standardise,
    theta_from_calculation,
)
from aqil_research.persistence.runs import save_research_run
from aqil_research.pipeline.models import ResearchRun

METHOD_ID = "STOCK_WATSON_COINCIDENT_1988_MODERN_REFIT"
FACTOR_LOCK = 410221002
DATASETS = MODERN_REFIT_DATASETS
PRESERVED_ESTIMATION_RUN_ID = "3f8c7611-c2a1-44a0-8c7e-01bebbfe9a8a"
LIKELIHOOD_IMPROVEMENT = 1e-3


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
          and coalesce(calculation->>'adopted_parameter_version', 'true') = 'true'
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


def load_coincident_levels(
    conn: psycopg.Connection,
) -> tuple[list[str], dict[str, dict[str, float]]] | None:
    """Balanced latest-revised months from January 1997, same panel as the refit."""
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
    return sorted(months), series


def _panel(
    conn: psycopg.Connection,
    moments: dict[str, dict[str, float]] | None,
) -> list[list[float]] | None:
    loaded = load_coincident_levels(conn)
    if loaded is None:
        return None
    ordered, series = loaded
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


def parameter_row_is_adopted(calculation: dict[str, object] | None) -> bool:
    """Missing flag keeps the preserved run. An explicit false does not."""
    if not calculation or "loadings_ip_income_sales_payroll" not in calculation:
        return False
    return calculation.get("adopted_parameter_version", True) is True


def adopt_parameter_version(
    *,
    maximum_likelihood_claimed: bool,
    new_log_likelihood: float,
    stored_log_likelihood: float,
) -> bool:
    """A verified optimum replaces the parameter version only when the likelihood improves."""
    return (
        maximum_likelihood_claimed
        and math.isfinite(new_log_likelihood)
        and math.isfinite(stored_log_likelihood)
        and new_log_likelihood > stored_log_likelihood + LIKELIHOOD_IMPROVEMENT
    )


@dataclass(frozen=True, slots=True)
class ReestimateRecord:
    run_id: str
    preserved_run_id: str
    overwrote_preserved_run: bool
    maximum_likelihood_claimed: bool
    adopted_parameter_version: bool
    gradient_norm: float | None
    gradient_norm_wide_step: float | None
    log_likelihood: float
    stored_log_likelihood: float
    starts_evaluated: int
    message: str


def prepare_modern_reestimate(
    conn: psycopg.Connection,
) -> tuple[list[list[float]], dict[str, object]]:
    """Read the preserved run and the balanced panel. Does not estimate."""
    preserved = _preserved_snapshot(conn)
    calculation = preserved["calculation"]
    moments = preserved["moments"]
    if not isinstance(calculation, dict):
        raise RuntimeError("preserved calculation is missing")
    if moments is not None and not isinstance(moments, dict):
        raise RuntimeError("preserved moments are missing")
    panel = _panel(conn, moments)
    if panel is None:
        raise RuntimeError("the balanced modern panel is unavailable")
    preserved["theta"] = theta_from_calculation(calculation)
    return panel, preserved


def store_modern_reestimate(
    conn: psycopg.Connection,
    fitted,
    preserved: dict[str, object],
    panel: list[list[float]],
) -> ReestimateRecord:
    """Append the re-estimate. The preserved run is read again and must be unchanged."""
    adopted = adopt_parameter_version(
        maximum_likelihood_claimed=fitted.maximum_likelihood_claimed,
        new_log_likelihood=fitted.log_likelihood,
        stored_log_likelihood=float(preserved["log_likelihood"]),
    )
    run_id = _new_run_id()
    _append_refit(conn, run_id, fitted, preserved, adopted, panel)
    _assert_preserved_unchanged(conn, preserved)
    return ReestimateRecord(
        run_id=run_id,
        preserved_run_id=PRESERVED_ESTIMATION_RUN_ID,
        overwrote_preserved_run=False,
        maximum_likelihood_claimed=fitted.maximum_likelihood_claimed,
        adopted_parameter_version=adopted,
        gradient_norm=_json_float(fitted.gradient_norm),
        gradient_norm_wide_step=_json_float(fitted.gradient_norm_wide_step),
        log_likelihood=fitted.log_likelihood,
        stored_log_likelihood=float(preserved["log_likelihood"]),
        starts_evaluated=fitted.starts_evaluated,
        message=fitted.message,
    )


def record_modern_reestimate(conn: psycopg.Connection) -> ReestimateRecord:
    """Append a multi-start re-estimate. Never update the preserved run."""
    panel, preserved = prepare_modern_reestimate(conn)
    theta = preserved["theta"]
    fitted = fit_coincident_factor(panel, extra_starts=[theta])
    return store_modern_reestimate(conn, fitted, preserved, panel)


def _new_run_id() -> str:
    candidate = str(uuid4())
    if candidate == PRESERVED_ESTIMATION_RUN_ID:
        raise RuntimeError("refusing to reuse the preserved estimation run")
    return candidate


def _json_float(value: float) -> float | None:
    if not math.isfinite(value):
        return None
    return value


def _preserved_snapshot(conn: psycopg.Connection) -> dict[str, object]:
    row = conn.execute(
        """
        select source_id, rights_record_id, evaluation_period::text,
               executed_at, publication_allowed, calculation,
               calculation->>'log_likelihood'
        from research.research_runs
        where run_id = %s
        """,
        (PRESERVED_ESTIMATION_RUN_ID,),
    ).fetchone()
    if row is None or row[5] is None:
        raise RuntimeError("preserved estimation run 3f8c7611 is not in this database")
    calculation = row[5]
    if calculation.get("publication_allowed") is True or row[4] is True:
        raise RuntimeError("preserved run must stay unpublished")
    return {
        "source_id": row[0],
        "rights_record_id": row[1],
        "evaluation_period": row[2],
        "executed_at": row[3],
        "publication_allowed": row[4],
        "calculation": calculation,
        "log_likelihood": float(calculation["log_likelihood"]),
        "moments": calculation.get("moments"),
        "likelihood_text": row[6],
    }


def _assert_preserved_unchanged(conn: psycopg.Connection, preserved: dict[str, object]) -> None:
    row = conn.execute(
        """
        select executed_at, publication_allowed, calculation->>'log_likelihood'
        from research.research_runs
        where run_id = %s
        """,
        (PRESERVED_ESTIMATION_RUN_ID,),
    ).fetchone()
    if row is None:
        raise RuntimeError("preserved estimation run disappeared")
    if row[0] != preserved["executed_at"] or row[1] is not False:
        raise RuntimeError("preserved estimation run was modified")
    if row[2] != preserved["likelihood_text"]:
        raise RuntimeError("preserved likelihood was modified")


def _append_refit(conn, run_id: str, fitted, preserved, adopted: bool, panel) -> None:
    if run_id == PRESERVED_ESTIMATION_RUN_ID:
        raise RuntimeError("refusing to write the preserved estimation run")
    calculation = preserved["calculation"]
    if not isinstance(calculation, dict):
        raise RuntimeError("preserved calculation is missing")
    if adopted and not fitted.maximum_likelihood_claimed:
        raise RuntimeError("an unverified gradient cannot become the parameter version")
    now = datetime.now(UTC)
    claim = (
        "The gradient condition was met."
        if fitted.maximum_likelihood_claimed
        else "Maximum likelihood is not claimed because the gradient condition failed."
    )
    payload = {
        "specification": METHOD_ID,
        "sample_levels": calculation.get("sample_levels"),
        "growth_start": calculation.get("growth_start"),
        "loadings_ip_income_sales_payroll": list(fitted.loadings),
        "factor_ar": list(fitted.factor_ar),
        "idiosyncratic_ar": [list(pair) for pair in fitted.idiosyncratic_ar],
        "idiosyncratic_scale": list(fitted.idiosyncratic_scale),
        "log_likelihood": fitted.log_likelihood,
        "filtered_factor": list(fitted.filtered_factor),
        "smoothed_factor": list(fitted.smoothed_factor),
        "filtered_factor_is_not_the_smoother": True,
        "moments": calculation.get("moments"),
        "real_time": False,
        "publication_allowed": False,
        "operationally_accepted": False,
        "input_vintage": "latest_revised",
        "update_kind": "reestimate",
        "adopted_parameter_version": adopted,
        "maximum_likelihood_claimed": fitted.maximum_likelihood_claimed,
        "gradient_norm": _json_float(fitted.gradient_norm),
        "gradient_norm_wide_step": _json_float(fitted.gradient_norm_wide_step),
        "gradient_step": GRADIENT_STEP,
        "starts_evaluated": fitted.starts_evaluated,
        "optimizer_converged": fitted.converged,
        "optimizer_message": fitted.message,
        "preserved_run_id": PRESERVED_ESTIMATION_RUN_ID,
        "overwrote_preserved_run": False,
        "sources": list(DATASETS),
        "not_a_gdp_nowcast": True,
    }
    narrative = (
        "Re-estimate of the 1988 coincident orders on the modern panel. "
        f"{claim} publication_allowed is false. "
        "The refit is not operationally accepted. "
        f"Preserved run {PRESERVED_ESTIMATION_RUN_ID} was not overwritten. "
        f"{NOT_THE_CITIBASE_SPECIFICATION}"
    )
    run = ResearchRun(
        run_id=run_id,
        executed_at=now,
        execution_status="completed",
        dataset_id=DATASETS[0],
        input_dataset_ids=list(DATASETS),
        source_id=str(preserved["source_id"]),
        rights_record_id=str(preserved["rights_record_id"]),
        analysis_mode=AnalysisMode.LATEST_REVISED,
        analysis_type="coincident_factor",
        decision_at=now,
        evaluation_period=str(preserved["evaluation_period"]),
        method_id=METHOD_ID,
        method_version="0.1.0",
        implementation_hash=modern_refit_implementation_hash(),
        config_id="sw1988-modern-multistart",
        config_hash="sw1988-modern-multistart",
        input_snapshot_hash=hashlib.sha256(repr(panel).encode("utf-8")).hexdigest(),
        data_sufficiency="sufficient",
        calculation=payload,
        statistical_interpretation=(
            "Multi-start re-estimate on the latest revised panel. "
            f"{claim} The filtered factor is not the smoother, not a real-time vintage, "
            "and not a GDP nowcast. "
            f"{NOT_THE_CITIBASE_SPECIFICATION}"
        ),
        causal_hypothesis="none",
        investment_implication="no_action",
        assumptions=[
            "Training-sample standardisation is the preserved run's moments.",
            "The path is latest revised.",
            NOT_THE_CITIBASE_SPECIFICATION,
        ],
        limitations=[
            "publication_allowed is false.",
            "The refit is not operationally accepted.",
            "The filtered factor is not the smoother.",
            claim,
        ],
        observation_ids=[],
        reproduction={
            "update_kind": "reestimate",
            "preserved_run_id": PRESERVED_ESTIMATION_RUN_ID,
            "overwrote_preserved_run": "false",
            "maximum_likelihood_claimed": str(fitted.maximum_likelihood_claimed).lower(),
            "adopted_parameter_version": str(adopted).lower(),
        },
        narrative=narrative,
        publication_allowed=False,
    )
    if run.publication_allowed:
        raise RuntimeError("publication_allowed must stay false")
    save_research_run(conn, run)
