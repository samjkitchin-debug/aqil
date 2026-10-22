"""Confirmed CE payroll binding. Codes were read from the official files on 22 October 2026."""

from __future__ import annotations

SERIES_ID = "CES0000000001"
DATASET_ID = "bls.ce.CES0000000001"
SOURCE_ID = "bls_ces_total_nonfarm_payrolls"
RIGHTS_RECORD_ID = SOURCE_ID
PROVIDER_ID = "bls"
ADAPTER_ID = "bls_payrolls_ces0000000001"
ADAPTER_VERSION = "1.0.0"

# ce.series: supersector 00, industry 00000000, data type 01, seasonal S.
SUPERSECTOR_CODE = "00"
INDUSTRY_CODE = "00000000"
DATA_TYPE_CODE = "01"
SEASONAL_CODE = "S"
UNIT = "thousands"

SERIES_URL = "https://download.bls.gov/pub/time.series/ce/ce.series"
DATATYPE_URL = "https://download.bls.gov/pub/time.series/ce/ce.datatype"
SEASONAL_URL = "https://download.bls.gov/pub/time.series/ce/ce.seasonal"
DATA_URL = "https://download.bls.gov/pub/time.series/ce/ce.data.00a.TotalNonfarm.Employment"

FIXTURE_SERIES = "ce.series"
FIXTURE_DATATYPE = "ce.datatype"
FIXTURE_SEASONAL = "ce.seasonal"
FIXTURE_DATA = "ce.data.00a.TotalNonfarm.Employment"

COMPATIBILITY_NOTE = (
    "None of Sahm, SLOOS, Census advance orders, MACRO_CONDITIONS_PANEL, "
    "or PERIOD_LEVEL_CHANGE consume dataset id bls.ce.CES0000000001. "
    "Sahm and PERIOD_LEVEL_CHANGE require bls.ln.LNS14000000. "
    "SLOOS requires fed.sloos.SUBLPDCILS_N.Q. "
    "Census advance orders requires census.m3.adv.MDM.NO. "
    "MACRO_CONDITIONS_PANEL requires those three dataset ids."
)
