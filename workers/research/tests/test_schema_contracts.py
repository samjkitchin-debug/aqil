"""JSON Schema contract validation for representative fixtures."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import jsonschema
import pytest

from aqil_research.contracts.method_card import MethodCard
from fixtures.observation_factory import make_observation, month_start

REPO_ROOT = Path(__file__).resolve().parents[3]
SCHEMAS = REPO_ROOT / "docs" / "schemas"


def _schema(name: str) -> dict:
    return json.loads((SCHEMAS / name).read_text(encoding="utf-8"))


def test_observation_valid_fixture_matches_schema() -> None:
    row = make_observation(
        period_start=month_start(2024, 1),
        raw_value="3.7",
        provider_vintage_date=date(2024, 2, 5),
    )
    payload = row.model_dump(mode="json", exclude_none=True)
    jsonschema.validate(payload, _schema("observation.v1.json"))


def test_observation_invalid_fixture_rejected() -> None:
    row = make_observation(
        period_start=month_start(2024, 1),
        raw_value="3.7",
        provider_vintage_date=date(2024, 2, 5),
    )
    payload = row.model_dump(mode="json", exclude_none=True)
    payload.pop("observation_id")
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(payload, _schema("observation.v1.json"))


def test_method_card_fixture_matches_schema() -> None:
    path = Path(__file__).parent / "fixtures" / "sahm_method_card.v1.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    jsonschema.validate(payload, _schema("method_card.v1.json"))
    MethodCard.model_validate(payload)


def test_source_claim_schema_rejects_incomplete_payload() -> None:
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate({"schema_version": "1.0"}, _schema("source_claim.v1.json"))
