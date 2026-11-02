"""Read-only macro-to-ETF discovery. Gate 0 writes no correlations."""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from aqil_research.discovery.classification import classification_rows, role_counts
from aqil_research.discovery.coverage import (
    MATRIX_FIELDS,
    build_matrix,
    status_counts,
    write_matrix,
)
from aqil_research.discovery.experiments import rerun_pilot, run_gates
from aqil_research.discovery.ledger import TrialLedger
from aqil_research.discovery.load import load_study
from aqil_research.discovery.report import negative_markdown, results_markdown

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "docs" / "research" / "macro-etf"
CATALOGUE_PATH = OUT / "EXPERIMENT_CATALOGUE.json"
MATRIX_PATH = OUT / "COVERAGE_MATRIX.csv"
CLASSIFICATION_PATH = OUT / "METHOD_CLASSIFICATION.csv"
STATE_PATH = OUT / "STATE.json"
LEDGER_PATH = OUT / "trials.jsonl"
REGISTER_PATH = (
    ROOT / "docs" / "sources" / "etf" / "register" / "aqil_etf_universe_v1_2026-11-03.csv"
)
BACKUP = Path(r"C:\Users\gamer\aqil-release-backups\2026-11-03-etf-history\aqil_etf.dump")
EXPECTED_BACKUP = "B7598DC08AEE375B4E29F66A0423075EAED2A6527B0DDBCBE1F1FE3C6BB96BEB"


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in {"gate0", "gates"}:
        raise SystemExit("usage: run_macro_etf_discovery.py gate0|gates")
    catalogue = _catalogue()
    _check_hashes(catalogue)
    study = load_study()
    register = _register()
    matrix = build_matrix(study, catalogue, register)
    if sys.argv[1] == "gate0":
        _write_gate0(study, catalogue, register, matrix)
        return
    _require_same_matrix(matrix)
    if LEDGER_PATH.exists() and LEDGER_PATH.stat().st_size > 0:
        raise SystemExit("the trial ledger already exists; it is append-only and was not replaced")
    first = rerun_pilot(study, catalogue, matrix)
    second = rerun_pilot(study, catalogue, matrix)
    if first["payload"].get("slope") != second["payload"].get("slope"):
        raise SystemExit("the pilot did not repeat from the frozen inputs")
    records = run_gates(study, catalogue, matrix)
    if records[0]["payload"].get("slope") != first["payload"].get("slope"):
        raise SystemExit("the recorded pilot does not match the frozen rerun")
    state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    ledger = TrialLedger(LEDGER_PATH)
    ledger.append(
        {
            "record_type": "freeze",
            "trial_id": "freeze",
            "catalogue_hash": catalogue["_hash"],
            "gate": "0",
            "cell_id": "inputs",
            "status": "frozen",
            "point_in_time_class": "retrospective_assumed_lag",
            "evidence_class": "not_claimed",
            "payload": {
                "input_hash": study.input_hash,
                "catalogue_id": catalogue["catalogue_id"],
                "pilot_repeated": True,
            },
        }
    )
    for record in records:
        ledger.append(record)
    (OUT / "RESULTS.md").write_text(results_markdown(records, state), encoding="utf-8")
    (OUT / "NEGATIVE_RESULTS.md").write_text(negative_markdown(records), encoding="utf-8")
    print(f"trials={len(records)} hash={catalogue['_hash']}")


def _write_gate0(
    study: Any,
    catalogue: dict[str, Any],
    register: list[dict[str, str]],
    matrix: list[dict[str, object]],
) -> None:
    write_matrix(MATRIX_PATH, matrix)
    rows = classification_rows()
    with CLASSIFICATION_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    backup_hash = hashlib.sha256(BACKUP.read_bytes()).hexdigest().upper() if BACKUP.exists() else ""
    state = {
        "live_latest_revised": study.live_latest_revised,
        "fixture_rows": study.fixture_rows,
        "provider_vintage_rows": study.provider_vintage_rows,
        "publication_allowed_true": study.publication_allowed_true,
        "research_runs": study.research_runs,
        "adjusted_close": study.adjusted_close,
        "raw_close": study.raw_close,
        "fx_observations": study.fx_observations,
        "share_classes": study.share_classes,
        "listings_stored": study.listings_stored,
        "input_hash": study.input_hash,
        "catalogue_hash": catalogue["_hash"],
        "backup_sha256": backup_hash,
        "backup_matches_expected": backup_hash == EXPECTED_BACKUP,
        "register_rows": len(register),
        "role_counts": role_counts(rows),
        "matrix_counts": status_counts(matrix),
        "matrix_rows": len(matrix),
        "gaps": study.gaps,
        "series_inventory": study.series_inventory,
        "listings": {
            ticker: {
                "isin": listing.isin,
                "mic": listing.mic,
                "currency": listing.currency,
                "distribution_policy": listing.distribution_policy,
                "inception_date": listing.inception_date,
                "sessions": len(listing.sessions),
                "first_session": listing.sessions[0].isoformat() if listing.sessions else None,
                "last_session": listing.sessions[-1].isoformat() if listing.sessions else None,
                "weekday_gaps": listing.weekday_gaps,
            }
            for ticker, listing in sorted(study.listings.items())
        },
    }
    STATE_PATH.write_text(json.dumps(state, indent=2, default=str) + "\n", encoding="utf-8")
    print(
        f"matrix={len(matrix)} counts={status_counts(matrix)} "
        f"roles={role_counts(rows)} backup_match={backup_hash == EXPECTED_BACKUP}"
    )


def _require_same_matrix(matrix: list[dict[str, object]]) -> None:
    with MATRIX_PATH.open(encoding="utf-8", newline="") as handle:
        stored = list(csv.DictReader(handle))
    rebuilt = [{field: str(row[field]) for field in MATRIX_FIELDS} for row in matrix]
    if stored != rebuilt:
        raise SystemExit("the coverage matrix does not match the frozen file")


def _catalogue() -> dict[str, Any]:
    payload = json.loads(CATALOGUE_PATH.read_text(encoding="utf-8"))
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    payload["_hash"] = hashlib.sha256(canonical).hexdigest()
    return payload


def _register() -> list[dict[str, str]]:
    with REGISTER_PATH.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _check_hashes(catalogue: dict[str, Any]) -> None:
    for relative, expected in catalogue["unchanged_sha256"].items():
        digest = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
        if digest != expected:
            raise SystemExit(f"protected file changed: {relative}")


if __name__ == "__main__":
    main()
