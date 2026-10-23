"""Cited issuer documents. Persistence stays on instruments, not forward.etf_*."""

from aqil_research.etf.documents.ingest import (
    FIRST_INSERT_REQUIREMENT,
    CitedIssuerDocument,
    DocumentIngestError,
    PersistResult,
    RepositoryIngestResult,
    apply_repository_documents,
    load_repository_documents,
    persist_cited_share_class,
)

__all__ = [
    "FIRST_INSERT_REQUIREMENT",
    "CitedIssuerDocument",
    "DocumentIngestError",
    "PersistResult",
    "RepositoryIngestResult",
    "apply_repository_documents",
    "load_repository_documents",
    "persist_cited_share_class",
]
