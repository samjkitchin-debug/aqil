"""Lifecycle of one prospective assessment.

The live decision is not_qualified. No 6- or 12-month hypothesis qualifies.
This module does not open a database and does not rewrite an earlier row.
"""

from __future__ import annotations

import copy
import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from aqil_research.methods.industrial_production_activity import (
    INDUSTRIAL_PRODUCTION_METHOD_ID,
    INDUSTRIAL_PRODUCTION_METHOD_VERSION,
    IndustrialProductionActivityMethod,
)
from aqil_research.methods.labour_market import (
    LABOUR_MARKET_METHOD_ID,
    LABOUR_MARKET_METHOD_VERSION,
    LabourMarketConditionsMethod,
)
from aqil_research.methods.prices_and_policy import (
    PRICES_AND_POLICY_METHOD_ID,
    PRICES_AND_POLICY_METHOD_VERSION,
    PricesAndPolicyMethod,
)

CAPTURE_NOTE_PHRASE = "not a reconstruction of dates before captured_at"
NOT_QUALIFIED_REASONS = (
    "no vintage panel",
    "no identified mechanism",
    "the stored windows do not share one horizon",
)
LIFECYCLE_STATUSES = (
    "not_qualified",
    "proposed_internal",
    "superseded",
    "evaluated",
)
ASSESSMENT_FIELDS = (
    "assessment_id",
    "created_at",
    "captured_at",
    "lifecycle_status",
    "publication_allowed",
    "revision_class",
    "completeness",
    "horizon_months",
    "evaluation_due",
    "run_ids",
    "observation_ids",
    "captured_values",
    "retrieval_timestamps",
    "publication_timestamps",
    "method_versions",
    "parameter_hashes",
    "support_text",
    "contradiction_text",
    "uncertainty_text",
    "unavailable_inputs",
    "input_hash",
    "output_hash",
    "supersedes_assessment_id",
    "capture_note",
)
_FORBIDDEN_KEYS = frozenset(
    {
        "direction",
        "probability",
        "return",
        "recommendation",
        "expected_return",
        "calibrated_probability",
    }
)
_LABOUR_WINDOW = (
    "12-month endpoint change; each series uses its own latest stored month; "
    "the joint reading uses only months present in all three"
)
_PRICES_WINDOW = (
    "CPI-U 12-month percent change; federal funds and the 10-year yield use a one-month change"
)
_PRODUCTION_WINDOW = "12-month percent change"
_SUPPORT_TEXT = (
    "No 6- or 12-month hypothesis qualifies because there is no vintage panel, "
    "no identified mechanism, and the stored windows do not share one horizon."
)
_CONTRADICTION_TEXT = (
    "Labour-market conditions and industrial production use a 12-month endpoint change. "
    "Prices and policy uses a 12-month CPI-U change and a one-month change for federal "
    "funds and for the 10-year yield. The stored windows do not share one horizon."
)
_UNCERTAINTY_TEXT = "No direction, probability, return, or recommendation is stated."
_CAPTURE_NOTE = (
    "The row records what was stored at capture and is "
    "not a reconstruction of dates before captured_at."
)


class LifecycleError(Exception):
    """The assessment payload or a lifecycle transition is refused."""


@dataclass(frozen=True, slots=True)
class LifecycleRefusal:
    """A pure refusal. No row is written."""

    rule: str
    reason: str


