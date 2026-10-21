"""Census Bureau advance durable-goods API client.

The dataset is ``timeseries/eits/advm3``. Census requires a key for every
Data API query. A missing key is refused here, before any request.
"""

from __future__ import annotations

import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

# Current documented dataset. The older /timeseries/eits/m3/adv path now 302s.
CENSUS_M3_ADV_BASE = "https://api.census.gov/data/timeseries/eits/advm3"


class CensusKeyRequired(RuntimeError):
    """The Census Data API will not answer without a key."""


def fetch_mdm_no_timeseries() -> list[list[str]]:
    params = {
        "get": "cell_value,time,category_code,data_type_code,seasonally_adj",
        "category_code": "MDM",
        "data_type_code": "NO",
        "seasonally_adj": "yes",
        "for": "us:*",
    }
    api_key = os.environ.get("CENSUS_API_KEY", "").strip()
    if not api_key:
        raise CensusKeyRequired(
            "CENSUS_API_KEY is not set. Census requires a key for every Data API "
            "query. No request was sent.",
        )
    params["key"] = api_key
    url = f"{CENSUS_M3_ADV_BASE}?{urlencode(params)}"
    request = Request(
        url,
        headers={"User-Agent": "AqilResearch/1.0 (macro research; contact: founder)"},
    )
    try:
        with urlopen(request, timeout=60) as response:
            body = response.read().decode("utf-8")
    except (HTTPError, URLError, TimeoutError) as exc:
        raise RuntimeError(f"Census M3 advance fetch failed: {exc}") from exc
    payload = json.loads(body)
    if not isinstance(payload, list):
        raise ValueError("Census API returned non-list JSON")
    return payload
