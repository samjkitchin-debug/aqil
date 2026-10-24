"""Structural theme assessment v1.

Field names match docs/schemas/structural_theme_assessment.v1.json.
There is no strength, confidence or gauge.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

THEME_SCHEMA_FILE = "structural_theme_assessment.v1.json"

ThemeDimensionName = Literal[
    "infrastructure_investment",
    "commercial_adoption",
    "semiconductor_equipment_demand",
    "earnings_cash_flow",
    "market_breadth_relative_performance",
    "financing_sustainability",
]
DimensionStatus = Literal[
    "available",
    "stale",
    "insufficient",
    "contradictory",
    "not_yet_monitored",
]
MeasureKind = Literal[
    "actual_capital_expenditure",
    "forecast_spending",
    "actual_spending",
    "infrastructure_demand",
    "commercial_adoption",
    "revenue",
    "earnings",
    "equity_price",
    "none",
]
RecordClass = Literal["recorded", "synthetic_fixture"]

_FITS: dict[str, frozenset[str]] = {
    "infrastructure_investment": frozenset(
        {"actual_capital_expenditure", "forecast_spending", "none"}
    ),
    "commercial_adoption": frozenset({"commercial_adoption", "none"}),
    "semiconductor_equipment_demand": frozenset({"infrastructure_demand", "none"}),
    "earnings_cash_flow": frozenset({"revenue", "earnings", "none"}),
    "market_breadth_relative_performance": frozenset({"equity_price", "none"}),
    "financing_sustainability": frozenset({"none"}),
}


def structural_theme_schema_path() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "docs" / "schemas" / THEME_SCHEMA_FILE
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(THEME_SCHEMA_FILE)


def structural_theme_field_names() -> tuple[str, ...]:
    document = json.loads(structural_theme_schema_path().read_text(encoding="utf-8"))
    required = document["required"]
    if not isinstance(required, list) or not all(isinstance(name, str) for name in required):
        raise ValueError("theme schema required list is not a list of names")
    return tuple(required)


class ThemeDimensionEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dimension: ThemeDimensionName
    status: DimensionStatus
    measure_kind: MeasureKind
    explanation: str = Field(min_length=10, max_length=800)
    update_id: str | None = None
    amount: str | None = None
    unit: str | None = None
    period_start: date | None = None
    period_end: date | None = None
    reporting_entity: str | None = None
    filed_at: date | None = None
    relationship: Literal["supports", "contradicts"] | None = None

    @model_validator(mode="after")
    def measure_matches_dimension(self) -> ThemeDimensionEvidence:
        allowed = _FITS[self.dimension]
        if self.measure_kind not in allowed:
            raise ValueError(f"{self.measure_kind} is not evidence for {self.dimension}")
        if self.status == "available" and (self.update_id is None or self.measure_kind == "none"):
            raise ValueError("available evidence requires a sourced update")
        if self.status == "not_yet_monitored" and self.measure_kind != "none":
            raise ValueError("a dimension that is not yet monitored has no measure")
        return self


class StructuralThemeAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    assessment_id: str = Field(min_length=1)
    theme_key: Literal["ai_infrastructure_investment"] = "ai_infrastructure_investment"
    supersedes_assessment_id: str | None = None
    real_economy_activity: str = Field(min_length=10, max_length=800)
    earnings: str = Field(min_length=10, max_length=800)
    market_prices: str = Field(min_length=10, max_length=800)
    media_attention: str = Field(min_length=10, max_length=800)
    publication_allowed: Literal[False] = False
    record_class: RecordClass
    dimensions: list[ThemeDimensionEvidence]
