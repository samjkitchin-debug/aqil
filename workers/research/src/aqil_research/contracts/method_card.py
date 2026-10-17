"""Methodology card v1 — registry metadata for deterministic methods."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class EvidenceStage(StrEnum):
    DOCUMENTED = "documented"
    IMPLEMENTED = "implemented"
    REPLICATED = "replicated"
    HISTORICALLY_EVALUATED = "historically_evaluated"
    PROSPECTIVELY_TESTING = "prospectively_testing"
    PROSPECTIVELY_SUPPORTED = "prospectively_supported"
    DEGRADED = "degraded"
    RETIRED = "retired"


class LicenceStatus(StrEnum):
    UNKNOWN = "unknown"
    PERMITTED_PRIVATE = "permitted_private"
    PERMITTED_PUBLIC = "permitted_public"
    RESTRICTED = "restricted"


class MethodCard(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = Field(default="1.0")
    method_id: str = Field(min_length=1)
    method_version: str = Field(min_length=1)
    name: str = Field(min_length=1)
    research_question: str = Field(min_length=1)
    primary_reference: str = Field(min_length=1)
    original_universe: str = Field(min_length=1)
    original_horizon: str | None = None
    formula_specification: str | None = None
    data_requirements: list[str]
    assumptions: list[str]
    limitations: list[str]
    evidence_stage: EvidenceStage
    implementation_hash: str | None = None
    licence_status: LicenceStatus = LicenceStatus.UNKNOWN
    reviewer_id: str | None = None
