"""Structured collection operation results."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

CollectionOutcome = Literal[
    "success",
    "unchanged",
    "partial",
    "failed_fetch",
    "failed_rights",
    "failed_validation",
    "conflicts",
]


class CollectionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "1.0"
    source_id: str
    dataset_id: str
    provider_id: str
    adapter_id: str
    adapter_version: str
    collected_at: datetime
    collection_mode: Literal["live", "fixture", "replay"]
    outcome: CollectionOutcome
    retrieval_id: str | None = None
    response_fingerprint: str | None = None
    observations_received: int = 0
    observations_newly_stored: int = 0
    observations_unchanged: int = 0
    conflicts_detected: int = 0
    completeness: Literal["complete", "partial", "empty", "unknown"] = "unknown"
    rights_record_id: str
    rights_decision_summary: str
    data_provenance: Literal["latest_revised", "provider_vintage", "first_seen_by_aqil"]
    warnings: list[str] = Field(default_factory=list)
    ingest_notes: list[str] = Field(default_factory=list)
    next_recommended_action: str
    http_status: int | None = None
    provider_status: str | None = None
