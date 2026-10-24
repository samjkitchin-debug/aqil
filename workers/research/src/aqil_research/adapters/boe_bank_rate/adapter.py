"""Bank of England Database adapter for official Bank Rate.

The bound series is IUDBEDR, described in the file as Official Bank Rate.
Selected exchange-rate series are excluded from the Database licence and are
not requested. Provisional data (VPD) is not requested. The CSV is the
current published series. It is not a historical vintage panel. An unchanged
value keeps the first observation id. A changed value is a new row. Days
marked unavailable, and days the file does not contain, are omitted and are
not stored as zero.

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

from aqil_research.adapters.boe_bank_rate.client import (
    BoeBankRateClientError,
    fetch_series_csv,
)
from aqil_research.adapters.boe_bank_rate.constants import (
    ADAPTER_ID,
    ADAPTER_VERSION,
    DATASET_ID,
    METHOD_COMPATIBILITY_NOTE,
    PROVIDER_ID,
    SOURCE_ID,
)
from aqil_research.adapters.boe_bank_rate.parse import (
    BoeBankRateParseResult,
    parse_boe_bank_rate_csv,
)
from aqil_research.adapters.boe_bank_rate.stability import (
    StoredBoePoint,
    stabilise_boe_observations,
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
class BoeBankRateAdapterConfig:
    live: bool = False
    fixture_path: Path | None = None


@dataclass
class BoeBankRateAdapter:
    """Fixture or live fetch of official Bank Rate."""

    config: BoeBankRateAdapterConfig
    retrieved_at: datetime | None = None
    prior_points: tuple[StoredBoePoint, ...] = ()
    last_parse: BoeBankRateParseResult | None = None
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
        except (OSError, BoeBankRateClientError) as exc:
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
            parsed = parse_boe_bank_rate_csv(text, retrieved_at=retrieved)
            observations = stabilise_boe_observations(
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
        self.last_parse = BoeBankRateParseResult(
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
            raise BoeBankRateClientError("offline Bank Rate adapter requires fixture_path")
        return self.config.fixture_path.read_text(encoding="utf-8")
