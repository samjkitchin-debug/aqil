"""Board H.15 monthly levels from the selected-interest-rates package.

The downloaded file is one latest-revised package, not a vintage panel.
These series are levels. They are not a near-term forward spread.

None of Sahm, SLOOS, Census advance orders, MACRO_CONDITIONS_PANEL, or
PERIOD_LEVEL_CHANGE consume these dataset ids. Sahm and PERIOD_LEVEL_CHANGE
require bls.ln.LNS14000000. SLOOS requires fed.sloos.SUBLPDCILS_N.Q. Census
advance orders requires census.m3.adv.MDM.NO. MACRO_CONDITIONS_PANEL requires
those three dataset ids.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from aqil_research.adapters.fed_h15.client import H15ClientError, download_h15_package
from aqil_research.adapters.fed_h15.package import H15PackageError, read_h15_series
from aqil_research.adapters.fed_h15.parse import parse_h15_payload
from aqil_research.adapters.fed_h15.series import PACKAGE_URL, H15Series
from aqil_research.adapters.fed_h15.stability import StoredH15Point, stabilise_h15_vintages
from aqil_research.adapters.protocol import (
    ProviderFailureCode,
    ProviderFetchError,
    ProviderFetchResult,
    ProviderIdentity,
)

ADAPTER_VERSION = "1.0.0"


@dataclass(frozen=True, slots=True)
class FedH15AdapterConfig:
    live: bool = False
    fixture_path: Path | None = None


@dataclass
class FedH15Adapter:
    series: H15Series
    config: FedH15AdapterConfig
    retrieved_at: datetime | None = None
    prior_points: tuple[StoredH15Point, ...] = ()

    @property
    def identity(self) -> ProviderIdentity:
        return ProviderIdentity(
            adapter_id=self.series.adapter_id,
            adapter_version=ADAPTER_VERSION,
            source_id=self.series.source_id,
            dataset_id=self.series.dataset_id,
            provider_id="federal_reserve_board",
        )

    def fetch(self) -> ProviderFetchResult:
        retrieved = self.retrieved_at or datetime.now(tz=UTC)
        try:
            package = self._package_bytes()
            extract = read_h15_series(package, self.series)
        except (H15ClientError, H15PackageError, OSError, ValueError) as exc:
            code = (
                ProviderFailureCode.FETCH_FAILED
                if isinstance(exc, H15ClientError)
                else ProviderFailureCode.PARSE_FAILED
            )
            return ProviderFetchResult(
                observations=(),
                errors=(ProviderFetchError(code=code, message=str(exc)),),
            )

        payload = stabilise_h15_vintages(
            {
                "series_name": self.series.series_name,
                "observations": [
                    {
                        "period": row.period_start.isoformat(),
                        "period_end": row.period_end.isoformat(),
                        "value": row.value,
                        "source_locator": PACKAGE_URL,
                    }
                    for row in extract.rows
                ],
            },
            self.series,
            self.prior_points,
            retrieved,
        )
        try:
            parsed = parse_h15_payload(
                payload,
                series=self.series,
                adapter_version=f"{self.series.adapter_id}:{ADAPTER_VERSION}",
                retrieved_at=retrieved,
                collection_vintage_date=retrieved.date(),
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

    def _package_bytes(self) -> bytes:
        if self.config.live:
            return download_h15_package().content
        if self.config.fixture_path is None:
            raise H15ClientError("offline H.15 adapter requires fixture_path")
        try:
            return self.config.fixture_path.read_bytes()
        except OSError as exc:
            raise H15ClientError(str(exc)) from exc
