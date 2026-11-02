"""Version 1 read contract for observations, methodology results, and cycles.

Consumers import this module. They do not import a method implementation
and they do not embed the SQL.
"""

from __future__ import annotations

from datetime import datetime

import psycopg

RESEARCH_READ_VERSION = "1"


def read_observations(conn: psycopg.Connection, dataset_id: str) -> tuple[dict[str, object], ...]:
    rows = conn.execute(
        """
        select observation_id, dataset_id, period_start, raw_value, unit, frequency
        from research.economic_observations
        where dataset_id = %s
        order by period_start, observation_id
        """,
        (dataset_id,),
    ).fetchall()
    return tuple(
        {
            "observation_id": row[0],
            "dataset_id": row[1],
            "period_start": row[2].isoformat(),
            "raw_value": row[3],
            "unit": row[4],
            "frequency": row[5],
        }
        for row in rows
    )


def read_methodology_result(conn: psycopg.Connection, run_id: str) -> dict[str, object] | None:
    row = conn.execute(
        """
        select run_id, method_id, method_version, executed_at, execution_status,
               publication_allowed, data_sufficiency, calculation
        from research.research_runs
        where run_id = %s
        """,
        (run_id,),
    ).fetchone()
    if row is None:
        return None
    executed: datetime = row[3]
    return {
        "version": RESEARCH_READ_VERSION,
        "run_id": row[0],
        "method_id": row[1],
        "method_version": row[2],
        "executed_at": executed.isoformat(),
        "execution_status": row[4],
        "publication_allowed": row[5] is True,
        "data_sufficiency": row[6],
        "calculation": row[7],
    }


def read_operational_state(conn: psycopg.Connection) -> dict[str, object]:
    cycle = conn.execute(
        """
        select cycle_id, started_at, finished_at, status, detail
        from research.research_cycles
        order by started_at desc
        limit 1
        """
    ).fetchone()
    if cycle is None:
        return {
            "version": RESEARCH_READ_VERSION,
            "cycle_id": None,
            "started_at": None,
            "finished_at": None,
            "status": None,
            "detail": "",
            "events": [],
        }
    events = conn.execute(
        """
        select phase, subject_id, outcome, detail
        from research.research_cycle_events
        where cycle_id = %s
        order by recorded_at, subject_id
        """,
        (cycle[0],),
    ).fetchall()
    return {
        "version": RESEARCH_READ_VERSION,
        "cycle_id": str(cycle[0]),
        "started_at": cycle[1].isoformat() if cycle[1] is not None else None,
        "finished_at": cycle[2].isoformat() if cycle[2] is not None else None,
        "status": cycle[3],
        "detail": cycle[4] or "",
        "events": [
            {
                "phase": row[0],
                "subject_id": row[1],
                "outcome": row[2],
                "detail": row[3],
            }
            for row in events
        ],
    }
