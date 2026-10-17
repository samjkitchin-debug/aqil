"""Operator CLI for bounded research runs."""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path

from aqil_research.adapters.bls.adapter import BlsAdapterConfig, BlsUnemploymentAdapter
from aqil_research.adapters.registry import AdapterRegistry
from aqil_research.contracts.observation import AnalysisMode
from aqil_research.interpret.research_note import render_bls_sahm_research_note
from aqil_research.methods.configs import SAHM_PUBLISHED
from aqil_research.methods.evaluation import sahm_window_complete
from aqil_research.methods.registry import SAHM_METHOD_ID, default_method_registry
from aqil_research.methods.sahm import SAHM_METHOD_VERSION
from aqil_research.pipeline.artefact import ResearchArtefact
from aqil_research.pipeline.ingestion import IngestionBlockedError, ingest_from_adapter
from aqil_research.pipeline.models import ResearchExecutionRequest
from aqil_research.pipeline.orchestrate import execute_research_run
from aqil_research.sources.rights import (
    RightsOperation,
    SourceRightsError,
    find_source_rights,
    load_source_rights,
    source_usable,
)
from aqil_research.vintages.store import InMemoryObservationStore

BLS_SOURCE_ID = "bls_cps_unemployment_rate"
BLS_DATASET_ID = "bls.ln.LNS14000000"
DEFAULT_FIXTURE = (
    Path(__file__).resolve().parents[2]
    / "tests"
    / "fixtures"
    / "bls"
    / "api_lns14000000_success.json"
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="aqil-research")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="Run a bounded macro research calculation")
    run.add_argument("--source", required=True, choices=["bls"])
    run.add_argument("--method", required=True, choices=["sahm"])
    run.add_argument(
        "--live",
        action="store_true",
        help="Opt in to live BLS API collection (default: offline fixture)",
    )
    run.add_argument("--start-year", type=int, default=None)
    run.add_argument("--end-year", type=int, default=None)
    run.add_argument(
        "--fixture",
        type=Path,
        default=DEFAULT_FIXTURE,
        help="Offline BLS API-shaped fixture path",
    )
    run.add_argument("--export", type=Path, default=None, help="Write research artefact JSON")
    run.add_argument(
        "--evaluation-period",
        type=str,
        default=None,
        help="Evaluation month YYYY-MM-DD (must be month start); default: latest month in series",
    )
    run.add_argument(
        "--allow-evaluation-fallback",
        action="store_true",
        help="If the latest month lacks a full Sahm window, use the latest sufficient month",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "run":
        return _run_bls_sahm(args)
    return 1


def _run_bls_sahm(args: argparse.Namespace) -> int:
    if args.source != "bls" or args.method != "sahm":
        print("Only --source bls --method sahm is supported in M1 Phase 4.", file=sys.stderr)
        return 2

    rights_records = load_source_rights()
    rights = find_source_rights(rights_records, source_id=BLS_SOURCE_ID)
    if rights is None:
        print(f"Unknown source rights for {BLS_SOURCE_ID}", file=sys.stderr)
        return 3
    if not _collection_allowed(rights):
        print("BLS automated collection is not permitted or source is disabled.", file=sys.stderr)
        return 4

    today = datetime.now(tz=UTC)
    end_year = args.end_year or today.year
    start_year = args.start_year or (end_year - 3)
    config = BlsAdapterConfig(
        start_year=start_year,
        end_year=end_year,
        live=bool(args.live),
        fixture_path=args.fixture if not args.live else None,
    )
    adapter = BlsUnemploymentAdapter(config=config, retrieved_at=today)
    store = InMemoryObservationStore()
    adapter_registry = AdapterRegistry()
    adapter_registry.register(adapter)

    try:
        ingest = ingest_from_adapter(store, adapter, rights, optional=False)
    except IngestionBlockedError as exc:
        print(str(exc), file=sys.stderr)
        return 5

    if ingest.fetch and ingest.fetch.errors and not ingest.fetch.observations:
        print(ingest.fetch.errors[0].message, file=sys.stderr)
        return 6

    by_period = store.as_of(BLS_DATASET_ID, today, AnalysisMode.LATEST_REVISED)
    if not by_period:
        print("No observations available after ingest.", file=sys.stderr)
        return 7
    if args.evaluation_period:
        evaluation = datetime.fromisoformat(args.evaluation_period).date()
        if evaluation.day != 1:
            print("evaluation-period must be the first day of a month.", file=sys.stderr)
            return 7
        if not sahm_window_complete(by_period, evaluation):
            print(
                f"Insufficient months for Sahm at {evaluation.isoformat()}.",
                file=sys.stderr,
            )
            return 7
    else:
        evaluation = max(by_period)
        if not sahm_window_complete(by_period, evaluation):
            if not args.allow_evaluation_fallback:
                print(
                    f"Latest month {evaluation.isoformat()} lacks a full Sahm window. "
                    "Pass --allow-evaluation-fallback or --evaluation-period.",
                    file=sys.stderr,
                )
                return 7
            from aqil_research.methods.evaluation import latest_sahm_evaluation_period

            fallback = latest_sahm_evaluation_period(by_period)
            if fallback is None:
                print("No month has a complete Sahm window.", file=sys.stderr)
                return 7
            evaluation = fallback
    request = ResearchExecutionRequest(
        source_id=BLS_SOURCE_ID,
        dataset_id=BLS_DATASET_ID,
        decision_at=today,
        analysis_mode=AnalysisMode.LATEST_REVISED,
        evaluation_period=evaluation.isoformat(),
        method_id=SAHM_METHOD_ID,
        method_config=SAHM_PUBLISHED.model_dump(mode="json"),
        collect=False,
        primary_adapter_id=None,
    )
    run = execute_research_run(
        request,
        store=store,
        rights_records=rights_records,
        method_registry=default_method_registry(),
        executed_at=today,
    )
    note = render_bls_sahm_research_note(run)
    diagnostics = {
        "live": bool(args.live),
        "start_year": start_year,
        "end_year": end_year,
        "observation_count": len(store.all_observations()),
        "ingest_conflicts": list(ingest.conflicts),
        "adapter_id": adapter.identity.adapter_id,
        "method_version": SAHM_METHOD_VERSION,
    }
    if ingest.fetch:
        diagnostics["provider_errors"] = [error.message for error in ingest.fetch.errors]

    artefact = ResearchArtefact(
        run=run,
        observations=store.all_observations(),
        diagnostics=diagnostics,
        research_note=note,
    )
    print(note)
    print("")
    print(f"execution_status={run.execution_status} data_sufficiency={run.data_sufficiency}")
    print(f"analytical_payload_hash={run.analytical_payload_hash}")
    print(f"requests=1 live={bool(args.live)} observations={len(store.all_observations())}")
    if args.export:
        args.export.write_text(artefact.to_json(), encoding="utf-8")
        print(f"exported={args.export}")
    return 0 if run.execution_status == "completed" else 8


def _collection_allowed(rights: object) -> bool:
    from aqil_research.sources.rights import SourceRightsRecord

    if not isinstance(rights, SourceRightsRecord):
        return False
    return (
        source_usable(rights, RightsOperation.AUTOMATED_ACCESS)
        and source_usable(
            rights,
            RightsOperation.INTERNAL_COMPUTATION,
        )
        and source_usable(rights, RightsOperation.RAW_DATA_RETENTION)
    )


def run_cli() -> None:
    try:
        code = main()
    except SourceRightsError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(9) from exc
    raise SystemExit(code)
