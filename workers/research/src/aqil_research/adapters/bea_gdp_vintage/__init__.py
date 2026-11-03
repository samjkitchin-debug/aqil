"""BEA GDP vintage-history import. This package does not change latest-revised GDP."""

from aqil_research.adapters.bea_gdp_vintage.parse import (
    DATASET_ID,
    SOURCE_ID,
    WORKBOOK_URL,
    parse_real_gdp_vintage_workbook,
)

__all__ = [
    "DATASET_ID",
    "SOURCE_ID",
    "WORKBOOK_URL",
    "parse_real_gdp_vintage_workbook",
]
