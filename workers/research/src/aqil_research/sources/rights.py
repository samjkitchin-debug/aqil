"""Typed source-rights register.

Unknown and prohibited decisions block the named operation. Disabling a source
blocks every operation without deleting its rights record. The loader accepts
any dataset row that matches the column contract, so a future provider does not
require a loader change.
"""

from __future__ import annotations

import csv
from datetime import date
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

REGISTER_FILENAME = "SOURCE_RIGHTS.csv"


class SourceRightsError(Exception):
    """Raised when a rights record or register is not usable."""


class RightsDecision(StrEnum):
    PERMITTED = "permitted"
    PROHIBITED = "prohibited"
    UNKNOWN = "unknown"


class AttributionRequirement(StrEnum):
    REQUIRED = "required"
    NOT_REQUIRED = "not_required"
    UNKNOWN = "unknown"


class OperationalStatus(StrEnum):
    ENABLED = "enabled"
    DISABLED = "disabled"


class M1Role(StrEnum):
    FIRST_LIVE_PROVIDER = "first_live_provider"
    YIELD_CURVE_CANDIDATE = "yield_curve_candidate"
    NOT_A_MODEL_INPUT = "not_a_model_input"
    INELIGIBLE = "ineligible"
    UNRESOLVED = "unresolved"


class RightsOperation(StrEnum):
    AUTOMATED_ACCESS = "automated_access"
    INTERNAL_COMPUTATION = "internal_computation"
    RAW_DATA_RETENTION = "raw_data_retention"
    HISTORICAL_ARCHIVING = "historical_archiving"
    REDISTRIBUTION = "redistribution"
    COMMERCIAL_PUBLICATION = "commercial_publication"
    AI_PROCESSING = "ai_processing"
    AI_MODEL_TRAINING = "ai_model_training"


FIRST_LIVE_OPERATIONS: tuple[RightsOperation, ...] = (
    RightsOperation.AUTOMATED_ACCESS,
    RightsOperation.INTERNAL_COMPUTATION,
    RightsOperation.RAW_DATA_RETENTION,
    RightsOperation.HISTORICAL_ARCHIVING,
    RightsOperation.REDISTRIBUTION,
    RightsOperation.COMMERCIAL_PUBLICATION,
)

REGISTER_COLUMNS: tuple[str, ...] = (
    "source_id",
    "dataset_id",
    "provider_name",
    "publication_name",
    "geography",
    "series_or_dataset_code",
    "category",
    "access_description",
    "access_url",
    "terms_url",
    "evidence_urls",
    "auth_requirement",
    "automated_access",
    "internal_computation",
    "raw_data_retention",
    "historical_archiving",
    "redistribution",
    "commercial_publication",
    "ai_processing",
    "ai_model_training",
    "attribution",
    "m1_role",
    "operational_status",
    "conditions",
    "revision_behaviour",
    "unresolved_questions",
    "evidence_note",
    "assessed_on",
)


def operation_allowed(record: SourceRightsRecord, operation: RightsOperation) -> bool:
    """Return whether the rights decision explicitly permits this operation."""
    return record.decision_for(operation) == RightsDecision.PERMITTED


def source_usable(record: SourceRightsRecord, operation: RightsOperation) -> bool:
    """Return whether an enabled source may perform this operation."""
    return record.operational_status == OperationalStatus.ENABLED and operation_allowed(
        record,
        operation,
    )


def blocked_operations(
    record: SourceRightsRecord,
    operations: tuple[RightsOperation, ...],
) -> tuple[RightsOperation, ...]:
    return tuple(operation for operation in operations if not operation_allowed(record, operation))


