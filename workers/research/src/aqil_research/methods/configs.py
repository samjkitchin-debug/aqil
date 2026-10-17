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
