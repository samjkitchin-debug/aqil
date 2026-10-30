"""BLS unemployment rate from the official LN flat file.

The file is one latest-revised extract. It is not a vintage panel and it is
not a real-time Sahm evaluation. The reader keeps every monthly value the
file names for LNS14000000. It does not apply the Public Data API year window.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from aqil_research.adapters.bls_ln_history.client import (
    LnClientError,
    fetch_unemployment_flat_files,
)
from aqil_research.adapters.bls_ln_history.constants import (
    ADAPTER_ID,
    ADAPTER_VERSION,
    DATASET_ID,
    SOURCE_ID,
)
from aqil_research.adapters.bls_ln_history.parse import (
    LnHistoryError,
    StoredLnPoint,
    confirm_unemployment_series,
    extract_unemployment_months,
    observations_from_months,
)
from aqil_research.adapters.protocol import (
    ProviderFailureCode,
    ProviderFetchError,
    ProviderFetchResult,
    ProviderIdentity,
)


@dataclass(frozen=True, slots=True)
class BlsLnHistoryConfig:
    live: bool = False
    series_path: Path | None = None
    data_path: Path | None = None


@dataclass
class BlsLnHistoryAdapter:
    config: BlsLnHistoryConfig
    retrieved_at: datetime | None = None
    prior_points: tuple[StoredLnPoint, ...] = ()
    omitted_periods: tuple[str, ...] = ()

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
        if retrieved.tzinfo is None:
            return _failed("retrieved_at must be timezone-aware")
        try:
            series_text, data_text = self._texts()
            binding = confirm_unemployment_series(series_text)
            extracted = extract_unemployment_months(data_text, binding)
            observations = observations_from_months(
                extracted,
                prior_points=self.prior_points,
                retrieved_at=retrieved,
            )
        except (LnClientError, LnHistoryError, OSError, ValueError) as exc:
            self.omitted_periods = ()
            code = (
                ProviderFailureCode.FETCH_FAILED
                if isinstance(exc, LnClientError | OSError)
                else ProviderFailureCode.PARSE_FAILED
            )
            return ProviderFetchResult(
                observations=(),
                errors=(ProviderFetchError(code=code, message=str(exc)),),
            )
        self.omitted_periods = extracted.omitted_periods
        return ProviderFetchResult(observations=observations)

    def _texts(self) -> tuple[str, str]:
        if self.config.live:
            files = fetch_unemployment_flat_files()
            return files.series_text, files.data_text
        if self.config.series_path is None or self.config.data_path is None:
            raise LnClientError("offline LN history adapter requires series and data paths")
        return (
            self.config.series_path.read_text(encoding="utf-8"),
            self.config.data_path.read_text(encoding="utf-8"),
        )


def _failed(message: str) -> ProviderFetchResult:
    return ProviderFetchResult(
        observations=(),
        errors=(ProviderFetchError(code=ProviderFailureCode.PARSE_FAILED, message=message),),
    )
