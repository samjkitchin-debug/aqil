"""Structured research insight contract (v1)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ChartPoint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    period: str
    value: float


class ResearchInsight(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "1.0"
    insight_id: str
    run_id: str
    generated_at: datetime
    headline: str
    what_changed: str
    why_it_matters: str
    historical_context: str
    investor_implications: str
    confidence_and_limitations: str
    what_comes_next: str
    method_id: str
    method_version: str
    dataset_id: str
    analysis_mode: str
    data_provenance: Literal["latest_revised", "provider_vintage", "first_seen_by_aqil"]
    publication_status: Literal["internal_preview", "not_eligible", "blocked"]
    verification_status: str
    calculation_summary: dict[str, object]
    source_attribution: str
    observation_ids: list[str]
    analytical_payload_hash: str = ""
    evidence_reasons: list[str] = Field(default_factory=list)
    chart_points: list[ChartPoint] = Field(default_factory=list)
