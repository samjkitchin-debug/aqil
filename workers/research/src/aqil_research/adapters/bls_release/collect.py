"""Rights-checked collection for BLS Employment Situation publications."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from aqil_research.adapters.bls_release.adapter import (
    BlsEmpsitReleaseAdapter,
    BlsReleaseAdapterConfig,
)
from aqil_research.adapters.bls_release.constants import (
    ADAPTER_ID,
    ADAPTER_VERSION,
    DATASET_ID,
    SOURCE_ID,
)
from aqil_research.adapters.bls_release.store import SourcedUpdateStore
from aqil_research.collection.models import CollectionOutcome
from aqil_research.sources.rights import (
    RightsOperation,
    find_source_rights,
    load_source_rights,
    source_usable,
)
from aqil_research.sources.rights_gate import RightsGateError, assert_rights_for_ingest


@dataclass(frozen=True, slots=True)
class BlsReleaseCollectResult:
    outcome: CollectionOutcome
    source_id: str
    dataset_id: str
    adapter_id: str
    adapter_version: str
    collected_at: datetime
    collection_mode: str
    retrieval_id: str | None
    updates_received: int
    updates_newly_stored: int
    updates_unchanged: int
    rights_decision_summary: str
    next_recommended_action: str
    http_status: int | None = None
    response_fingerprint: str | None = None


def collect_bls_releases(
    store: SourcedUpdateStore,
    *,
    live: bool = False,
    fixture_path: Path | str | None = None,
    retrieved_at: datetime | None = None,
) -> BlsReleaseCollectResult:
    """Fetch, normalise and persist BLS Employment Situation publication items."""
    now = retrieved_at or datetime.now(tz=UTC)
    collection_mode = "live" if live else "fixture"
    rights_records = load_source_rights()
    rights = find_source_rights(rights_records, source_id=SOURCE_ID)
    if rights is None:
        return _failed(
            now,
            collection_mode,
            outcome="failed_rights",
            summary="source not in register",
            action="Add bls_employment_situation_archive to SOURCE_RIGHTS.csv",
        )

    if not source_usable(rights, RightsOperation.AUTOMATED_ACCESS):
        return _failed(
            now,
            collection_mode,
            outcome="failed_rights",
            summary="automated_access not permitted or source disabled",
            action="Enable source or obtain rights before collection",
        )

    path = Path(fixture_path) if fixture_path is not None else None
    if not live and path is None:
        return _failed(
            now,
            collection_mode,
            outcome="failed_fetch",
            summary="offline collection requires fixture_path",
            action="Pass a fixture RSS or Atom file",
        )

    adapter = BlsEmpsitReleaseAdapter(
        config=BlsReleaseAdapterConfig(live=live, fixture_path=path),
        retrieved_at=now,
    )

    try:
        assert_rights_for_ingest(rights, adapter)
    except RightsGateError as exc:
        return _failed(
            now,
            collection_mode,
            outcome="failed_rights",
            summary=str(exc),
            action="Resolve rights gate before retrying",
        )

    drafts, errors = adapter.fetch_publications()
    if errors and not drafts:
        return BlsReleaseCollectResult(
            outcome="failed_fetch",
            source_id=SOURCE_ID,
            dataset_id=DATASET_ID,
            adapter_id=ADAPTER_ID,
            adapter_version=ADAPTER_VERSION,
            collected_at=now,
            collection_mode=collection_mode,
            retrieval_id=None,
            updates_received=0,
            updates_newly_stored=0,
            updates_unchanged=0,
            rights_decision_summary="rights permitted for ingest",
            next_recommended_action="Inspect feed fixture or provider response",
            http_status=_http_status(adapter),
        )

    body = adapter._last_fetch.body if adapter._last_fetch else b""
    fingerprint = adapter.response_fingerprint(body) if body else None
    endpoint_host = "www.bls.gov" if live else None
    diag = adapter._last_fetch.diagnostics if adapter._last_fetch else None
    append = store.persist_publication_fetch(
        rights=rights,
        adapter=adapter,
        retrieved_at=now,
        collection_mode=collection_mode,
        drafts=drafts,
        response_fingerprint=fingerprint,
        endpoint_host=endpoint_host,
        http_status=diag.http_status if diag else None,
        response_bytes=diag.response_bytes if diag else None,
        ingest_notes=[error.message for error in errors],
    )

    received = len(drafts)
    if received == 0:
        outcome: CollectionOutcome = "partial"
        action = "Feed returned no publication items"
    elif append.inserted == 0 and append.unchanged > 0:
        outcome = "unchanged"
        action = "No new sourced updates stored"
    elif errors:
        outcome = "partial"
        action = "Review feed warnings; some items may be missing"
    else:
        outcome = "success"
        action = "Proceed to Today / Evidence reader or await next release"

    return BlsReleaseCollectResult(
        outcome=outcome,
        source_id=SOURCE_ID,
        dataset_id=DATASET_ID,
        adapter_id=ADAPTER_ID,
        adapter_version=ADAPTER_VERSION,
        collected_at=now,
        collection_mode=collection_mode,
        retrieval_id=append.retrieval_id,
        updates_received=received,
        updates_newly_stored=append.inserted,
        updates_unchanged=append.unchanged,
        rights_decision_summary="rights permitted for ingest",
        next_recommended_action=action,
        http_status=diag.http_status if diag else None,
        response_fingerprint=fingerprint,
    )


def _failed(
    now: datetime,
    collection_mode: str,
    *,
    outcome: CollectionOutcome,
    summary: str,
    action: str,
) -> BlsReleaseCollectResult:
    return BlsReleaseCollectResult(
        outcome=outcome,
        source_id=SOURCE_ID,
        dataset_id=DATASET_ID,
        adapter_id=ADAPTER_ID,
        adapter_version=ADAPTER_VERSION,
        collected_at=now,
        collection_mode=collection_mode,
        retrieval_id=None,
        updates_received=0,
        updates_newly_stored=0,
        updates_unchanged=0,
        rights_decision_summary=summary,
        next_recommended_action=action,
    )


def _http_status(adapter: BlsEmpsitReleaseAdapter) -> int | None:
    fetch = adapter._last_fetch
    return fetch.diagnostics.http_status if fetch is not None else None
