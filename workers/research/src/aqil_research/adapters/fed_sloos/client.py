"""Optional live fetch for SLOOS SUBLPDCILS_N.Q (Board public data)."""

from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from aqil_research.adapters.fed_sloos.parse import SERIES_ID

# Board Data Download preformatted package for the Senior Loan Officer Survey.
# No API key is documented for this public CSV/JSON export path.
SLOOS_JSON_URL = (
    "https://www.federalreserve.gov/data/sloos/sloos-series.json"
)


def fetch_sloos_bundle() -> dict[str, object]:
    """Fetch the published SLOOS JSON bundle and extract SUBLPDCILS_N.Q rows."""
    request = Request(
        SLOOS_JSON_URL,
        headers={"User-Agent": "AqilResearch/1.0 (macro research; contact: founder)"},
    )
    try:
        with urlopen(request, timeout=60) as response:
            body = response.read().decode("utf-8")
    except (HTTPError, URLError, TimeoutError) as exc:
        raise RuntimeError(f"SLOOS fetch failed: {exc}") from exc

    payload = json.loads(body)
    if isinstance(payload, dict) and "observations" in payload:
        if str(payload.get("series_id", SERIES_ID)) != SERIES_ID:
            payload = _extract_series(payload, SERIES_ID)
        return payload
    if isinstance(payload, list):
        return _normalize_list_payload(payload, SERIES_ID)
    raise ValueError("unrecognised SLOOS JSON shape from Board feed")


def _extract_series(payload: dict[str, object], series_id: str) -> dict[str, object]:
    series_list = payload.get("series")
    if isinstance(series_list, list):
        for entry in series_list:
            if isinstance(entry, dict) and str(entry.get("series_id")) == series_id:
                return {
                    "series_id": series_id,
                    "observations": entry.get("observations", []),
                }
    raise ValueError(f"series {series_id} not found in SLOOS bundle")


def _normalize_list_payload(rows: list[object], series_id: str) -> dict[str, object]:
    observations: list[dict[str, object]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        if str(row.get("series_id", series_id)) != series_id:
            continue
        observations.append(row)
    if not observations:
        raise ValueError(f"no rows for {series_id}")
    return {"series_id": series_id, "observations": observations}
