"""BLS total nonfarm job-openings adapter for JTS000000000000000JOL.

The current JT file is latest_revised with availability_precision unknown.
A preliminary footnote on a printed number stays an observed current value.
It is not an earlier vintage. Only jt.data.2.JobOpenings is read, and only
this series id is kept.

None of Sahm, SLOOS, Census advance orders, MACRO_CONDITIONS_PANEL, or
PERIOD_LEVEL_CHANGE consume dataset id bls.jt.JTS000000000000000JOL. Sahm and
PERIOD_LEVEL_CHANGE require bls.ln.LNS14000000. SLOOS requires
fed.sloos.SUBLPDCILS_N.Q. Census advance orders requires census.m3.adv.MDM.NO.
MACRO_CONDITIONS_PANEL requires those three dataset ids.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from aqil_research.adapters.bls_jolts.client import JoltsFetchDiagnostics, JoltsFlatFiles
from aqil_research.adapters.bls_jolts.constants import (
    ADAPTER_ID,
    ADAPTER_VERSION,
    DATA_URL,
    DATASET_ID,
    FIXTURE_DATA,
    FIXTURE_DATAELEMENT,
    FIXTURE_INDUSTRY,
    FIXTURE_RATELEVEL,
    FIXTURE_SEASONAL,
    FIXTURE_SERIES,
    SOURCE_ID,
)
from aqil_research.adapters.bls_jolts.parse import (
    JoltsBindingError,
    confirm_jolts_binding,
    extract_jolts_rows,
    observations_from_payload,
)
from aqil_research.adapters.bls_jolts.stability import StoredJoltsPoint, stabilise_jolts_vintages
from aqil_research.adapters.protocol import (
    ProviderFailureCode,
    ProviderFetchError,
    ProviderFetchResult,
    ProviderIdentity,
)


@dataclass(frozen=True, slots=True)
class BlsJoltsAdapterConfig:
    live: bool = False
    fixture_dir: Path | None = None


@dataclass
class BlsJoltsAdapter:
    """Flat-file job-openings adapter. Does not call the BLS Public Data API."""

    config: BlsJoltsAdapterConfig
    retrieved_at: datetime | None = None
    prior_points: tuple[StoredJoltsPoint, ...] = ()
    omitted_periods: tuple[str, ...] = ()
    _last_diagnostics: JoltsFetchDiagnostics | None = None

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
            files = _fetch_live() if self.config.live else _read_fixture(self.config.fixture_dir)
        except (OSError, JoltsBindingError, RuntimeError) as exc:
            return _failed(str(exc))
        self._last_diagnostics = files.diagnostics
        try:
            binding = confirm_jolts_binding(
                files.series_text,
                files.seasonal_text,
                files.industry_text,
                files.dataelement_text,
                files.ratelevel_text,
            )
            extracted = extract_jolts_rows(files.data_text, binding)
            payload = stabilise_jolts_vintages(
                {"observations": list(extracted.rows)},
                self.prior_points,
                retrieved,
            )
            observations = observations_from_payload(
                payload,
                retrieved_at=retrieved,
                adapter_version=f"{ADAPTER_ID}:{ADAPTER_VERSION}",
            )
        except (JoltsBindingError, ValueError) as exc:
            self.omitted_periods = ()
            return _failed(str(exc))
        self.omitted_periods = extracted.omitted_periods
        return ProviderFetchResult(observations=observations)


def _fetch_live() -> JoltsFlatFiles:
    from aqil_research.adapters.bls_jolts.client import fetch_jolts_files

    return fetch_jolts_files()


def _read_fixture(fixture_dir: Path | None) -> JoltsFlatFiles:
    if fixture_dir is None:
        raise JoltsBindingError("offline job-openings adapter requires fixture_dir")
    series_text = _read(fixture_dir, FIXTURE_SERIES)
    seasonal_text = _read(fixture_dir, FIXTURE_SEASONAL)
    industry_text = _read(fixture_dir, FIXTURE_INDUSTRY)
    dataelement_text = _read(fixture_dir, FIXTURE_DATAELEMENT)
    ratelevel_text = _read(fixture_dir, FIXTURE_RATELEVEL)
    data_text = _read(fixture_dir, FIXTURE_DATA)
    return JoltsFlatFiles(
        series_text=series_text,
        seasonal_text=seasonal_text,
        industry_text=industry_text,
        dataelement_text=dataelement_text,
        ratelevel_text=ratelevel_text,
        data_text=data_text,
        diagnostics=JoltsFetchDiagnostics(
            endpoint=DATA_URL,
            attempts=0,
            http_status=None,
            bls_status="fixture",
            response_bytes=len(data_text.encode("utf-8")),
        ),
    )


def _read(directory: Path, name: str) -> str:
    return (directory / name).read_text(encoding="utf-8")


def _failed(message: str) -> ProviderFetchResult:
    return ProviderFetchResult(
        observations=(),
        errors=(
            ProviderFetchError(
                code=ProviderFailureCode.PARSE_FAILED,
                message=message,
            ),
        ),
    )
