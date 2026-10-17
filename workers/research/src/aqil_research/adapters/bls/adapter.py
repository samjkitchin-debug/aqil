"""BLS LNS14000000 provider adapter."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from aqil_research.adapters.bls.client import BlsClientError, fetch_timeseries
from aqil_research.adapters.bls.parse import BlsParseResult, parse_bls_payload
from aqil_research.adapters.protocol import (
    ProviderFailureCode,
    ProviderFetchError,
    ProviderFetchResult,
    ProviderIdentity,
)

ADAPTER_ID = "bls_api_lns14000000"
ADAPTER_VERSION = "1.0.0"
SERIES_ID = "LNS14000000"


@dataclass(frozen=True, slots=True)
class BlsAdapterConfig:
    start_year: int
    end_year: int
    live: bool = False
    fixture_path: Path | None = None


@dataclass
class BlsUnemploymentAdapter:
    """Official BLS API adapter for seasonally adjusted U-3 unemployment."""

    config: BlsAdapterConfig
    retrieved_at: datetime | None = None

    @property
    def identity(self) -> ProviderIdentity:
        return ProviderIdentity(
            adapter_id=ADAPTER_ID,
            adapter_version=ADAPTER_VERSION,
            source_id="bls_cps_unemployment_rate",
            dataset_id="bls.ln.LNS14000000",
        )

    def fetch(self) -> ProviderFetchResult:
        retrieved = self.retrieved_at or datetime.now(tz=UTC)
        collection_vintage = retrieved.date()
        fixture_payload: dict[str, Any] | None = None
        if not self.config.live:
            if self.config.fixture_path is None:
                return ProviderFetchResult(
                    observations=(),
                    errors=(
                        ProviderFetchError(
                            code=ProviderFailureCode.FETCH_FAILED,
                            message="offline BLS adapter requires fixture_path",
                        ),
                    ),
                )
            try:
                fixture_payload = json.loads(self.config.fixture_path.read_text(encoding="utf-8"))
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

        try:
            api_response = fetch_timeseries(
                SERIES_ID,
                self.config.start_year,
                self.config.end_year,
                live=self.config.live,
                fixture_payload=fixture_payload,
            )
            parsed: BlsParseResult = parse_bls_payload(
                api_response.payload,
                adapter_version=f"{ADAPTER_ID}:{ADAPTER_VERSION}",
                retrieved_at=retrieved,
                collection_vintage_date=collection_vintage,
            )
        except (BlsClientError, ValueError) as exc:
            code = ProviderFailureCode.FETCH_FAILED
            if "parse" in str(exc).lower() or isinstance(exc, ValueError):
                code = ProviderFailureCode.PARSE_FAILED
            return ProviderFetchResult(
                observations=(),
                errors=(ProviderFetchError(code=code, message=str(exc)),),
            )

        errors: list[ProviderFetchError] = []
        if parsed.warnings:
            for warning in parsed.warnings:
                errors.append(
                    ProviderFetchError(
                        code=ProviderFailureCode.EMPTY_RESPONSE,
                        message=warning,
                        optional=True,
                    ),
                )
        return ProviderFetchResult(
            observations=parsed.observations,
            errors=tuple(errors),
            partial=bool(parsed.missing_months),
        )
