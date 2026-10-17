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
from aqil_research.persistence.connection import research_connection
from aqil_research.persistence.ingest import ingest_adapter_to_postgres
from aqil_research.persistence.reproduce import recompute_stored_run
from aqil_research.persistence.runs import load_research_run, save_research_run
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
    run.add_argument(
        "--store",
        choices=["memory", "postgres"],
        default="memory",
        help="Observation and run persistence backend (default: memory)",
    )
    run.add_argument(
        "--run-id", type=str, default=None, help="Explicit research run id when persisting"
    )
    retrieve = sub.add_parser("retrieve-run", help="Load a persisted research run from PostgreSQL")
    retrieve.add_argument("--run-id", required=True)
    retrieve.add_argument(
        "--recompute",
        action="store_true",
        help="Recompute Sahm from frozen observation evidence and print comparison",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "run":
        return _run_bls_sahm(args)
    if args.command == "retrieve-run":
        return _retrieve_run(args)
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
    adapter_registry = AdapterRegistry()
    adapter_registry.register(adapter)
    collection_mode = "live" if args.live else "fixture"
    ingest_notes: list[str] = []

    if args.store == "postgres":
        try:
            with research_connection() as conn:
                store, ingest = ingest_adapter_to_postgres(
                    conn,
                    adapter,
                    rights,
                    retrieved_at=today,
                    collection_mode=collection_mode,
                )
                ingest_notes = list(ingest.conflicts)
                if ingest.fetch and ingest.fetch.errors and not ingest.fetch.observations:
                    print(ingest.fetch.errors[0].message, file=sys.stderr)
                    return 6
                by_period, _evaluation, run = _evaluate_and_run(
                    store,
                    rights_records,
                    today,
                    args,
                    run_id=args.run_id,
                )
                if not by_period or run is None:
                    print("No observations available after ingest.", file=sys.stderr)
                    return 7
                save_research_run(conn, run)
                note = render_bls_sahm_research_note(run)
                _print_run_summary(run, note, store, ingest, args, collection_mode, ingest_notes)
                if args.export:
                    artefact = ResearchArtefact(
                        run=run,
                        observations=store.all_observations(),
                        diagnostics=_diagnostics(
                            args, store, ingest, collection_mode, ingest_notes
                        ),
                        research_note=note,
                        persistence="postgresql",
                    )
                    args.export.write_text(artefact.to_json(), encoding="utf-8")
                    print(f"exported={args.export}")
                return 0 if run.execution_status == "completed" else 8
        except IngestionBlockedError as exc:
            print(str(exc), file=sys.stderr)
            return 5
        except OSError as exc:
            print(f"database error: {exc}", file=sys.stderr)
            return 10

    store = InMemoryObservationStore()
    try:
        ingest = ingest_from_adapter(store, adapter, rights, optional=False)
    except IngestionBlockedError as exc:
        print(str(exc), file=sys.stderr)
        return 5

    if ingest.fetch and ingest.fetch.errors and not ingest.fetch.observations:
        print(ingest.fetch.errors[0].message, file=sys.stderr)
        return 6

    by_period, _evaluation, run = _evaluate_and_run(
        store,
        rights_records,
        today,
        args,
        run_id=args.run_id,
    )
    if not by_period or run is None:
        print("No observations available after ingest.", file=sys.stderr)
        return 7
    note = render_bls_sahm_research_note(run)
    _print_run_summary(run, note, store, ingest, args, collection_mode, ingest_notes)
    if args.export:
        artefact = ResearchArtefact(
            run=run,
            observations=store.all_observations(),
            diagnostics=_diagnostics(args, store, ingest, collection_mode, ingest_notes),
            research_note=note,
        )
        args.export.write_text(artefact.to_json(), encoding="utf-8")
        print(f"exported={args.export}")
    return 0 if run.execution_status == "completed" else 8


def _retrieve_run(args: argparse.Namespace) -> int:
    try:
        with research_connection() as conn:
            run = load_research_run(conn, args.run_id)
            print(f"run_id={run.run_id}")
            print(f"execution_status={run.execution_status}")
            print(f"analytical_payload_hash={run.analytical_payload_hash}")
            if args.recompute:
                fresh = recompute_stored_run(conn, args.run_id)
                print(f"recompute_calculation_match={fresh.calculation == run.calculation}")
    except LookupError as exc:
        print(str(exc), file=sys.stderr)
        return 11
    except OSError as exc:
        print(f"database error: {exc}", file=sys.stderr)
        return 10
    return 0


def _evaluate_and_run(
    store: object,
    rights_records: object,
    today: datetime,
    args: argparse.Namespace,
    *,
    run_id: str | None,
):
    from aqil_research.methods.evaluation import latest_sahm_evaluation_period
    from aqil_research.vintages.store import ObservationStore

    if not isinstance(store, ObservationStore):
        raise TypeError("store must implement ObservationStore")
    by_period = store.as_of(BLS_DATASET_ID, today, AnalysisMode.LATEST_REVISED)
    if not by_period:
        return {}, None, None
    if args.evaluation_period:
        evaluation = datetime.fromisoformat(args.evaluation_period).date()
        if evaluation.day != 1:
            print("evaluation-period must be the first day of a month.", file=sys.stderr)
            return by_period, None, None
        if not sahm_window_complete(by_period, evaluation):
            print(
                f"Insufficient months for Sahm at {evaluation.isoformat()}.",
                file=sys.stderr,
            )
            return by_period, None, None
    else:
        evaluation = max(by_period)
        if not sahm_window_complete(by_period, evaluation):
            if not args.allow_evaluation_fallback:
                print(
                    f"Latest month {evaluation.isoformat()} lacks a full Sahm window. "
                    "Pass --allow-evaluation-fallback or --evaluation-period.",
                    file=sys.stderr,
                )
                return by_period, None, None
            fallback = latest_sahm_evaluation_period(by_period)
            if fallback is None:
                print("No month has a complete Sahm window.", file=sys.stderr)
                return by_period, None, None
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
        run_id=run_id,
    )
    return by_period, evaluation, run


def _diagnostics(
    args: argparse.Namespace,
    store: object,
    ingest: object,
    collection_mode: str,
    ingest_notes: list[str],
) -> dict[str, object]:
    from aqil_research.vintages.store import ObservationStore

    count = len(store.all_observations()) if isinstance(store, ObservationStore) else 0
    conflicts = list(getattr(ingest, "conflicts", ())) or ingest_notes
    diagnostics: dict[str, object] = {
        "live": bool(args.live),
        "start_year": args.start_year,
        "end_year": args.end_year,
        "observation_count": count,
        "ingest_conflicts": conflicts,
        "collection_mode": collection_mode,
        "method_version": SAHM_METHOD_VERSION,
    }
    fetch = getattr(ingest, "fetch", None)
    if fetch and fetch.errors:
        diagnostics["provider_errors"] = [error.message for error in fetch.errors]
    return diagnostics


def _print_run_summary(
    run: object,
    note: str,
    store: object,
    ingest: object,
    args: argparse.Namespace,
    collection_mode: str,
    ingest_notes: list[str],
) -> None:
    from aqil_research.vintages.store import ObservationStore

    print(note)
    print("")
    print(f"execution_status={run.execution_status} data_sufficiency={run.data_sufficiency}")
    print(f"analytical_payload_hash={run.analytical_payload_hash}")
    count = len(store.all_observations()) if isinstance(store, ObservationStore) else 0
    print(
        f"requests=1 live={bool(args.live)} store={args.store} "
        f"mode={collection_mode} observations={count}",
    )


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
