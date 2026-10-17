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
