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


def test_sourced_update_schema_matches_model_and_mirror() -> None:
    from datetime import UTC, datetime

    from aqil_research.contracts.sourced_update import SourcedUpdate, sourced_update_field_names

    schema = _schema("sourced_update.v1.json")
    mirror = json.loads(
        (REPO_ROOT / "packages" / "contracts" / "schemas" / "sourced_update.v1.json").read_text(
            encoding="utf-8"
        )
    )
    assert mirror == schema
    assert sourced_update_field_names() == tuple(schema["required"])
    assert tuple(SourcedUpdate.model_fields) == tuple(schema["required"])

    row = SourcedUpdate(
        update_id="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        source_id="bls_employment_situation_archive",
        title="Employment situation",
        canonical_url="https://www.bls.gov/news.release/empsit.htm",
        published_at=datetime(2025, 2, 7, 13, 30, tzinfo=UTC),
        retrieved_at=datetime(2025, 2, 7, 14, 0, tzinfo=UTC),
        retrieval_id="11111111-1111-4111-8111-111111111111",
        content_hash="a" * 64,
    )
    payload = row.model_dump(mode="json")
    jsonschema.validate(payload, schema)
    payload["status"] = "inferred"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(payload, schema)


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


def test_macro_event_schema_matches_model_and_mirror() -> None:
    from datetime import UTC, datetime

    from aqil_research.contracts.macro_event import MacroEvent, macro_event_field_names

    schema = _schema("macro_event.v1.json")
    mirror = json.loads(
        (REPO_ROOT / "packages" / "contracts" / "schemas" / "macro_event.v1.json").read_text(
            encoding="utf-8"
        )
    )
    assert mirror == schema
    assert macro_event_field_names() == tuple(schema["required"])
    assert tuple(MacroEvent.model_fields) == tuple(schema["required"])
    row = MacroEvent(
        event_id="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        event_key="ustr_section_301_china_continuation_2026",
        category="trade_policy",
        epistemic_class="confirmed_event",
        claim_scope="policy_action_stated",
        summary="USTR states that the actions remain in effect.",
        country="United States",
        region=None,
        industries=[],
        event_on=date(2026, 8, 23),
        event_dates_stated="6 July 2026 and 23 August 2026",
        indicator_source_ids=["bls_cpi_u_all_items", "federal_reserve_g17_total_ip"],
        channel_note=(
            "CPI-U and industrial production are plausible channels, not a measured effect."
        ),
        surface_on_today=True,
        surface_reason="USTR states that the actions did not terminate and remain in effect.",
        surfaced_at=datetime(2026, 10, 24, 12, 0, tzinfo=UTC),
        record_class="synthetic_fixture",
        investment_implication="no_action",
        evidence=[
            {
                "update_id": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
                "role": "primary",
                "cluster_key": "fr-2026-20510",
            }
        ],
    )
    jsonschema.validate(row.model_dump(mode="json"), schema)
    rejected = row.model_dump(mode="json")
    rejected["evidence"] = []
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(rejected, schema)


def test_structural_theme_schema_rejects_price_as_infrastructure() -> None:
    from aqil_research.contracts.structural_theme import (
        StructuralThemeAssessment,
        structural_theme_field_names,
    )

    schema = _schema("structural_theme_assessment.v1.json")
    mirror = json.loads(
        (
            REPO_ROOT / "packages" / "contracts" / "schemas" / "structural_theme_assessment.v1.json"
        ).read_text(encoding="utf-8")
    )
    assert mirror == schema
    assert structural_theme_field_names() == tuple(schema["required"])
    assert tuple(StructuralThemeAssessment.model_fields) == tuple(schema["required"])
    payload = {
        "schema_version": "1.0",
        "assessment_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        "theme_key": "ai_infrastructure_investment",
        "supersedes_assessment_id": None,
        "real_economy_activity": "Company-wide actual capital expenditure is recorded.",
        "earnings": "Earnings are not established by this filing.",
        "market_prices": "Market prices are not established by this filing.",
        "media_attention": "Media attention is not established by this filing.",
        "publication_allowed": False,
        "record_class": "synthetic_fixture",
        "dimensions": [
            {
                "dimension": "infrastructure_investment",
                "status": "insufficient",
                "measure_kind": "equity_price",
                "explanation": "An equity price is not infrastructure investment evidence.",
                "update_id": None,
                "amount": None,
                "unit": None,
                "period_start": None,
                "period_end": None,
                "reporting_entity": None,
                "filed_at": None,
                "relationship": None,
            }
        ],
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(payload, schema)
