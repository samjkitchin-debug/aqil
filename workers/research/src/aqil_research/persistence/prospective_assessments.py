"""Append-only persistence for research.prospective_assessments.

A later revision is a new row. This module does not store a forecast, and it
does not rewrite an earlier assessment.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime
from typing import Any

import psycopg
from psycopg.rows import dict_row

from aqil_research.persistence.test_database import (
    assert_connected_test_database,
    running_under_pytest,
)

CAPTURE_NOTE_PHRASE = "not a reconstruction of dates before captured_at"
REVISION_CLASS = "latest_revised"
PUBLICATION_ALLOWED = False

# Frozen into input_hash. assessment_id, created_at, and the hashes stay out.
INPUT_HASH_FIELDS = (
    "captured_at",
    "captured_values",
    "completeness",
    "method_versions",
    "observation_ids",
    "parameter_hashes",
    "publication_timestamps",
    "retrieval_timestamps",
    "run_ids",
    "unavailable_inputs",
)

# Frozen into output_hash. publication_allowed stays false in this object.
OUTPUT_HASH_FIELDS = (
    "assessment_id",
    "capture_note",
    "contradiction_text",
    "created_at",
    "evaluation_due",
    "horizon_months",
    "lifecycle_status",
    "publication_allowed",
    "revision_class",
    "supersedes_assessment_id",
    "support_text",
    "uncertainty_text",
)

_LIFECYCLE_STATUSES = frozenset(
    {
        "not_qualified",
        "proposed_internal",
        "superseded",
        "evaluated",
    }
)
_FORECAST_KEYS = frozenset(
    {
        "forecast",
        "direction",
        "probability",
        "expected_return",
        "recommendation",
    }
)
_HASH_RE = re.compile(r"^[0-9a-f]{64}$")


class ProspectiveAssessmentPersistenceError(RuntimeError):
    """The assessment cannot be stored."""


def payload_document_hash(document: Mapping[str, Any]) -> str:
    """SHA-256 of one canonical JSON object."""
    encoded = json.dumps(document, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def stored_payload(row: StoredProspectiveAssessment) -> dict[str, dict[str, Any]]:
    """Rebuild the hashed input and output documents from a stored row."""
    payload = {
        "input": {
            "captured_at": _iso_timestamp(row.captured_at),
            "captured_values": row.captured_values,
            "completeness": row.completeness,
            "method_versions": row.method_versions,
            "observation_ids": list(row.observation_ids),
            "parameter_hashes": row.parameter_hashes,
            "publication_timestamps": list(row.publication_timestamps),
            "retrieval_timestamps": list(row.retrieval_timestamps),
            "run_ids": list(row.run_ids),
            "unavailable_inputs": list(row.unavailable_inputs),
        },
        "output": {
            "assessment_id": row.assessment_id,
            "capture_note": row.capture_note,
            "contradiction_text": row.contradiction_text,
            "created_at": _iso_timestamp(row.created_at),
            "evaluation_due": None
            if row.evaluation_due is None
            else row.evaluation_due.isoformat(),
            "horizon_months": row.horizon_months,
            "lifecycle_status": row.lifecycle_status,
            "publication_allowed": row.publication_allowed,
            "revision_class": row.revision_class,
            "supersedes_assessment_id": row.supersedes_assessment_id,
            "support_text": row.support_text,
            "uncertainty_text": row.uncertainty_text,
        },
    }
    if set(payload["input"]) != set(INPUT_HASH_FIELDS):
        raise ProspectiveAssessmentPersistenceError("input hash fields drifted")
    if set(payload["output"]) != set(OUTPUT_HASH_FIELDS):
        raise ProspectiveAssessmentPersistenceError("output hash fields drifted")
    return payload


def insert_prospective_assessment(
    conn: psycopg.Connection,
    draft: ProspectiveAssessmentDraft,
) -> StoredProspectiveAssessment:
    """Insert one assessment. Hashes are computed from the stored payload shape."""
    _validate_draft(draft)
    _refuse_preserved_database(conn)
    captured_values = _copy_observation_values(draft.observation_ids, draft.captured_values)
    payload = stored_payload(
        StoredProspectiveAssessment(
            assessment_id=draft.assessment_id,
            created_at=draft.created_at,
            captured_at=draft.captured_at,
            lifecycle_status=draft.lifecycle_status,
            publication_allowed=PUBLICATION_ALLOWED,
            revision_class=REVISION_CLASS,
            completeness=draft.completeness,
            horizon_months=draft.horizon_months,
            evaluation_due=draft.evaluation_due,
            run_ids=draft.run_ids,
            observation_ids=draft.observation_ids,
            captured_values=captured_values,
            retrieval_timestamps=draft.retrieval_timestamps,
            publication_timestamps=draft.publication_timestamps,
            method_versions=dict(draft.method_versions),
            parameter_hashes=dict(draft.parameter_hashes),
            support_text=draft.support_text,
            contradiction_text=draft.contradiction_text,
            uncertainty_text=draft.uncertainty_text,
            unavailable_inputs=draft.unavailable_inputs,
            input_hash="",
            output_hash="",
            supersedes_assessment_id=draft.supersedes_assessment_id,
            capture_note=draft.capture_note,
        )
    )
    _reject_forecast(payload)
    input_hash = payload_document_hash(payload["input"])
    output_hash = payload_document_hash(payload["output"])
    if _HASH_RE.fullmatch(input_hash) is None or _HASH_RE.fullmatch(output_hash) is None:
        raise ProspectiveAssessmentPersistenceError("payload hash was not a sha256 digest")

    with conn.cursor() as cur:
        cur.execute(
            """
            insert into research.prospective_assessments (
              assessment_id, created_at, captured_at, lifecycle_status,
              publication_allowed, revision_class, completeness, horizon_months,
              evaluation_due, run_ids, observation_ids, captured_values,
              retrieval_timestamps, publication_timestamps, method_versions,
              parameter_hashes, support_text, contradiction_text, uncertainty_text,
              unavailable_inputs, input_hash, output_hash, supersedes_assessment_id,
              capture_note
            )
            values (
              %s, %s, %s, %s, %s, %s, %s, %s, %s,
              %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb,
              %s::jsonb, %s::jsonb, %s, %s, %s, %s::jsonb, %s, %s, %s, %s
            )
            """,
            (
                draft.assessment_id,
                draft.created_at,
                draft.captured_at,
                draft.lifecycle_status,
                PUBLICATION_ALLOWED,
                REVISION_CLASS,
                draft.completeness,
                draft.horizon_months,
                draft.evaluation_due,
                psycopg.types.json.Json(payload["input"]["run_ids"]),
                psycopg.types.json.Json(payload["input"]["observation_ids"]),
                psycopg.types.json.Json(payload["input"]["captured_values"]),
                psycopg.types.json.Json(payload["input"]["retrieval_timestamps"]),
                psycopg.types.json.Json(payload["input"]["publication_timestamps"]),
                psycopg.types.json.Json(payload["input"]["method_versions"]),
                psycopg.types.json.Json(payload["input"]["parameter_hashes"]),
                draft.support_text,
                draft.contradiction_text,
                draft.uncertainty_text,
                psycopg.types.json.Json(payload["input"]["unavailable_inputs"]),
                input_hash,
                output_hash,
                draft.supersedes_assessment_id,
                draft.capture_note,
            ),
        )
    return load_prospective_assessment(conn, draft.assessment_id)


def load_prospective_assessment(
    conn: psycopg.Connection,
    assessment_id: str,
) -> StoredProspectiveAssessment:
    """Load one stored assessment."""
    _refuse_preserved_database(conn)
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            select
              assessment_id, created_at, captured_at, lifecycle_status,
              publication_allowed, revision_class, completeness, horizon_months,
              evaluation_due, run_ids, observation_ids, captured_values,
              retrieval_timestamps, publication_timestamps, method_versions,
              parameter_hashes, support_text, contradiction_text, uncertainty_text,
              unavailable_inputs, input_hash, output_hash, supersedes_assessment_id,
              capture_note
            from research.prospective_assessments
            where assessment_id = %s
            """,
            (assessment_id,),
        )
        row = cur.fetchone()
    if row is None:
        raise ProspectiveAssessmentPersistenceError(f"assessment not found: {assessment_id}")
    stored = _row_to_stored(row)
    if stored.publication_allowed is not False:
        raise ProspectiveAssessmentPersistenceError("publication_allowed must be false")
    if stored.revision_class != REVISION_CLASS:
        raise ProspectiveAssessmentPersistenceError("revision_class must be latest_revised")
    return stored


