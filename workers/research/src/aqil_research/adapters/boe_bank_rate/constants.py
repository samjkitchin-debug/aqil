"""Bound Bank of England official Bank Rate. Values are those the response carried."""

from __future__ import annotations

from urllib.parse import urlencode

SOURCE_ID = "boe_official_bank_rate"
DATASET_ID = "boe.iudbedr"
PROVIDER_ID = "boe"
RIGHTS_RECORD_ID = SOURCE_ID

ADAPTER_ID = "boe_official_bank_rate"
ADAPTER_VERSION = "1.0.0"

SERIES_CODE = "IUDBEDR"
SERIES_DESCRIPTION = "Official Bank Rate"
GEOGRAPHY = "United Kingdom"
UNIT_TEXT = "percent"
FREQUENCY_LABEL = "Daily"

API_ORIGIN = "https://www.bankofengland.co.uk"
SERIES_PATH = "/boeapps/database/_iadb-fromshowcolumns.asp"
DATE_FROM = "01/Jan/1975"

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


def access_url() -> str:
    """Current published series. Provisional data (VPD) is not requested."""
    query = urlencode(
        (
            ("csv.x", "yes"),
            ("Datefrom", DATE_FROM),
            ("Dateto", "now"),
            ("SeriesCodes", SERIES_CODE),
            ("CSVF", "CT"),
            ("UsingCodes", "Y"),
        ),
    )
    url = f"{API_ORIGIN}{SERIES_PATH}?{query}"
    if "VPD=" in url or "includeHistory" in url:
        raise RuntimeError("Bank Rate request must not ask for provisional data or history")
    return url


ACCESS_URL = access_url()
