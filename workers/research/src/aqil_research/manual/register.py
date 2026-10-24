"""Append macro events and one theme assessment. Not part of research refresh."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Literal
from uuid import uuid4

import psycopg

from aqil_research.events.cluster import SyndicatedDocument, cluster_syndicated_documents
from aqil_research.manual.rights_gate import RegistrationBlocked, require_rights
from aqil_research.manual.sec_capex import (
    THEME_DOES_NOT_ESTABLISH,
    AnnualCapexFact,
    extract_annual_capex,
)
from aqil_research.manual.ustr_notice import (
    USTR_CHANNEL_NOTE,
    USTR_CHANNELS,
    USTR_CLAIM,
    USTR_CLUSTER_KEY,
    USTR_EVENT_DATES,
    USTR_EVENT_KEY,
    USTR_NOTICE_URL,
    USTR_TITLE,
    SuppliedUstrNotice,
    notice_supports_ustr_claim,
)
from aqil_research.sources.rights import (
    RightsOperation,
    SourceRightsRecord,
    find_source_rights,
    load_source_rights,
)

RecordClass = Literal["recorded", "synthetic_fixture"]
PRESS_SOURCE_IDS = ("federal_reserve_monetary_press", "ecb_monetary_press")
_STORE_AND_DISPLAY = (
    RightsOperation.RAW_DATA_RETENTION,
    RightsOperation.REDISTRIBUTION,
)
_NOT_YET: tuple[tuple[str, str], ...] = (
    (
        "commercial_adoption",
        "A measure of customers using the infrastructure in production is still required. "
        "This observation is missing.",
    ),
    (
        "semiconductor_equipment_demand",
        "A measure of semiconductor equipment orders or shipments is still required. "
        "This observation is missing.",
    ),
    (
        "earnings_cash_flow",
        "Revenue and earnings for the infrastructure activity are still required. "
        "This observation is missing.",
    ),
    (
        "market_breadth_relative_performance",
        "Relative market performance across the related companies is still required. "
        "This observation is missing.",
    ),
    (
        "financing_sustainability",
        "A measure of funding that can sustain the spending is still required. "
        "This observation is missing.",
    ),
)


@dataclass(frozen=True, slots=True)
class RegistrationResult:
    outcome: str
    detail: str


def cluster_key_for(document_id: str, origin_key: str) -> str:
    """Store the helper's cluster key. Repeats of one origin stay one cluster."""
    clustered = cluster_syndicated_documents(
        (SyndicatedDocument(document_id=document_id, cluster_key=origin_key),)
    )
    return clustered.clusters[0].cluster_key


def register_ustr_notice(
    conn: psycopg.Connection,
    *,
    body: str,
    rights: SourceRightsRecord,
    record_class: RecordClass,
    retrieved_at: datetime,
    fetch_performed: bool,
) -> RegistrationResult:
    if rights.source_id != "govinfo_federal_register":
        raise RegistrationBlocked("USTR registration requires govinfo_federal_register")
    if fetch_performed:
        require_rights(
            rights,
            (RightsOperation.AUTOMATED_ACCESS, RightsOperation.RAW_DATA_RETENTION),
        )
    require_rights(rights, _STORE_AND_DISPLAY)
    if not notice_supports_ustr_claim(body):
        raise RegistrationBlocked(
            "The Federal Register notice does not support the stated continuation claim.",
        )
    published_at = datetime(2026, 10, 7, tzinfo=UTC)
    if published_at > retrieved_at:
        raise RegistrationBlocked("publication time is after retrieval")
    title = USTR_TITLE
    url = USTR_NOTICE_URL
    content_hash = _content_hash(rights.source_id, title, url, published_at)
    with conn.transaction():
        _defer(conn)
        update_id, inserted_update = _upsert_sourced_update(
            conn,
            rights=rights,
            title=title,
            canonical_url=url,
            published_at=published_at,
            retrieved_at=retrieved_at,
            content_hash=content_hash,
            collection_mode="live" if record_class == "recorded" else "fixture",
            endpoint_host="www.govinfo.gov",
            request_series_ids=["2026-20510"],
            http_status=200 if fetch_performed else None,
            response_bytes=len(body.encode("utf-8")),
            fingerprint=hashlib.sha256(body.encode("utf-8")).hexdigest(),
            ingest_notes=["short summary stored; document body not stored"],
        )
        event_inserted = _upsert_event(
            conn,
            event_key=USTR_EVENT_KEY,
            category="trade_policy",
            epistemic_class="confirmed_event",
            claim_scope="policy_action_stated",
            summary=USTR_CLAIM,
            country="United States",
            event_on=date(2026, 8, 23),
            event_dates_stated=USTR_EVENT_DATES,
            indicator_source_ids=list(USTR_CHANNELS),
            channel_note=USTR_CHANNEL_NOTE,
            surface_on_today=True,
            surface_reason=USTR_CLAIM,
            surfaced_at=retrieved_at,
            record_class=record_class,
            investment_implication="no_action",
        )
        event_id = _event_id(conn, USTR_EVENT_KEY)
        _link_evidence(
            conn,
            event_id=event_id,
            update_id=update_id,
            role="primary",
            cluster_key=cluster_key_for(update_id, USTR_CLUSTER_KEY),
        )
        _check(conn)
    outcome = "recorded" if event_inserted or inserted_update else "unchanged"
    return RegistrationResult(outcome, USTR_EVENT_KEY)


