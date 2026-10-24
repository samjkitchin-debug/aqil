"""Bound DOSM industrial production index. The level is the absolute index, not a growth rate."""

from __future__ import annotations

SOURCE_ID = "dosm_ipi_abs"
DATASET_ID = "dosm.ipi.abs"
PROVIDER_ID = "dosm"
RIGHTS_RECORD_ID = SOURCE_ID

ADAPTER_ID = "dosm_ipi_abs"
ADAPTER_VERSION = "1.0.0"

SERIES_KEY = "abs"
LEVEL_COLUMN = "index"
SA_COLUMN = "index_sa"
UNIT_TEXT = "index, 2015 = 100"
FREQUENCY_LABEL = "Monthly"
GEOGRAPHY = "MY"
SEASONAL_ADJUSTMENT_LABEL = "not seasonally adjusted"
VINTAGE_CLASS = "latest_revised"
GROWTH_SERIES = frozenset({"growth_yoy", "growth_mom"})

API_ORIGIN = "https://storage.dosm.gov.my"
SERIES_PATH = "/ipi/ipi.csv"
ACCESS_URL = f"{API_ORIGIN}{SERIES_PATH}"

METHOD_COMPATIBILITY_NOTE = (
    "None of Sahm, SLOOS, Census advance orders, MACRO_CONDITIONS_PANEL, "
    "or PERIOD_LEVEL_CHANGE consume this dataset id. "
    "Sahm requires bls.ln.LNS14000000. "
    "SLOOS requires fed.sloos.SUBLPDCILS_N.Q. "
    "Census advance orders requires census.m3.adv.MDM.NO. "
    "MACRO_CONDITIONS_PANEL requires those three dataset ids. "
    "PERIOD_LEVEL_CHANGE requires bls.ln.LNS14000000."
)
