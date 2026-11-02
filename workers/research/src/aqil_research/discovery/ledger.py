"""Append-only trial ledger. The writer never truncates an existing file."""

from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

REQUIRED_FIELDS = (
    "record_type",
    "trial_id",
    "catalogue_hash",
    "gate",
    "cell_id",
    "status",
    "point_in_time_class",
    "evidence_class",
    "payload",
)


class LedgerError(Exception):
    """Raised when a trial line would break the append-only contract."""


def _jsonable(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, date | datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_jsonable(item) for item in value]
    return value


class TrialLedger:
    def __init__(self, path: Path) -> None:
        self.path = path
        if path.exists() and path.stat().st_size > 0:
            self._validate_existing()

    def _validate_existing(self) -> None:
        for line_number, line in enumerate(
            self.path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if not line.strip():
                raise LedgerError(f"blank ledger line {line_number}")
            payload = json.loads(line)
            missing = [field for field in REQUIRED_FIELDS if field not in payload]
            if missing:
                raise LedgerError(f"ledger line {line_number} is missing {missing[0]}")

    def append(self, record: dict[str, Any]) -> None:
        missing = [field for field in REQUIRED_FIELDS if field not in record]
        if missing:
            raise LedgerError(f"a trial is missing {missing[0]}")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        encoded = json.dumps(_jsonable(record), sort_keys=True, separators=(",", ":"))
        with self.path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(encoded + "\n")

    def records(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        return [
            json.loads(line) for line in self.path.read_text(encoding="utf-8").splitlines() if line
        ]
