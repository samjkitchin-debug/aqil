"""Analytical method contract — deterministic calculation on normalised observations."""

from __future__ import annotations

from dataclasses import dataclass
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


class AnalyticalMethod(Protocol):
    method_id: str
    method_version: str

    def implementation_hash(self) -> str: ...

    def required_dataset_ids(self) -> tuple[str, ...]: ...

    def parse_config(self, payload: dict[str, object]) -> BaseModel: ...

    def config_hash(self, config: BaseModel) -> str: ...

    def run(self, context: MethodContext, config: BaseModel) -> MethodExecutionResult: ...
