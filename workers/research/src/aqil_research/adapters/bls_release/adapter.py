"""BLS Employment Situation publication feed adapter."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from aqil_research.adapters.bls_release.client import (
    BlsReleaseClientError,
    BlsReleaseFetchResult,
    fetch_empsit_publication_feed,
)
from aqil_research.adapters.bls_release.constants import (
    ADAPTER_ID,
    ADAPTER_VERSION,
    BLS_EMPSIT_RSS_URL,
    DATASET_ID,
    SOURCE_ID,
)
from aqil_research.adapters.bls_release.normalize import (
    SourcedUpdateDraft,
    drafts_from_items,
    feed_response_fingerprint,
)
from aqil_research.adapters.bls_release.parse import parse_publication_feed
from aqil_research.adapters.protocol import (
    ProviderFailureCode,
    ProviderFetchError,
    ProviderFetchResult,
    ProviderIdentity,
)


@dataclass(frozen=True, slots=True)
class BlsReleaseAdapterConfig:
    live: bool = False
    fixture_path: Path | None = None


@dataclass
class BlsEmpsitReleaseAdapter:
    """Official BLS Employment Situation RSS / archive adapter."""

    config: BlsReleaseAdapterConfig
    retrieved_at: datetime | None = None
    _last_fetch: BlsReleaseFetchResult | None = None

    @property
    def identity(self) -> ProviderIdentity:
        return ProviderIdentity(
            adapter_id=ADAPTER_ID,
            adapter_version=ADAPTER_VERSION,
            source_id=SOURCE_ID,
            dataset_id=DATASET_ID,
        )

    def fetch(self) -> ProviderFetchResult:
        """ProviderAdapter compatibility — publications are not economic observations."""
        return ProviderFetchResult(observations=(), errors=())

    def fetch_publications(
        self,
    ) -> tuple[tuple[SourcedUpdateDraft, ...], tuple[ProviderFetchError, ...]]:
        retrieved = self.retrieved_at or datetime.now(tz=UTC)
        try:
            fetch_result = fetch_empsit_publication_feed(
                live=self.config.live,
                fixture_path=self.config.fixture_path,
            )
            self._last_fetch = fetch_result
            items = parse_publication_feed(fetch_result.body, base_url=BLS_EMPSIT_RSS_URL)
            drafts = drafts_from_items(items)
            for draft in drafts:
                if draft.published_at is not None and draft.published_at > retrieved:
                    raise ValueError("published_at cannot be after retrieved_at")
            return drafts, ()
        except (BlsReleaseClientError, ValueError) as exc:
            code = ProviderFailureCode.PARSE_FAILED
            if isinstance(exc, BlsReleaseClientError):
                code = ProviderFailureCode.FETCH_FAILED
            return (), (ProviderFetchError(code=code, message=str(exc)),)

    def response_fingerprint(self, body: bytes) -> str:
        identity = self.identity
        return feed_response_fingerprint(
            body,
            adapter_id=identity.adapter_id,
            adapter_version=identity.adapter_version,
        )
