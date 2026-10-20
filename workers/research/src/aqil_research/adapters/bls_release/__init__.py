"""BLS Employment Situation publication feed adapter."""

from aqil_research.adapters.bls_release.collect import BlsReleaseCollectResult, collect_bls_releases
from aqil_research.adapters.bls_release.constants import SOURCE_ID
from aqil_research.adapters.bls_release.store import (
    InMemorySourcedUpdateStore,
    PostgresSourcedUpdateStore,
    SourcedUpdateStore,
)

__all__ = [
    "BlsReleaseCollectResult",
    "InMemorySourcedUpdateStore",
    "PostgresSourcedUpdateStore",
    "SOURCE_ID",
    "SourcedUpdateStore",
    "collect_bls_releases",
]
