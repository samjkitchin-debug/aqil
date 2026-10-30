"""Append one registered method run.

The default command calculates with the method's accepted configuration.
``--refit`` is refused unless the method declares a separate refit command.
No method currently does. Stock–Watson keeps ``fixed_accepted``: its registered
``run`` estimates, and a completed row that omits ``adopted_parameter_version``
is read as adopted. This module does not call that estimator and does not
write the preserved runs.

``new_observation_requires_recalculation`` on the dependency is metadata only.
Nothing here installs a trigger, a job, or a schedule.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime

import psycopg

from aqil_research.contracts.observation import AnalysisMode, EconomicObservation
from aqil_research.methods.protocol import AnalyticalMethod
from aqil_research.methods.registry import MethodRegistry, default_method_registry
from aqil_research.persistence.observation_store import PostgresResearchObservationStore
from aqil_research.persistence.runs import save_research_run
from aqil_research.pipeline.models import ResearchExecutionRequest, ResearchRun
from aqil_research.pipeline.orchestrate import execute_research_run
from aqil_research.sources.rights import load_source_rights
from aqil_research.sources.rights_gate import RightsGateError, resolve_research_rights_by_dataset
from aqil_research.vintages.store import AppendResult

# These rows stay as stored. A missing adopted_parameter_version on the first
# is the adopted parameter version. The second is explicitly unadopted.
PRESERVED_PARAMETER_RUN_ID = "3f8c7611-c2a1-44a0-8c7e-01bebbfe9a8a"
UNADOPTED_REESTIMATE_RUN_ID = "940955f1-50d5-4c06-9d90-5ceebd05d352"
PROTECTED_RUN_IDS = frozenset({PRESERVED_PARAMETER_RUN_ID, UNADOPTED_REESTIMATE_RUN_ID})


class MethodExecutionRefused(Exception):
    """The command is not available. No run is written."""


def execution_refusal(method: AnalyticalMethod, *, refit: bool) -> str | None:
    """Return the refusal text, or None when the default calculation may run."""
    dependency = method.dependency()
    if refit and not dependency.refit_is_different_command:
        return (
            f"Refit is not available for {method.method_id}. "
            "This method does not declare a separate refit command."
        )
    if refit:
        return (
            f"Refit is declared for {method.method_id} "
            "but this command has no separate refit entry."
        )
    if dependency.parameter_policy == "fixed_accepted":
        return (
            f"Calculation with the accepted parameters is not available for {method.method_id}. "
            "The registered run estimates a new parameter vector, and a stored row without "
            "adopted_parameter_version is treated as adopted. Refit is not available, so this "
            "command will not append an estimate and will not replace the preserved "
            "parameter version."
        )
    return None


@dataclass(slots=True)
class PeriodCutoffStore:
    """Read the inner store, dropping periods after an optional cutoff."""

    inner: PostgresResearchObservationStore
    cutoff: date | None

    def append(self, observation: EconomicObservation) -> AppendResult:
        raise RuntimeError("the method executor does not append observations")

    def append_many(self, observations: tuple[EconomicObservation, ...]) -> AppendResult:
        raise RuntimeError("the method executor does not append observations")

    def all_observations(self) -> tuple[EconomicObservation, ...]:
        return _within_cutoff(self.inner.all_observations(), self.cutoff)

    def as_of(
        self,
        dataset_id: str,
        decision_at: datetime,
        mode: AnalysisMode,
    ) -> dict[date, EconomicObservation]:
        series = self.inner.as_of(dataset_id, decision_at, mode)
        if self.cutoff is None:
            return series
        return {period: row for period, row in series.items() if period <= self.cutoff}


def execute_registered_method(
    conn: psycopg.Connection,
    method_id: str,
    *,
    cutoff: date | None = None,
    refit: bool = False,
    registry: MethodRegistry | None = None,
    executed_at: datetime | None = None,
) -> ResearchRun:
    """Load required series from this connection, run the method, and append."""
    chosen = registry if registry is not None else default_method_registry()
    method = chosen.get(method_id)
    refusal = execution_refusal(method, refit=refit)
    if refusal is not None:
        raise MethodExecutionRefused(refusal)

    wall = executed_at or datetime.now(tz=UTC)
    if wall.tzinfo is None:
        wall = wall.replace(tzinfo=UTC)
    rights_records = load_source_rights()
    primary = method.required_dataset_ids()[0]
    try:
        rights = resolve_research_rights_by_dataset(rights_records, dataset_id=primary)
    except RightsGateError as exc:
        raise MethodExecutionRefused(str(exc)) from exc

    store = PeriodCutoffStore(PostgresResearchObservationStore(conn), cutoff)
    series = store.as_of(primary, wall, AnalysisMode.LATEST_REVISED)
    if series:
        evaluation = max(series)
    elif cutoff is not None:
        evaluation = cutoff
    else:
        evaluation = wall.date().replace(day=1)

    run = execute_research_run(
        ResearchExecutionRequest(
            source_id=rights.source_id,
            dataset_id=primary,
            decision_at=wall,
            analysis_mode=AnalysisMode.LATEST_REVISED,
            evaluation_period=evaluation.isoformat(),
            method_id=method.method_id,
            method_config=method.accepted_config_payload(),
            collect=False,
        ),
        store=store,
        rights_records=rights_records,
        method_registry=chosen,
        executed_at=wall,
    )
    if run.publication_allowed:
        raise RuntimeError("publication_allowed must stay false")
    if run.calculation is not None and run.calculation.get("publication_allowed") is True:
        raise RuntimeError("publication_allowed must stay false")
    if run.run_id in PROTECTED_RUN_IDS:
        raise RuntimeError("refusing to write a preserved research run")
    save_research_run(conn, run)
    return run


def _within_cutoff(
    rows: tuple[EconomicObservation, ...],
    cutoff: date | None,
) -> tuple[EconomicObservation, ...]:
    if cutoff is None:
        return rows
    return tuple(row for row in rows if row.period_start <= cutoff)
