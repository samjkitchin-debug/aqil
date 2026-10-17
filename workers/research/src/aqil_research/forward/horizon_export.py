"""Build forward_horizon.v1 bundle from persisted records."""

from __future__ import annotations

import json
from datetime import date, timedelta
from decimal import Decimal

import psycopg

from aqil_research.forward.demo_fixtures import horizon_bundle_generated_at
from aqil_research.forward.macro_relevance import assess_macro_relevance
from aqil_research.forward.materiality import assess_event_materiality


def build_horizon_from_database(
    conn: psycopg.Connection,
    *,
    reference_date: date | None = None,
    horizon_days: int = 180,
    include_demonstration: bool = True,
) -> dict[str, object]:
    ref = reference_date or date.today()
    window_end = ref + timedelta(days=horizon_days)
    events = _load_verified_events(conn, ref, window_end)
    etfs, exposures = _load_etf_exposure(conn, ref)

    demo_events: list[dict[str, object]] = []
    demo_scenarios: list[dict[str, object]] = []
    demo_outcomes: list[dict[str, object]] = []
    if include_demonstration:
        from aqil_research.forward.persistence import load_persisted_forward_horizon

        try:
            demo_bundle = load_persisted_forward_horizon(conn)
        except Exception:
            demo_bundle = None
        if demo_bundle is not None:
            for event in demo_bundle["events"]:
                if event.get("is_fixture"):
                    demo_events.append(event)
            demo_scenarios = demo_bundle.get("scenarios", [])
            demo_outcomes = demo_bundle.get("outcomes", [])

    merged_events = events + demo_events
    merged_events.sort(key=lambda row: row.get("scheduled_date", "unknown"))

    has_verified = any(not row.get("is_fixture") for row in merged_events)
    has_demo = any(row.get("is_fixture") for row in merged_events) or include_demonstration
    if has_verified and has_demo:
        data_mode = "mixed"
    elif has_verified:
        data_mode = "verified_source"
    else:
        data_mode = "fixture_demonstration"

    return {
        "schema_version": "1.0",
        "generated_at": horizon_bundle_generated_at().isoformat(),
        "data_mode": data_mode,
        "etfs": etfs,
        "events": merged_events,
        "exposures": exposures,
        "scenarios": demo_scenarios,
        "outcomes": demo_outcomes,
    }


def _load_verified_events(
    conn: psycopg.Connection,
    start: date,
    end: date,
) -> list[dict[str, object]]:
    with conn.cursor() as cur:
        cur.execute(
            """
            select event_id, title, category, subject_id, scheduled_at, timezone,
                   date_precision, evidence_class, payload
            from forward.catalyst_events
            where evidence_class in (
              'verified_schedule', 'verified_announcement', 'curated_verified'
            )
              and scheduled_at is not null
              and scheduled_at::date >= %s
              and scheduled_at::date <= %s
            order by scheduled_at
            """,
            (start, end),
        )
        rows = cur.fetchall()

    events: list[dict[str, object]] = []
    for row in rows:
        payload = row[8]
        if isinstance(payload, str):
            payload = json.loads(payload)
        category = row[2]
        macro = assess_macro_relevance(category)
        materiality = assess_event_materiality(
            weight_percentage=None,
            holdings_completeness=None,
            snapshot_as_of=None,
            reference_date=start,
            event_category=category,
        )
        scheduled_at = row[4]
        scheduled_date = scheduled_at.date().isoformat() if scheduled_at else "unknown"
        events.append(
            {
                "event_id": row[0],
                "title": row[1],
                "category": category,
                "subject_label": row[3],
                "scheduled_date": scheduled_date,
                "scheduled_time": scheduled_at.isoformat() if scheduled_at else None,
                "timezone": row[5],
                "date_precision": row[6],
                "schedule_evidence": row[7],
                "materiality": materiality.category,
                "materiality_basis": "insufficient_evidence"
                if materiality.category == "insufficient_evidence"
                else "macro_qualitative",
                "interpretation_status": "unverified",
                "source_confidence": row[7],
                "why_it_matters": macro.rationale,
                "etf_ids": [],
                "is_fixture": False,
                "macro_relevance": {
                    "transmission": macro.transmission_mechanism,
                    "geography": macro.geographic_exposure,
                    "confidence": macro.confidence,
                },
            },
        )
    return events


