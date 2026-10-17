"""Fixture adapter: Aqil bundle JSON (alternate provider-native shape)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path

from aqil_research.adapters.fixture_ln_csv import (
    ADAPTER_VERSION,
    DATASET_ID,
    PROVIDER_ID,
    RIGHTS_RECORD_ID,
    SOURCE_ID,
)
from aqil_research.adapters.protocol import (
    ProviderFailureCode,
    ProviderFetchError,
    ProviderFetchResult,
    ProviderIdentity,
)
from aqil_research.contracts.observation import (
    AvailabilityPrecision,
    EconomicObservation,
    Frequency,
    QualityStatus,
    SeasonalAdjustment,
    SeriesProvenance,
)

ADAPTER_ID = "fixture_aqil_series_json"


@dataclass(frozen=True, slots=True)
class FixtureSeriesJsonAdapter:
    fixture_path: Path

    @property
    def identity(self) -> ProviderIdentity:
        return ProviderIdentity(
            adapter_id=ADAPTER_ID,
            adapter_version=ADAPTER_VERSION,
            source_id=SOURCE_ID,
            dataset_id=DATASET_ID,
        )

    def fetch(self) -> ProviderFetchResult:
        if not self.fixture_path.is_file():
            return ProviderFetchResult(
                observations=(),
                errors=(
                    ProviderFetchError(
                        code=ProviderFailureCode.FETCH_FAILED,
                        message=f"missing fixture {self.fixture_path}",
                    ),
                ),
            )
        try:
            payload = json.loads(self.fixture_path.read_text(encoding="utf-8"))
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
        observations_raw = payload.get("observations")
        if not isinstance(observations_raw, list) or not observations_raw:
            return ProviderFetchResult(
                observations=(),
                errors=(
                    ProviderFetchError(
                        code=ProviderFailureCode.EMPTY_RESPONSE,
                        message="bundle contained no observations",
                    ),
                ),
                partial=True,
            )
        rows: list[EconomicObservation] = []
        for index, item in enumerate(observations_raw, start=1):
            try:
                rows.append(_item_to_observation(item))
            except (TypeError, ValueError, KeyError) as exc:
                return ProviderFetchResult(
                    observations=(),
                    errors=(
                        ProviderFetchError(
                            code=ProviderFailureCode.PARSE_FAILED,
                            message=f"item {index}: {exc}",
                        ),
                    ),
                )
        return ProviderFetchResult(observations=tuple(rows))


def _item_to_observation(item: dict[str, object]) -> EconomicObservation:
    period_start = date.fromisoformat(str(item["period"]))
    vintage = date.fromisoformat(str(item["vintage"]))
    retrieved = datetime(
        vintage.year,
        vintage.month,
        min(vintage.day + 1, 28),
        12,
        0,
        tzinfo=UTC,
    )
    return EconomicObservation(
        observation_id=str(item["observation_id"]),
        dataset_id=DATASET_ID,
        provider_id=PROVIDER_ID,
        source_id=SOURCE_ID,
        rights_record_id=RIGHTS_RECORD_ID,
        period_start=period_start,
        frequency=Frequency.MONTHLY,
        geography="US",
        unit="percent",
        seasonal_adjustment=SeasonalAdjustment.SEASONALLY_ADJUSTED,
        raw_value=str(item["value"]),
        quality_status=QualityStatus.OBSERVED,
        series_provenance=SeriesProvenance.PROVIDER_VINTAGE,
        provider_vintage_date=vintage,
        availability_precision=AvailabilityPrecision.DATE,
        retrieved_at=retrieved,
        first_seen_at=retrieved,
        adapter_version=f"{ADAPTER_ID}:{ADAPTER_VERSION}",
    )
