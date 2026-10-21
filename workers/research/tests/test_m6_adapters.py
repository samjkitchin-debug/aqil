"""M6 adapter parse tests (fixtures only)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from aqil_research.adapters.census_adv_orders.parse import parse_census_adv_payload
from aqil_research.adapters.fed_sloos.parse import parse_sloos_payload

FIXTURES = Path(__file__).parent / "fixtures"
RETRIEVED = datetime(2025, 6, 1, 12, 0, tzinfo=UTC)


def test_sloos_treats_na_as_missing_not_zero() -> None:
    payload = json.loads(
        (FIXTURES / "fed_sloos" / "sublpdcils_n_q_bundle.json").read_text(encoding="utf-8"),
    )
    parsed = parse_sloos_payload(
        payload,
        adapter_version="test",
        retrieved_at=RETRIEVED,
        collection_vintage_date=RETRIEVED.date(),
    )
    periods = {obs.period_start.isoformat() for obs in parsed.observations}
    assert "2024-04-01" not in periods  # Q2 n.a. skipped
    zero_rows = [obs for obs in parsed.observations if obs.raw_value == "0.0"]
    assert len(zero_rows) == 1
    assert zero_rows[0].period_start.isoformat() == "2024-10-01"


def test_census_multi_vintage_fixture_parses() -> None:
    payload = json.loads(
        (FIXTURES / "census" / "mdm_no_adv_vintages.json").read_text(encoding="utf-8"),
    )
    vintage = payload["vintages"][1]
    parsed = parse_census_adv_payload(
        vintage["data"],
        adapter_version="test",
        retrieved_at=RETRIEVED,
        collection_vintage_date=RETRIEVED.date(),
        vintage_date=datetime.fromisoformat("2024-09-25").date(),
    )
    assert len(parsed.observations) == 3
    july_rows = [obs for obs in parsed.observations if obs.period_start.month == 7]
    assert len(july_rows) == 1
    assert july_rows[0].raw_value == "510000"
