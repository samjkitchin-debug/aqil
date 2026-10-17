import json
from pathlib import Path

import jsonschema
import pytest

from aqil_research.forward.horizon import build_forward_horizon_bundle


def test_forward_horizon_matches_schema() -> None:
    schema_path = (
        Path(__file__).resolve().parents[3] / "docs" / "schemas" / "forward_horizon.v1.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    bundle = build_forward_horizon_bundle()
    jsonschema.validate(bundle, schema)
    assert bundle["data_mode"] == "mixed"
    events = {event["event_id"]: event for event in bundle["events"]}
    msft = events["event:fixture:msft:fy26q2:earnings"]
    fomc = events["event:verified:fed:fomc:2025-09-17"]
    assert msft["schedule_evidence"] == "synthetic_demonstration"
    assert msft["materiality_basis"] == "calculated"
    assert fomc["schedule_evidence"] == "verified_schedule"
    assert fomc["materiality"] == "insufficient_evidence"
    assert fomc["materiality_basis"] == "insufficient_evidence"
    assert fomc["interpretation_status"] == "unverified"
    etf = bundle["etfs"][0]
    assert etf["identity_evidence"] == "verified_instrument_identity"
    assert etf["holdings_evidence"] == "synthetic_demonstration"
    assert bundle["scenarios"][0]["evidence_class"] == "synthetic_demonstration"
    assert bundle["scenarios"][0]["record_source"] == "fixture"
    assert bundle["outcomes"][0]["scenario_id"] == bundle["scenarios"][0]["scenario_id"]


def test_schema_rejects_fixture_event_labelled_verified() -> None:
    schema_path = (
        Path(__file__).resolve().parents[3] / "docs" / "schemas" / "forward_horizon.v1.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    bundle = build_forward_horizon_bundle()
    bundle["events"][0]["schedule_evidence"] = "verified_schedule"
    bundle["events"][0]["is_fixture"] = True
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bundle, schema)
