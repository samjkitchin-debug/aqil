import json
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from aqil_research.contracts.method_card import MethodCard
from aqil_research.contracts.observation import AnalysisMode
from aqil_research.editorial.claim_verifier import (
    ClaimVerificationError,
    verify_claim_for_publication,
)
from aqil_research.methods.configs import SAHM_PUBLISHED
from aqil_research.methods.sahm import SAHM_METHOD_VERSION
from aqil_research.pipeline.models import ResearchRunRequest
from aqil_research.pipeline.run_research import run_research
from aqil_research.vintages.store import InMemoryObservationStore, content_snapshot_hash
from fixtures.observation_factory import (
    DATASET_ID,
    constant_unemployment_series,
    make_observation,
    month_start,
)


def test_method_card_fixture_validates() -> None:
    path = Path(__file__).parent / "fixtures" / "sahm_method_card.v1.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    card = MethodCard.model_validate(payload)
    assert card.method_id == "SAHM_UNEMPLOYMENT_GAP"
    assert card.evidence_stage.value == "implemented"


def test_end_to_end_research_result_on_synthetic_data() -> None:
    base = constant_unemployment_series(month_start(2023, 10), 12, "4.0")
    spike = (
        make_observation(
            period_start=month_start(2024, 10),
            raw_value="4.5",
            provider_vintage_date=date(2024, 11, 5),
        ),
        make_observation(
            period_start=month_start(2024, 11),
            raw_value="4.5",
            provider_vintage_date=date(2024, 12, 5),
        ),
        make_observation(
            period_start=month_start(2024, 12),
            raw_value="4.5",
            provider_vintage_date=date(2025, 1, 5),
        ),
    )
    store = InMemoryObservationStore()
    store.append_many(base + spike)

    decision_at = datetime(2025, 2, 1, 12, 0, tzinfo=UTC)
    request = ResearchRunRequest(
        dataset_id=DATASET_ID,
        decision_at=decision_at,
        analysis_mode=AnalysisMode.POINT_IN_TIME,
        evaluation_period="2024-12-01",
        sahm_config=SAHM_PUBLISHED,
        method_version=SAHM_METHOD_VERSION,
    )
    result = run_research(store, request)
    assert result.data_sufficiency == "sufficient"
    assert result.calculation is not None
    assert result.calculation["triggered"] is True
    assert result.market_pricing == "unknown"
    assert result.investment_implication == "no_action"
    assert result.publication_allowed is False
    assert "NBER" in result.narrative

    with pytest.raises(ClaimVerificationError):
        verify_claim_for_publication(result.model_dump())


def test_historical_replay_snapshot_hash_stable() -> None:
    rows = constant_unemployment_series(month_start(2023, 10), 15, "4.0")
    store = InMemoryObservationStore()
    store.append_many(rows)
    decision_at = datetime(2025, 1, 15, tzinfo=UTC)
    first = store.as_of(DATASET_ID, decision_at, AnalysisMode.POINT_IN_TIME)
    first_hash = content_snapshot_hash(tuple(first[p] for p in sorted(first)))
    store.append(
        make_observation(
            period_start=month_start(2024, 12),
            raw_value="9.9",
            provider_vintage_date=date(2025, 6, 1),
        ),
    )
    second = store.as_of(DATASET_ID, decision_at, AnalysisMode.POINT_IN_TIME)
    second_hash = content_snapshot_hash(tuple(second[p] for p in sorted(second)))
    assert first_hash == second_hash
