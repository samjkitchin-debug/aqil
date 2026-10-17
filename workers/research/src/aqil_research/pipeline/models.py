"""Structured research run inputs and outputs."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from aqil_research.contracts.observation import AnalysisMode
from aqil_research.methods.sahm import SahmConfig


class ResearchExecutionRequest(BaseModel):
    """Configuration-driven research request."""

    model_config = ConfigDict(extra="forbid")

    source_id: str = Field(min_length=1)
    dataset_id: str = Field(min_length=1)
    decision_at: datetime
    analysis_mode: AnalysisMode
    evaluation_period: str
    method_id: str = Field(min_length=1)
    method_config: dict[str, object]
    collect: bool = False
    primary_adapter_id: str | None = None
    optional_adapter_ids: tuple[str, ...] = ()


class ResearchRunRequest(BaseModel):
    """Sahm shortcut request (Phase 1–2 compatibility)."""

    model_config = ConfigDict(extra="forbid")

    dataset_id: str = Field(min_length=1)
    decision_at: datetime
    analysis_mode: AnalysisMode
    evaluation_period: str
    sahm_config: SahmConfig
    method_version: str = Field(min_length=1)
    source_id: str = Field(default="bls_cps_unemployment_rate", min_length=1)


class ResearchRun(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    executed_at: datetime
    execution_status: Literal[
        "completed",
        "completed_insufficient",
        "failed_rights",
        "failed_ingest",
        "failed_method",
    ]
    dataset_id: str
    input_dataset_ids: list[str] = Field(default_factory=list)
    source_id: str
    rights_record_id: str
    analysis_mode: AnalysisMode
    analysis_type: str
    decision_at: datetime
    evaluation_period: str
    method_id: str
    method_version: str
    implementation_hash: str
    config_id: str
    config_hash: str
    input_snapshot_hash: str
    analytical_payload_hash: str = ""
    data_sufficiency: Literal["sufficient", "insufficient"]
    missing_data_reason: str | None = None
    calculation: dict[str, object] | None = None
    statistical_interpretation: str
    causal_hypothesis: str
    market_pricing: Literal["unknown"] = "unknown"
    investment_implication: Literal["no_action", "insufficient_evidence"]
    assumptions: list[str]
    limitations: list[str]
    observation_ids: list[str]
    adapter_ids: list[str] = Field(default_factory=list)
    ingest_notes: list[str] = Field(default_factory=list)
    reproduction: dict[str, str]
    narrative: str
    publication_allowed: bool = False
    verification_status: Literal["unverified"] = "unverified"
    evidence_reasons: list[str] = Field(default_factory=list)


# Backward-compatible alias
ResearchResult = ResearchRun
