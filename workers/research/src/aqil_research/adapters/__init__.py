"""Provider adapters — normalise external shapes to EconomicObservation."""

from aqil_research.adapters.protocol import (
    ProviderAdapter,
    ProviderFailureCode,
    ProviderFetchError,
    ProviderFetchResult,
    ProviderIdentity,
)
from aqil_research.adapters.registry import AdapterRegistry, AdapterRegistryError

__all__ = [
    "AdapterRegistry",
    "AdapterRegistryError",
    "ProviderAdapter",
    "ProviderFetchError",
    "ProviderFetchResult",
    "ProviderFailureCode",
    "ProviderIdentity",
]
