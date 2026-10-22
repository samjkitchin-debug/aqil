"""Bound ECB Data Portal series. Values are those the SDMX response carried."""

from __future__ import annotations

SOURCE_ID = "ecb_sdw_hicp_sa"
DATASET_ID = "ecb.icp.M.U2.Y.000000.3.INX"
PROVIDER_ID = "ecb"
RIGHTS_RECORD_ID = SOURCE_ID

ADAPTER_ID = "ecb_sdw_hicp_sa"
ADAPTER_VERSION = "1.0.0"

# ICP.M.U2.Y.000000.3.INX — monthly, euro area, working day and seasonally adjusted,
# all-items HICP index, European Central Bank institution code.
SERIES_KEY = "ICP.M.U2.Y.000000.3.INX"
FLOW_REF = "ICP"
SERIES_DIMENSIONS = "M.U2.Y.000000.3.INX"

API_ORIGIN = "https://data-api.ecb.europa.eu"
SERIES_PATH = f"/service/data/{FLOW_REF}/{SERIES_DIMENSIONS}"
ACCESS_URL = f"{API_ORIGIN}{SERIES_PATH}"

FREQ_CODE = "M"
FREQUENCY_LABEL = "Monthly"
REF_AREA = "U2"
GEOGRAPHY = "EA"
ADJUSTMENT_CODE = "Y"
SEASONAL_ADJUSTMENT_LABEL = "Working day and seasonally adjusted"
ICP_ITEM = "000000"
INSTITUTION_CODE = "3"
ICP_SUFFIX = "INX"
COMPILING_ORG = "4F0"
SOURCE_AGENCY = "4F0"
UNIT_CODE = "IX"
UNIT_INDEX_BASE = "2015 = 100"
UNIT_MULT = "0"
UNIT_TEXT = "index, 2015 = 100"

# TITLE_COMPL on the current CSV, including the compiler name.
COMPILER_SENTENCE = (
    "Euro area (Member States and Institutions of the Euro Area) changing composition -  "
    "HICP - Overall index, Index, European Central Bank (ECB), "
    "Working day and seasonally adjusted"
)

VINTAGE_CLASS = "latest_revised"

METHOD_COMPATIBILITY_NOTE = (
    "None of Sahm, SLOOS, Census advance orders, MACRO_CONDITIONS_PANEL, "
    "or PERIOD_LEVEL_CHANGE consume this dataset id. "
    "Sahm requires bls.ln.LNS14000000. "
    "SLOOS requires fed.sloos.SUBLPDCILS_N.Q. "
    "Census advance orders requires census.m3.adv.MDM.NO. "
    "MACRO_CONDITIONS_PANEL requires those three dataset ids. "
    "PERIOD_LEVEL_CHANGE requires bls.ln.LNS14000000."
)
