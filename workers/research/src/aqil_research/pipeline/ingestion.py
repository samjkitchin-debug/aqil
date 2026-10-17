"""Rights-checked observation ingestion from adapters."""

from __future__ import annotations

from dataclasses import dataclass

from aqil_research.adapters.protocol import ProviderAdapter, ProviderFetchResult
from aqil_research.sources.rights import SourceRightsRecord
from aqil_research.sources.rights_gate import RightsGateError, assert_rights_for_ingest
from aqil_research.vintages.store import (
    AppendResult,
    ObservationStore,
    VintageConflictError,
)


class IngestionBlockedError(Exception):
    """Raised when rights or operational status block collection."""


@dataclass(frozen=True, slots=True)
class IngestOutcome:
    append: AppendResult | None
    fetch: ProviderFetchResult | None
    blocked: bool
    block_reason: str | None
    conflicts: tuple[str, ...]


def ingest_from_adapter(
    store: ObservationStore,
    adapter: ProviderAdapter,
    rights: SourceRightsRecord,
    *,
    optional: bool = False,
) -> IngestOutcome:
    """Append provider rows. Empty responses never delete existing observations."""
    try:
        assert_rights_for_ingest(rights, adapter)
    except RightsGateError as exc:
        message = str(exc)
        if optional:
            return IngestOutcome(
                append=None,
                fetch=None,
                blocked=True,
                block_reason=message,
                conflicts=(),
            )
        raise IngestionBlockedError(message) from exc

    fetch_result = adapter.fetch()
    return ingest_from_fetch(store, fetch_result, rights, optional=optional)


def ingest_from_fetch(
    store: ObservationStore,
    fetch_result: ProviderFetchResult,
    rights: SourceRightsRecord,
    *,
    optional: bool = False,
) -> IngestOutcome:
    """Append a pre-fetched provider payload."""
    if fetch_result.errors and not fetch_result.observations:
        if optional:
            return IngestOutcome(
                append=None,
                fetch=fetch_result,
                blocked=False,
                block_reason=None,
                conflicts=(),
            )
        return IngestOutcome(
            append=None,
            fetch=fetch_result,
            blocked=False,
            block_reason=fetch_result.errors[0].message,
            conflicts=(),
        )

    if not fetch_result.observations:
        return IngestOutcome(
            append=AppendResult(inserted=0, unchanged=0, conflicts=0),
            fetch=fetch_result,
            blocked=False,
            block_reason=None,
            conflicts=(),
        )

    conflicts: list[str] = []
    inserted = 0
    unchanged = 0
    for observation in fetch_result.observations:
        try:
            result = store.append(observation)
            inserted += result.inserted
            unchanged += result.unchanged
        except VintageConflictError as exc:
            conflicts.append(str(exc))
    return IngestOutcome(
        append=AppendResult(inserted=inserted, unchanged=unchanged, conflicts=len(conflicts)),
        fetch=fetch_result,
        blocked=False,
        block_reason=None,
        conflicts=tuple(conflicts),
    )
