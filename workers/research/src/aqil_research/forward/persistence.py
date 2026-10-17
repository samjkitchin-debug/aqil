"""Persist forward intelligence records (idempotent where noted)."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

import psycopg

from aqil_research.forward.demo_fixtures import (
    DEMO_ETF_ID,
    DEMO_EVENT_MSFT_EARNINGS,
    DEMO_ISSUER_MSFT,
    DEMO_OUTCOME_ID,
    DEMO_SCENARIO_ID,
    FED_EVENT_FOMC,
    fed_fomc_event_payload,
    msft_earnings_event_payload,
    msft_expectation_payload,
    msft_outcome_payload,
    msft_scenario_payload,
    reference_horizon_date,
    vwra_holdings_snapshot_payload,
    vwra_instrument_payload,
)
from aqil_research.forward.horizon import assemble_forward_horizon
from aqil_research.forward.materiality import assess_event_materiality


class FrozenScenarioConflict(RuntimeError):
    """A later import tried to replace an already frozen scenario."""


def _payload_hash(payload: dict[str, object]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def import_demo_fixture_bundle(
    conn: psycopg.Connection, *, recorded_at: datetime
) -> dict[str, str]:
    """Insert demonstration records. Identical payloads keep the first historical row."""
    ids: dict[str, str] = {}
    instrument = vwra_instrument_payload()
    instrument_hash = _payload_hash(instrument)
    with conn.cursor() as cur:
        cur.execute(
            """
            insert into forward.etf_instrument_records (
              etf_id, payload, content_hash, evidence_class, source_id, source_locator,
              verification_date, research_status, recorded_at
            )
            values (%s, %s::jsonb, %s, %s, %s, %s, %s, %s, %s)
            on conflict (etf_id, source_id, content_hash) do nothing
            """,
            (
                DEMO_ETF_ID,
                json.dumps(instrument),
                instrument_hash,
                instrument["evidence_class"],
                instrument["source_id"],
                instrument["source_locator"],
                instrument["verification_date"],
                instrument["research_status"],
                recorded_at,
            ),
        )

    holdings = vwra_holdings_snapshot_payload()
    snapshot_id, _ = import_etf_holdings_snapshot(conn, holdings, recorded_at=recorded_at)
    ids["snapshot_id"] = str(snapshot_id)

    for event_payload, event_id in (
        (msft_earnings_event_payload(), DEMO_EVENT_MSFT_EARNINGS),
        (fed_fomc_event_payload(), FED_EVENT_FOMC),
    ):
        _upsert_catalyst(conn, event_id, event_payload, recorded_at=recorded_at)

    weight = Decimal("4.20")
    materiality = assess_event_materiality(
        weight_percentage=weight,
        holdings_completeness=str(holdings["completeness"]),
        snapshot_as_of=date.fromisoformat(str(holdings["as_of_date"])),
        reference_date=reference_horizon_date(),
        event_category="company_earnings",
    )
    _insert_exposure(
        conn,
        event_id=DEMO_EVENT_MSFT_EARNINGS,
        etf_id=DEMO_ETF_ID,
        snapshot_id=snapshot_id,
        issuer_id=DEMO_ISSUER_MSFT,
        weight=weight,
        materiality=materiality,
        holdings_completeness=str(holdings["completeness"]),
        snapshot_as_of=datetime.fromisoformat(str(holdings["as_of_date"])).date(),
        recorded_at=recorded_at,
    )

    _insert_expectation(conn, DEMO_EVENT_MSFT_EARNINGS, msft_expectation_payload(), recorded_at)
    scenario_payload = msft_scenario_payload()
    frozen_at = datetime(2026, 1, 20, 12, 0, tzinfo=UTC)
    _freeze_scenario(conn, DEMO_SCENARIO_ID, DEMO_EVENT_MSFT_EARNINGS, scenario_payload, frozen_at)
    _insert_outcome(
        conn,
        DEMO_OUTCOME_ID,
        DEMO_EVENT_MSFT_EARNINGS,
        DEMO_SCENARIO_ID,
        msft_outcome_payload(),
        datetime(2026, 1, 29, 14, 0, tzinfo=UTC),
    )
    ids["scenario_id"] = str(DEMO_SCENARIO_ID)
    return ids


def import_etf_holdings_snapshot(
    conn: psycopg.Connection,
    holdings: dict[str, object],
    *,
    recorded_at: datetime,
) -> tuple[UUID, Literal["new", "unchanged"]]:
    """Insert a holdings snapshot when content hash is new; otherwise return the existing row."""
    snapshot_id, inserted = _upsert_holdings_snapshot(conn, holdings, recorded_at=recorded_at)
    return snapshot_id, "new" if inserted else "unchanged"


def _upsert_holdings_snapshot(
    conn: psycopg.Connection,
    holdings: dict[str, object],
    *,
    recorded_at: datetime,
) -> tuple[UUID, bool]:
    retrieved_at = recorded_at
    content_hash = _payload_hash(holdings)
    with conn.cursor() as cur:
        cur.execute(
            """
            insert into forward.etf_holdings_snapshots (
              etf_id, as_of_date, source_publication_date, retrieved_at, completeness,
              source_id, source_locator, licence_evidence, currency, payload, content_hash,
              evidence_class, recorded_at
            )
            values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s)
            on conflict (etf_id, as_of_date, source_id, content_hash) do nothing
            returning snapshot_id
            """,
            (
                holdings["etf_id"],
                holdings["as_of_date"],
                holdings.get("source_publication_date"),
                retrieved_at,
                holdings["completeness"],
                holdings["source_id"],
                holdings["source_locator"],
                holdings.get("licence_evidence"),
                holdings.get("currency"),
                json.dumps(holdings),
                content_hash,
                holdings["evidence_class"],
                recorded_at,
            ),
        )
        row = cur.fetchone()
        inserted = row is not None
        if inserted:
            snapshot_id = row[0]
        else:
            cur.execute(
                """
                select snapshot_id from forward.etf_holdings_snapshots
                where etf_id = %s and as_of_date = %s and source_id = %s and content_hash = %s
                """,
                (
                    holdings["etf_id"],
                    holdings["as_of_date"],
                    holdings["source_id"],
                    content_hash,
                ),
            )
            snapshot_id = cur.fetchone()[0]

        for line in holdings.get("lines", []):
            if not isinstance(line, dict):
                continue
            cur.execute(
                """
                insert into forward.etf_holding_lines (
                  snapshot_id, line_id, holding_name, issuer_id, weight_percentage, category
                )
                values (%s, %s, %s, %s, %s, %s)
                on conflict (snapshot_id, line_id) do nothing
                """,
                (
                    snapshot_id,
                    line["line_id"],
                    line["holding_name"],
                    line.get("issuer_id"),
                    Decimal(str(line["weight_percentage"])),
                    line.get("category", "equity"),
                ),
            )
    return snapshot_id, inserted


def _upsert_catalyst(
    conn: psycopg.Connection,
    event_id: str,
    payload: dict[str, object],
    *,
    recorded_at: datetime,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            insert into forward.catalyst_events (
              event_id, category, subject_type, subject_id, title, scheduled_at, timezone,
              date_precision, status, source_id, source_locator, provider_published_at,
              first_observed_at, last_verified_at, payload, evidence_class, recorded_at
            )
            values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s)
            on conflict (event_id) do nothing
            """,
            (
                event_id,
                payload["category"],
                payload["subject_type"],
                payload["subject_id"],
                payload["title"],
                payload.get("scheduled_at"),
                payload.get("timezone"),
                payload["date_precision"],
                payload["status"],
                payload["source_id"],
                payload["source_locator"],
                payload.get("provider_published_at"),
                recorded_at,
                recorded_at,
                json.dumps(payload),
                payload["evidence_class"],
                recorded_at,
            ),
        )


