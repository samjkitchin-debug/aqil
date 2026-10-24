"""Bound Eurostat real GDP for the euro area. Values are those the response carried."""

from __future__ import annotations

SOURCE_ID = "eurostat_gdp_real_ea21"
DATASET_ID = "eurostat.namq_10_gdp.Q.CLV_I15.SCA.B1GQ.EA21"
PROVIDER_ID = "eurostat"
RIGHTS_RECORD_ID = SOURCE_ID
ADAPTER_ID = "eurostat_gdp_real_ea21"
ADAPTER_VERSION = "1.0.0"

DATASET_CODE = "namq_10_gdp"
AGENCY_ID = "ESTAT"
SOURCE_NAME = "ESTAT"
GEO_CODE = "EA21"
GEO_LABEL = "Euro area \u2013 21 countries (from 2026)"
GEOGRAPHY = "EA21"
PERIOD_KIND = "quarter"
UNIT_TEXT = "index, 2015 = 100"
FREQUENCY_VALUE = "quarterly"
SEASONAL_VALUE = "seasonally_adjusted"
ADJUSTMENT_LABEL = "Seasonally and calendar adjusted data"
VINTAGE_CLASS = "latest_revised"

API_ORIGIN = "https://ec.europa.eu"
SERIES_PATH = f"/eurostat/api/dissemination/statistics/1.0/data/{DATASET_CODE}"
ACCESS_URL = f"{API_ORIGIN}{SERIES_PATH}"
QUERY: tuple[tuple[str, str], ...] = (
    ("lang", "EN"),
    ("geo", "EA21"),
    ("na_item", "B1GQ"),
    ("s_adj", "SCA"),
    ("unit", "CLV_I15"),
)

# Dimension code and the label the response must repeat.
DIMENSIONS: tuple[tuple[str, str, str], ...] = (
    ("freq", "Q", "Quarterly"),
    ("unit", "CLV_I15", "Chain linked volumes, index 2015=100"),
    ("s_adj", "SCA", "Seasonally and calendar adjusted data"),
    ("na_item", "B1GQ", "Gross domestic product at market prices"),
    ("geo", GEO_CODE, GEO_LABEL),
)

METHOD_COMPATIBILITY_NOTE = (
    "None of Sahm, SLOOS, Census advance orders, MACRO_CONDITIONS_PANEL, "
    "or PERIOD_LEVEL_CHANGE consume this dataset id. "
    "Sahm requires bls.ln.LNS14000000. "
    "SLOOS requires fed.sloos.SUBLPDCILS_N.Q. "
    "Census advance orders requires census.m3.adv.MDM.NO. "
    "MACRO_CONDITIONS_PANEL requires those three dataset ids. "
    "PERIOD_LEVEL_CHANGE requires bls.ln.LNS14000000."
)
