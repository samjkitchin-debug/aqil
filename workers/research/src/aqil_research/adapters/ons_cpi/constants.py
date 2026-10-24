"""Bound ONS consumer price index. Identity fields are those the CSV header carried."""

from __future__ import annotations

SOURCE_ID = "ons_mm23_cpi_d7bt"
DATASET_ID = "ons.mm23.D7BT"
PROVIDER_ID = "ons"
RIGHTS_RECORD_ID = SOURCE_ID

ADAPTER_ID = "ons_mm23_cpi_d7bt"
ADAPTER_VERSION = "1.0.0"

SERIES_KEY = "D7BT"
TITLE = "CPI INDEX 00: ALL ITEMS 2015=100"
SOURCE_DATASET = "MM23"
UNIT_HEADER = "Index, base year = 100"
UNIT_TEXT = "index, 2015 = 100"
FREQUENCY_LABEL = "Monthly"
GEOGRAPHY = "GB"
SEASONAL_ADJUSTMENT_LABEL = "not seasonally adjusted"
VINTAGE_CLASS = "latest_revised"

API_ORIGIN = "https://www.ons.gov.uk"
SERIES_PATH = "/generator"
ACCESS_URL = (
    f"{API_ORIGIN}{SERIES_PATH}?format=csv"
    "&uri=/economy/inflationandpriceindices/timeseries/d7bt/mm23"
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