class ProspectiveAssessmentDraft:
    """Fields the caller supplies. Publication and revision class are fixed."""

    def __init__(
        self,
        *,
        assessment_id: str,
        created_at: datetime,
        captured_at: datetime,
        lifecycle_status: str,
        completeness: str,
        run_ids: Sequence[str],
        observation_ids: Sequence[str],
        captured_values: Mapping[str, Any],
        retrieval_timestamps: Sequence[str],
        publication_timestamps: Sequence[str],
        method_versions: Mapping[str, str],
        parameter_hashes: Mapping[str, str],
        support_text: str,
        contradiction_text: str,
        uncertainty_text: str,
        unavailable_inputs: Sequence[str],
        capture_note: str,
        horizon_months: int | None = None,
        evaluation_due: date | None = None,
        supersedes_assessment_id: str | None = None,
    ) -> None:
        self.assessment_id = assessment_id
        self.created_at = created_at
        self.captured_at = captured_at
        self.lifecycle_status = lifecycle_status
        self.completeness = completeness
        self.run_ids = tuple(run_ids)
        self.observation_ids = tuple(observation_ids)
        self.captured_values = dict(captured_values)
        self.retrieval_timestamps = tuple(retrieval_timestamps)
        self.publication_timestamps = tuple(publication_timestamps)
        self.method_versions = dict(method_versions)
        self.parameter_hashes = dict(parameter_hashes)
        self.support_text = support_text
        self.contradiction_text = contradiction_text
        self.uncertainty_text = uncertainty_text
        self.unavailable_inputs = tuple(unavailable_inputs)
        self.capture_note = capture_note
        self.horizon_months = horizon_months
        self.evaluation_due = evaluation_due
        self.supersedes_assessment_id = supersedes_assessment_id


