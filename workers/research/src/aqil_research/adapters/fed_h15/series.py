"""The two H.15 monthly series this package is allowed to bind."""

from __future__ import annotations

from dataclasses import dataclass

PACKAGE_URL = "https://www.federalreserve.gov/datadownload/Output.aspx?rel=H15&filetype=zip"
PROVIDER_ID = "federal_reserve_board"
DATASET_CODE = "H15"
SERIES_NAMESPACE = "http://www.federalreserve.gov/structure/compact/H15_H15"
MONTHLY_FREQUENCY = "129"
UNIT_CODE = "Percent:_Per_Year"
UNIT = "percent_per_year"
ND_SENTINEL = "-9999"

METHOD_COMPATIBILITY_NOTE = (
    "None of Sahm, SLOOS, Census advance orders, MACRO_CONDITIONS_PANEL, "
    "or PERIOD_LEVEL_CHANGE consume these dataset ids. "
    "Sahm and PERIOD_LEVEL_CHANGE require bls.ln.LNS14000000. "
    "SLOOS requires fed.sloos.SUBLPDCILS_N.Q. "
    "Census advance orders requires census.m3.adv.MDM.NO. "
    "MACRO_CONDITIONS_PANEL requires those three dataset ids."
)


@dataclass(frozen=True, slots=True)
class H15Series:
    """One monthly Board series. The description is checked against the file."""

    series_name: str
    preview_code: str
    dataset_id: str
    source_id: str
    adapter_id: str
    id_token: str
    long_description: str


FEDERAL_FUNDS = H15Series(
    series_name="RIFSPFF_N.M",
    preview_code="H15/H15/RIFSPFF_N.M",
    dataset_id="fed.h15.RIFSPFF_N.M",
    source_id="federal_reserve_h15_federal_funds_effective",
    adapter_id="fed_h15_rifspff_n_m",
    id_token="ff",
    long_description="Federal funds effective rate",
)

TREASURY_10Y = H15Series(
    series_name="RIFLGFCY10_N.M",
    preview_code="H15/H15/RIFLGFCY10_N.M",
    dataset_id="fed.h15.RIFLGFCY10_N.M",
    source_id="federal_reserve_h15_treasury_10y_constant_maturity",
    adapter_id="fed_h15_riflgfcy10_n_m",
    id_token="cm10",
    long_description=(
        "Market yield on U.S. Treasury securities at 10-year constant maturity, "
        "quoted on investment basis"
    ),
)

SERIES_BY_SOURCE = {
    FEDERAL_FUNDS.source_id: FEDERAL_FUNDS,
    TREASURY_10Y.source_id: TREASURY_10Y,
}