def not_qualified_assessment(
    *,
    assessment_id: str,
    created_at: datetime,
    captured_at: datetime,
    run_ids: Sequence[str] = (),
    observation_ids: Sequence[str] = (),
    retrieval_timestamps: Sequence[str] = (),
    publication_timestamps: Sequence[str] = (),
) -> dict[str, Any]:
    """Return the live not_qualified row. horizon_months stays null.

    Supplied ids are recorded as given. They do not qualify a hypothesis.
    """
    if not isinstance(assessment_id, str) or not assessment_id.strip():
        raise LifecycleError("assessment_id is required")
    method_versions, parameter_hashes, windows = _method_identity()
    unavailable_inputs = [
        "vintage panel",
        "identified mechanism",
        "shared horizon",
    ]
    captured_values = {
        "series_values": None,
        "reasons": list(NOT_QUALIFIED_REASONS),
        "windows": windows,
    }
    row: dict[str, Any] = {
        "assessment_id": assessment_id,
        "created_at": _aware_timestamp(created_at, "created_at"),
        "captured_at": _aware_timestamp(captured_at, "captured_at"),
        "lifecycle_status": "not_qualified",
        "publication_allowed": False,
        "revision_class": "latest_revised",
        "completeness": "insufficient",
        "horizon_months": None,
        "evaluation_due": None,
        "run_ids": _string_list(run_ids, "run_ids"),
        "observation_ids": _string_list(observation_ids, "observation_ids"),
        "captured_values": captured_values,
        "retrieval_timestamps": _string_list(retrieval_timestamps, "retrieval_timestamps"),
        "publication_timestamps": _string_list(publication_timestamps, "publication_timestamps"),
        "method_versions": method_versions,
        "parameter_hashes": parameter_hashes,
        "support_text": _SUPPORT_TEXT,
        "contradiction_text": _CONTRADICTION_TEXT,
        "uncertainty_text": _UNCERTAINTY_TEXT,
        "unavailable_inputs": unavailable_inputs,
        "input_hash": "",
        "output_hash": "",
        "supersedes_assessment_id": None,
        "capture_note": _CAPTURE_NOTE,
    }
    _reject_forbidden_keys(row)
    if CAPTURE_NOTE_PHRASE not in row["capture_note"]:
        raise LifecycleError("capture_note is missing the required phrase")
    row["input_hash"] = _canonical_hash(
        {
            "reasons": list(NOT_QUALIFIED_REASONS),
            "windows": windows,
            "method_versions": method_versions,
            "parameter_hashes": parameter_hashes,
            "run_ids": row["run_ids"],
            "observation_ids": row["observation_ids"],
            "retrieval_timestamps": row["retrieval_timestamps"],
            "publication_timestamps": row["publication_timestamps"],
            "captured_at": row["captured_at"],
            "unavailable_inputs": unavailable_inputs,
        }
    )
    without_output = {key: value for key, value in row.items() if key != "output_hash"}
    row["output_hash"] = _canonical_hash(without_output)
    return row


def refusal_before_due_date(*, as_of: date, evaluation_due: date) -> LifecycleRefusal | None:
    """Refuse evaluation while as_of is still before the due date."""
    _require_date(as_of, "as_of")
    _require_date(evaluation_due, "evaluation_due")
    if as_of < evaluation_due:
        return LifecycleRefusal(
            rule="before_due_date",
            reason="evaluation is refused before the due date",
        )
    return None


def refusal_missing_outcome(*, outcome_observation_id: str | None) -> LifecycleRefusal | None:
    """Refuse evaluation when the outcome observation is missing."""
    if outcome_observation_id is None or not outcome_observation_id.strip():
        return LifecycleRefusal(
            rule="missing_outcome",
            reason="evaluation is refused because the outcome observation is missing",
        )
    return None


def refusal_snapshot_observations_only(
    *,
    snapshot_observation_ids: set[str] | frozenset[str],
    available_observation_ids: set[str] | frozenset[str],
) -> LifecycleRefusal | None:
    """Refuse when every available observation id was already in the snapshot.

    An empty available set is refused: there is no observation outside the snapshot.
    """
    snapshot = _id_set(snapshot_observation_ids, "snapshot_observation_ids")
    available = _id_set(available_observation_ids, "available_observation_ids")
    if available <= snapshot:
        return LifecycleRefusal(
            rule="snapshot_observations_only",
            reason=(
                "evaluation is refused because every available observation id "
                "was already inside the original snapshot"
            ),
        )
    return None


def evaluation_refusal(
    *,
    as_of: date,
    evaluation_due: date,
    outcome_observation_id: str | None,
    snapshot_observation_ids: set[str] | frozenset[str],
    available_observation_ids: set[str] | frozenset[str],
) -> LifecycleRefusal | None:
    """Return the first evaluation refusal, or None when none of the three rules fire."""
    return (
        refusal_before_due_date(as_of=as_of, evaluation_due=evaluation_due)
        or refusal_missing_outcome(outcome_observation_id=outcome_observation_id)
        or refusal_snapshot_observations_only(
            snapshot_observation_ids=snapshot_observation_ids,
            available_observation_ids=available_observation_ids,
        )
    )