def register_supplied_ustr_notice(
    conn: psycopg.Connection,
    *,
    notice: SuppliedUstrNotice,
    rights: SourceRightsRecord,
    record_class: RecordClass,
    retrieved_at: datetime,
) -> RegistrationResult:
    """Store the operator's short summary. This function does not fetch the notice."""
    if rights.source_id in PRESS_SOURCE_IDS:
        raise RegistrationBlocked(
            "policy_action_stated cannot use a central-bank press release as the primary source",
        )
    if rights.source_id != "govinfo_federal_register":
        raise RegistrationBlocked("USTR registration requires govinfo_federal_register")
    require_rights(rights, _STORE_AND_DISPLAY)
    if notice.published_at > retrieved_at:
        raise RegistrationBlocked("publication time is after retrieval")
    content_hash = _content_hash(
        rights.source_id,
        notice.title,
        notice.canonical_url,
        notice.published_at,
    )
    summary_bytes = notice.summary.encode("utf-8")
    with conn.transaction():
        _defer(conn)
        update_id, inserted_update = _upsert_sourced_update(
            conn,
            rights=rights,
            title=notice.title,
            canonical_url=notice.canonical_url,
            published_at=notice.published_at,
            retrieved_at=retrieved_at,
            content_hash=content_hash,
            collection_mode="live" if record_class == "recorded" else "fixture",
            endpoint_host="www.govinfo.gov",
            request_series_ids=["2026-20510"],
            http_status=None,
            response_bytes=len(summary_bytes),
            fingerprint=hashlib.sha256(summary_bytes).hexdigest(),
            ingest_notes=["no HTTP fetch; short summary stored; document body not stored"],
        )
        event_inserted = _upsert_event(
            conn,
            event_key=USTR_EVENT_KEY,
            category="trade_policy",
            epistemic_class="confirmed_event",
            claim_scope="policy_action_stated",
            summary=notice.summary,
            country="United States",
            event_on=notice.event_on,
            event_dates_stated=notice.event_dates,
            indicator_source_ids=list(USTR_CHANNELS),
            channel_note=USTR_CHANNEL_NOTE,
            surface_on_today=True,
            surface_reason=notice.summary,
            surfaced_at=retrieved_at,
            record_class=record_class,
            investment_implication="no_action",
        )
        event_id = _event_id(conn, USTR_EVENT_KEY)
        _link_evidence(
            conn,
            event_id=event_id,
            update_id=update_id,
            role="primary",
            cluster_key=cluster_key_for(update_id, USTR_CLUSTER_KEY),
        )
        _check(conn)
    outcome = "recorded" if event_inserted or inserted_update else "unchanged"
    return RegistrationResult(outcome, USTR_EVENT_KEY)