def _load_etf_exposure(
    conn: psycopg.Connection,
    reference_date: date,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    with conn.cursor() as cur:
        cur.execute(
            """
            select distinct on (etf_id)
              etf_id, payload, evidence_class, as_of_date, completeness, source_locator
            from forward.etf_holdings_snapshots
            order by etf_id, as_of_date desc, recorded_at desc
            """,
        )
        holding_rows = cur.fetchall()
        cur.execute(
            """
            select distinct on (etf_id)
              etf_id, payload
            from forward.etf_instrument_records
            order by etf_id, recorded_at desc
            """,
        )
        instrument_rows = {row[0]: row[1] for row in cur.fetchall()}

    etfs: list[dict[str, object]] = []
    exposures: list[dict[str, object]] = []
    for etf_id, holdings_payload, evidence_class, as_of, completeness, _locator in holding_rows:
        instrument = instrument_rows.get(etf_id, {})
        if isinstance(instrument, str):
            instrument = json.loads(instrument)
        if isinstance(holdings_payload, str):
            holdings_payload = json.loads(holdings_payload)
        holdings_evidence = (
            "provider_holdings"
            if evidence_class == "provider_holdings"
            else "synthetic_demonstration"
        )
        caveat = (
            "Holdings weights are from the labelled provider snapshot."
            if holdings_evidence == "provider_holdings"
            else (
                "The ISIN may identify the share class. Weights are synthetic demonstration "
                "data unless holdings_evidence is provider_holdings."
            )
        )
        top_holdings = []
        for line in holdings_payload.get("lines", []):
            if not isinstance(line, dict) or line.get("category") == "cash":
                continue
            top_holdings.append(
                {
                    "name": line["holding_name"],
                    "issuer_id": line.get("issuer_id"),
                    "weight_percentage": str(line["weight_percentage"]),
                },
            )
        etfs.append(
            {
                "etf_id": etf_id,
                "legal_name": instrument.get("legal_name", etf_id),
                "ticker": instrument.get("ticker", ""),
                "exchange": instrument.get("exchange", ""),
                "isin": instrument.get("isin"),
                "identity_evidence": instrument.get("evidence_class", "unverified"),
                "holdings_as_of": as_of.isoformat() if hasattr(as_of, "isoformat") else str(as_of),
                "completeness": completeness,
                "holdings_evidence": holdings_evidence,
                "holdings_caveat": caveat,
                "top_holdings": top_holdings,
            },
        )

        with conn.cursor() as cur:
            cur.execute(
                """
                select event_id, issuer_id, weight_percentage, materiality, snapshot_as_of
                from forward.catalyst_etf_exposure
                where etf_id = %s
                """,
                (etf_id,),
            )
            for event_id, issuer_id, weight, _stored_mat, snapshot_as_of in cur.fetchall():
                snap_date = (
                    snapshot_as_of
                    if isinstance(snapshot_as_of, date)
                    else date.fromisoformat(str(snapshot_as_of))
                )
                mat = assess_event_materiality(
                    weight_percentage=Decimal(str(weight)),
                    holdings_completeness=completeness,
                    snapshot_as_of=snap_date,
                    reference_date=reference_date,
                    event_category="company_earnings",
                )
                exposures.append(
                    {
                        "event_id": event_id,
                        "etf_id": etf_id,
                        "issuer_id": issuer_id,
                        "weight_percentage": str(weight),
                        "weight_evidence": holdings_evidence,
                        "materiality": mat.category,
                        "materiality_evidence": "calculated",
                        "snapshot_as_of": snap_date.isoformat(),
                    },
                )

    return etfs, exposures
