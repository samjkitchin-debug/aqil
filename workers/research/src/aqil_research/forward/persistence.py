"""Persist forward intelligence records (idempotent where noted)."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, date, datetime
from decimal import Decimal
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
from aqil_research.forward.materiality import MaterialityInput, assess_materiality


def _payload_hash(payload: dict[str, object]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def import_demo_fixture_bundle(
    conn: psycopg.Connection, *, recorded_at: datetime
) -> dict[str, str]:
    """Insert demonstration records; safe to call once per empty demo."""
    ids: dict[str, str] = {}
    instrument = vwra_instrument_payload()
    with conn.cursor() as cur:
        cur.execute(
            """
            insert into forward.etf_instrument_records (
              etf_id, payload, source_id, source_locator,
              verification_date, research_status, recorded_at
            )
            values (%s, %s::jsonb, %s, %s, %s, %s, %s)
            """,
            (
                DEMO_ETF_ID,
                json.dumps(instrument),
                instrument["source_id"],
                instrument["source_locator"],
                instrument["verification_date"],
                instrument["research_status"],
                recorded_at,
            ),
        )

    holdings = vwra_holdings_snapshot_payload()
    snapshot_id = _upsert_holdings_snapshot(conn, holdings, recorded_at=recorded_at)
    ids["snapshot_id"] = str(snapshot_id)

    for event_payload, event_id in (
        (msft_earnings_event_payload(), DEMO_EVENT_MSFT_EARNINGS),
        (fed_fomc_event_payload(), FED_EVENT_FOMC),
    ):
        _upsert_catalyst(conn, event_id, event_payload, recorded_at=recorded_at)

    weight = Decimal("4.20")
    materiality = assess_materiality(
        MaterialityInput(
            weight_percentage=weight,
            holdings_completeness=str(holdings["completeness"]),
            snapshot_as_of=date.fromisoformat(str(holdings["as_of_date"])),
            reference_date=reference_horizon_date(),
            event_category="company_earnings",
        ),
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


def _upsert_holdings_snapshot(
    conn: psycopg.Connection,
    holdings: dict[str, object],
    *,
    recorded_at: datetime,
) -> UUID:
    retrieved_at = recorded_at
    with conn.cursor() as cur:
        cur.execute(
            """
            insert into forward.etf_holdings_snapshots (
              etf_id, as_of_date, source_publication_date, retrieved_at, completeness,
              source_id, source_locator, licence_evidence, currency, payload, recorded_at
            )
            values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s)
            on conflict (etf_id, as_of_date, source_id, retrieved_at) do nothing
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
                recorded_at,
            ),
        )
        row = cur.fetchone()
        if row is not None:
            snapshot_id = row[0]
        else:
            cur.execute(
                """
                select snapshot_id from forward.etf_holdings_snapshots
                where etf_id = %s and as_of_date = %s and source_id = %s and retrieved_at = %s
                """,
                (holdings["etf_id"], holdings["as_of_date"], holdings["source_id"], retrieved_at),
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
                on conflict do nothing
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
    return snapshot_id


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
              first_observed_at, last_verified_at, payload, recorded_at
            )
            values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s)
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
              holdings_completeness, snapshot_as_of, recorded_at
            )
            values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                recorded_at,
            ),
        )


def _insert_expectation(
    conn: psycopg.Connection,
    event_id: str,
    payload: dict[str, object],
    recorded_at: datetime,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            insert into forward.event_expectations (event_id, recorded_at, payload, source_id)
            values (%s, %s, %s::jsonb, %s)
            """,
            (event_id, recorded_at, json.dumps(payload), payload.get("source_id", "fixture")),
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
              scenario_id, event_id, frozen_at, payload, payload_hash
            )
            values (%s, %s, %s, %s::jsonb, %s)
            on conflict do nothing
            """,
            (scenario_id, event_id, frozen_at, json.dumps(payload), digest),
        )


def _insert_outcome(
    conn: psycopg.Connection,
    outcome_id: UUID,
    event_id: str,
    scenario_id: UUID,
    payload: dict[str, object],
    observed_at: datetime,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            insert into forward.event_outcomes (
              outcome_id, event_id, scenario_id, observed_at, payload, source_id
            )
            values (%s, %s, %s, %s, %s::jsonb, %s)
            on conflict do nothing
            """,
            (
                outcome_id,
                event_id,
                scenario_id,
                observed_at,
                json.dumps(payload),
                payload.get("source_id", "fixture"),
            ),
        )
