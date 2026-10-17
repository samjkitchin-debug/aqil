"""Execution-scoped research artefacts (not durable database storage)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from aqil_research.contracts.observation import EconomicObservation
from aqil_research.pipeline.models import ResearchRun


@dataclass(frozen=True, slots=True)
class ResearchArtefact:
    """Serializable bundle for reproduction within the same execution or export."""

    run: ResearchRun
    observations: tuple[EconomicObservation, ...]
    diagnostics: dict[str, Any]
    research_note: str
    persistence: str = "execution_only_in_memory"

    def to_json(self) -> str:
        payload = {
            "persistence": self.persistence,
            "diagnostics": self.diagnostics,
            "research_note": self.research_note,
            "run": self.run.model_dump(mode="json"),
            "observations": [
                row.model_dump(mode="json", exclude_none=True) for row in self.observations
            ],
        }
        return json.dumps(payload, indent=2, sort_keys=True)
