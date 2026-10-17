"""Method registry — configuration-driven analytical methodology selection."""

from __future__ import annotations

from pydantic import BaseModel

from aqil_research.methods.period_change import PERIOD_CHANGE_METHOD_ID, PeriodChangeMethod
from aqil_research.methods.protocol import AnalyticalMethod
from aqil_research.methods.sahm import SAHM_METHOD_ID
from aqil_research.methods.sahm_registered import SahmAnalyticalMethod


class MethodRegistryError(Exception):
    """Raised when a method id is unknown or config is invalid."""


class MethodRegistry:
    def __init__(self) -> None:
        self._methods: dict[str, AnalyticalMethod] = {}

    def register(self, method: AnalyticalMethod) -> None:
        self._methods[method.method_id] = method

    def get(self, method_id: str) -> AnalyticalMethod:
        method = self._methods.get(method_id)
        if method is None:
            raise MethodRegistryError(f"unknown method_id: {method_id}")
        return method

    def parse_config(self, method_id: str, payload: dict[str, object]) -> BaseModel:
        return self.get(method_id).parse_config(payload)


def default_method_registry() -> MethodRegistry:
    registry = MethodRegistry()
    registry.register(SahmAnalyticalMethod())
    registry.register(PeriodChangeMethod())
    return registry


__all__ = [
    "MethodRegistry",
    "MethodRegistryError",
    "PERIOD_CHANGE_METHOD_ID",
    "SAHM_METHOD_ID",
    "default_method_registry",
]
