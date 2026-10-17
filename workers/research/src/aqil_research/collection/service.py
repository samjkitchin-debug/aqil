"""Rights-checked collection with idempotent persistence."""

from __future__ import annotations

from datetime import UTC, datetime

import psycopg

from aqil_research.adapters.bls.adapter import BlsAdapterConfig, BlsUnemploymentAdapter
from aqil_research.adapters.protocol import ProviderAdapter
from aqil_research.collection.fingerprint import fetch_fingerprint
from aqil_research.collection.models import CollectionResult
from aqil_research.persistence.observation_store import PostgresDatasetObservationStore
from aqil_research.persistence.retrieval import (
    find_retrieval_by_fingerprint,
    insert_source_retrieval,
)
from aqil_research.pipeline.ingestion import (
    IngestionBlockedError,
    ingest_from_adapter,
    ingest_from_fetch,
)
from aqil_research.sources.rights import (
    RightsOperation,
    SourceRightsRecord,
    find_source_rights,
    load_source_rights,
    source_usable,
)
from aqil_research.sources.rights_gate import RightsGateError, assert_rights_for_ingest
from aqil_research.vintages.store import InMemoryObservationStore, VintageConflictError

BLS_SOURCE_ID = "bls_cps_unemployment_rate"


def _rights_summary(rights: SourceRightsRecord) -> str:
    parts = [f"operational_status={rights.operational_status.value}"]
    for op in RightsOperation:
        parts.append(f"{op.value}={rights.decision_for(op).value}")
    return "; ".join(parts)


def _validate_adapter_rights(adapter: ProviderAdapter, rights: SourceRightsRecord) -> list[str]:
    warnings: list[str] = []
    identity = adapter.identity
    if identity.source_id != rights.source_id:
        warnings.append("adapter source_id does not match rights record")
    if identity.dataset_id != rights.dataset_id:
        warnings.append("adapter dataset_id does not match rights record")
    return warnings


def collect_bls_unemployment(
    *,
    store_backend: str,
    collected_at: datetime | None = None,
    live: bool = False,
    fixture_path: str | None = None,
    start_year: int | None = None,
    end_year: int | None = None,
    conn: psycopg.Connection | None = None,
) -> tuple[CollectionResult, object]:
    """Collect BLS unemployment observations. Returns (result, observation_store)."""
    now = collected_at or datetime.now(tz=UTC)
    rights_records = load_source_rights()
    rights = find_source_rights(rights_records, source_id=BLS_SOURCE_ID)
    if rights is None:
        return (
            CollectionResult(
                source_id=BLS_SOURCE_ID,
                dataset_id="bls.ln.LNS14000000",
                provider_id="bls",
                adapter_id="unknown",
                adapter_version="unknown",
                collected_at=now,
                collection_mode="fixture" if not live else "live",
                outcome="failed_rights",
                rights_record_id=BLS_SOURCE_ID,
                rights_decision_summary="source not in register",
                data_provenance="latest_revised",
                next_recommended_action="Add source to SOURCE_RIGHTS.csv",
            ),
            InMemoryObservationStore(),
        )

    if not source_usable(rights, RightsOperation.AUTOMATED_ACCESS):
        return (
            CollectionResult(
                source_id=rights.source_id,
                dataset_id=rights.dataset_id,
                provider_id="bls",
                adapter_id="bls_api_lns14000000",
                adapter_version="1.0.0",
                collected_at=now,
                collection_mode="fixture" if not live else "live",
                outcome="failed_rights",
                rights_record_id=rights.source_id,
                rights_decision_summary=_rights_summary(rights),
                data_provenance="latest_revised",
                next_recommended_action="Enable source or obtain rights before collection",
            ),
            InMemoryObservationStore(),
        )

    end_year = end_year or now.year
    start_year = start_year or (end_year - 3)
    from pathlib import Path

    config = BlsAdapterConfig(
        start_year=start_year,
        end_year=end_year,
        live=live,
        fixture_path=Path(fixture_path) if fixture_path and not live else None,
    )
    adapter = BlsUnemploymentAdapter(config=config, retrieved_at=now)
    collection_mode = "live" if live else "fixture"
    identity = adapter.identity
    warnings = _validate_adapter_rights(adapter, rights)

    try:
        assert_rights_for_ingest(rights, adapter)
    except RightsGateError as exc:
        return (
            CollectionResult(
                source_id=rights.source_id,
                dataset_id=rights.dataset_id,
                provider_id="bls",
                adapter_id=identity.adapter_id,
                adapter_version=identity.adapter_version,
                collected_at=now,
                collection_mode=collection_mode,
                outcome="failed_rights",
                rights_record_id=rights.source_id,
                rights_decision_summary=str(exc),
                data_provenance="latest_revised",
                warnings=warnings,
                next_recommended_action="Resolve rights gate before retrying",
            ),
            InMemoryObservationStore(),
        )

    if store_backend == "postgres":
        if conn is None:
            raise ValueError("postgres collection requires an open connection")
        return _collect_postgres(conn, adapter, rights, now, collection_mode, warnings)

    return _collect_memory(adapter, rights, now, collection_mode, warnings)


