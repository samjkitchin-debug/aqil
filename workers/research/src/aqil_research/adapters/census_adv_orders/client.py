"""Census Bureau EITS M3 advance API client (optional API key)."""

from __future__ import annotations

import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

# Documented timeseries endpoint for the advance M3 release.
# Low-volume access does not require a key; a key may be supplied for higher quotas.
CENSUS_M3_ADV_BASE = "https://api.census.gov/data/timeseries/eits/m3/adv"


def fetch_mdm_no_timeseries() -> list[list[str]]:
    params = {
        "get": "cell_value,time,category_code,data_type_code,seasonally_adj",
        "category_code": "MDM",
        "data_type_code": "NO",
        "seasonally_adj": "yes",
        "for": "us:*",
    }
    api_key = os.environ.get("CENSUS_API_KEY", "").strip()
    if api_key:
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
