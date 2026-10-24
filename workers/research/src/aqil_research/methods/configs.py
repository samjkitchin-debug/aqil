"""Versioned Sahm-rule configuration presets."""

from __future__ import annotations

from decimal import Decimal

from aqil_research.methods.sahm import SahmConfig

SAHM_PUBLISHED = SahmConfig(
    config_id="sahm_published_v1",
    threshold_percentage_points=Decimal("0.50"),
    label="Published Sahm rule threshold (0.50 percentage points)",
)

SAHM_SENSITIVITY = SahmConfig(
    config_id="sahm_sensitivity_v1",
    threshold_percentage_points=Decimal("0.30"),
    label="Aqil sensitivity configuration; not the published Sahm rule",
)

MACRO_CONDITIONS_PUBLISHED = {
    "config_id": "macro_conditions_published_v1",
    "label": "Labour, business credit and manufacturing demand panel",
    "labour_evaluation_period": "2024-12-01",
    "sloos_evaluation_period": "2024-10-01",
    "census_evaluation_period": "2024-08-01",
    "sahm_config_id": SAHM_PUBLISHED.config_id,
}

SLOOS_CIL_PUBLISHED = {
    "config_id": "sloos_cil_published_v1",
    "label": "SLOOS C&I lending standards (SUBLPDCILS_N.Q)",
}

CENSUS_ADV_ORDERS_PUBLISHED = {
    "config_id": "census_adv_orders_published_v1",
    "label": "Census advance durable goods new orders (MDM / NO)",
}

LABOUR_MARKET_PUBLISHED = {
    "config_id": "labour_market_conditions_v1",
    "label": "Latest-revised labour levels, endpoint changes, and ranks",
}

PRICES_AND_POLICY_PUBLISHED = {
    "config_id": "prices_and_policy_v1",
    "label": "Latest-revised CPI-U change and separate H.15 levels",
}

INDUSTRIAL_PRODUCTION_PUBLISHED = {
    "config_id": "industrial_production_activity_v1",
    "label": "Latest-revised industrial production level and 12-month change",
}

BRY_BOSCHAN_SPENCER15_PUBLISHED = {
    "config_id": "bry_boschan_spencer15_variant_v1",
    "label": "Macaulay 15-term Spencer weights and the six-lag five-lead twelve-month average",
}

CREDIT_STANDARDS_AND_VOLUMES_PUBLISHED = {
    "config_id": "credit_standards_and_volumes_v1",
    "label": "Latest-revised SLOOS share and H.8 bank credit",
}
