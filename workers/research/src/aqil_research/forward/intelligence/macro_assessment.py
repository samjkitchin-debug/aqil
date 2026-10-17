"""Freeze pre-event macro assessments for verified calendar events."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

import psycopg

from aqil_research.forward.intelligence.pre_event import build_macro_pre_event_scenario
from aqil_research.forward.macro_relevance import assess_macro_relevance
from aqil_research.forward.persistence import FrozenScenarioConflict, _freeze_scenario

MACRO_SCENARIO_NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")
MACRO_CATEGORIES = frozenset(
    {
        "central_bank_meeting",
        "us_employment_report",
    },
)


def scenario_id_for_event(event_id: str) -> uuid.UUID:
    return uuid.uuid5(MACRO_SCENARIO_NAMESPACE, event_id)


def freeze_macro_pre_event_assessments(
    conn: psycopg.Connection,
    *,
    frozen_at: datetime | None = None,
) -> tuple[int, int]:
    """Ensure each verified macro event has an immutable research_assessment scenario.

    Returns (newly_frozen, already_present).
    """
    when = frozen_at or datetime.now(tz=UTC)
    new_count = 0
    existing_count = 0
    with conn.cursor() as cur:
        cur.execute(
            """
            select event_id, category, payload
            from forward.catalyst_events
            where evidence_class = 'verified_schedule'
              and category = any(%s)
            """,
            (list(MACRO_CATEGORIES),),
        )
        rows = cur.fetchall()

    for event_id, category, payload in rows:
        if isinstance(payload, str):
            payload = json.loads(payload)
        if not isinstance(payload, dict):
            continue
        scenario_id = scenario_id_for_event(str(event_id))
        macro = assess_macro_relevance(str(category))
        scenario_payload = build_macro_pre_event_scenario(
            event_payload=payload,
            macro_rationale=macro.rationale,
            transmission=macro.transmission_mechanism,
            geographic_exposure=macro.geographic_exposure,
        )
        scenario_payload["frozen_at_reference"] = when.isoformat()
        with conn.cursor() as cur:
            cur.execute(
                "select 1 from forward.forward_scenarios where scenario_id = %s",
                (scenario_id,),
            )
            if cur.fetchone() is not None:
                existing_count += 1
                continue
        try:
            _freeze_scenario(conn, scenario_id, str(event_id), scenario_payload, when)
            new_count += 1
        except FrozenScenarioConflict:
            existing_count += 1
    return new_count, existing_count
