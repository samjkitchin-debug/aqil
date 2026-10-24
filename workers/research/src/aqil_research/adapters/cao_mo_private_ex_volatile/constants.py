"""Bound Cabinet Office machinery-orders series. Values are those the workbook carried."""

from __future__ import annotations

SOURCE_ID = "cao_mo_private_ex_volatile_sa_monthly"
DATASET_ID = "cao.mo.private_ex_volatile.nominal.million_yen.sa.monthly.calendar"
PROVIDER_ID = "cao"
RIGHTS_RECORD_ID = SOURCE_ID

ADAPTER_ID = "cao_mo_private_ex_volatile_sa_monthly"
ADAPTER_VERSION = "1.0.0"

SHEET_NAME = "季調・月次"
TITLE_JA = "主要需要者別受注額(季調系列・月次)"
TITLE_EN_MARK = "Seasonally adjusted, Monthly"
UNIT_MARK = "(単位:100万円)"
COLUMN = "J"
HEADER_JA_MARK = "船舶・電力を除く"
HEADER_EN_MARK = "Volatile"
FIRST_DATA_ROW = 10

API_ORIGIN = "https://www.esri.cao.go.jp"
CATALOGUE_URL = f"{API_ORIGIN}/jp/stat/juchu/juchu.html"

GEOGRAPHY = "JP"
FREQUENCY_LABEL = "monthly"
SEASONAL_ADJUSTMENT_LABEL = "seasonally adjusted"
UNIT_TEXT = "million yen, nominal, not a real volume index"
CALENDAR_BASIS = "calendar_month"
SERIES_KEY = "private_ex_volatile"
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
