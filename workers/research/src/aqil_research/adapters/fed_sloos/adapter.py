"""Federal Reserve SLOOS adapter for SUBLPDCILS_N.Q (fixture or live JSON bundle)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from aqil_research.adapters.fed_sloos.parse import parse_sloos_payload
from aqil_research.adapters.protocol import (
    ProviderFailureCode,
    ProviderFetchError,
    ProviderFetchResult,
    ProviderIdentity,
)

ADAPTER_ID = "fed_sloos_sublpdcils_n_q"
ADAPTER_VERSION = "1.0.0"


@dataclass(frozen=True, slots=True)
class FedSloosAdapterConfig:
    live: bool = False
    fixture_path: Path | None = None


@dataclass
class FedSloosAdapter:
    config: FedSloosAdapterConfig
    retrieved_at: datetime | None = None

    @property
    def identity(self) -> ProviderIdentity:
        from aqil_research.adapters.fed_sloos.parse import DATASET_ID, SOURCE_ID

        return ProviderIdentity(
            adapter_id=ADAPTER_ID,
            adapter_version=ADAPTER_VERSION,
            source_id=SOURCE_ID,
            dataset_id=DATASET_ID,
        )

    def fetch(self) -> ProviderFetchResult:
        retrieved = self.retrieved_at or datetime.now(tz=UTC)
        collection_vintage = retrieved.date()
        payload: dict[str, Any] | None = None

        if not self.config.live:
            if self.config.fixture_path is None:
                return ProviderFetchResult(
                    observations=(),
                    errors=(
                        ProviderFetchError(
                            code=ProviderFailureCode.FETCH_FAILED,
                            message="offline SLOOS adapter requires fixture_path",
                        ),
                    ),
                )
            try:
                payload = json.loads(self.config.fixture_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                return ProviderFetchResult(
                    observations=(),
                    errors=(
                        ProviderFetchError(
                            code=ProviderFailureCode.PARSE_FAILED,
                            message=str(exc),
                        ),
                    ),
                )
        else:
            from aqil_research.adapters.fed_sloos.client import fetch_sloos_bundle

            try:
                payload = fetch_sloos_bundle()
            except Exception as exc:  # noqa: BLE001 — surfaced as provider error
                return ProviderFetchResult(
                    observations=(),
                    errors=(
                        ProviderFetchError(
                            code=ProviderFailureCode.FETCH_FAILED,
                            message=str(exc),
                        ),
                    ),
                )

        try:
            parsed = parse_sloos_payload(
                payload or {},
                adapter_version=f"{ADAPTER_ID}:{ADAPTER_VERSION}",
                retrieved_at=retrieved,
                collection_vintage_date=collection_vintage,
            )
        except ValueError as exc:
            return ProviderFetchResult(
                observations=(),
                errors=(
                    ProviderFetchError(
                        code=ProviderFailureCode.PARSE_FAILED,
                        message=str(exc),
                    ),
                ),
            )

        return ProviderFetchResult(observations=parsed.observations)
