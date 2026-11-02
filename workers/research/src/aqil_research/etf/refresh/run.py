"""Isolated ETF refresh. This module does not import the macro refresh workflow."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from aqil_research.etf.prices.models import PriceObservation
from aqil_research.etf.prices.persist import apply_price_writes, plan_price_writes


@dataclass(frozen=True)
class RefreshRun:
    dataset: str
    provider: str
    status: str
    idempotency_key: str
    error: str | None
    last_good_observation_at: datetime | None
    prices: tuple[PriceObservation, ...]


def run_price_refresh(
    *,
    existing: tuple[PriceObservation, ...],
    incoming: tuple[PriceObservation, ...],
    provider: str,
    idempotency_key: str,
    rights_allowed: bool,
    provider_failed: bool,
    market_closed: bool,
    finished_at: datetime,
    previous_run: RefreshRun | None = None,
) -> RefreshRun:
    """Refresh prices without deleting the previous close.

    The same idempotency key and the same closes do not append a revision.
    A provider failure or a closed market leaves the stored closes unchanged.
    """

    last_good = _last_good(existing)
    if previous_run is not None and previous_run.idempotency_key == idempotency_key:
        if previous_run.status == "succeeded":
            return RefreshRun(
                dataset="prices",
                provider=provider,
                status="succeeded",
                idempotency_key=idempotency_key,
                error=None,
                last_good_observation_at=previous_run.last_good_observation_at,
                prices=existing,
            )
    if not rights_allowed:
        return _unchanged(
            existing,
            provider=provider,
            status="blocked",
            idempotency_key=idempotency_key,
            error="price retention or display rights are not permitted",
            last_good=last_good,
        )
    if market_closed:
        return _unchanged(
            existing,
            provider=provider,
            status="market_closed",
            idempotency_key=idempotency_key,
            error=None,
            last_good=last_good,
        )
    if provider_failed:
        return _unchanged(
            existing,
            provider=provider,
            status="failed",
            idempotency_key=idempotency_key,
            error="the price provider failed; the previous close is unchanged",
            last_good=last_good,
        )
    writes = plan_price_writes(existing, incoming)
    stored = apply_price_writes(existing, writes)
    return RefreshRun(
        dataset="prices",
        provider=provider,
        status="succeeded",
        idempotency_key=idempotency_key,
        error=None,
        last_good_observation_at=_last_good(stored) or finished_at,
        prices=stored,
    )


def run_holdings_refresh_failure(
    *,
    prices: tuple[PriceObservation, ...],
    idempotency_key: str,
) -> RefreshRun:
    """A holdings failure records itself and does not delete prices."""

    return RefreshRun(
        dataset="holdings",
        provider="issuer",
        status="failed",
        idempotency_key=idempotency_key,
        error="holdings were not fetched; stored prices were left in place",
        last_good_observation_at=_last_good(prices),
        prices=prices,
    )


def _unchanged(
    existing: tuple[PriceObservation, ...],
    *,
    provider: str,
    status: str,
    idempotency_key: str,
    error: str | None,
    last_good: datetime | None,
) -> RefreshRun:
    return RefreshRun(
        dataset="prices",
        provider=provider,
        status=status,
        idempotency_key=idempotency_key,
        error=error,
        last_good_observation_at=last_good,
        prices=existing,
    )


def _last_good(prices: tuple[PriceObservation, ...]) -> datetime | None:
    accepted = [
        row.observation_time
        for row in prices
        if row.price_type == "close" and row.quality in {"accepted", "stale"}
    ]
    if not accepted:
        return None
    return max(accepted)