def _insert_exposure(
    conn: psycopg.Connection,
    *,
    event_id: str,
    etf_id: str,
    snapshot_id: UUID,
    issuer_id: str,
    weight: Decimal,
    materiality: object,
    holdings_completeness: str,
    snapshot_as_of: date,
    recorded_at: datetime,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            insert into forward.catalyst_etf_exposure (
              event_id, etf_id, snapshot_id, issuer_id, weight_percentage,
              materiality, materiality_rules_version, rationale,
              holdings_completeness, snapshot_as_of, evidence_class, recorded_at
            )
            values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            on conflict (event_id, etf_id, snapshot_id, issuer_id) do nothing
            """,
            (
                event_id,
                etf_id,
                snapshot_id,
                issuer_id,
                weight,
                materiality.category,
                materiality.rules_version,
                materiality.rationale,
                holdings_completeness,
                snapshot_as_of,
                "calculated",
                recorded_at,
            ),
        )


def _insert_expectation(
    conn: psycopg.Connection,
    event_id: str,
    payload: dict[str, object],
    recorded_at: datetime,
) -> None:
    digest = _payload_hash(payload)
    source_id = str(payload.get("source_id", "fixture"))
    with conn.cursor() as cur:
        cur.execute(
            """
            insert into forward.event_expectations (
              event_id, recorded_at, payload, content_hash, source_id, evidence_class
            )
            values (%s, %s, %s::jsonb, %s, %s, %s)
            on conflict (event_id, source_id, content_hash) do nothing
            """,
            (
                event_id,
                recorded_at,
                json.dumps(payload),
                digest,
                source_id,
                payload.get("evidence_class", "synthetic_demonstration"),
            ),
        )


def _freeze_scenario(
    conn: psycopg.Connection,
    scenario_id: UUID,
    event_id: str,
    payload: dict[str, object],
    frozen_at: datetime,
) -> None:
    digest = _payload_hash(payload)
    with conn.cursor() as cur:
        cur.execute(
            """
            insert into forward.forward_scenarios (
              scenario_id, event_id, frozen_at, payload, payload_hash, evidence_class
            )
            values (%s, %s, %s, %s::jsonb, %s, %s)
            on conflict (scenario_id) do nothing
            returning scenario_id
            """,
            (
                scenario_id,
                event_id,
                frozen_at,
                json.dumps(payload),
                digest,
                payload.get("evidence_class", "synthetic_demonstration"),
            ),
        )
        inserted = cur.fetchone()
        if inserted is None:
            cur.execute(
                "select payload_hash from forward.forward_scenarios where scenario_id = %s",
                (scenario_id,),
            )
            existing = cur.fetchone()[0]
            if existing != digest:
                raise FrozenScenarioConflict(
                    "frozen scenario already exists with a different payload",
                )


def _insert_outcome(
    conn: psycopg.Connection,
    outcome_id: UUID,
    event_id: str,
    scenario_id: UUID,
    payload: dict[str, object],
    observed_at: datetime,
) -> None:
    digest = _payload_hash(payload)
    with conn.cursor() as cur:
        cur.execute(
            """
            insert into forward.event_outcomes (
              outcome_id, event_id, scenario_id, observed_at, payload, content_hash,
              source_id, evidence_class
            )
            values (%s, %s, %s, %s, %s::jsonb, %s, %s, %s)
            on conflict (outcome_id) do nothing
            """,
            (
                outcome_id,
                event_id,
                scenario_id,
                observed_at,
                json.dumps(payload),
                digest,
                payload.get("source_id", "fixture"),
                payload.get("evidence_class", "synthetic_demonstration"),
            ),
        )


def load_frozen_scenario(conn: psycopg.Connection, scenario_id: UUID) -> dict[str, object]:
    """Return the stored scenario row. Callers must not rebuild it from fixtures."""
    with conn.cursor() as cur:
        cur.execute(
            """
            select scenario_id::text, event_id, frozen_at, payload, payload_hash, evidence_class
            from forward.forward_scenarios
            where scenario_id = %s
            """,
            (scenario_id,),
        )
        row = cur.fetchone()
    if row is None:
        raise RuntimeError("frozen scenario was not persisted")
    payload = row[3]
    if isinstance(payload, str):
        payload = json.loads(payload)
    return {
        "scenario_id": row[0],
        "event_id": row[1],
        "frozen_at": row[2],
        "payload": payload,
        "payload_hash": row[4],
        "evidence_class": row[5],
    }


def load_persisted_forward_horizon(conn: psycopg.Connection) -> dict[str, object]:
    """Post-event bundle from the frozen scenario row and the exposure it was linked to."""
    scenario = load_frozen_scenario(conn, DEMO_SCENARIO_ID)
    with conn.cursor() as cur:
        cur.execute(
            """
            select outcome_id::text, event_id, scenario_id::text, payload
            from forward.event_outcomes
            where scenario_id = %s
            order by observed_at
            limit 1
            """,
            (DEMO_SCENARIO_ID,),
        )
        outcome_row = cur.fetchone()
        cur.execute(
            """
            select payload from forward.etf_instrument_records
            where etf_id = %s
            order by recorded_at
            limit 1
            """,
            (DEMO_ETF_ID,),
        )
        instrument = cur.fetchone()[0]
        cur.execute(
            """
            select snap.payload
            from forward.catalyst_etf_exposure exposure
            join forward.etf_holdings_snapshots snap
              on snap.snapshot_id = exposure.snapshot_id
            where exposure.event_id = %s
            order by exposure.recorded_at
            limit 1
            """,
            (DEMO_EVENT_MSFT_EARNINGS,),
        )
        holdings = cur.fetchone()[0]
        cur.execute(
            "select payload from forward.catalyst_events where event_id = %s",
            (DEMO_EVENT_MSFT_EARNINGS,),
        )
        msft_event = cur.fetchone()[0]
        cur.execute(
            "select payload from forward.catalyst_events where event_id = %s",
            (FED_EVENT_FOMC,),
        )
        fed_event = cur.fetchone()[0]

    if isinstance(instrument, str):
        instrument = json.loads(instrument)
    if isinstance(holdings, str):
        holdings = json.loads(holdings)
    if isinstance(msft_event, str):
        msft_event = json.loads(msft_event)
    if isinstance(fed_event, str):
        fed_event = json.loads(fed_event)

    outcome_payload = None
    outcome_id = None
    if outcome_row is not None:
        if outcome_row[2] != scenario["scenario_id"]:
            raise RuntimeError("outcome does not reference the frozen scenario")
        outcome_id = outcome_row[0]
        outcome_payload = outcome_row[3]
        if isinstance(outcome_payload, str):
            outcome_payload = json.loads(outcome_payload)

    frozen_at = scenario["frozen_at"]
    frozen_text = frozen_at.isoformat() if isinstance(frozen_at, datetime) else str(frozen_at)
    payload = scenario["payload"]
    if not isinstance(payload, dict):
        raise RuntimeError("frozen scenario payload is not an object")
    return assemble_forward_horizon(
        instrument=instrument,
        holdings=holdings,
        msft_event=msft_event,
        fed_event=fed_event,
        scenario_id=str(scenario["scenario_id"]),
        scenario_frozen_at=frozen_text,
        scenario=payload,
        outcome_id=outcome_id,
        outcome=outcome_payload,
        scenario_source="database",
    )
