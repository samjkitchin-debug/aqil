"""Additional operator commands (collect, collect-and-run, export-insight)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from aqil_research.cli import DEFAULT_FIXTURE
from aqil_research.collection.service import collect_bls_unemployment
from aqil_research.insight.build_sahm import build_sahm_insight
from aqil_research.insight.io import DEFAULT_WEB_INSIGHT_PATH, write_insight
from aqil_research.persistence.connection import research_connection
from aqil_research.persistence.runs import load_research_run
from aqil_research.workflow.collect_and_run import collect_and_run_sahm
from aqil_research.workflow.research_ingest import run_research_ingest


def register_collect_parsers(sub: argparse._SubParsersAction) -> None:
    collect = sub.add_parser("collect", help="Collect and persist permitted source data")
    collect.add_argument("--source", required=True, choices=["bls"])
    collect.add_argument("--dataset", default="bls.ln.LNS14000000")
    collect.add_argument("--live", action="store_true")
    collect.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    collect.add_argument("--start-year", type=int, default=None)
    collect.add_argument("--end-year", type=int, default=None)
    collect.add_argument("--store", choices=["memory", "postgres"], default="postgres")
    collect.add_argument("--format", choices=["text", "json"], default="text")

    car = sub.add_parser(
        "collect-and-run",
        help="Collect, run Sahm, persist run, verify replay, optional insight export",
    )
    car.add_argument("--source", required=True, choices=["bls"])
    car.add_argument("--method", required=True, choices=["sahm"])
    car.add_argument("--live", action="store_true")
    car.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    car.add_argument("--start-year", type=int, default=None)
    car.add_argument("--end-year", type=int, default=None)
    car.add_argument("--run-id", required=True)
    car.add_argument("--evaluation-period", type=str, default=None)
    car.add_argument("--allow-evaluation-fallback", action="store_true")
    car.add_argument(
        "--export-insight",
        type=Path,
        default=None,
        help=f"Write research insight JSON (default: {DEFAULT_WEB_INSIGHT_PATH})",
        nargs="?",
        const=DEFAULT_WEB_INSIGHT_PATH,
    )

    export = sub.add_parser("export-insight", help="Export structured insight from a stored run")
    export.add_argument("--run-id", required=True)
    export.add_argument("--output", type=Path, default=DEFAULT_WEB_INSIGHT_PATH)

    demo = sub.add_parser(
        "forward-demo",
        help="Import fixture forward-intelligence demo and export horizon bundle JSON",
    )
    demo.add_argument(
        "--export-horizon",
        type=Path,
        default=None,
        help="Write forward-horizon.v1.json for the web app",
    )
    demo.add_argument("--skip-db", action="store_true", help="Only export JSON bundle")

    ingest = sub.add_parser(
        "ingest",
        help=(
            "Ingest permitted sources into the local research database "
            "(live BLS series by default)"
        ),
    )
    ingest.add_argument(
        "--fixture",
        type=Path,
        default=None,
        help="Offline BLS fixture path (CI/tests; default is live BLS API)",
    )
    ingest.add_argument("--start-year", type=int, default=None)
    ingest.add_argument("--end-year", type=int, default=None)
    ingest.add_argument("--format", choices=["text", "json"], default="text")


def run_ingest(args: argparse.Namespace) -> int:
    live = args.fixture is None
    try:
        outcome = run_research_ingest(
            live=live,
            fixture_path=args.fixture,
            start_year=args.start_year,
            end_year=args.end_year,
        )
    except OSError as exc:
        print(f"database error: {exc}", file=sys.stderr)
        return 10

    result = outcome.bls_unemployment
    payload = {
        "bls_unemployment": result.model_dump(mode="json"),
        "publications_attempted": outcome.publications_attempted,
        "publications_outcome": outcome.publications_outcome,
        "calendar_outcome": outcome.calendar_outcome,
        "calendar_new": outcome.calendar_new,
        "calendar_unchanged": outcome.calendar_unchanged,
    }
    if args.format == "json":
        print(json.dumps(payload, indent=2, default=str))
    else:
        mode = "live" if live else "fixture"
        print(f"ingest_mode={mode} bls_outcome={result.outcome}")
        print(
            f"received={result.observations_received} "
            f"new={result.observations_newly_stored} unchanged={result.observations_unchanged}",
        )
        if outcome.publications_attempted:
            print(f"publications_outcome={outcome.publications_outcome}")
        if outcome.calendar_outcome:
            print(
                f"calendar_outcome={outcome.calendar_outcome} "
                f"calendar_new={outcome.calendar_new} "
                f"calendar_unchanged={outcome.calendar_unchanged}",
            )
        print(result.next_recommended_action)

    if result.outcome in ("failed_rights", "failed_fetch", "failed_validation"):
        return 5
    if result.conflicts_detected:
        return 6
    return 0


def run_collect(args: argparse.Namespace) -> int:
    if args.source != "bls":
        print("Only --source bls is supported.", file=sys.stderr)
        return 2
    if args.dataset != "bls.ln.LNS14000000":
        print("Only BLS LNS14000000 dataset is wired for collection.", file=sys.stderr)
        return 2

    if args.store == "postgres":
        try:
            with research_connection() as conn:
                result, _store = collect_bls_unemployment(
                    store_backend="postgres",
                    live=args.live,
                    fixture_path=str(args.fixture) if not args.live else None,
                    start_year=args.start_year,
                    end_year=args.end_year,
                    conn=conn,
                )
        except OSError as exc:
            print(f"database error: {exc}", file=sys.stderr)
            return 10
    else:
        result, _store = collect_bls_unemployment(
            store_backend="memory",
            live=args.live,
            fixture_path=str(args.fixture) if not args.live else None,
            start_year=args.start_year,
            end_year=args.end_year,
        )

    payload = result.model_dump(mode="json")
    if args.format == "json":
        print(json.dumps(payload, indent=2, default=str))
    else:
        print(f"outcome={result.outcome} received={result.observations_received}")
        print(f"new={result.observations_newly_stored} unchanged={result.observations_unchanged}")
        print(f"conflicts={result.conflicts_detected} completeness={result.completeness}")
        print(result.next_recommended_action)
    if result.outcome in ("failed_rights", "failed_fetch", "failed_validation"):
        return 5
    if result.conflicts_detected:
        return 6
    return 0


def run_collect_and_run(args: argparse.Namespace) -> int:
    if args.source != "bls" or args.method != "sahm":
        return 2
    try:
        with research_connection() as conn:
            outcome = collect_and_run_sahm(
                conn,
                live=args.live,
                fixture_path=args.fixture if not args.live else None,
                start_year=args.start_year,
                end_year=args.end_year,
                run_id=args.run_id,
                evaluation_period=args.evaluation_period,
                allow_evaluation_fallback=args.allow_evaluation_fallback,
            )
    except OSError as exc:
        print(f"database error: {exc}", file=sys.stderr)
        return 10

    print(f"collection_outcome={outcome.collection_outcome}")
    print(f"run_id={outcome.run_id} execution_status={outcome.execution_status}")
    print(f"analytical_payload_hash={outcome.analytical_payload_hash}")
    print(f"recompute_match={outcome.recompute_match}")
    for warning in outcome.warnings:
        print(f"warning: {warning}", file=sys.stderr)

    if args.export_insight is not None and outcome.insight is not None:
        write_insight(args.export_insight, outcome.insight)
        print(f"insight_exported={args.export_insight}")

    if outcome.run_id is None:
        return 7
    if outcome.execution_status != "completed":
        return 8
    if outcome.recompute_match is False:
        return 9
    return 0


def run_forward_demo(args: argparse.Namespace) -> int:
    from datetime import UTC, datetime

    from aqil_research.forward.horizon import build_forward_horizon_bundle
    from aqil_research.forward.persistence import (
        import_demo_fixture_bundle,
        load_persisted_forward_horizon,
    )

    now = datetime.now(tz=UTC)
    bundle = None
    if not args.skip_db:
        try:
            with research_connection() as conn:
                import_demo_fixture_bundle(conn, recorded_at=now)
                bundle = load_persisted_forward_horizon(conn)
        except OSError as exc:
            print(f"database error: {exc}", file=sys.stderr)
            return 10
    if bundle is None:
        bundle = build_forward_horizon_bundle()
    if args.export_horizon is not None:
        args.export_horizon.write_text(
            json.dumps(bundle, indent=2, default=str) + "\n",
            encoding="utf-8",
        )
        print(f"horizon_exported={args.export_horizon}")
    else:
        print(json.dumps(bundle, indent=2, default=str))
    return 0


def run_export_insight(args: argparse.Namespace) -> int:
    try:
        with research_connection() as conn:
            run = load_research_run(conn, args.run_id)
            from aqil_research.persistence.reproduce import verify_stored_run_replay

            replay = verify_stored_run_replay(conn, args.run_id)
            match = replay.full_match
            insight = build_sahm_insight(run)
            write_insight(args.output, insight)
    except OSError as exc:
        print(f"database error: {exc}", file=sys.stderr)
        return 10
    print(f"insight_exported={args.output} recompute_match={match}")
    return 0 if match else 9