class StoredProspectiveAssessment:
    """One row as read back from research.prospective_assessments."""

    def __init__(
        self,
        *,
        assessment_id: str,
        created_at: datetime,
        captured_at: datetime,
        lifecycle_status: str,
        publication_allowed: bool,
        revision_class: str,
        completeness: str,
        horizon_months: int | None,
        evaluation_due: date | None,
        run_ids: tuple[str, ...],
        observation_ids: tuple[str, ...],
        captured_values: dict[str, Any],
        retrieval_timestamps: tuple[str, ...],
        publication_timestamps: tuple[str, ...],
        method_versions: dict[str, str],
        parameter_hashes: dict[str, str],
        support_text: str,
        contradiction_text: str,
        uncertainty_text: str,
        unavailable_inputs: tuple[str, ...],
        input_hash: str,
        output_hash: str,
        supersedes_assessment_id: str | None,
        capture_note: str,
    ) -> None:
        self.assessment_id = assessment_id
        self.created_at = created_at
        self.captured_at = captured_at
        self.lifecycle_status = lifecycle_status
        self.publication_allowed = publication_allowed
        self.revision_class = revision_class
        self.completeness = completeness
        self.horizon_months = horizon_months
        self.evaluation_due = evaluation_due
        self.run_ids = run_ids
        self.observation_ids = observation_ids
        self.captured_values = captured_values
        self.retrieval_timestamps = retrieval_timestamps
        self.publication_timestamps = publication_timestamps
        self.method_versions = method_versions
        self.parameter_hashes = parameter_hashes
        self.support_text = support_text
        self.contradiction_text = contradiction_text
        self.uncertainty_text = uncertainty_text
        self.unavailable_inputs = unavailable_inputs
        self.input_hash = input_hash
        self.output_hash = output_hash
        self.supersedes_assessment_id = supersedes_assessment_id
        self.capture_note = capture_note

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, StoredProspectiveAssessment):
            return NotImplemented
        return self.__dict__ == other.__dict__


def _copy_observation_values(
    observation_ids: Sequence[str],
    captured_values: Mapping[str, Any],
) -> dict[str, str]:
    """Copy each observation id and its value into the stored object."""
    if not isinstance(captured_values, Mapping):
        raise ProspectiveAssessmentPersistenceError(
            "captured_values must copy observation ids and values"
        )
    if len(tuple(observation_ids)) != len(set(observation_ids)):
        raise ProspectiveAssessmentPersistenceError("observation ids must be unique")
    if set(captured_values) != set(observation_ids):
        raise ProspectiveAssessmentPersistenceError(
            "captured_values must copy each observation id and value"
        )
    copied: dict[str, str] = {}
    for observation_id in observation_ids:
        if not isinstance(observation_id, str) or observation_id == "":
            raise ProspectiveAssessmentPersistenceError("observation_id is required")
        value = captured_values[observation_id]
        if not isinstance(value, str):
            raise ProspectiveAssessmentPersistenceError("observation values are copied as text")
        copied[observation_id] = value
    return copied


