"""BLS total nonfarm payrolls adapter for CES0000000001.

The current CE file is latest_revised with availability_precision unknown.
A preliminary footnote on a printed number stays an observed current value.
It is not an earlier vintage.

None of Sahm, SLOOS, Census advance orders, MACRO_CONDITIONS_PANEL, or
PERIOD_LEVEL_CHANGE consume dataset id bls.ce.CES0000000001. Sahm and
PERIOD_LEVEL_CHANGE require bls.ln.LNS14000000. SLOOS requires
fed.sloos.SUBLPDCILS_N.Q. Census advance orders requires census.m3.adv.MDM.NO.
MACRO_CONDITIONS_PANEL requires those three dataset ids.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from aqil_research.adapters.bls_payrolls.client import (
    PayrollFetchDiagnostics,
    PayrollFlatFiles,
)
from aqil_research.adapters.bls_payrolls.constants import (
    ADAPTER_ID,
    ADAPTER_VERSION,
    DATA_URL,
    DATASET_ID,
    FIXTURE_DATA,
    FIXTURE_DATATYPE,
    FIXTURE_SEASONAL,
    FIXTURE_SERIES,
    SOURCE_ID,
)
from aqil_research.adapters.bls_payrolls.parse import (
    PayrollBindingError,
    confirm_payroll_binding,
    extract_payroll_rows,
    observations_from_payload,
)
from aqil_research.adapters.bls_payrolls.stability import (
    StoredPayrollPoint,
    stabilise_payroll_vintages,
)
from aqil_research.adapters.protocol import (
    ProviderFailureCode,
    ProviderFetchError,
    ProviderFetchResult,
    ProviderIdentity,
)


@dataclass(frozen=True, slots=True)
class BlsPayrollsAdapterConfig:
    live: bool = False
    fixture_dir: Path | None = None


@dataclass
class BlsPayrollsAdapter:
    """Flat-file payroll adapter. Does not call the BLS Public Data API."""

    config: BlsPayrollsAdapterConfig
    retrieved_at: datetime | None = None
    prior_points: tuple[StoredPayrollPoint, ...] = ()
    omitted_periods: tuple[str, ...] = ()
    _last_diagnostics: PayrollFetchDiagnostics | None = None

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
        except (OSError, PayrollBindingError, RuntimeError) as exc:
            return _failed(str(exc))
        self._last_diagnostics = files.diagnostics
        try:
            binding = confirm_payroll_binding(
                files.series_text,
                files.datatype_text,
                files.seasonal_text,
            )
            extracted = extract_payroll_rows(files.data_text, binding)
            payload = stabilise_payroll_vintages(
                {"observations": list(extracted.rows)},
                self.prior_points,
                retrieved,
            )
            observations = observations_from_payload(
                payload,
                retrieved_at=retrieved,
                adapter_version=f"{ADAPTER_ID}:{ADAPTER_VERSION}",
            )
        except (PayrollBindingError, ValueError) as exc:
            self.omitted_periods = ()
            return _failed(str(exc))
        self.omitted_periods = extracted.omitted_periods
        return ProviderFetchResult(observations=observations)


def _fetch_live() -> PayrollFlatFiles:
    from aqil_research.adapters.bls_payrolls.client import fetch_payroll_files

    return fetch_payroll_files()


def _read_fixture(fixture_dir: Path | None) -> PayrollFlatFiles:
    if fixture_dir is None:
        raise PayrollBindingError("offline payroll adapter requires fixture_dir")
    series_text = _read(fixture_dir, FIXTURE_SERIES)
    datatype_text = _read(fixture_dir, FIXTURE_DATATYPE)
    seasonal_text = _read(fixture_dir, FIXTURE_SEASONAL)
    data_text = _read(fixture_dir, FIXTURE_DATA)
    return PayrollFlatFiles(
        series_text=series_text,
        datatype_text=datatype_text,
        seasonal_text=seasonal_text,
        data_text=data_text,
        diagnostics=PayrollFetchDiagnostics(
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
