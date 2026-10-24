"""Bound BIS global-liquidity series. Values are those the response carried."""

from __future__ import annotations

SOURCE_ID = "bis_gli_usd_credit_nonbanks"
DATASET_ID = "bis.ws_gli.Q.USD.3P.N.A.I.B.USD"
PROVIDER_ID = "bis"
RIGHTS_RECORD_ID = SOURCE_ID

ADAPTER_ID = "bis_gli_usd_credit_nonbanks"
ADAPTER_VERSION = "1.0.0"

SERIES_KEY = "Q.USD.3P.N.A.I.B.USD"
FLOW_REF = "WS_GLI"
DATAFLOW = "BIS:WS_GLI(1.0)"

API_ORIGIN = "https://stats.bis.org"
SERIES_PATH = f"/api/v1/data/{FLOW_REF}/{SERIES_KEY}/all"
ACCESS_URL = f"{API_ORIGIN}{SERIES_PATH}?detail=full"

FREQ_CODE = "Q"
FREQUENCY_LABEL = "Quarterly"
CURR_DENOM = "USD"
BORROWERS_CTY = "3P"
BORROWERS_SECTOR = "N"
LENDERS_SECTOR = "A"
POSITION_TYPE = "I"
INSTRUMENT = "B"
UNIT_MEASURE = "USD"
UNIT_MULT = "6"
GEOGRAPHY = "Outside the United States"
UNIT_TEXT = "US dollar, millions"
OBS_STATUS_OBSERVED = "A"
OBS_CONF_FREE = "F"

TITLE = (
    "USD denominated credit (bank loans & debt securities) to non-bank "
    "borrowers located outside the US"
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
