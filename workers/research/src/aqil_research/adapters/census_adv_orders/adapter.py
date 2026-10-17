"""Census advance durable goods new orders adapter (MDM / NO)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path

from aqil_research.adapters.census_adv_orders.parse import parse_census_adv_payload
from aqil_research.contracts.observation import EconomicObservation
from aqil_research.adapters.protocol import (
    ProviderFailureCode,
    ProviderFetchError,
    ProviderFetchResult,
    ProviderIdentity,
)

ADAPTER_ID = "census_m3_adv_mdm_no"
ADAPTER_VERSION = "1.0.0"


@dataclass(frozen=True, slots=True)
class CensusAdvOrdersAdapterConfig:
    live: bool = False
    fixture_path: Path | None = None


@dataclass
class CensusAdvOrdersAdapter:
    config: CensusAdvOrdersAdapterConfig
    retrieved_at: datetime | None = None

    @property
    def identity(self) -> ProviderIdentity:
        from aqil_research.adapters.census_adv_orders.parse import DATASET_ID, SOURCE_ID

        return ProviderIdentity(
            adapter_id=ADAPTER_ID,
            adapter_version=ADAPTER_VERSION,
            source_id=SOURCE_ID,
            dataset_id=DATASET_ID,
        )

    def fetch(self) -> ProviderFetchResult:
        retrieved = self.retrieved_at or datetime.now(tz=UTC)
        collection_vintage = retrieved.date()

        if not self.config.live:
            if self.config.fixture_path is None:
                return ProviderFetchResult(
                    observations=(),
                    errors=(
                        ProviderFetchError(
                            code=ProviderFailureCode.FETCH_FAILED,
                            message="offline Census adapter requires fixture_path",
                        ),
                    ),
                )
            try:
                raw = json.loads(self.config.fixture_path.read_text(encoding="utf-8"))
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
            from aqil_research.adapters.census_adv_orders.client import fetch_mdm_no_timeseries

            try:
                raw = fetch_mdm_no_timeseries()
            except Exception as exc:  # noqa: BLE001
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
            observations = _parse_fixture_or_live(
                raw,
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
        return ProviderFetchResult(observations=observations)


def _parse_fixture_or_live(
    raw: object,
    *,
    adapter_version: str,
    retrieved_at: datetime,
    collection_vintage_date: date,
) -> tuple[EconomicObservation, ...]:
    if isinstance(raw, dict) and isinstance(raw.get("vintages"), list):
        rows: list[EconomicObservation] = []
        for entry in raw["vintages"]:
            if not isinstance(entry, dict):
                raise ValueError("vintage entry must be an object")
            vintage_date = date.fromisoformat(str(entry["provider_vintage_date"]))
            model_raw = entry.get("earliest_model_available_at")
            earliest = datetime.fromisoformat(str(model_raw)) if model_raw else None
            parsed = parse_census_adv_payload(
                entry.get("data", entry),
                adapter_version=adapter_version,
                retrieved_at=retrieved_at,
                collection_vintage_date=collection_vintage_date,
                vintage_date=vintage_date,
                earliest_model_available_at=earliest,
            )
            rows.extend(parsed.observations)
        return tuple(rows)

    vintage_date = None
    earliest = None
    payload = raw
    if isinstance(raw, dict):
        payload = raw.get("data", raw)
        vintage_raw = raw.get("provider_vintage_date")
        if vintage_raw:
            vintage_date = date.fromisoformat(str(vintage_raw))
        model_raw = raw.get("earliest_model_available_at")
        if model_raw:
            earliest = datetime.fromisoformat(str(model_raw))

    parsed = parse_census_adv_payload(
        payload,
        adapter_version=adapter_version,
        retrieved_at=retrieved_at,
        collection_vintage_date=collection_vintage_date,
        vintage_date=vintage_date,
        earliest_model_available_at=earliest,
    )
    return parsed.observations
