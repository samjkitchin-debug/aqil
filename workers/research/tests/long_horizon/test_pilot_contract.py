"""The frozen window and the specification contract."""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from pathlib import Path

import jsonschema

from aqil_research.long_horizon.pilot import run_frozen_comparison
from aqil_research.long_horizon.simulator import PriceBar
from aqil_research.long_horizon.spec import (
    FROZEN_PILOT_SPECIFICATION,
    frozen_specification_hash,
)
from aqil_research.long_horizon.status import FORBIDDEN_FOR_CATEGORY_C

ROOT = Path(__file__).resolve().parents[4]


def test_specification_hash_is_stable_and_category_c() -> None:
    assert frozen_specification_hash() == frozen_specification_hash()
    assert FROZEN_PILOT_SPECIFICATION["category"] == "C"
    assert FROZEN_PILOT_SPECIFICATION["not_macroeconomic_investment_intelligence"] is True
    assert FROZEN_PILOT_SPECIFICATION["macro_vintage_ids"] == []
    assert FROZEN_PILOT_SPECIFICATION["publication_allowed"] is False
    forbidden = set(FROZEN_PILOT_SPECIFICATION["acceptance_criteria"]["forbidden_statuses"])
    assert forbidden == set(FORBIDDEN_FOR_CATEGORY_C)
    schema_path = ROOT / "docs" / "schemas" / "long_horizon_experiment.v1.json"
    mirror_path = ROOT / "packages" / "contracts" / "schemas" / "long_horizon_experiment.v1.json"
    schema_bytes = schema_path.read_bytes()
    assert schema_bytes == mirror_path.read_bytes()
    schema = json.loads(schema_bytes)
    jsonschema.validate(FROZEN_PILOT_SPECIFICATION, schema)


def test_overlap_starts_at_the_later_stored_listing() -> None:
    early = date(2016, 11, 3)
    late = date(2019, 7, 25)
    prices = {
        "CSPX": {
            early: PriceBar(early, Decimal("200"), "USD"),
            late: PriceBar(late, Decimal("210"), "USD"),
        },
        "VWRA": {late: PriceBar(late, Decimal("80"), "USD")},
    }
    sessions, contributions, passive, alternative, status = run_frozen_comparison(prices)
    assert sessions == [late]
    assert [item.session for item in contributions] == [late]
    assert passive.snapshots[0].session == late
    assert alternative.snapshots[0].session == late
    assert status == "rejected"
    assert passive.terminal_wealth == alternative.terminal_wealth
