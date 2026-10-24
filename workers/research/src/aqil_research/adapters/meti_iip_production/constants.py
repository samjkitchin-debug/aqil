"""Bound METI industrial production series. Values are those the workbook carried."""

from __future__ import annotations

SOURCE_ID = "meti_iip_production_sa"
DATASET_ID = "meti.iip.b2020.production.sa.m.1000000000"
PROVIDER_ID = "meti"
RIGHTS_RECORD_ID = SOURCE_ID

ADAPTER_ID = "meti_iip_production_sa"
ADAPTER_VERSION = "1.0.0"

# 品目番号 on the production sheet. The per-month 時系列コード is a column check, not this key.
SERIES_KEY = "1000000000"
SERIES_NAME = "鉱工業"
WEIGHT_TEXT = "10000"
SHEET_NAME = "生産"
TITLE = "項目：総合季節調整済指数【月次】付加価値額生産（2020＝100.0）"

API_ORIGIN = "https://www.meti.go.jp"
WORKBOOK_PATH = "/statistics/tyo/iip/xls/b2020_gsm1j.xlsx"
ACCESS_URL = f"{API_ORIGIN}{WORKBOOK_PATH}"

PAGE_URL = "https://www.meti.go.jp/statistics/tyo/iip/b2020_result-2.html"
TERMS_URL = "https://www.meti.go.jp/main/rules.html"
LICENCE_URL = "https://www.digital.go.jp/resources/open_data/public_data_license_v1.0"

GEOGRAPHY = "JP"
UNIT_TEXT = "index, 2020 = 100"
SEASONAL_ADJUSTMENT_LABEL = "Seasonally adjusted"
FREQUENCY_LABEL = "Monthly"
VINTAGE_CLASS = "latest_revised"

METHOD_COMPATIBILITY_NOTE = (
    "None of Sahm, labour, prices, industrial production, credit, SLOOS, Census, "
    "or MACRO_CONDITIONS_PANEL consume this dataset id. "
    "Sahm requires bls.ln.LNS14000000. "
    "Labour requires bls.ln.LNS14000000, bls.ce.CES0000000001, "
    "and bls.jt.JTS000000000000000JOL. "
    "Prices requires bls.cu.CUSR0000SA0, fed.h15.RIFSPFF_N.M, and fed.h15.RIFLGFCY10_N.M. "
    "Industrial production requires fed.g17.IP.B50001.S. "
    "Credit requires fed.sloos.SUBLPDCILS_N.Q and fed.h8.B1001NCBA. "
    "SLOOS requires fed.sloos.SUBLPDCILS_N.Q. "
    "Census requires census.m3.adv.MDM.NO. "
    "MACRO_CONDITIONS_PANEL requires bls.ln.LNS14000000, fed.sloos.SUBLPDCILS_N.Q, "
    "and census.m3.adv.MDM.NO."
)
