"""Configuration-driven adapter lookup."""

from __future__ import annotations

from aqil_research.adapters.protocol import ProviderAdapter


class AdapterRegistryError(Exception):
    """Raised when an adapter id is unknown."""


class AdapterRegistry:
    def __init__(self) -> None:
        self._adapters: dict[str, ProviderAdapter] = {}

    def register(self, adapter: ProviderAdapter) -> None:
        self._adapters[adapter.identity.adapter_id] = adapter

    def get(self, adapter_id: str) -> ProviderAdapter:
        adapter = self._adapters.get(adapter_id)
        if adapter is None:
            raise AdapterRegistryError(f"unknown adapter_id: {adapter_id}")
        return adapter


def default_adapter_registry() -> AdapterRegistry:
    return AdapterRegistry()