def _collect_memory(
    adapter: BlsUnemploymentAdapter,
    rights: SourceRightsRecord,
    now: datetime,
    collection_mode: str,
    warnings: list[str],
) -> tuple[CollectionResult, InMemoryObservationStore]:
    identity = adapter.identity
    store = InMemoryObservationStore()
    try:
        outcome = ingest_from_adapter(store, adapter, rights, optional=False)
    except IngestionBlockedError as exc:
        return (
            CollectionResult(
                source_id=rights.source_id,
                dataset_id=rights.dataset_id,
                provider_id="bls",
                adapter_id=identity.adapter_id,
                adapter_version=identity.adapter_version,
                collected_at=now,
                collection_mode=collection_mode,  # type: ignore[arg-type]
                outcome="failed_rights",
                rights_record_id=rights.source_id,
                rights_decision_summary=str(exc),
                data_provenance="latest_revised",
                warnings=warnings,
                next_recommended_action="Fix rights or adapter configuration",
            ),
            store,
        )

    return _result_from_ingest(
        outcome, adapter, rights, now, collection_mode, warnings, store, None
    )


def _collect_postgres(
    conn: psycopg.Connection,
    adapter: BlsUnemploymentAdapter,
    rights: SourceRightsRecord,
    now: datetime,
    collection_mode: str,
    warnings: list[str],
) -> tuple[CollectionResult, PostgresDatasetObservationStore]:
    identity = adapter.identity
    dataset_id = identity.dataset_id
    fetch = adapter.fetch()
    fingerprint = fetch_fingerprint(adapter, fetch)
    ingest_notes = [e.message for e in fetch.errors] if fetch.errors else []

    if fetch.errors and not fetch.observations:
        return (
            CollectionResult(
                source_id=rights.source_id,
                dataset_id=dataset_id,
                provider_id="bls",
                adapter_id=identity.adapter_id,
                adapter_version=identity.adapter_version,
                collected_at=now,
                collection_mode=collection_mode,  # type: ignore[arg-type]
                outcome="failed_fetch",
                rights_record_id=rights.source_id,
                rights_decision_summary=_rights_summary(rights),
                data_provenance="latest_revised",
                warnings=warnings,
                ingest_notes=ingest_notes,
                http_status=_http_status(adapter),
                provider_status=_provider_status(adapter),
                next_recommended_action="Inspect provider response and retry",
            ),
            PostgresDatasetObservationStore(conn, dataset_id),
        )

    if fingerprint is not None:
        existing = find_retrieval_by_fingerprint(conn, dataset_id, fingerprint)
        if existing is not None:
            store = PostgresDatasetObservationStore(conn, dataset_id)
            count = len(fetch.observations)
            return (
                CollectionResult(
                    source_id=rights.source_id,
                    dataset_id=dataset_id,
                    provider_id="bls",
                    adapter_id=identity.adapter_id,
                    adapter_version=identity.adapter_version,
                    collected_at=now,
                    collection_mode=collection_mode,  # type: ignore[arg-type]
                    outcome="unchanged",
                    retrieval_id=str(existing),
                    response_fingerprint=fingerprint,
                    observations_received=count,
                    observations_newly_stored=0,
                    observations_unchanged=count,
                    completeness="complete" if count else "empty",
                    rights_record_id=rights.source_id,
                    rights_decision_summary=_rights_summary(rights),
                    data_provenance="latest_revised",
                    warnings=warnings,
                    ingest_notes=ingest_notes,
                    next_recommended_action="No action — identical payload already recorded",
                ),
                store,
            )

    from aqil_research.persistence.ingest import _diagnostics, _endpoint_host

    endpoint_host = _endpoint_host(adapter)
    (
        series_ids,
        year_start,
        year_end,
        attempt_count,
        http_status,
        provider_status,
        response_bytes,
    ) = _diagnostics(adapter, fetch)

    retrieval_id = insert_source_retrieval(
        conn,
        rights=rights,
        adapter=adapter,
        retrieved_at=now,
        collection_mode=collection_mode,
        endpoint_host=endpoint_host,
        request_series_ids=series_ids,
        request_year_start=year_start,
        request_year_end=year_end,
        attempt_count=attempt_count,
        http_status=http_status,
        provider_status=provider_status,
        response_byte_count=response_bytes,
        ingest_notes=ingest_notes,
        response_fingerprint=fingerprint,
    )

    from aqil_research.persistence.observation_store import PostgresObservationStore

    append_store = PostgresObservationStore(conn, retrieval_id=retrieval_id)
    try:
        outcome = ingest_from_fetch(append_store, fetch, rights, optional=False)
    except VintageConflictError:
        conn.rollback()
        raise

    store = PostgresDatasetObservationStore(conn, dataset_id)
    return _result_from_ingest(
        outcome,
        adapter,
        rights,
        now,
        collection_mode,
        warnings,
        store,
        retrieval_id,
        fingerprint=fingerprint,
        http_status=http_status,
        provider_status=provider_status,
    )


