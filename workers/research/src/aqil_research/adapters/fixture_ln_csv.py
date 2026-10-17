"""Fixture adapter: BLS-like LN flat rows (CSV)."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path

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

ADAPTER_ID = "fixture_bls_ln_csv"
ADAPTER_VERSION = "1.0.0"
PROVIDER_ID = "bls"
SOURCE_ID = "bls_cps_unemployment_rate"
DATASET_ID = "bls.ln.LNS14000000"
RIGHTS_RECORD_ID = "bls_cps_unemployment_rate"


@dataclass(frozen=True, slots=True)
class FixtureLnCsvAdapter:
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
        rows: list[EconomicObservation] = []
        try:
            with self.fixture_path.open(newline="", encoding="utf-8") as handle:
                reader = csv.DictReader(handle)
                for line_number, row in enumerate(reader, start=2):
                    try:
                        rows.append(_row_to_observation(row))
                    except ValueError as exc:
                        return ProviderFetchResult(
                            observations=(),
                            errors=(
                                ProviderFetchError(
                                    code=ProviderFailureCode.PARSE_FAILED,
                                    message=f"line {line_number}: {exc}",
                                ),
                            ),
                        )
        except OSError as exc:
            return ProviderFetchResult(
                observations=(),
                errors=(
                    ProviderFetchError(
                        code=ProviderFailureCode.FETCH_FAILED,
                        message=str(exc),
                    ),
                ),
            )
        if not rows:
            return ProviderFetchResult(
                observations=(),
                errors=(
                    ProviderFetchError(
                        code=ProviderFailureCode.EMPTY_RESPONSE,
                        message="fixture contained no observations",
                    ),
                ),
                partial=True,
            )
        return ProviderFetchResult(observations=tuple(rows))


def _row_to_observation(row: dict[str, str]) -> EconomicObservation:
    period_start = date.fromisoformat(row["period_start"])
    vintage = date.fromisoformat(row["provider_vintage_date"])
    retrieved = datetime(
        vintage.year,
        vintage.month,
        min(vintage.day + 1, 28),
        12,
        0,
        tzinfo=UTC,
    )
    return EconomicObservation(
        observation_id=row["observation_id"],
        dataset_id=DATASET_ID,
        provider_id=PROVIDER_ID,
        source_id=SOURCE_ID,
        rights_record_id=RIGHTS_RECORD_ID,
        period_start=period_start,
        frequency=Frequency.MONTHLY,
        geography="US",
        unit="percent",
        seasonal_adjustment=SeasonalAdjustment.SEASONALLY_ADJUSTED,
        raw_value=row["raw_value"],
        quality_status=QualityStatus.OBSERVED,
        series_provenance=SeriesProvenance.PROVIDER_VINTAGE,
        provider_vintage_date=vintage,
        availability_precision=AvailabilityPrecision.DATE,
        retrieved_at=retrieved,
        first_seen_at=retrieved,
        adapter_version=f"{ADAPTER_ID}:{ADAPTER_VERSION}",
    )
