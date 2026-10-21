"""Unchanged SLOOS values keep their identity. A changed value does not."""

from datetime import UTC, datetime

from aqil_research.adapters.fed_sloos.parse import parse_sloos_payload
from aqil_research.adapters.fed_sloos.stability import StoredSloosPoint, stabilise_sloos_vintages
from aqil_research.contracts.observation import (
    AnalysisMode,
    AvailabilityPrecision,
    SeriesProvenance,
)
from aqil_research.methods.configs import SLOOS_CIL_PUBLISHED
from aqil_research.methods.registry import default_method_registry
from aqil_research.methods.sloos_cil import SLOOS_CIL_METHOD_ID
from aqil_research.pipeline.models import ResearchExecutionRequest
from aqil_research.pipeline.orchestrate import execute_research_run
from aqil_research.sources.rights import load_source_rights
from aqil_research.vintages.store import InMemoryObservationStore

RETRIEVED = datetime(2026, 10, 22, 8, 0, tzinfo=UTC)


def test_unchanged_value_reuses_the_stored_identity() -> None:
    payload = {
        "series_id": "SUBLPDCILS_N.Q",
        "observations": [{"period": "2026-Q3", "value": "11.8"}],
    }
    first = stabilise_sloos_vintages(payload, (), RETRIEVED)
    parsed = parse_sloos_payload(
        first,
        adapter_version="test",
        retrieved_at=RETRIEVED,
        collection_vintage_date=RETRIEVED.date(),
    )
    stored = parsed.observations[0]
    assert stored.series_provenance == SeriesProvenance.LATEST_REVISED
    assert stored.availability_precision == AvailabilityPrecision.UNKNOWN
    assert stored.source_release_at == RETRIEVED

    prior = StoredSloosPoint(
        period_start=stored.period_start,
        observation_id=stored.observation_id,
        raw_value=stored.raw_value,
        provider_vintage_date=stored.provider_vintage_date,
        source_release_at=stored.source_release_at,
        retrieved_at=stored.retrieved_at,
    )
    later = datetime(2026, 10, 23, 8, 0, tzinfo=UTC)
    repeat = stabilise_sloos_vintages(payload, (prior,), later)
    assert repeat["observations"][0]["observation_id"] == stored.observation_id
    assert repeat["observations"][0]["source_release_at"] == RETRIEVED.isoformat()

    changed = stabilise_sloos_vintages(
        {
            "series_id": "SUBLPDCILS_N.Q",
            "observations": [{"period": "2026-Q3", "value": "12.4"}],
        },
        (prior,),
        later,
    )
    assert changed["observations"][0]["observation_id"] != stored.observation_id


def test_missing_sloos_observation_stays_unpublished() -> None:
    request = ResearchExecutionRequest(
        source_id="federal_reserve_sloos_cil",
        dataset_id="fed.sloos.SUBLPDCILS_N.Q",
        decision_at=RETRIEVED,
        analysis_mode=AnalysisMode.LATEST_REVISED,
        evaluation_period="2026-10-01",
        method_id=SLOOS_CIL_METHOD_ID,
        method_config=dict(SLOOS_CIL_PUBLISHED),
        collect=False,
    )
    run = execute_research_run(
        request,
        store=InMemoryObservationStore(),
        rights_records=load_source_rights(),
        method_registry=default_method_registry(),
        executed_at=RETRIEVED,
    )
    assert run.execution_status == "completed_insufficient"
    assert run.publication_allowed is False
    assert run.investment_implication == "insufficient_evidence"
    assert run.missing_data_reason == "no SLOOS observation on or before 2026-10-01"
