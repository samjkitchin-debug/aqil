"""Confirmed JOLTS job-openings binding. Codes were read from jt.series on 22 October 2026."""

from __future__ import annotations

SERIES_ID = "JTS000000000000000JOL"
DATASET_ID = "bls.jt.JTS000000000000000JOL"
SOURCE_ID = "bls_jolts_total_nonfarm_job_openings"
RIGHTS_RECORD_ID = SOURCE_ID
PROVIDER_ID = "bls"
ADAPTER_ID = "bls_jolts_jts000000000000000jol"
ADAPTER_VERSION = "1.0.0"

# jt.series: seasonal S, industry 000000, data element JO, rate/level L, from 2000.
SEASONAL_CODE = "S"
INDUSTRY_CODE = "000000"
STATE_CODE = "00"
AREA_CODE = "00000"
SIZECLASS_CODE = "00"
DATAELEMENT_CODE = "JO"
RATELEVEL_CODE = "L"
BEGIN_YEAR = "2000"
UNIT = "thousands"

SERIES_URL = "https://download.bls.gov/pub/time.series/jt/jt.series"
SEASONAL_URL = "https://download.bls.gov/pub/time.series/jt/jt.seasonal"
INDUSTRY_URL = "https://download.bls.gov/pub/time.series/jt/jt.industry"
DATAELEMENT_URL = "https://download.bls.gov/pub/time.series/jt/jt.dataelement"
RATELEVEL_URL = "https://download.bls.gov/pub/time.series/jt/jt.ratelevel"
DATA_URL = "https://download.bls.gov/pub/time.series/jt/jt.data.2.JobOpenings"

FIXTURE_SERIES = "jt.series"
FIXTURE_SEASONAL = "jt.seasonal"
FIXTURE_INDUSTRY = "jt.industry"
FIXTURE_DATAELEMENT = "jt.dataelement"
FIXTURE_RATELEVEL = "jt.ratelevel"
FIXTURE_DATA = "jt.data.2.JobOpenings"

COMPATIBILITY_NOTE = (
    "None of Sahm, SLOOS, Census advance orders, MACRO_CONDITIONS_PANEL, "
    "or PERIOD_LEVEL_CHANGE consume dataset id bls.jt.JTS000000000000000JOL. "
    "Sahm and PERIOD_LEVEL_CHANGE require bls.ln.LNS14000000. "
    "SLOOS requires fed.sloos.SUBLPDCILS_N.Q. "
    "Census advance orders requires census.m3.adv.MDM.NO. "
    "MACRO_CONDITIONS_PANEL requires those three dataset ids."
)
