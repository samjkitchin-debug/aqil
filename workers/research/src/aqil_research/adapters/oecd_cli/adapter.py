"""OECD Data Explorer adapter for one G20 composite leading indicator.

This package is only G20.M.LI.IX._Z.AA.IX._Z.H. It is not a shared SDMX
client. The response methodology label is OECD harmonised. The current CSV
is the latest revised series. It is not a historical vintage panel.
includeHistory is not requested. An unchanged value keeps the first
observation id. A changed value is a new row. Blank months are omitted and
are not interpolated.

None of Sahm, SLOOS, Census advance orders, MACRO_CONDITIONS_PANEL, or
PERIOD_LEVEL_CHANGE consume this dataset id. Sahm requires
bls.ln.LNS14000000. SLOOS requires fed.sloos.SUBLPDCILS_N.Q. Census advance
orders requires census.m3.adv.MDM.NO. MACRO_CONDITIONS_PANEL requires those
three dataset ids. PERIOD_LEVEL_CHANGE requires bls.ln.LNS14000000.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from aqil_research.adapters.oecd_cli.client import OecdCliClientError, fetch_series_csv
from aqil_research.adapters.oecd_cli.constants import (
    ADAPTER_ID,
    ADAPTER_VERSION,
    DATASET_ID,
    METHOD_COMPATIBILITY_NOTE,
    PROVIDER_ID,
    SOURCE_ID,
)
from aqil_research.adapters.oecd_cli.parse import OecdCliParseResult, parse_oecd_cli_csv
from aqil_research.adapters.oecd_cli.stability import (
    StoredOecdPoint,
    stabilise_oecd_observations,
)
from aqil_research.adapters.protocol import (
    ProviderFailureCode,
    ProviderFetchError,
    ProviderFetchResult,
    ProviderIdentity,
)


def _collapsed(value: str) -> str:
    return " ".join(value.split())


if _collapsed(METHOD_COMPATIBILITY_NOTE) not in _collapsed(__doc__ or ""):
    raise RuntimeError("adapter docstring is missing the method compatibility note")


@dataclass(frozen=True, slots=True)
class OecdCliAdapterConfig:
    live: bool = False
    fixture_path: Path | None = None


@dataclass
class OecdCliAdapter:
    """Fixture or live fetch of the single bound G20 CLI series."""

    config: OecdCliAdapterConfig
    retrieved_at: datetime | None = None
    prior_points: tuple[StoredOecdPoint, ...] = ()
    last_parse: OecdCliParseResult | None = None
    last_http_status: int | None = None

    @property
    def identity(self) -> ProviderIdentity:
        return ProviderIdentity(
            adapter_id=ADAPTER_ID,
            adapter_version=ADAPTER_VERSION,
            source_id=SOURCE_ID,
            dataset_id=DATASET_ID,
            provider_id=PROVIDER_ID,
        )

    def fetch(self) -> ProviderFetchResult:
        retrieved = self.retrieved_at or datetime.now(tz=UTC)
        self.last_http_status = None
        try:
            text = self._load_text()
        except (OSError, OecdCliClientError) as exc:
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
            parsed = parse_oecd_cli_csv(text, retrieved_at=retrieved)
            observations = stabilise_oecd_observations(
                parsed.observations,
                self.prior_points,
                retrieved,
            )
        except ValueError as exc:
            self.last_parse = None
            return ProviderFetchResult(
                observations=(),
                errors=(
                    ProviderFetchError(
                        code=ProviderFailureCode.PARSE_FAILED,
                        message=str(exc),
                    ),
                ),
            )
        self.last_parse = OecdCliParseResult(
            observations=observations,
            omitted_periods=parsed.omitted_periods,
            series_key=parsed.series_key,
            compiler_sentence=parsed.compiler_sentence,
            unit=parsed.unit,
            seasonal_adjustment=parsed.seasonal_adjustment,
            frequency=parsed.frequency,
            vintage_class=parsed.vintage_class,
        )
        return ProviderFetchResult(observations=observations)

    def _load_text(self) -> str:
        if self.config.live:
            text, status = fetch_series_csv()
            self.last_http_status = status
            return text
        if self.config.fixture_path is None:
            raise OecdCliClientError("offline OECD adapter requires fixture_path")
        return self.config.fixture_path.read_text(encoding="utf-8")