def register_publication_recorded(
    conn: psycopg.Connection,
    *,
    record_class: RecordClass,
    rights_records: tuple[SourceRightsRecord, ...] | None = None,
) -> RegistrationResult:
    records = rights_records if rights_records is not None else load_source_rights()
    row = conn.execute(
        """
        select update_id::text, source_id, title, canonical_url, published_at, content_hash
        from research.sourced_updates
        where source_id = any(%s)
          and published_at is not null
        order by published_at desc
        limit 1
        """,
        (list(PRESS_SOURCE_IDS),),
    ).fetchone()
    if row is None:
        raise RegistrationBlocked(
            "No federal_reserve_monetary_press or ecb_monetary_press sourced update is stored.",
        )
    update_id, source_id, title, _url, published_at, content_hash = row
    rights = find_source_rights(records, source_id=source_id)
    if rights is None:
        raise RegistrationBlocked(f"no rights row for {source_id}")
    require_rights(rights, _STORE_AND_DISPLAY)
    summary = _publication_summary(source_id, title)
    event_key = f"publication_{source_id}_{update_id.replace('-', '')}"
    published_date = published_at.date()
    with conn.transaction():
        _defer(conn)
        inserted = _upsert_event(
            conn,
            event_key=event_key,
            category="monetary_publication",
            epistemic_class="confirmed_event",
            claim_scope="publication_recorded",
            summary=summary,
            country="United States" if source_id.startswith("federal_reserve") else "Euro area",
            event_on=published_date,
            event_dates_stated=_uk_date(published_date),
            indicator_source_ids=[],
            channel_note=None,
            surface_on_today=False,
            surface_reason=None,
            surfaced_at=None,
            record_class=record_class,
            investment_implication="no_action",
        )
        event_id = _event_id(conn, event_key)
        origin = f"publication-{source_id}-{content_hash[:16]}"
        _link_evidence(
            conn,
            event_id=event_id,
            update_id=update_id,
            role="primary",
            cluster_key=cluster_key_for(update_id, origin),
        )
        _check(conn)
    return RegistrationResult("recorded" if inserted else "unchanged", event_key)


def register_ai_infrastructure(
    conn: psycopg.Connection,
    *,
    payload: object,
    rights: SourceRightsRecord,
    record_class: RecordClass,
    retrieved_at: datetime,
    fetch_performed: bool,
) -> RegistrationResult:
    if rights.source_id != "sec_edgar_company_filings":
        raise RegistrationBlocked("theme registration requires sec_edgar_company_filings")
    if fetch_performed:
        require_rights(
            rights,
            (RightsOperation.AUTOMATED_ACCESS, RightsOperation.RAW_DATA_RETENTION),
        )
    require_rights(rights, _STORE_AND_DISPLAY)
    extracted = extract_annual_capex(payload)
    if extracted is None:
        raise RegistrationBlocked(
            "SEC companyfacts did not contain two comparable annual "
            "PaymentsToAcquirePropertyPlantAndEquipment facts.",
        )
    newer, older = extracted
    if _theme_periods_stored(conn, newer, older, record_class):
        return RegistrationResult("unchanged", "ai_infrastructure_investment")
    real_economy = _real_economy_text(newer, older)
    fingerprint = hashlib.sha256(
        f"{newer.accession}|{older.accession}".encode(),
    ).hexdigest()
    with conn.transaction():
        _defer(conn)
        retrieval_id = _insert_retrieval(
            conn,
            rights=rights,
            retrieved_at=retrieved_at,
            collection_mode="live" if record_class == "recorded" else "fixture",
            endpoint_host="data.sec.gov",
            request_series_ids=["CIK0000789019"],
            http_status=200 if fetch_performed else None,
            response_bytes=None,
            fingerprint=fingerprint,
            ingest_notes=["filing facts stored; companyfacts JSON body not stored"],
        )
        links: list[tuple[str, AnnualCapexFact]] = []
        for fact in (newer, older):
            published_at = datetime(
                fact.filed_at.year,
                fact.filed_at.month,
                fact.filed_at.day,
                tzinfo=UTC,
            )
            content_hash = _content_hash(
                rights.source_id,
                f"{fact.entity_name} {fact.form} {fact.period_end.isoformat()}",
                fact.filing_url,
                published_at,
            )
            update_id, _inserted = _insert_sourced_update(
                conn,
                rights=rights,
                title=f"{fact.entity_name} {fact.form} property, plant and equipment",
                canonical_url=fact.filing_url,
                published_at=published_at,
                retrieved_at=retrieved_at,
                retrieval_id=retrieval_id,
                content_hash=content_hash,
            )
            links.append((update_id, fact))
        assessment_id = str(uuid4())
        conn.execute(
            """
            insert into research.theme_assessments (
              assessment_id, theme_key, real_economy_activity, earnings,
              market_prices, media_attention, publication_allowed, record_class
            ) values (%s::uuid, 'ai_infrastructure_investment', %s, %s, %s, %s, false, %s)
            """,
            (
                assessment_id,
                real_economy,
                "Earnings and cash flow for this theme are not established by "
                "company-wide capital expenditure.",
                "Market prices are not established by this filing.",
                "Media attention is not established by this filing.",
                record_class,
            ),
        )
        for update_id, fact in links:
            conn.execute(
                """
                insert into research.theme_dimension_evidence (
                  assessment_id, dimension, status, measure_kind, explanation, update_id,
                  amount, unit, period_start, period_end, reporting_entity, filed_at,
                  relationship
                ) values (
                  %s::uuid, 'infrastructure_investment', 'available',
                  'actual_capital_expenditure', %s, %s::uuid,
                  %s, %s, %s, %s, %s, %s, 'supports'
                )
                """,
                (
                    assessment_id,
                    "Company-wide actual capital expenditure. " + THEME_DOES_NOT_ESTABLISH,
                    update_id,
                    fact.amount,
                    fact.unit,
                    fact.period_start,
                    fact.period_end,
                    fact.entity_name,
                    fact.filed_at,
                ),
            )
        for dimension, explanation in _NOT_YET:
            conn.execute(
                """
                insert into research.theme_dimension_evidence (
                  assessment_id, dimension, status, measure_kind, explanation
                ) values (%s::uuid, %s, 'not_yet_monitored', 'none', %s)
                """,
                (assessment_id, dimension, explanation),
            )
        _check(conn)
    return RegistrationResult("recorded", assessment_id)


