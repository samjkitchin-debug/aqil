import json
from pathlib import Path

import jsonschema

from aqil_research.forward.horizon import build_forward_horizon_bundle


def test_forward_horizon_matches_schema() -> None:
    schema_path = (
        Path(__file__).resolve().parents[3] / "docs" / "schemas" / "forward_horizon.v1.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    bundle = build_forward_horizon_bundle()
    jsonschema.validate(bundle, schema)
    assert bundle["data_mode"] == "mixed"
    assert any(e["event_id"].startswith("event:fixture:") for e in bundle["events"])
