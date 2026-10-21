"""A missing Census key must not become a network request."""

import pytest

from aqil_research.adapters.census_adv_orders.client import (
    CensusKeyRequired,
    fetch_mdm_no_timeseries,
)


def test_missing_census_key_does_not_call_the_api(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CENSUS_API_KEY", raising=False)
    with pytest.raises(CensusKeyRequired, match="No request was sent"):
        fetch_mdm_no_timeseries()
