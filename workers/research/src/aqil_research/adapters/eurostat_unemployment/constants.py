"""Bound Eurostat unemployment rate for the euro area. Values are those the response carried."""

from __future__ import annotations

SOURCE_ID = "eurostat_unemployment_ea21"
DATASET_ID = "eurostat.une_rt_m.M.SA.TOTAL.PC_ACT.T.EA21"
PROVIDER_ID = "eurostat"
RIGHTS_RECORD_ID = SOURCE_ID
ADAPTER_ID = "eurostat_unemployment_ea21"
ADAPTER_VERSION = "1.0.0"

DATASET_CODE = "une_rt_m"
AGENCY_ID = "ESTAT"
SOURCE_NAME = "ESTAT"
GEO_CODE = "EA21"
GEO_LABEL = "Euro area \u2013 21 countries (from 2026)"
GEOGRAPHY = "EA21"
PERIOD_KIND = "month"
UNIT_TEXT = "percent"
FREQUENCY_VALUE = "monthly"
SEASONAL_VALUE = "seasonally_adjusted"
ADJUSTMENT_LABEL = "Seasonally adjusted data, not calendar adjusted data"
VINTAGE_CLASS = "latest_revised"

API_ORIGIN = "https://ec.europa.eu"
SERIES_PATH = f"/eurostat/api/dissemination/statistics/1.0/data/{DATASET_CODE}"
ACCESS_URL = f"{API_ORIGIN}{SERIES_PATH}"
QUERY: tuple[tuple[str, str], ...] = (
    ("lang", "EN"),
    ("age", "TOTAL"),
    ("geo", "EA21"),
    ("s_adj", "SA"),
    ("sex", "T"),
    ("unit", "PC_ACT"),
)

DIMENSIONS: tuple[tuple[str, str, str], ...] = (
    ("freq", "M", "Monthly"),
    ("s_adj", "SA", "Seasonally adjusted data, not calendar adjusted data"),
    ("age", "TOTAL", "Total"),
    ("unit", "PC_ACT", "Percentage of population in the labour force"),
    ("sex", "T", "Total"),
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
