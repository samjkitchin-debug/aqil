"""Federal Reserve H.8 adapter for weekly bank credit (fixture or live package).

Series B1001NCBA is bank credit for all commercial banks, seasonally adjusted,
as a weekly level in millions of US dollars. SLOOS already covers lending
standards. This series is volumes. The Board file is latest-revised, not a
vintage panel. No historical vintage is invented.

None of Sahm, SLOOS, Census advance orders, MACRO_CONDITIONS_PANEL, or
PERIOD_LEVEL_CHANGE consumes fed.h8.B1001NCBA. Sahm and PERIOD_LEVEL_CHANGE
require bls.ln.LNS14000000. SLOOS requires fed.sloos.SUBLPDCILS_N.Q. Census
advance orders requires census.m3.adv.MDM.NO. MACRO_CONDITIONS_PANEL requires
those three dataset ids.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from aqil_research.adapters.fed_h8.client import PACKAGE_URL
from aqil_research.adapters.fed_h8.package import H8PackageError, series_from_h8_bytes
from aqil_research.adapters.fed_h8.parse import DATASET_ID, SOURCE_ID, parse_h8_payload
from aqil_research.adapters.fed_h8.stability import StoredH8Point, stabilise_h8_vintages
from aqil_research.adapters.protocol import (
    ProviderFailureCode,
    ProviderFetchError,
    ProviderFetchResult,
    ProviderIdentity,
)

ADAPTER_ID = "fed_h8_b1001ncba"
ADAPTER_VERSION = "1.0.0"


@dataclass(frozen=True, slots=True)
class FedH8AdapterConfig:
    live: bool = False
    fixture_path: Path | None = None


@dataclass
class FedH8Adapter:
    """Latest-revised weekly bank credit. Current methods do not consume this dataset."""

    config: FedH8AdapterConfig
    retrieved_at: datetime | None = None
    prior_points: tuple[StoredH8Point, ...] = ()
    description: str = ""
    omitted_periods: tuple[str, ...] = ()

    @property
    def identity(self) -> ProviderIdentity:
        return ProviderIdentity(
            adapter_id=ADAPTER_ID,
            adapter_version=ADAPTER_VERSION,
            source_id=SOURCE_ID,
            dataset_id=DATASET_ID,
            provider_id="federal_reserve_board",
        )

    def fetch(self) -> ProviderFetchResult:
        retrieved = self.retrieved_at or datetime.now(tz=UTC)
        collection_vintage = retrieved.date()
        try:
            payload = self._load_payload()
        except H8PackageError as exc:
            return _failure(ProviderFailureCode.PARSE_FAILED, str(exc))
        except Exception as exc:  # noqa: BLE001 — surfaced as provider error
            return _failure(ProviderFailureCode.FETCH_FAILED, str(exc))

        self.description = str(payload.get("description", ""))
        omitted = payload.get("omitted_periods")
        self.omitted_periods = (
            tuple(str(period) for period in omitted) if isinstance(omitted, list) else ()
        )
        payload = stabilise_h8_vintages(payload, self.prior_points, retrieved)
        try:
            parsed = parse_h8_payload(
                payload,
                adapter_version=f"{ADAPTER_ID}:{ADAPTER_VERSION}",
                retrieved_at=retrieved,
                collection_vintage_date=collection_vintage,
            )
        except ValueError as exc:
            return _failure(ProviderFailureCode.PARSE_FAILED, str(exc))
        self.omitted_periods = parsed.omitted_periods
        return ProviderFetchResult(observations=parsed.observations)

    def _load_payload(self) -> dict[str, object]:
        if self.config.live:
            from aqil_research.adapters.fed_h8.client import fetch_h8_bundle

            return fetch_h8_bundle()
        if self.config.fixture_path is None:
            raise FileNotFoundError("offline H.8 adapter requires fixture_path")
        try:
            body = self.config.fixture_path.read_bytes()
        except OSError as exc:
            raise FileNotFoundError(str(exc)) from exc
        payload = series_from_h8_bytes(body)
        return _with_locator(payload)


def _with_locator(payload: dict[str, object]) -> dict[str, object]:
    rows = payload.get("observations")
    if not isinstance(rows, list):
        return payload
    located = [
        {**row, "source_locator": PACKAGE_URL} if isinstance(row, dict) else row for row in rows
    ]
    return {**payload, "observations": located}


def _failure(code: ProviderFailureCode, message: str) -> ProviderFetchResult:
    return ProviderFetchResult(
        observations=(),
        errors=(ProviderFetchError(code=code, message=message),),
    )