def register_synthetic_supersession(conn: psycopg.Connection) -> RegistrationResult:
    """Prove a later synthetic assessment leaves the prior row in place."""
    prior = str(uuid4())
    successor = str(uuid4())
    texts = (
        "Synthetic assessment of company-wide capital expenditure only.",
        "Earnings are not established by this synthetic row.",
        "Market prices are not established by this synthetic row.",
        "Media attention is not established by this synthetic row.",
    )
    with conn.transaction():
        conn.execute(
            """
            insert into research.theme_assessments (
              assessment_id, theme_key, real_economy_activity, earnings,
              market_prices, media_attention, record_class
            ) values (%s::uuid, 'ai_infrastructure_investment', %s, %s, %s, %s, 'synthetic_fixture')
            """,
            (prior, *texts),
        )
        conn.execute(
            """
            insert into research.theme_assessments (
              assessment_id, theme_key, supersedes_assessment_id, real_economy_activity,
              earnings, market_prices, media_attention, record_class
            ) values (
              %s::uuid, 'ai_infrastructure_investment', %s::uuid, %s, %s, %s, %s,
              'synthetic_fixture'
            )
            """,
            (successor, prior, *texts),
        )
    kept = conn.execute(
        """
        select count(*) from research.theme_assessments
        where assessment_id in (%s::uuid, %s::uuid)
        """,
        (prior, successor),
    ).fetchone()
    if kept is None or kept[0] != 2:
        raise RegistrationBlocked("supersession did not keep the prior assessment")
    return RegistrationResult("recorded", prior)


def _publication_summary(source_id: str, title: str) -> str:
    labels = {
        "federal_reserve_monetary_press": "The Federal Reserve Board",
        "ecb_monetary_press": "The European Central Bank",
    }
    name = labels[source_id]
    summary = f"{name} published this document: {title}."
    if len(summary) > 500 or "policy changed" in summary.lower():
        summary = f"{name} published this document."
    if "policy changed" in summary.lower():
        raise RegistrationBlocked("summary would say that policy changed")
    return summary


