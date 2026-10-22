"""BLS CPI-U all-items adapter for the CU flat file.

Dataset bls.cu.CUSR0000SA0 is series CUSR0000SA0 from cu.data.1.AllItems,
confirmed by cu.series. It is the current seasonally adjusted index, not a
historical vintage file, and it is not the CPI Atom feed (source
bls_cpi_archive).

No current method consumes this dataset id. Sahm requires
bls.ln.LNS14000000. SLOOS requires fed.sloos.SUBLPDCILS_N.Q. Census advance
orders requires census.m3.adv.MDM.NO. MACRO_CONDITIONS_PANEL requires those
three dataset ids. PERIOD_LEVEL_CHANGE requires bls.ln.LNS14000000.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from aqil_research.adapters.bls_cpi_series.client import CpiClientError, fetch_cpi_flat_files
from aqil_research.adapters.bls_cpi_series.parse import (
    DATASET_ID,
    SOURCE_ID,
    CpiParseResult,
    OmittedCpiPeriod,
    confirm_cpi_series,
    parse_cpi_data,
)
from aqil_research.adapters.bls_cpi_series.stability import StoredCpiPoint
from aqil_research.adapters.protocol import (
    ProviderFailureCode,
    ProviderFetchError,
    ProviderFetchResult,
    ProviderIdentity,
)

ADAPTER_ID = "bls_cpi_u_cusr0000sa0"
ADAPTER_VERSION = "1.0.0"


@dataclass(frozen=True, slots=True)
class BlsCpiSeriesAdapterConfig:
    live: bool = False
    fixture_path: Path | None = None
    series_fixture_path: Path | None = None


@dataclass
class BlsCpiSeriesAdapter:
    """Read the confirmed CPI-U series into memory. This adapter does not persist rows."""

    config: BlsCpiSeriesAdapterConfig
    retrieved_at: datetime | None = None
    prior_points: tuple[StoredCpiPoint, ...] = ()
    omitted_periods: tuple[OmittedCpiPeriod, ...] = ()

    @property
    def identity(self) -> ProviderIdentity:
        return ProviderIdentity(
            adapter_id=ADAPTER_ID,
            adapter_version=ADAPTER_VERSION,
            source_id=SOURCE_ID,
            dataset_id=DATASET_ID,
            provider_id="bls",
        )

    def fetch(self) -> ProviderFetchResult:
        retrieved = self.retrieved_at or datetime.now(tz=UTC)
        self.omitted_periods = ()
        try:
            series_text, data_text = self._load_texts()
            binding = confirm_cpi_series(series_text)
            parsed: CpiParseResult = parse_cpi_data(
                data_text,
                binding=binding,
                adapter_version=f"{ADAPTER_ID}:{ADAPTER_VERSION}",
                retrieved_at=retrieved,
                prior_points=self.prior_points,
            )
        except CpiClientError as exc:
            return ProviderFetchResult(
                observations=(),
                errors=(
                    ProviderFetchError(
                        code=ProviderFailureCode.FETCH_FAILED,
                        message=str(exc),
                    ),
                ),
            )
        except (OSError, ValueError) as exc:
            return ProviderFetchResult(
                observations=(),
                errors=(
                    ProviderFetchError(
                        code=ProviderFailureCode.PARSE_FAILED,
                        message=str(exc),
                    ),
                ),
            )
        self.omitted_periods = parsed.omitted_periods
        return ProviderFetchResult(observations=parsed.observations, partial=False)

    def _load_texts(self) -> tuple[str, str]:
        if self.config.live:
            files = fetch_cpi_flat_files()
            return files.series_text, files.data_text
        if self.config.fixture_path is None or self.config.series_fixture_path is None:
            raise ValueError("offline CPI adapter requires the series and data excerpts")
        series_text = self.config.series_fixture_path.read_text(encoding="utf-8")
        data_text = self.config.fixture_path.read_text(encoding="utf-8")
        return series_text, data_text