def supersession_refusal(
    earlier: Mapping[str, Any],
    new_payload: Mapping[str, Any],
) -> LifecycleRefusal | None:
    """A proposed_internal row may be superseded only by a payload that points at it.

    This does not rewrite the earlier mapping.
    """
    if new_payload is earlier:
        return LifecycleRefusal(
            rule="rewrites_earlier",
            reason="the earlier row is not rewritten",
        )
    if earlier.get("lifecycle_status") != "proposed_internal":
        return LifecycleRefusal(
            rule="not_proposed_internal",
            reason="only a proposed_internal row may be superseded",
        )
    earlier_id = earlier.get("assessment_id")
    if not isinstance(earlier_id, str) or not earlier_id.strip():
        return LifecycleRefusal(
            rule="missing_pointer",
            reason=(
                "a proposed_internal row may be superseded only by a new payload "
                "that points at the earlier assessment id"
            ),
        )
    if new_payload.get("supersedes_assessment_id") != earlier_id:
        return LifecycleRefusal(
            rule="missing_pointer",
            reason=(
                "a proposed_internal row may be superseded only by a new payload "
                "that points at the earlier assessment id"
            ),
        )
    new_id = new_payload.get("assessment_id")
    if not isinstance(new_id, str) or not new_id.strip() or new_id == earlier_id:
        return LifecycleRefusal(
            rule="same_assessment",
            reason="the earlier row is not rewritten",
        )
    if new_payload.get("publication_allowed") is not False:
        return LifecycleRefusal(
            rule="publication_allowed",
            reason="publication_allowed stays false",
        )
    note = new_payload.get("capture_note")
    if not isinstance(note, str) or CAPTURE_NOTE_PHRASE not in note:
        return LifecycleRefusal(
            rule="capture_note",
            reason="capture_note must include the required phrase",
        )
    status = new_payload.get("lifecycle_status")
    if status not in LIFECYCLE_STATUSES:
        return LifecycleRefusal(
            rule="lifecycle_status",
            reason="lifecycle_status is not one of the stored statuses",
        )
    if "horizon_months" in new_payload and new_payload.get("horizon_months") not in (None, 6, 12):
        return LifecycleRefusal(
            rule="horizon_months",
            reason="horizon_months must stay null, or be 6, or be 12",
        )
    if "revision_class" in new_payload and new_payload.get("revision_class") != "latest_revised":
        return LifecycleRefusal(
            rule="revision_class",
            reason="revision_class is latest_revised",
        )
    forbidden = _find_forbidden_key(new_payload)
    if forbidden is not None:
        return LifecycleRefusal(
            rule="forbidden_claim",
            reason="a direction, probability, return, or recommendation is not recorded",
        )
    return None


def supersede_proposed_internal(
    earlier: Mapping[str, Any],
    new_payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Return a copy of the new payload when it may supersede the earlier row.

    The earlier mapping is left unchanged.
    """
    refusal = supersession_refusal(earlier, new_payload)
    if refusal is not None:
        raise LifecycleError(refusal.reason)
    return copy.deepcopy(dict(new_payload))


def _method_identity() -> tuple[dict[str, str], dict[str, str], list[dict[str, str]]]:
    methods = (
        (
            LABOUR_MARKET_METHOD_ID,
            LABOUR_MARKET_METHOD_VERSION,
            LabourMarketConditionsMethod,
            _LABOUR_WINDOW,
        ),
        (
            PRICES_AND_POLICY_METHOD_ID,
            PRICES_AND_POLICY_METHOD_VERSION,
            PricesAndPolicyMethod,
            _PRICES_WINDOW,
        ),
        (
            INDUSTRIAL_PRODUCTION_METHOD_ID,
            INDUSTRIAL_PRODUCTION_METHOD_VERSION,
            IndustrialProductionActivityMethod,
            _PRODUCTION_WINDOW,
        ),
    )
    versions: dict[str, str] = {}
    hashes: dict[str, str] = {}
    windows: list[dict[str, str]] = []
    for method_id, version, method_cls, span in methods:
        versions[method_id] = version
        hashes[method_id] = method_cls().implementation_hash()
        windows.append(
            {
                "method_id": method_id,
                "method_version": version,
                "span": span,
            }
        )
    return versions, hashes, windows


def _aware_timestamp(value: datetime, name: str) -> str:
    if not isinstance(value, datetime):
        raise LifecycleError(f"{name} must be timezone-aware")
    offset = None if value.tzinfo is None else value.tzinfo.utcoffset(value)
    if offset is None:
        raise LifecycleError(f"{name} must be timezone-aware")
    return value.isoformat()


def _require_date(value: date, name: str) -> None:
    if type(value) is not date:
        raise LifecycleError(f"{name} must be a date")


def _string_list(values: Sequence[str], name: str) -> list[str]:
    if isinstance(values, (str, bytes)):
        raise LifecycleError(f"{name} must be a list of strings")
    items = list(values)
    if any(not isinstance(item, str) or not item.strip() for item in items):
        raise LifecycleError(f"{name} must contain non-empty strings")
    return items


def _id_set(values: set[str] | frozenset[str], name: str) -> set[str]:
    if not isinstance(values, (set, frozenset)):
        raise LifecycleError(f"{name} must be a set of ids")
    if any(not isinstance(item, str) for item in values):
        raise LifecycleError(f"{name} must contain strings")
    return set(values)


def _canonical_hash(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _find_forbidden_key(value: object) -> str | None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if key in _FORBIDDEN_KEYS:
                return str(key)
            found = _find_forbidden_key(item)
            if found is not None:
                return found
    elif isinstance(value, (list, tuple)):
        for item in value:
            found = _find_forbidden_key(item)
            if found is not None:
                return found
    return None


def _reject_forbidden_keys(value: object) -> None:
    found = _find_forbidden_key(value)
    if found is not None:
        raise LifecycleError("a direction, probability, return, or recommendation is not recorded")
