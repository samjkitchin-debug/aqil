"""Bound ECB deposit-facility rate. Values are those the SDMX response carried."""

from __future__ import annotations

SOURCE_ID = "ecb_fm_deposit_facility"
DATASET_ID = "ecb.fm.D.U2.EUR.4F.KR.DFR.LEV"
PROVIDER_ID = "ecb"
RIGHTS_RECORD_ID = SOURCE_ID

ADAPTER_ID = "ecb_fm_deposit_facility"
ADAPTER_VERSION = "1.0.0"

SERIES_KEY = "FM.D.U2.EUR.4F.KR.DFR.LEV"
FLOW_REF = "FM"
SERIES_DIMENSIONS = "D.U2.EUR.4F.KR.DFR.LEV"

API_ORIGIN = "https://data-api.ecb.europa.eu"
SERIES_PATH = f"/service/data/{FLOW_REF}/{SERIES_DIMENSIONS}"
ACCESS_URL = f"{API_ORIGIN}{SERIES_PATH}"

FREQ_CODE = "D"
FREQUENCY_LABEL = "Daily"
REF_AREA = "U2"
GEOGRAPHY = "EA"
CURRENCY = "EUR"
PROVIDER_FM = "4F"
INSTRUMENT_FM = "KR"
PROVIDER_FM_ID = "DFR"
DATA_TYPE_FM = "LEV"
COMPILING_ORG = "4F0"
UNIT_CODE = "PCPA"
UNIT_MULT = "0"
UNIT_TEXT = "percent_per_year"
TITLE = "Deposit facility - date of changes (raw data) - Level"
COMPILER_SENTENCE = (
    "Euro area (changing composition) - Key interest rate - Deposit facility - "
    "date of changes (raw data) - Level - Euro, provided by ECB"
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
