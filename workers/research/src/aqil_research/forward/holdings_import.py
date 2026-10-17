"""Manual ETF holdings snapshot import from a JSON file."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

import psycopg

from aqil_research.forward.holdings_rights import assert_manual_holdings_ingest
from aqil_research.forward.persistence import import_etf_holdings_snapshot
from aqil_research.sources.rights import find_source_rights, load_source_rights
from aqil_research.sources.rights_gate import RightsGateError

ALLOWED_EVIDENCE = frozenset({"synthetic_demonstration", "provider_holdings"})
REQUIRED_FIELDS = frozenset(
    {
        "etf_id",
        "as_of_date",
        "completeness",
        "source_id",
        "source_locator",
        "evidence_class",
        "lines",
    },
)


class HoldingsImportValidationError(ValueError):
    """Holdings JSON does not match the import contract."""


@dataclass(frozen=True, slots=True)
class HoldingsImportResult:
    source_id: str
    outcome: Literal["completed", "failed_rights", "failed_validation"]
    snapshot_id: str | None
    row_status: Literal["new", "unchanged"] | None
    error_summary: str | None = None


def load_holdings_document(path: Path) -> dict[str, object]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise HoldingsImportValidationError("holdings file must be a JSON object")
    return document


def validate_holdings_document(document: dict[str, object]) -> None:
    """Validate structure. Provider weights require explicit internal-retention authorisation."""
    missing = REQUIRED_FIELDS - set(document)
    if missing:
        raise HoldingsImportValidationError(f"missing required fields: {sorted(missing)}")
    evidence = str(document["evidence_class"])
    if evidence not in ALLOWED_EVIDENCE:
        raise HoldingsImportValidationError(f"unsupported evidence_class {evidence}")
    if (
        evidence == "provider_holdings"
        and document.get("internal_retention_authorized") is not True
    ):
        raise HoldingsImportValidationError(
            "provider_holdings requires internal_retention_authorized=true "
            "with founder-confirmed rights; manual import does not imply redistribution rights",
        )
    lines = document.get("lines")
    if not isinstance(lines, list) or not lines:
        raise HoldingsImportValidationError("lines must be a non-empty list")
    for index, line in enumerate(lines):
        if not isinstance(line, dict):
            raise HoldingsImportValidationError(f"line {index} must be an object")
        for key in ("line_id", "holding_name", "weight_percentage"):
            if key not in line:
                raise HoldingsImportValidationError(f"line {index} missing {key}")


def import_holdings_from_file(
    conn: psycopg.Connection,
    path: Path,
    *,
    recorded_at: datetime | None = None,
) -> HoldingsImportResult:
    observed = recorded_at or datetime.now(tz=UTC)
    try:
        document = load_holdings_document(path)
        validate_holdings_document(document)
    except (OSError, json.JSONDecodeError, HoldingsImportValidationError) as exc:
        return HoldingsImportResult(
            source_id="",
            outcome="failed_validation",
            snapshot_id=None,
            row_status=None,
            error_summary=str(exc),
        )

    source_id = str(document["source_id"])
    rights = find_source_rights(load_source_rights(), source_id=source_id)
    if rights is None:
        return HoldingsImportResult(
            source_id=source_id,
            outcome="failed_rights",
            snapshot_id=None,
            row_status=None,
            error_summary="source not in register",
        )
    try:
        assert_manual_holdings_ingest(
            rights,
            source_id=source_id,
            dataset_id=rights.dataset_id,
        )
    except RightsGateError as exc:
        return HoldingsImportResult(
            source_id=source_id,
            outcome="failed_rights",
            snapshot_id=None,
            row_status=None,
            error_summary=str(exc),
        )

    snapshot_id, row_status = import_etf_holdings_snapshot(
        conn,
        document,
        recorded_at=observed,
    )
    return HoldingsImportResult(
        source_id=source_id,
        outcome="completed",
        snapshot_id=str(snapshot_id),
        row_status=row_status,
    )