def _result_from_ingest(
    outcome: object,
    adapter: BlsUnemploymentAdapter,
    rights: SourceRightsRecord,
    now: datetime,
    collection_mode: str,
    warnings: list[str],
    store: object,
    retrieval_id: object | None,
    *,
    fingerprint: str | None = None,
    http_status: int | None = None,
    provider_status: str | None = None,
) -> tuple[CollectionResult, object]:
    from aqil_research.pipeline.ingestion import IngestOutcome

    assert isinstance(outcome, IngestOutcome)
    identity = adapter.identity
    received = len(outcome.fetch.observations) if outcome.fetch else 0
    inserted = outcome.append.inserted if outcome.append else 0
    unchanged = outcome.append.unchanged if outcome.append else 0
    conflicts = len(outcome.conflicts)

    if conflicts:
        outcome_kind = "conflicts"
        next_action = "Review observation_conflicts and reconcile before research"
    elif outcome.blocked:
        outcome_kind = "failed_rights"
        next_action = outcome.block_reason or "Rights blocked collection"
    elif outcome.fetch and outcome.fetch.errors and not outcome.fetch.observations:
        outcome_kind = "failed_fetch"
        next_action = "Fix provider or fixture before retrying"
    elif received == 0:
        outcome_kind = "partial"
        next_action = "Provider returned no observations"
    elif inserted == 0 and unchanged > 0:
        outcome_kind = "unchanged"
        next_action = "No new observations stored"
    elif outcome.fetch and outcome.fetch.errors:
        outcome_kind = "partial"
        next_action = "Review warnings; some periods may be missing"
    else:
        outcome_kind = "success"
        next_action = "Proceed to research run or await next release"

    completeness = (
        "empty" if received == 0 else ("partial" if outcome_kind == "partial" else "complete")
    )

    result = CollectionResult(
        source_id=rights.source_id,
        dataset_id=identity.dataset_id,
        provider_id="bls",
        adapter_id=identity.adapter_id,
        adapter_version=identity.adapter_version,
        collected_at=now,
        collection_mode=collection_mode,  # type: ignore[arg-type]
        outcome=outcome_kind,  # type: ignore[arg-type]
        retrieval_id=str(retrieval_id) if retrieval_id else None,
        response_fingerprint=fingerprint,
        observations_received=received,
        observations_newly_stored=inserted,
        observations_unchanged=unchanged,
        conflicts_detected=conflicts,
        completeness=completeness,  # type: ignore[arg-type]
        rights_record_id=rights.source_id,
        rights_decision_summary=_rights_summary(rights),
        data_provenance="latest_revised",
        warnings=warnings,
        ingest_notes=[e.message for e in outcome.fetch.errors]
        if outcome.fetch and outcome.fetch.errors
        else [],
        http_status=http_status or _http_status(adapter),
        provider_status=provider_status or _provider_status(adapter),
        next_recommended_action=next_action,
    )
    return result, store


def _http_status(adapter: BlsUnemploymentAdapter) -> int | None:
    diag = getattr(adapter, "_last_diagnostics", None)
    return diag.http_status if diag is not None else None


def _provider_status(adapter: BlsUnemploymentAdapter) -> str | None:
    diag = getattr(adapter, "_last_diagnostics", None)
    return diag.bls_status if diag is not None else None
