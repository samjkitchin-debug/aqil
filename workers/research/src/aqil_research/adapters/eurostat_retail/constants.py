"""Bound Eurostat retail sales volume for the euro area."""

from __future__ import annotations

SOURCE_ID = "eurostat_retail_volume_ea21"
DATASET_ID = "eurostat.sts_trtu_m.M.VOL_SLS.G47.SCA.I21.EA21"
PROVIDER_ID = "eurostat"
RIGHTS_RECORD_ID = SOURCE_ID
ADAPTER_ID = "eurostat_retail_volume_ea21"
ADAPTER_VERSION = "1.0.0"

DATASET_CODE = "sts_trtu_m"
AGENCY_ID = "ESTAT"
SOURCE_NAME = "ESTAT"
GEO_CODE = "EA21"
GEO_LABEL = "Euro area \u2013 21 countries (from 2026)"
GEOGRAPHY = "EA21"
PERIOD_KIND = "month"
UNIT_TEXT = "index, 2021 = 100"
FREQUENCY_VALUE = "monthly"
SEASONAL_VALUE = "seasonally_adjusted"
ADJUSTMENT_LABEL = "Seasonally and calendar adjusted data"
VINTAGE_CLASS = "latest_revised"

API_ORIGIN = "https://ec.europa.eu"
SERIES_PATH = f"/eurostat/api/dissemination/statistics/1.0/data/{DATASET_CODE}"
ACCESS_URL = f"{API_ORIGIN}{SERIES_PATH}"
QUERY: tuple[tuple[str, str], ...] = (
    ("lang", "EN"),
    ("geo", "EA21"),
    ("indic_bt", "VOL_SLS"),
    ("nace_r2", "G47"),
    ("s_adj", "SCA"),
    ("unit", "I21"),
)

DIMENSIONS: tuple[tuple[str, str, str], ...] = (
    ("freq", "M", "Monthly"),
    ("indic_bt", "VOL_SLS", "Volume of sales"),
    ("nace_r2", "G47", "Retail trade, except of motor vehicles and motorcycles"),
    ("s_adj", "SCA", "Seasonally and calendar adjusted data"),
    ("unit", "I21", "Index, 2021=100"),
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
