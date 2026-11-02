"""Analytical method contract — deterministic calculation on normalised observations."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Literal, Protocol

from pydantic import BaseModel

from aqil_research.contracts.observation import AnalysisMode, EconomicObservation


@dataclass(frozen=True, slots=True)
class MethodContext:
    inputs_by_dataset: dict[str, dict[date, EconomicObservation]]
    evaluation_period: date
    analysis_mode: AnalysisMode
    primary_dataset_id: str
    all_vintages_by_dataset: dict[str, tuple[EconomicObservation, ...]] = field(
        default_factory=dict,
    )

    def primary_series(self) -> dict[date, EconomicObservation]:
        series = self.inputs_by_dataset.get(self.primary_dataset_id)
        if series is None:
            raise ValueError(f"missing primary dataset {self.primary_dataset_id}")
        return series

    @property
    def by_period(self) -> dict[date, EconomicObservation]:
        """Backward-compatible alias for the primary input series."""
        return self.primary_series()

    @property
    def input_dataset_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self.inputs_by_dataset))


@dataclass(frozen=True, slots=True)
class MethodExecutionResult:
    sufficiency: Literal["sufficient", "insufficient"]
    calculation: dict[str, object] | None
    observation_ids: tuple[str, ...]
    assumptions: tuple[str, ...]
    limitations: tuple[str, ...]
    missing_reason: str | None
    statistical_interpretation: str
    causal_hypothesis: str
    investment_implication: Literal["no_action", "insufficient_evidence"]
    narrative: str


ParameterPolicy = Literal["none", "fixed_accepted", "refit_separate"]
VintageClass = Literal["latest_revised"]
_KNOWN_FREQUENCIES = frozenset({"weekly", "monthly", "quarterly"})


@dataclass(frozen=True, slots=True)
class MethodDependency:
    """What a method reads, and whether a refit is a different command.

    ``new_observation_requires_recalculation`` is metadata. It does not install
    a trigger. ``vintage_class`` stays ``latest_revised`` until a lawful
    vintage panel exists.
    """

    source_series: tuple[str, ...]
    frequency: tuple[str, ...]
    minimum_history: str
    vintage_class: VintageClass
    parameter_policy: ParameterPolicy
    depends_on_method_ids: tuple[str, ...]
    new_observation_requires_recalculation: bool
    refit_is_different_command: bool


def bind_dependency(
    source_series: tuple[str, ...],
    *,
    frequency: tuple[str, ...],
    minimum_history: str,
    parameter_policy: ParameterPolicy,
    new_observation_requires_recalculation: bool,
    refit_is_different_command: bool,
    depends_on_method_ids: tuple[str, ...] = (),
) -> MethodDependency:
    """Build the one dependency record every registered method exposes."""
    if not source_series:
        raise ValueError("a method dependency needs at least one source series")
    if not frequency or any(item not in _KNOWN_FREQUENCIES for item in frequency):
        raise ValueError("frequency must be weekly, monthly, or quarterly")
    if not minimum_history.strip():
        raise ValueError("minimum history must state the gate the method already enforces")
    if parameter_policy == "refit_separate" and not refit_is_different_command:
        raise ValueError("refit_separate requires a separate refit command")
    if refit_is_different_command and parameter_policy != "refit_separate":
        raise ValueError("a separate refit command requires parameter policy refit_separate")
    return MethodDependency(
        source_series=source_series,
        frequency=frequency,
        minimum_history=minimum_history,
        vintage_class="latest_revised",
        parameter_policy=parameter_policy,
        depends_on_method_ids=depends_on_method_ids,
        new_observation_requires_recalculation=new_observation_requires_recalculation,
        refit_is_different_command=refit_is_different_command,
    )


class AnalyticalMethod(Protocol):
    method_id: str
    method_version: str

    def implementation_hash(self) -> str: ...

    def required_dataset_ids(self) -> tuple[str, ...]: ...

    def dependency(self) -> MethodDependency: ...

    def accepted_config_payload(self) -> dict[str, object]: ...

    def parse_config(self, payload: dict[str, object]) -> BaseModel: ...

    def config_hash(self, config: BaseModel) -> str: ...

    def run(self, context: MethodContext, config: BaseModel) -> MethodExecutionResult: ...
