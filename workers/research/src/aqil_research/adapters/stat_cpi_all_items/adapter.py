"""Statistics Bureau CPI adapter for one Japan all-items reference series.

The bound series is group code 0001, Japanese header 総合, English header
All items, in the three-decimal reference CSV for Japan. It is a price index
on a 2025 = 100 base, not a nominal yen amount and not a real volume. Periods
are calendar months, not fiscal years. The file is not seasonally adjusted and
is not the separate table titled 季節調整済指数.

The current CSV is the latest revised reference file. It is not a historical
vintage panel. includeHistory is not requested. An unchanged value keeps the
first observation id. A changed value is a new row. Blank months are omitted
and are not interpolated.

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

from aqil_research.adapters.protocol import (
    ProviderFailureCode,
    ProviderFetchError,
    ProviderFetchResult,
    ProviderIdentity,
)
from aqil_research.adapters.stat_cpi_all_items.client import StatCpiClientError, fetch_cpi_csv
from aqil_research.adapters.stat_cpi_all_items.constants import (
    ADAPTER_ID,
    ADAPTER_VERSION,
    DATASET_ID,
    METHOD_COMPATIBILITY_NOTE,
    PROVIDER_ID,
    SOURCE_ID,
)
from aqil_research.adapters.stat_cpi_all_items.parse import (
    StatCpiParseResult,
    parse_stat_cpi_csv,
)
from aqil_research.adapters.stat_cpi_all_items.stability import (
    StoredStatCpiPoint,
    stabilise_stat_cpi_observations,
)


def _collapsed(value: str) -> str:
    return " ".join(value.split())


if _collapsed(METHOD_COMPATIBILITY_NOTE) not in _collapsed(__doc__ or ""):
    raise RuntimeError("adapter docstring is missing the method compatibility note")


@dataclass(frozen=True, slots=True)
class StatCpiAdapterConfig:
    live: bool = False
    fixture_path: Path | None = None


@dataclass
class StatCpiAdapter:
    """Fixture or live fetch of the single bound CPI reference series."""

    config: StatCpiAdapterConfig
    retrieved_at: datetime | None = None
    prior_points: tuple[StoredStatCpiPoint, ...] = ()
    last_parse: StatCpiParseResult | None = None
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
            payload = self._load_payload()
        except (OSError, StatCpiClientError) as exc:
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
            parsed = parse_stat_cpi_csv(payload, retrieved_at=retrieved)
            observations = stabilise_stat_cpi_observations(
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
        self.last_parse = StatCpiParseResult(
            observations=observations,
            omitted_periods=parsed.omitted_periods,
            series_key=parsed.series_key,
            unit=parsed.unit,
            seasonal_adjustment=parsed.seasonal_adjustment,
            frequency=parsed.frequency,
            calendar_basis=parsed.calendar_basis,
            vintage_class=parsed.vintage_class,
        )
        return ProviderFetchResult(observations=observations)

    def _load_payload(self) -> bytes:
        if self.config.live:
            payload, status = fetch_cpi_csv()
            self.last_http_status = status
            return payload
        if self.config.fixture_path is None:
            raise StatCpiClientError("offline CPI adapter requires fixture_path")
        return self.config.fixture_path.read_bytes()
