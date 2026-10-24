"""METI adapter for one Japan industrial production series.

The bound series is the mining and manufacturing value-added production index
on the 生産 sheet of b2020_gsm1j.xlsx. The sheet title states that the index
is seasonally adjusted, monthly, and 2020 = 100. The item number is
1000000000 and the item name is 鉱工業. Shipments, inventories, the
inventory ratio, fiscal-year columns, and calendar-year columns are not stored.
The workbook is the latest revised file. It is not a historical vintage panel.
includeHistory is not a parameter of this file.

None of Sahm, labour, prices, industrial production, credit, SLOOS, Census,
or MACRO_CONDITIONS_PANEL consume this dataset id. Sahm requires
bls.ln.LNS14000000. Labour requires bls.ln.LNS14000000,
bls.ce.CES0000000001, and bls.jt.JTS000000000000000JOL. Prices requires
bls.cu.CUSR0000SA0, fed.h15.RIFSPFF_N.M, and fed.h15.RIFLGFCY10_N.M.
Industrial production requires fed.g17.IP.B50001.S. Credit requires
fed.sloos.SUBLPDCILS_N.Q and fed.h8.B1001NCBA. SLOOS requires
fed.sloos.SUBLPDCILS_N.Q. Census requires census.m3.adv.MDM.NO.
MACRO_CONDITIONS_PANEL requires bls.ln.LNS14000000,
fed.sloos.SUBLPDCILS_N.Q, and census.m3.adv.MDM.NO.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from aqil_research.adapters.meti_iip_production.client import (
    MetiIipClientError,
    fetch_workbook,
)
from aqil_research.adapters.meti_iip_production.constants import (
    ADAPTER_ID,
    ADAPTER_VERSION,
    DATASET_ID,
    METHOD_COMPATIBILITY_NOTE,
    PROVIDER_ID,
    SOURCE_ID,
)
from aqil_research.adapters.meti_iip_production.parse import (
    MetiIipParseResult,
    parse_meti_iip_workbook,
)
from aqil_research.adapters.meti_iip_production.stability import (
    StoredMetiPoint,
    stabilise_meti_observations,
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
class MetiIipProductionAdapterConfig:
    live: bool = False
    fixture_path: Path | None = None


@dataclass
class MetiIipProductionAdapter:
    """Fixture or live fetch of the single bound production series."""

    config: MetiIipProductionAdapterConfig
    retrieved_at: datetime | None = None
    prior_points: tuple[StoredMetiPoint, ...] = ()
    last_parse: MetiIipParseResult | None = None
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
            payload = self._load_bytes()
        except (OSError, MetiIipClientError) as exc:
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
            parsed = parse_meti_iip_workbook(payload, retrieved_at=retrieved)
            observations = stabilise_meti_observations(
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
        self.last_parse = MetiIipParseResult(
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

    def _load_bytes(self) -> bytes:
        if self.config.live:
            payload, status = fetch_workbook()
            self.last_http_status = status
            return payload
        if self.config.fixture_path is None:
            raise MetiIipClientError("offline METI adapter requires fixture_path")
        return self.config.fixture_path.read_bytes()
