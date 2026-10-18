"""Method registry — configuration-driven analytical methodology selection."""

from __future__ import annotations

from pydantic import BaseModel

from aqil_research.methods.census_adv_orders import (
    CENSUS_ADV_ORDERS_METHOD_ID,
    CensusAdvOrdersMethod,
)
from aqil_research.methods.macro_conditions import (
    MACRO_CONDITIONS_METHOD_ID,
    MacroConditionsMethod,
)
from aqil_research.methods.period_change import PERIOD_CHANGE_METHOD_ID, PeriodChangeMethod
from aqil_research.methods.protocol import AnalyticalMethod
from aqil_research.methods.sahm import SAHM_METHOD_ID
from aqil_research.methods.sahm_registered import SahmAnalyticalMethod
from aqil_research.methods.sloos_cil import SLOOS_CIL_METHOD_ID, SloosCilMethod


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
    registry.register(SloosCilMethod())
    registry.register(CensusAdvOrdersMethod())
    registry.register(MacroConditionsMethod())
    return registry


__all__ = [
    "MethodRegistry",
    "MethodRegistryError",
    "CENSUS_ADV_ORDERS_METHOD_ID",
    "MACRO_CONDITIONS_METHOD_ID",
    "PERIOD_CHANGE_METHOD_ID",
    "SAHM_METHOD_ID",
    "SLOOS_CIL_METHOD_ID",
    "default_method_registry",
]