def _validate_draft(draft: ProspectiveAssessmentDraft) -> None:
    if draft.lifecycle_status not in _LIFECYCLE_STATUSES:
        raise ProspectiveAssessmentPersistenceError("lifecycle_status is not recognised")
    if draft.horizon_months not in {None, 6, 12}:
        raise ProspectiveAssessmentPersistenceError("horizon_months must be null, 6, or 12")
    if CAPTURE_NOTE_PHRASE not in draft.capture_note:
        raise ProspectiveAssessmentPersistenceError(
            "capture_note must contain the exact phrase: "
            "not a reconstruction of dates before captured_at"
        )
    _copy_observation_values(draft.observation_ids, draft.captured_values)
    _iso_timestamp(draft.created_at)
    _iso_timestamp(draft.captured_at)
    for name, values in (
        ("run_ids", draft.run_ids),
        ("observation_ids", draft.observation_ids),
        ("retrieval_timestamps", draft.retrieval_timestamps),
        ("publication_timestamps", draft.publication_timestamps),
        ("unavailable_inputs", draft.unavailable_inputs),
    ):
        if any(not isinstance(item, str) for item in values):
            raise ProspectiveAssessmentPersistenceError(f"{name} must be strings")


def _reject_forecast(payload: Mapping[str, Any]) -> None:
    found = _forecast_key(payload)
    if found is not None:
        raise ProspectiveAssessmentPersistenceError("a forecast must not be stored")


def _forecast_key(value: object) -> str | None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if str(key) in _FORECAST_KEYS:
                return str(key)
            found = _forecast_key(item)
            if found is not None:
                return found
    elif isinstance(value, Sequence) and not isinstance(value, str):
        for item in value:
            found = _forecast_key(item)
            if found is not None:
                return found
    return None


def _iso_timestamp(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ProspectiveAssessmentPersistenceError("timestamps must be timezone-aware")
    return value.astimezone(UTC).isoformat()


def _refuse_preserved_database(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute("select current_database()")
        row = cur.fetchone()
    database_name = row[0] if row else ""
    if database_name == "postgres":
        raise ProspectiveAssessmentPersistenceError(
            "refusing to connect to the database named postgres"
        )
    if running_under_pytest():
        assert_connected_test_database(conn)


def _row_to_stored(row: Mapping[str, Any]) -> StoredProspectiveAssessment:
    created_at = row["created_at"]
    captured_at = row["captured_at"]
    evaluation_due = row["evaluation_due"]
    if not isinstance(created_at, datetime) or not isinstance(captured_at, datetime):
        raise ProspectiveAssessmentPersistenceError("stored timestamps are missing")
    if evaluation_due is not None and not isinstance(evaluation_due, date):
        raise ProspectiveAssessmentPersistenceError("stored evaluation_due is not a date")
    return StoredProspectiveAssessment(
        assessment_id=str(row["assessment_id"]),
        created_at=created_at,
        captured_at=captured_at,
        lifecycle_status=str(row["lifecycle_status"]),
        publication_allowed=bool(row["publication_allowed"]),
        revision_class=str(row["revision_class"]),
        completeness=str(row["completeness"]),
        horizon_months=None if row["horizon_months"] is None else int(row["horizon_months"]),
        evaluation_due=evaluation_due,
        run_ids=_string_tuple(row["run_ids"], "run_ids"),
        observation_ids=_string_tuple(row["observation_ids"], "observation_ids"),
        captured_values=_object(row["captured_values"], "captured_values"),
        retrieval_timestamps=_string_tuple(row["retrieval_timestamps"], "retrieval_timestamps"),
        publication_timestamps=_string_tuple(
            row["publication_timestamps"],
            "publication_timestamps",
        ),
        method_versions=_string_object(row["method_versions"], "method_versions"),
        parameter_hashes=_string_object(row["parameter_hashes"], "parameter_hashes"),
        support_text=str(row["support_text"]),
        contradiction_text=str(row["contradiction_text"]),
        uncertainty_text=str(row["uncertainty_text"]),
        unavailable_inputs=_string_tuple(row["unavailable_inputs"], "unavailable_inputs"),
        input_hash=str(row["input_hash"]),
        output_hash=str(row["output_hash"]),
        supersedes_assessment_id=(
            None
            if row["supersedes_assessment_id"] is None
            else str(row["supersedes_assessment_id"])
        ),
        capture_note=str(row["capture_note"]),
    )


def _string_tuple(value: object, name: str) -> tuple[str, ...]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ProspectiveAssessmentPersistenceError(f"stored {name} is not a list of strings")
    return tuple(value)


def _object(value: object, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ProspectiveAssessmentPersistenceError(f"stored {name} is not an object")
    return value


def _string_object(value: object, name: str) -> dict[str, str]:
    document = _object(value, name)
    if any(not isinstance(item, str) for item in document.values()):
        raise ProspectiveAssessmentPersistenceError(f"stored {name} values must be strings")
    return {str(key): item for key, item in document.items()}
