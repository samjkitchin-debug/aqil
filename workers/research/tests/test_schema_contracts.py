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


def test_research_insight_matches_schema() -> None:
    from datetime import UTC, datetime

    from aqil_research.adapters.fixture_ln_csv import FixtureLnCsvAdapter
    from aqil_research.contracts.observation import AnalysisMode
    from aqil_research.insight.build_sahm import build_sahm_insight
    from aqil_research.methods.configs import SAHM_PUBLISHED
    from aqil_research.methods.registry import SAHM_METHOD_ID, default_method_registry
    from aqil_research.pipeline.ingestion import ingest_from_adapter
    from aqil_research.pipeline.models import ResearchExecutionRequest
    from aqil_research.pipeline.orchestrate import execute_research_run
    from aqil_research.sources.rights import load_source_rights
    from aqil_research.vintages.store import InMemoryObservationStore

    providers = Path(__file__).parent / "fixtures" / "providers"
    adapter = FixtureLnCsvAdapter(providers / "unemployment_equivalent.csv")
    rights = next(r for r in load_source_rights() if r.source_id == "bls_cps_unemployment_rate")
    store = InMemoryObservationStore()
    ingest_from_adapter(store, adapter, rights)
    run = execute_research_run(
        ResearchExecutionRequest(
            source_id=rights.source_id,
            dataset_id=rights.dataset_id,
            decision_at=datetime(2025, 2, 1, 12, 0, tzinfo=UTC),
            analysis_mode=AnalysisMode.LATEST_REVISED,
            evaluation_period="2024-12-01",
            method_id=SAHM_METHOD_ID,
            method_config=SAHM_PUBLISHED.model_dump(mode="json"),
        ),
        store=store,
        rights_records=load_source_rights(),
        method_registry=default_method_registry(),
        run_id="schema-insight-run",
    )
    insight = build_sahm_insight(run)
    jsonschema.validate(insight.model_dump(mode="json"), _schema("research_insight.v1.json"))
