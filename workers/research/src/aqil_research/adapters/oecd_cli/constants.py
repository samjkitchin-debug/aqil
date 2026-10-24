"""Bound OECD composite leading indicator. Values are those the response carried."""

from __future__ import annotations

SOURCE_ID = "oecd_cli_g20"
DATASET_ID = "oecd.stes.DF_CLI.G20.M.LI.IX._Z.AA.IX._Z.H"
PROVIDER_ID = "oecd"
RIGHTS_RECORD_ID = SOURCE_ID

ADAPTER_ID = "oecd_cli_g20"
ADAPTER_VERSION = "1.0.0"

SERIES_KEY = "G20.M.LI.IX._Z.AA.IX._Z.H"
FLOW = "OECD.SDD.STES,DSD_STES@DF_CLI,4.1"
STRUCTURE_ID = "OECD.SDD.STES:DSD_STES@DF_CLI(4.1)"
STRUCTURE_NAME = "Composite leading indicators"

API_ORIGIN = "https://sdmx.oecd.org"
SERIES_PATH = f"/public/rest/data/{FLOW}/{SERIES_KEY}"
ACCESS_URL = f"{API_ORIGIN}{SERIES_PATH}?format=csvfilewithlabels"

REF_AREA = "G20"
GEOGRAPHY = "G20"
FREQ_CODE = "M"
FREQUENCY_LABEL = "Monthly"
MEASURE = "LI"
MEASURE_LABEL = "Composite leading indicator (CLI)"
UNIT_MEASURE = "IX"
UNIT_LABEL = "Index"
ACTIVITY = "_Z"
ADJUSTMENT = "AA"
ADJUSTMENT_LABEL = "Amplitude adjusted"
TRANSFORMATION = "IX"
TIME_HORIZON = "_Z"
METHODOLOGY = "H"
METHODOLOGY_LABEL = "OECD harmonised"
UNIT_MULT = "0"
UNIT_TEXT = "Index, amplitude adjusted"
OBS_STATUS_OBSERVED = "A"
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