def _real_economy_text(newer: AnnualCapexFact, older: AnnualCapexFact) -> str:
    text = (
        f"{newer.entity_name} reported company-wide actual capital expenditure of "
        f"{newer.amount} {newer.unit} for the year {newer.period_start.isoformat()} to "
        f"{newer.period_end.isoformat()}, and {older.amount} {older.unit} for the year "
        f"{older.period_start.isoformat()} to {older.period_end.isoformat()}. "
        f"These amounts are company-wide actual capital expenditure. {THEME_DOES_NOT_ESTABLISH}"
    )
    if len(text) > 800:
        raise RegistrationBlocked("theme text exceeds the summary cap")
    return text


def _theme_periods_stored(
    conn: psycopg.Connection,
    newer: AnnualCapexFact,
    older: AnnualCapexFact,
    record_class: RecordClass,
) -> bool:
    row = conn.execute(
        """
        select count(distinct d.period_end)
        from research.theme_dimension_evidence d
        join research.theme_assessments a on a.assessment_id = d.assessment_id
        where a.record_class = %s
          and a.theme_key = 'ai_infrastructure_investment'
          and d.dimension = 'infrastructure_investment'
          and d.period_end in (%s, %s)
        """,
        (record_class, newer.period_end, older.period_end),
    ).fetchone()
    return row is not None and row[0] == 2


def _defer(conn: psycopg.Connection) -> None:
    conn.execute("set constraints all deferred")


def _check(conn: psycopg.Connection) -> None:
    conn.execute("set constraints all immediate")


def _event_id(conn: psycopg.Connection, event_key: str) -> str:
    row = conn.execute(
        "select event_id::text from research.macro_events where event_key = %s",
        (event_key,),
    ).fetchone()
    if row is None:
        raise RegistrationBlocked(f"event {event_key} was not stored")
    return str(row[0])


def _upsert_event(conn: psycopg.Connection, **values: object) -> bool:
    row = conn.execute(
        """
        insert into research.macro_events (
          event_key, category, epistemic_class, claim_scope, summary, country,
          event_on, event_dates_stated, indicator_source_ids, channel_note,
          surface_on_today, surface_reason, surfaced_at, record_class,
          monitoring, publication_allowed, investment_implication
        ) values (
          %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'manual', false, %s
        )
        on conflict (event_key) do nothing
        returning event_id
        """,
        (
            values["event_key"],
            values["category"],
            values["epistemic_class"],
            values["claim_scope"],
            values["summary"],
            values["country"],
            values["event_on"],
            values["event_dates_stated"],
            values["indicator_source_ids"],
            values["channel_note"],
            values["surface_on_today"],
            values["surface_reason"],
            values["surfaced_at"],
            values["record_class"],
            values["investment_implication"],
        ),
    ).fetchone()
    return row is not None


def _link_evidence(
    conn: psycopg.Connection,
    *,
    event_id: str,
    update_id: str,
    role: str,
    cluster_key: str,
) -> None:
    conn.execute(
        """
        insert into research.macro_event_evidence (event_id, update_id, role, cluster_key)
        values (%s::uuid, %s::uuid, %s, %s)
        on conflict (event_id, update_id) do nothing
        """,
        (event_id, update_id, role, cluster_key),
    )


def _insert_retrieval(
    conn: psycopg.Connection,
    *,
    rights: SourceRightsRecord,
    retrieved_at: datetime,
    collection_mode: str,
    endpoint_host: str,
    request_series_ids: list[str],
    http_status: int | None,
    response_bytes: int | None,
    fingerprint: str,
    ingest_notes: list[str],
) -> str:
    row = conn.execute(
        """
        insert into research.source_retrievals (
          source_id, dataset_id, rights_record_id, provider_id,
          adapter_id, adapter_version, retrieved_at, collection_mode,
          endpoint_host, request_series_ids, attempt_count, http_status,
          response_byte_count, rights_decision_snapshot, ingest_notes,
          response_fingerprint
        ) values (
          %s, %s, %s, %s, 'manual_macro', '1.0.0', %s, %s, %s, %s, 1, %s, %s,
          %s::jsonb, %s, %s
        )
        returning retrieval_id::text
        """,
        (
            rights.source_id,
            rights.dataset_id,
            rights.source_id,
            rights.source_id,
            retrieved_at,
            collection_mode,
            endpoint_host,
            request_series_ids,
            http_status,
            response_bytes,
            json.dumps({"source_id": rights.source_id, "raw_data_retention": "permitted"}),
            ingest_notes,
            fingerprint,
        ),
    ).fetchone()
    if row is None:
        raise RegistrationBlocked("retrieval was not stored")
    return str(row[0])


