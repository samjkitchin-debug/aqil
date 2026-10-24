"""Bound Statistics Bureau CPI reference series. Values are those the CSV carried."""

from __future__ import annotations

SOURCE_ID = "stat_cpi_2025_all_items_reference"
DATASET_ID = "stat.cpi.2025base.JP.0001.all_items.monthly.calendar.nsa.reference_3dp"
PROVIDER_ID = "stat"
RIGHTS_RECORD_ID = SOURCE_ID

ADAPTER_ID = "stat_cpi_2025_all_items_reference"
ADAPTER_VERSION = "1.0.0"

# 品目別価格指数, Japan, monthly, group code 0001. Not the 1-decimal official table.
ITEM_CODE = "0001"
ITEM_JA = "総合"
ITEM_EN = "All items"
JAPANESE_HEADER = "類・品目"
ENGLISH_HEADER = "Group/Item"
CODE_HEADER_MARK = "Group/Item code"

API_ORIGIN = "https://www.stat.go.jp"
SERIES_PATH = "/data/cpi/2025/csv/zmi2025aa.csv"
ACCESS_URL = f"{API_ORIGIN}{SERIES_PATH}"
CATALOGUE_URL = "https://www.stat.go.jp/data/cpi/1.html"

GEOGRAPHY = "JP"
FREQUENCY_LABEL = "monthly"
SEASONAL_ADJUSTMENT_LABEL = "not seasonally adjusted"
UNIT_TEXT = (
    "index, 2025 = 100, three-decimal reference price index, "
    "not a nominal yen amount and not a real volume"
)
CALENDAR_BASIS = "calendar_month"
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
