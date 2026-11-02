"""The trial file is append-only and every line carries the same fields."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from aqil_research.discovery.ledger import REQUIRED_FIELDS, LedgerError, TrialLedger


def _record() -> dict[str, object]:
    return {
        "record_type": "trial",
        "trial_id": "pilot:example",
        "catalogue_hash": "abc",
        "gate": "pilot",
        "cell_id": "example",
        "status": "blocked",
        "point_in_time_class": "retrospective_assumed_lag",
        "evidence_class": "not_claimed",
        "payload": {"estimated": False},
    }


def test_ledger_appends_and_keeps_required_fields(tmp_path: Path) -> None:
    path = tmp_path / "trials.jsonl"
    ledger = TrialLedger(path)
    ledger.append(_record())
    ledger.append(_record() | {"trial_id": "second"})
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    for line in lines:
        payload = json.loads(line)
        assert set(REQUIRED_FIELDS) <= set(payload)


def test_ledger_refuses_a_truncated_record(tmp_path: Path) -> None:
    path = tmp_path / "trials.jsonl"
    with pytest.raises(LedgerError):
        TrialLedger(path).append({"trial_id": "missing"})


def test_existing_ledger_is_not_rewritten(tmp_path: Path) -> None:
    path = tmp_path / "trials.jsonl"
    TrialLedger(path).append(_record())
    before = path.read_text(encoding="utf-8")
    TrialLedger(path).append(_record() | {"trial_id": "later"})
    assert path.read_text(encoding="utf-8").startswith(before)
