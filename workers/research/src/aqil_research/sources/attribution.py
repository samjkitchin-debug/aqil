"""Required source attribution text (deterministic, not LLM-generated)."""


def bls_unemployment_attribution(retrieval_date: str) -> str:
    return (
        "Source: U.S. Bureau of Labor Statistics, series LNS14000000 "
        "(seasonally adjusted unemployment rate). "
        f"Retrieved on {retrieval_date}. "
        "BLS.gov cannot vouch for the data or analyses derived from these data "
        "after the data have been retrieved from BLS.gov. "
        "Figures are presented as returned by BLS without modification."
    )


BLS_LATEST_REVISED_LIMITATION = (
    "These rows are labelled latest-revised retrospective data from BLS. "
    "They reflect values published today, not what was known at an earlier "
    "decision date. They must not be used for genuine point-in-time backtests "
    "until independently archived provider vintages exist."
)

CENSUS_ATTRIBUTION = (
    "Source: U.S. Census Bureau, Economic Indicators — Manufacturers' Shipments, "
    "Inventories, and Orders (M3) advance report, category MDM, data type new orders (NO), "
    "seasonally adjusted. "
    "This product uses the Census Bureau Data API but is not endorsed or certified by "
    "the Census Bureau."
)

FED_SLOOS_ATTRIBUTION = (
    "Source: Board of Governors of the Federal Reserve System, Senior Loan Officer Opinion "
    "Survey on Bank Lending Practices, series SUBLPDCILS_N.Q (net percentage of domestic "
    "banks tightening standards for C&I loans to large and middle-market firms). "
    "Cite the Board as the source."
)


def census_adv_orders_attribution(retrieval_date: str) -> str:
    return f"{CENSUS_ATTRIBUTION} Retrieved on {retrieval_date}."


def fed_sloos_attribution(retrieval_date: str) -> str:
    return f"{FED_SLOOS_ATTRIBUTION} Retrieved on {retrieval_date}."
