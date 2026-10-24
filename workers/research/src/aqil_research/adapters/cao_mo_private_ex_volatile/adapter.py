"""Cabinet Office adapter for one nominal machinery-orders series.

The bound series is private demand excluding ships and electric power, on the
sheet 季調・月次, column J, unit million yen. It is nominal, not a real volume
index. It is seasonally adjusted and calendar-monthly. The sheet 年度・暦年 is
not read, so fiscal-year and calendar-year totals are not stored as this series.

The current workbook is the latest revised long series. It is not a historical
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

from aqil_research.adapters.cao_mo_private_ex_volatile.client import (
    CaoMoClientError,
    fetch_workbook,
)
from aqil_research.adapters.cao_mo_private_ex_volatile.constants import (
    ADAPTER_ID,
    ADAPTER_VERSION,
    CATALOGUE_URL,
    DATASET_ID,
    METHOD_COMPATIBILITY_NOTE,
    PROVIDER_ID,
    SOURCE_ID,
)
from aqil_research.adapters.cao_mo_private_ex_volatile.parse import (
    CaoMoParseResult,
    parse_cao_mo_workbook,
)
from aqil_research.adapters.cao_mo_private_ex_volatile.stability import (
    StoredCaoMoPoint,
    stabilise_cao_mo_observations,
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
class CaoMoAdapterConfig:
    live: bool = False
    fixture_path: Path | None = None


@dataclass
class CaoMoAdapter:
    """Fixture or live fetch of the single bound machinery-orders series."""

    config: CaoMoAdapterConfig
    retrieved_at: datetime | None = None
    prior_points: tuple[StoredCaoMoPoint, ...] = ()
    last_parse: CaoMoParseResult | None = None
    last_http_status: int | None = None
    last_file_url: str | None = None

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
        self.last_file_url = None
        try:
            payload, source_locator = self._load_payload()
        except (OSError, CaoMoClientError) as exc:
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
            parsed = parse_cao_mo_workbook(
                payload,
                retrieved_at=retrieved,
                source_locator=source_locator,
            )
            observations = stabilise_cao_mo_observations(
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
        self.last_parse = CaoMoParseResult(
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

    def _load_payload(self) -> tuple[bytes, str]:
        if self.config.live:
            payload, status, file_url = fetch_workbook()
            self.last_http_status = status
            self.last_file_url = file_url
            return payload, file_url
        if self.config.fixture_path is None:
            raise CaoMoClientError("offline machinery-orders adapter requires fixture_path")
        self.last_file_url = CATALOGUE_URL
        return self.config.fixture_path.read_bytes(), CATALOGUE_URL