def _insert_sourced_update(
    conn: psycopg.Connection,
    *,
    rights: SourceRightsRecord,
    title: str,
    canonical_url: str,
    published_at: datetime,
    retrieved_at: datetime,
    retrieval_id: str,
    content_hash: str,
) -> tuple[str, bool]:
    existing = conn.execute(
        """
        select update_id::text from research.sourced_updates
        where source_id = %s and content_hash = %s
        """,
        (rights.source_id, content_hash),
    ).fetchone()
    if existing is not None:
        return str(existing[0]), False
    update = conn.execute(
        """
        insert into research.sourced_updates (
          source_id, title, canonical_url, published_at, retrieved_at,
          retrieval_id, content_hash, status
        ) values (%s, %s, %s, %s, %s, %s::uuid, %s, 'sourced')
        returning update_id::text
        """,
        (
            rights.source_id,
            title,
            canonical_url,
            published_at,
            retrieved_at,
            retrieval_id,
            content_hash,
        ),
    ).fetchone()
    if update is None:
        raise RegistrationBlocked("sourced update was not stored")
    return str(update[0]), True


def _upsert_sourced_update(
    conn: psycopg.Connection,
    *,
    rights: SourceRightsRecord,
    title: str,
    canonical_url: str,
    published_at: datetime,
    retrieved_at: datetime,
    content_hash: str,
    collection_mode: str,
    endpoint_host: str,
    request_series_ids: list[str],
    http_status: int | None,
    response_bytes: int | None,
    fingerprint: str,
    ingest_notes: list[str],
) -> tuple[str, bool]:
    existing = conn.execute(
        """
        select update_id::text from research.sourced_updates
        where source_id = %s and content_hash = %s
        """,
        (rights.source_id, content_hash),
    ).fetchone()
    if existing is not None:
        return str(existing[0]), False
    retrieval = conn.execute(
        """
        insert into research.source_retrievals (
          source_id, dataset_id, rights_record_id, provider_id,
          adapter_id, adapter_version, retrieved_at, collection_mode,
          endpoint_host, request_series_ids, attempt_count, http_status,
          response_byte_count, rights_decision_snapshot, ingest_notes,
          response_fingerprint
        ) values (
          %s, %s, %s, %s, 'manual_macro', '1.0.0', %s, %s, %s, %s, 1, %s, %s,
          %s::jsonb, %s, %s
        )
        returning retrieval_id::text
        """,
        (
            rights.source_id,
            rights.dataset_id,
            rights.source_id,
            rights.source_id,
            retrieved_at,
            collection_mode,
            endpoint_host,
            request_series_ids,
            http_status,
            response_bytes,
            json.dumps({"source_id": rights.source_id, "raw_data_retention": "permitted"}),
            ingest_notes,
            fingerprint,
        ),
    ).fetchone()
    if retrieval is None:
        raise RegistrationBlocked("retrieval was not stored")
    update = conn.execute(
        """
        insert into research.sourced_updates (
          source_id, title, canonical_url, published_at, retrieved_at,
          retrieval_id, content_hash, status
        ) values (%s, %s, %s, %s, %s, %s::uuid, %s, 'sourced')
        returning update_id::text
        """,
        (
            rights.source_id,
            title,
            canonical_url,
            published_at,
            retrieved_at,
            retrieval[0],
            content_hash,
        ),
    ).fetchone()
    if update is None:
        raise RegistrationBlocked("sourced update was not stored")
    return str(update[0]), True


def _content_hash(
    source_id: str,
    title: str,
    canonical_url: str,
    published_at: datetime | None,
) -> str:
    payload = {
        "source_id": source_id,
        "title": title,
        "canonical_url": canonical_url,
        "published_at": published_at.isoformat() if published_at is not None else None,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _uk_date(value: date) -> str:
    return f"{value.day} {value.strftime('%B')} {value.year}"
