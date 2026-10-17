"""Operator coverage and health summary for forward intelligence."""

from __future__ import annotations

import json
from datetime import UTC, datetime

import psycopg

from aqil_research.sources.rights import load_source_rights, source_usable


def build_coverage_report(conn: psycopg.Connection) -> dict[str, object]:
    now = datetime.now(tz=UTC)
    rights_rows = load_source_rights()
    forward_sources = [
        row
        for row in rights_rows
        if row.dataset_id.startswith("forward.")
        or row.source_id.startswith("federal_reserve")
        or row.source_id.startswith("bls_release")
        or row.source_id.startswith("vanguard")
    ]

    with conn.cursor() as cur:
        cur.execute(
            """
            select evidence_class, count(*)
            from forward.catalyst_events
            group by evidence_class
            """,
        )
        events_by_class = {row[0]: row[1] for row in cur.fetchall()}
        cur.execute(
            """
            select count(*) from forward.catalyst_events
            where evidence_class = 'verified_schedule' and date_precision = 'confirmed'
            """,
        )
        confirmed_schedules = cur.fetchone()[0]
        cur.execute(
            """
            select count(*) from forward.catalyst_events
            where evidence_class = 'verified_schedule' and date_precision = 'tentative'
            """,
        )
        tentative_schedules = cur.fetchone()[0]
        cur.execute(
            """
            select evidence_class, count(*)
            from forward.etf_holdings_snapshots
            group by evidence_class
            """,
        )
        holdings_by_class = {row[0]: row[1] for row in cur.fetchall()}
        cur.execute(
            """
            select source_id, outcome, finished_at, records_new, records_updated, error_summary
            from forward.collection_runs
            order by finished_at desc
            limit 10
            """,
        )
        recent_runs = [
            {
                "source_id": row[0],
                "outcome": row[1],
                "finished_at": row[2].isoformat() if row[2] else None,
                "records_new": row[3],
                "records_updated": row[4],
                "error_summary": row[5],
            }
            for row in cur.fetchall()
        ]

    providers = []
    for row in forward_sources:
        providers.append(
            {
                "source_id": row.source_id,
                "dataset_id": row.dataset_id,
                "operational_status": row.operational_status.value,
                "automated_access": row.automated_access.value,
                "usable_for_ingest": source_usable(row),
            },
        )

    return {
        "schema_version": "1.0",
        "generated_at": now.isoformat(),
        "providers": providers,
        "catalyst_events_by_evidence_class": events_by_class,
        "confirmed_future_schedules": confirmed_schedules,
        "tentative_future_schedules": tentative_schedules,
        "holdings_snapshots_by_evidence_class": holdings_by_class,
        "synthetic_records_remaining": events_by_class.get("synthetic_demonstration", 0),
        "recent_collection_runs": recent_runs,
    }


def format_coverage_report(report: dict[str, object]) -> str:
    return json.dumps(report, indent=2, default=str)
