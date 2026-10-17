"""Canonical fingerprints for provider fetch payloads."""

from __future__ import annotations

import hashlib
import json

from aqil_research.adapters.protocol import ProviderAdapter, ProviderFetchResult
from aqil_research.contracts.observation import EconomicObservation


def observation_set_fingerprint(observations: tuple[EconomicObservation, ...]) -> str:
    """Stable hash over sorted period/value identity (excludes retrieval timestamps)."""
    rows = [
        {
            "observation_id": obs.observation_id,
            "period_start": obs.period_start.isoformat(),
            "raw_value": obs.raw_value,
            "dataset_id": obs.dataset_id,
        }
        for obs in sorted(observations, key=lambda o: o.observation_id)
    ]
    payload = json.dumps(rows, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def fetch_fingerprint(adapter: ProviderAdapter, fetch: ProviderFetchResult) -> str | None:
    if not fetch.observations:
        return None
    identity = adapter.identity
    base = observation_set_fingerprint(fetch.observations)
    meta = f"{identity.adapter_id}:{identity.adapter_version}:{identity.dataset_id}"
    return hashlib.sha256(f"{meta}:{base}".encode()).hexdigest()