class SourceRightsRecord(BaseModel):
    """One dataset's rights decisions. Silence is not permission."""

    model_config = ConfigDict(extra="forbid")

    source_id: str = Field(min_length=1)
    dataset_id: str = Field(min_length=1)
    provider_name: str = Field(min_length=1)
    publication_name: str = Field(min_length=1)
    geography: str = Field(min_length=1)
    series_or_dataset_code: str = Field(min_length=1)
    category: str = Field(min_length=1)
    access_description: str = Field(min_length=1)
    access_url: str
    terms_url: str
    evidence_urls: tuple[str, ...]
    auth_requirement: str = Field(min_length=1)
    automated_access: RightsDecision
    internal_computation: RightsDecision
    raw_data_retention: RightsDecision
    historical_archiving: RightsDecision
    redistribution: RightsDecision
    commercial_publication: RightsDecision
    ai_processing: RightsDecision
    ai_model_training: RightsDecision
    attribution: AttributionRequirement
    m1_role: M1Role
    operational_status: OperationalStatus
    conditions: str = Field(min_length=1)
    revision_behaviour: str = Field(min_length=1)
    unresolved_questions: str = Field(min_length=1)
    evidence_note: str = Field(min_length=1)
    assessed_on: date

    @field_validator("access_url", "terms_url")
    @classmethod
    def https_url(cls, value: str) -> str:
        _require_https(value)
        return value

    @field_validator("evidence_urls")
    @classmethod
    def https_evidence(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value:
            raise ValueError("at least one evidence URL is required")
        for url in value:
            _require_https(url)
        return value

    @model_validator(mode="after")
    def evidence_covers_terms(self) -> SourceRightsRecord:
        if self.terms_url not in self.evidence_urls:
            raise ValueError(f"{self.source_id} terms_url is not listed in evidence_urls")
        return self

    @model_validator(mode="after")
    def first_live_provider_is_cleared(self) -> SourceRightsRecord:
        if self.m1_role != M1Role.FIRST_LIVE_PROVIDER:
            return self
        blocked = blocked_operations(self, FIRST_LIVE_OPERATIONS)
        if blocked or self.attribution == AttributionRequirement.UNKNOWN:
            names = ", ".join(operation.value for operation in blocked) or "none"
            raise ValueError(
                f"{self.source_id} is not cleared for first live use "
                f"(blocked: {names}; attribution: {self.attribution.value})",
            )
        return self

    def decision_for(self, operation: RightsOperation) -> RightsDecision:
        return RightsDecision(getattr(self, operation.value))


def default_register_path() -> Path:
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "docs" / "sources" / REGISTER_FILENAME
        if candidate.is_file():
            return candidate
    raise SourceRightsError(f"{REGISTER_FILENAME} was not found from the worker package")


def find_source_rights(
    records: tuple[SourceRightsRecord, ...],
    *,
    source_id: str | None = None,
    dataset_id: str | None = None,
) -> SourceRightsRecord | None:
    """Resolve a rights row. source_id, when provided, must match exactly."""
    if source_id is not None:
        for record in records:
            if record.source_id == source_id:
                return record
        return None
    if dataset_id is not None:
        for record in records:
            if record.dataset_id == dataset_id:
                return record
    return None


def load_source_rights(path: Path | None = None) -> tuple[SourceRightsRecord, ...]:
    """Load and validate a rights register. This function does not contact providers."""
    register_path = path or default_register_path()
    with register_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise SourceRightsError(f"{register_path} has no header")
        if tuple(reader.fieldnames) != REGISTER_COLUMNS:
            raise SourceRightsError(
                f"{register_path} columns do not match the rights register contract",
            )
        records: list[SourceRightsRecord] = []
        seen: set[str] = set()
        for line_number, row in enumerate(reader, start=2):
            source_id = (row.get("source_id") or "").strip()
            if source_id in seen:
                raise SourceRightsError(f"duplicate source_id {source_id} at line {line_number}")
            seen.add(source_id)
            try:
                records.append(_record_from_row(row))
            except ValueError as exc:
                raise SourceRightsError(f"{register_path}:{line_number}: {exc}") from exc
    if not records:
        raise SourceRightsError(f"{register_path} has no dataset rows")
    return tuple(records)


def _record_from_row(row: dict[str, str | None]) -> SourceRightsRecord:
    evidence = tuple(
        part.strip() for part in (row.get("evidence_urls") or "").split("|") if part.strip()
    )
    payload: dict[str, object] = {
        column: (row.get(column) or "").strip() for column in REGISTER_COLUMNS
    }
    payload["evidence_urls"] = evidence
    return SourceRightsRecord.model_validate(payload)


def _require_https(value: str) -> None:
    if not value.startswith("https://"):
        raise ValueError("rights evidence URLs must use https")
