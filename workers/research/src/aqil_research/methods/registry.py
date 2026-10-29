"""Method registry — configuration-driven analytical methodology selection."""

from __future__ import annotations

from pydantic import BaseModel

from aqil_research.methods.bry_boschan_spencer15 import (
    BRY_BOSCHAN_SPENCER15_VARIANT,
    BryBoschanSpencer15Method,
)
from aqil_research.methods.census_adv_orders import (
    CENSUS_ADV_ORDERS_METHOD_ID,
    CensusAdvOrdersMethod,
)
from aqil_research.methods.credit_standards_volumes import (
    CREDIT_STANDARDS_AND_VOLUMES_METHOD_ID,
    CreditStandardsVolumesMethod,
)
from aqil_research.methods.harding_pagan_characteristics import (
    HARDING_PAGAN_CHARACTERISTICS,
    HardingPaganCharacteristicsMethod,
)
from aqil_research.methods.industrial_production_activity import (
    INDUSTRIAL_PRODUCTION_METHOD_ID,
    IndustrialProductionActivityMethod,
)
from aqil_research.methods.labour_market import (
    LABOUR_MARKET_METHOD_ID,
    LabourMarketConditionsMethod,
)
from aqil_research.methods.macro_conditions import (
    MACRO_CONDITIONS_METHOD_ID,
    MacroConditionsMethod,
)
from aqil_research.methods.period_change import PERIOD_CHANGE_METHOD_ID, PeriodChangeMethod
from aqil_research.methods.prices_and_policy import (
    PRICES_AND_POLICY_METHOD_ID,
    PricesAndPolicyMethod,
)
from aqil_research.methods.protocol import AnalyticalMethod
from aqil_research.methods.restricted_coincident_diffusion import (
    METHOD_ID as RESTRICTED_COINCIDENT_DIFFUSION_METHOD_ID,
)
from aqil_research.methods.restricted_coincident_diffusion import (
    RestrictedCoincidentDiffusionMethod,
)
from aqil_research.methods.sahm import SAHM_METHOD_ID
from aqil_research.methods.sahm_registered import SahmAnalyticalMethod
from aqil_research.methods.sloos_cil import SLOOS_CIL_METHOD_ID, SloosCilMethod
from aqil_research.methods.stock_watson_1988_fit import (
    SPECIFICATION_ID as STOCK_WATSON_MODERN_REFIT_ID,
)
from aqil_research.methods.stock_watson_1988_fit import StockWatsonModernRefitMethod


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
    registry.register(LabourMarketConditionsMethod())
    registry.register(PricesAndPolicyMethod())
    registry.register(IndustrialProductionActivityMethod())
    registry.register(CreditStandardsVolumesMethod())
    registry.register(BryBoschanSpencer15Method())
    registry.register(StockWatsonModernRefitMethod())
    registry.register(RestrictedCoincidentDiffusionMethod())
    registry.register(HardingPaganCharacteristicsMethod())
    return registry


__all__ = [
    "MethodRegistry",
    "MethodRegistryError",
    "BRY_BOSCHAN_SPENCER15_VARIANT",
    "HARDING_PAGAN_CHARACTERISTICS",
    "RESTRICTED_COINCIDENT_DIFFUSION_METHOD_ID",
    "STOCK_WATSON_MODERN_REFIT_ID",
    "CENSUS_ADV_ORDERS_METHOD_ID",
    "CREDIT_STANDARDS_AND_VOLUMES_METHOD_ID",
    "INDUSTRIAL_PRODUCTION_METHOD_ID",
    "LABOUR_MARKET_METHOD_ID",
    "MACRO_CONDITIONS_METHOD_ID",
    "PERIOD_CHANGE_METHOD_ID",
    "PRICES_AND_POLICY_METHOD_ID",
    "SAHM_METHOD_ID",
    "SLOOS_CIL_METHOD_ID",
    "default_method_registry",
]
