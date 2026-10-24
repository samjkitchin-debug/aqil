"""Bound Eurostat all-items HICP index. Values are those the response carried.

The live response on 25 October 2026 named table prc_hicp_minr, ECOICOP version 2,
unit I25 (Index, 2025=100), coicop18 TOTAL (Total), and geo EA. Eurostat's
metadata says the data are not seasonally adjusted. This package does not
write either ECB HICP dataset id and does not store a core aggregate.
"""

from __future__ import annotations

SOURCE_ID = "eurostat_hicp_total_ea"
DATASET_ID = "eurostat.prc_hicp_minr.M.I25.TOTAL.EA"
PROVIDER_ID = "eurostat"
RIGHTS_RECORD_ID = SOURCE_ID
ADAPTER_ID = "eurostat_hicp_total_ea"
ADAPTER_VERSION = "1.0.0"

DATASET_CODE = "prc_hicp_minr"
DISCONTINUED_DATASET_CODE = "prc_hicp_midx"
EXTENSION_ID = "PRC_HICP_MINR"
AGENCY_ID = "ESTAT"
SOURCE_NAME = "ESTAT"
DATASET_LABEL_MARK = "ECOICOP ver.2"
GEO_CODE = "EA"
GEO_LABEL = (
    "Euro area (EA11-1999, EA12-2001, EA13-2007, EA15-2008, EA16-2009, "
    "EA17-2011, EA18-2014, EA19-2015, EA20-2023, EA21-2026)"
)
GEOGRAPHY = "EA"
PERIOD_KIND = "month"
UNIT_CODE = "I25"
UNIT_LABEL = "Index, 2025=100"
UNIT_TEXT = "index, 2025 = 100"
COICOP_CODE = "TOTAL"
COICOP_LABEL = "Total"
FREQUENCY_VALUE = "monthly"
SEASONAL_VALUE = "not_seasonally_adjusted"
ADJUSTMENT_LABEL = "Not seasonally adjusted"
VINTAGE_CLASS = "latest_revised"
RATE_UNIT_PREFIX = "RCH"

ECB_HEADLINE_DATASET_ID = "ecb.icp.M.U2.Y.000000.3.INX"
ECB_CORE_DATASET_ID = "ecb.icp.M.U2.Y.XEF000.3.INX"
FORBIDDEN_DATASET_IDS = (ECB_HEADLINE_DATASET_ID, ECB_CORE_DATASET_ID)

# The live coicop18 label for TOT_X_NRG_FOOD also excludes alcohol and tobacco.
# That is not the ECB aggregate "all-items excluding energy and food".
CORE_COUNTERPART_STORED = False

API_ORIGIN = "https://ec.europa.eu"
SERIES_PATH = f"/eurostat/api/dissemination/statistics/1.0/data/{DATASET_CODE}"
ACCESS_URL = f"{API_ORIGIN}{SERIES_PATH}"
QUERY: tuple[tuple[str, str], ...] = (
    ("lang", "EN"),
    ("freq", "M"),
    ("unit", UNIT_CODE),
    ("coicop18", COICOP_CODE),
    ("geo", GEO_CODE),
)

DIMENSIONS: tuple[tuple[str, str, str], ...] = (
    ("freq", "M", "Monthly"),
    ("unit", UNIT_CODE, UNIT_LABEL),
    ("coicop18", COICOP_CODE, COICOP_LABEL),
    ("geo", GEO_CODE, GEO_LABEL),
)

METHOD_COMPATIBILITY_NOTE = (
    "None of Sahm, SLOOS, Census advance orders, MACRO_CONDITIONS_PANEL, "
    "or PERIOD_LEVEL_CHANGE consume this dataset id. "
    "Sahm requires bls.ln.LNS14000000. "
    "SLOOS requires fed.sloos.SUBLPDCILS_N.Q. "
    "Census advance orders requires census.m3.adv.MDM.NO. "
    "MACRO_CONDITIONS_PANEL requires those three dataset ids. "
    "PERIOD_LEVEL_CHANGE requires bls.ln.LNS14000000. "
    "PRICES_AND_POLICY and MACRO_READING_SYNTHESIS do not consume this dataset id."
)


def assert_bound_identity() -> None:
    """Fail closed if this package is pointed at a different HICP object."""
    if DATASET_CODE == DISCONTINUED_DATASET_CODE:
        raise RuntimeError("refusing discontinued table prc_hicp_midx")
    if DATASET_ID in FORBIDDEN_DATASET_IDS:
        raise RuntimeError("refusing a write onto an ECB HICP dataset id")
    if SEASONAL_VALUE != "not_seasonally_adjusted":
        raise RuntimeError("refusing to label this index as seasonally adjusted")
    if any(name == "s_adj" for name, _code, _label in DIMENSIONS):
        raise RuntimeError("refusing a seasonal-adjustment flag")
    unit_code = next(code for name, code, _label in DIMENSIONS if name == "unit")
    if unit_code.startswith(RATE_UNIT_PREFIX):
        raise RuntimeError("refusing a rate-of-change unit")
    if unit_code != UNIT_CODE:
        raise RuntimeError("refusing an index base other than 2025=100")
    if GEO_CODE != "EA":
        raise RuntimeError("refusing a geography that is not the changing-composition euro area")
    if CORE_COUNTERPART_STORED:
        raise RuntimeError(
            "refusing a Eurostat core series while the special aggregate is ambiguous"
        )


assert_bound_identity()
