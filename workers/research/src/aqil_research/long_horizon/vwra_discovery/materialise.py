"""Build the VWRA dossier. persist=False rolls back and writes no document."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import psycopg

from aqil_research.long_horizon.events.scan import load_prices
from aqil_research.long_horizon.money import sha256_document
from aqil_research.long_horizon.pilot import (
    LOCAL_ETF_URL,
    LOCAL_RESEARCH_URL,
    assert_loopback,
    git_commit,
    library_versions,
    repo_root,
)
from aqil_research.long_horizon.state_atlas.features import period_bound
from aqil_research.long_horizon.vwra_discovery.dossier import (
    Anchor,
    Dossier,
    MarketEvent,
    Outcome,
    build_dossier,
)
from aqil_research.long_horizon.vwra_discovery.replay import load_panel, replay_methods
from aqil_research.long_horizon.vwra_discovery.report import write_documents
from aqil_research.long_horizon.vwra_discovery.specification import (
    SPECIFICATION_ID,
    VWRA_FIRST_SESSION,
    specification_hash,
)
from aqil_research.long_horizon.vwra_discovery.store import artifacts, store_dossier
from aqil_research.methods.registry import default_method_registry


def code_hash() -> str:
    root = Path(__file__).resolve().parent
    digest = hashlib.sha256()
    for path in sorted(root.glob("*.py")):
        digest.update(path.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def run(*, persist: bool) -> dict[str, object]:
    assert_loopback(LOCAL_RESEARCH_URL, "postgres")
    assert_loopback(LOCAL_ETF_URL, "aqil_etf")
    dataset_ids = tuple(
        dict.fromkeys(
            dataset_id
            for method in default_method_registry().registered()
            for dataset_id in method.required_dataset_ids()
        )
    )
    with psycopg.connect(LOCAL_ETF_URL) as etf:
        listings, hashes, _fx, _tables = load_prices(etf)
    vwra = next(item for item in listings if item.symbol == "VWRA")
    kept = [
        (session, close)
        for session, close in zip(vwra.dates, vwra.closes, strict=True)
        if session >= VWRA_FIRST_SESSION
    ]
    refused_early = len(vwra.dates) - len(kept)
    sessions = tuple(session for session, _close in kept)
    closes = tuple(close for _session, close in kept)
    eimi = next((item for item in listings if item.symbol == "EIMI"), None)
    with psycopg.connect(LOCAL_RESEARCH_URL) as research:
        series, counts = load_panel(research, dataset_ids)
        anchors, atlas, outcomes, events = _atlas(research)
        eimi_anchors = _eimi_anchors(research)
        runs = replay_methods(research, series, counts)
        last = anchors[-1].session if anchors else VWRA_FIRST_SESSION
        macro_periods, macro_series_periods = _macro_counts(series, last)
        dossier = build_dossier(
            anchors=anchors,
            atlas=atlas,
            outcomes=outcomes,
            events=events,
            sessions=sessions,
            closes=closes,
            runs=runs,
            macro_periods=macro_periods,
            macro_series_periods=macro_series_periods,
        )
        dossier.coverage["refused_sessions_before_listing"] = refused_early
        dossier.coverage["specification_hash"] = specification_hash()
        bodies = artifacts(dossier)
        digests = {key: sha256_document(value) for key, value in bodies.items()}
        inserted = 0
        if persist:
            versions = library_versions()
            try:
                versions["statsmodels"] = version("statsmodels")
            except PackageNotFoundError:
                versions["statsmodels"] = "not_installed"
            inserted = store_dossier(
                research,
                dossier,
                bodies,
                digests,
                recorded_at=datetime.now(UTC),
                git_commit=git_commit(repo_root()),
                code_hash=code_hash(),
                input_manifest={
                    "specification_id": SPECIFICATION_ID,
                    "specification_hash": specification_hash(),
                    "dataset_counts": counts,
                    "vwra_sessions": len(sessions),
                    "refused_sessions_before_listing": refused_early,
                    "bea_vintage_used_as_decision_input": False,
                    "portfolio_simulation": "not_called",
                    "eimi_scored": False,
                },
                price_series_versions=[
                    {
                        "symbol": "VWRA",
                        "sha256": hashes["VWRA"],
                        "price_type": "adjusted_close",
                    }
                ],
                library_versions=versions,
                simulation_start=VWRA_FIRST_SESSION,
                simulation_end=sessions[-1] if sessions else VWRA_FIRST_SESSION,
            )
            if inserted:
                write_documents(
                    dossier,
                    digests,
                    _eimi_note(eimi, eimi_anchors),
                    repo_root() / "docs" / "research" / "vwra-discovery",
                )
        else:
            research.rollback()
    _print_summary(dossier, inserted, persist)
    return {
        "inserted_executions": inserted,
        "persist": persist,
        "coverage": dossier.coverage,
        "findings": [
            {
                "finding_id": item.finding_id,
                "experiment_id": item.experiment_id,
                "finding_class": item.finding_class,
                "statement": item.statement,
            }
            for item in dossier.findings
        ],
        "methods": [
            {
                "method_id": run.method_id,
                "status": run.status,
                "numeric_count": run.numeric_count,
                "reason": run.reason,
                "method_class": run.method_class,
                "reconstruction": run.reconstruction,
            }
            for run in dossier.runs
        ],
        "artifact_sha256": digests,
    }


def _atlas(
    connection: psycopg.Connection,
) -> tuple[
    list[Anchor], dict[tuple[str, str], tuple[str, str, str]], dict[str, Outcome], list[MarketEvent]
]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            select anchor_id, session_date
            from research.decision_anchors
            where symbol = 'VWRA' and anchor_kind = 'listing_month_end'
            order by session_date
            """
        )
        anchors = [Anchor(str(row[0]), row[1]) for row in cursor.fetchall()]
        cursor.execute(
            """
            select s.anchor_id, s.feature_id, s.availability, s.value_text, s.clock
            from research.state_observations s
            join research.decision_anchors a on a.anchor_id = s.anchor_id
            where a.symbol = 'VWRA' and a.anchor_kind = 'listing_month_end'
            """
        )
        atlas = {
            (str(anchor_id), str(feature_id)): (str(availability), value_text, str(clock))
            for anchor_id, feature_id, availability, value_text, clock in cursor.fetchall()
        }
        cursor.execute(
            """
            select o.anchor_id, o.status, o.value_text, o.labelled_advance
            from research.outcome_measures o
            join research.decision_anchors a on a.anchor_id = o.anchor_id
            where a.symbol = 'VWRA'
              and a.anchor_kind = 'listing_month_end'
              and o.horizon_label = '6m'
              and o.session_steps = 126
            """
        )
        outcomes = {
            str(anchor_id): Outcome(str(status), value_text, labelled)
            for anchor_id, status, value_text, labelled in cursor.fetchall()
        }
        cursor.execute(
            """
            select event_id, definition_id, family, start_date, end_date
            from research.market_events
            where symbol = 'VWRA'
              and definition_id in ('EVT-DEF-001', 'EVT-DEF-002')
            order by start_date, event_id
            """
        )
        events = [
            MarketEvent(str(event_id), str(definition_id), str(family), start, end)
            for event_id, definition_id, family, start, end in cursor.fetchall()
        ]
    return anchors, atlas, outcomes, events


