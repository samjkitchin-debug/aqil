"""Federal Reserve G.17 total industrial production index (fixture or live package).

The bound series is the Board package row "Total index; s.a. IP"
(unit Index:_2017_100, unique identifier G17/IP_MARKET_GROUPS/IP.B50001.S).
Stored observations use unit index_2017_100, monthly frequency, and
seasonally adjusted. The file is the latest revised release and is not a
historical vintage panel. ND, blank, and NA are omitted. They are not stored
as zero and they are not interpolated.

None of Sahm, SLOOS, Census advance orders, MACRO_CONDITIONS_PANEL, or
PERIOD_LEVEL_CHANGE consume dataset fed.g17.IP.B50001.S. Sahm and
PERIOD_LEVEL_CHANGE require bls.ln.LNS14000000. SLOOS requires
fed.sloos.SUBLPDCILS_N.Q. Census advance orders requires
census.m3.adv.MDM.NO. MACRO_CONDITIONS_PANEL requires those three dataset ids.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from aqil_research.adapters.fed_g17.client import PACKAGE_URL
from aqil_research.adapters.fed_g17.package import G17PackageError, extract_total_index
from aqil_research.adapters.fed_g17.parse import DATASET_ID, SOURCE_ID, parse_g17_payload
from aqil_research.adapters.fed_g17.stability import StoredG17Point, stabilise_g17_vintages
from aqil_research.adapters.protocol import (
    ProviderFailureCode,
    ProviderFetchError,
    ProviderFetchResult,
    ProviderIdentity,
)

ADAPTER_ID = "fed_g17_total_ip"
ADAPTER_VERSION = "1.0.0"


@dataclass(frozen=True, slots=True)
class FedG17AdapterConfig:
    live: bool = False
    fixture_path: Path | None = None


@dataclass
class FedG17Adapter:
    config: FedG17AdapterConfig
    retrieved_at: datetime | None = None
    prior_points: tuple[StoredG17Point, ...] = ()

    @property
    def identity(self) -> ProviderIdentity:
        return ProviderIdentity(
            adapter_id=ADAPTER_ID,
            adapter_version=ADAPTER_VERSION,
            source_id=SOURCE_ID,
            dataset_id=DATASET_ID,
            provider_id="federal_reserve_board",
        )

    def fetch(self) -> ProviderFetchResult:
        retrieved = self.retrieved_at or datetime.now(tz=UTC)
        collection_vintage = retrieved.date()
        try:
            if self.config.live:
                from aqil_research.adapters.fed_g17.client import fetch_g17_bundle

                payload = fetch_g17_bundle()
            else:
                payload = _fixture_payload(self.config.fixture_path)
            payload = stabilise_g17_vintages(payload, self.prior_points, retrieved)
            parsed = parse_g17_payload(
                payload,
                adapter_version=f"{ADAPTER_ID}:{ADAPTER_VERSION}",
                retrieved_at=retrieved,
                collection_vintage_date=collection_vintage,
            )
        except G17PackageError as exc:
            return _failure(ProviderFailureCode.PARSE_FAILED, str(exc))
        except ValueError as exc:
            return _failure(ProviderFailureCode.PARSE_FAILED, str(exc))
        except OSError as exc:
            return _failure(ProviderFailureCode.PARSE_FAILED, str(exc))
        except Exception as exc:  # noqa: BLE001 — live fetch errors stay inside the adapter
            if not self.config.live:
                raise
            return _failure(ProviderFailureCode.FETCH_FAILED, str(exc))
        return ProviderFetchResult(observations=parsed.observations)


def _fixture_payload(path: Path | None) -> dict[str, object]:
    if path is None:
        raise G17PackageError("offline G.17 adapter requires fixture_path")
    extracted = extract_total_index(path.read_text(encoding="utf-8"))
    rows = extracted["observations"]
    if not isinstance(rows, list):
        raise G17PackageError("G.17 fixture did not contain observations")
    located = [{**row, "source_locator": PACKAGE_URL} for row in rows]
    return {**extracted, "observations": located}


def _failure(code: ProviderFailureCode, message: str) -> ProviderFetchResult:
    return ProviderFetchResult(
        observations=(),
        errors=(ProviderFetchError(code=code, message=message),),
    )