def _eimi_anchors(connection: psycopg.Connection) -> tuple[int, object, object]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            select count(*)::int, min(session_date), max(session_date)
            from research.decision_anchors
            where symbol = 'EIMI' and anchor_kind = 'listing_month_end'
            """
        )
        count, first, last = cursor.fetchone()
    return int(count), first, last


def _macro_counts(series: dict, last: object) -> tuple[int, int]:
    ends: set[object] = set()
    pairs: set[tuple[str, object]] = set()
    for dataset_id, rows in series.items():
        for period, observation in rows.items():
            frequency = getattr(observation.frequency, "value", str(observation.frequency))
            bound = period_bound(period, observation.period_end, frequency)
            if VWRA_FIRST_SESSION <= bound <= last:
                ends.add(bound)
                pairs.add((dataset_id, period))
    return len(ends), len(pairs)


def _eimi_note(listing: object, anchors: tuple[int, object, object]) -> dict[str, object]:
    count, first, last = anchors
    first_session = None if listing is None else listing.dates[0].isoformat()
    return {
        "scored": False,
        "anchor_count": count,
        "first_anchor": None if first is None else first.isoformat(),
        "last_anchor": None if last is None else last.isoformat(),
        "first_stored_session": first_session,
        "stored_sessions": 0 if listing is None else len(listing.dates),
    }


def _print_summary(dossier: Dossier, inserted: int, persist: bool) -> None:
    print(f"persist={persist} inserted_executions={inserted}", flush=True)
    for run in dossier.runs:
        reason = f" reason={run.reason}" if run.reason else ""
        print(
            f"{run.method_id} {run.status} class={run.method_class} "
            f"numeric={run.numeric_count}{reason}",
            flush=True,
        )
    print(dossier.coverage, flush=True)
    for finding in dossier.findings:
        print(f"{finding.finding_id} {finding.finding_class}: {finding.statement}", flush=True)
