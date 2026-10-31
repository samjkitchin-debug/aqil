"""Replay uses frozen observation evidence only."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from aqil_research.adapters.fixture_ln_csv import FixtureLnCsvAdapter
from aqil_research.contracts.observation import AnalysisMode
from aqil_research.methods.configs import SAHM_PUBLISHED
from aqil_research.methods.registry import SAHM_METHOD_ID, default_method_registry
from aqil_research.methods.stock_watson_1988_fit import ACCEPTED_CONFIG, SPECIFICATION_ID
from aqil_research.persistence.reproduce import (
    scientific_field_report,
    stored_specification,
)
from aqil_research.pipeline.ingestion import ingest_from_adapter
from aqil_research.pipeline.models import ResearchExecutionRequest
from aqil_research.pipeline.orchestrate import (
    cited_observation_snapshot_hash,
    execute_research_run,
)
from aqil_research.sources.rights import load_source_rights
from aqil_research.vintages.store import InMemoryObservationStore, content_snapshot_hash
from aqil_research.workflow.stock_watson_reading import adopt_parameter_version
from fixtures.observation_factory import make_observation, month_start

PROVIDERS = Path(__file__).parent / "fixtures" / "providers"
DECISION_AT = datetime(2025, 2, 1, 12, 0, tzinfo=UTC)


def _run(store: InMemoryObservationStore, run_id: str):
    rights = load_source_rights()
    return execute_research_run(
        ResearchExecutionRequest(
            source_id="bls_cps_unemployment_rate",
            dataset_id="bls.ln.LNS14000000",
            decision_at=DECISION_AT,
            analysis_mode=AnalysisMode.POINT_IN_TIME,
            evaluation_period="2024-12-01",
            method_id=SAHM_METHOD_ID,
            method_config=SAHM_PUBLISHED.model_dump(mode="json"),
            collect=False,
        ),
        store=store,
        rights_records=rights,
        method_registry=default_method_registry(),
        executed_at=DECISION_AT,
        run_id=run_id,
    )


def test_cited_snapshot_ignores_extra_observations_in_store() -> None:
    rights = next(r for r in load_source_rights() if r.source_id == "bls_cps_unemployment_rate")
    adapter = FixtureLnCsvAdapter(PROVIDERS / "unemployment_equivalent.csv")
    store = InMemoryObservationStore()
    ingest_from_adapter(store, adapter, rights)
    first = _run(store, "replay-cited-1")

    store.append(
        make_observation(
            period_start=month_start(2022, 1),
            raw_value="3.5",
            provider_vintage_date=month_start(2022, 2),
        ),
    )

    as_of_rows = store.as_of(
        "bls.ln.LNS14000000",
        DECISION_AT,
        AnalysisMode.POINT_IN_TIME,
    )
    full_hash = content_snapshot_hash(tuple(as_of_rows[p] for p in sorted(as_of_rows)))
    cited_hash = cited_observation_snapshot_hash(store, list(first.observation_ids))

    assert cited_hash == first.input_snapshot_hash
    assert full_hash != cited_hash

    second = _run(store, "replay-cited-2")
    assert second.calculation == first.calculation
    assert second.input_snapshot_hash == first.input_snapshot_hash
    assert second.analytical_payload_hash == first.analytical_payload_hash


def test_same_calculation_different_cited_sets_have_distinct_snapshot_hashes() -> None:
    """Matching Sahm numbers must not collapse distinct provenance snapshots."""
    rights = next(r for r in load_source_rights() if r.source_id == "bls_cps_unemployment_rate")
    adapter = FixtureLnCsvAdapter(PROVIDERS / "unemployment_equivalent.csv")
    store_a = InMemoryObservationStore()
    ingest_from_adapter(store_a, adapter, rights)
    run_a = _run(store_a, "prov-a")

    store_b = InMemoryObservationStore()
    ingest_from_adapter(store_b, adapter, rights)
    run_b = _run(store_b, "prov-b")

    assert run_a.calculation == run_b.calculation
    assert run_a.input_snapshot_hash == run_b.input_snapshot_hash


def test_later_diagnostic_field_does_not_hide_a_numerical_mismatch() -> None:
    differences, notes = scientific_field_report(
        {"break_count": 0, "bic": -7.9},
        {
            "break_count": 1,
            "bic": -7.9,
            "minimum_duration_alternative": {"recession_label": False},
        },
    )
    assert differences == ("break_count",)
    assert any("minimum_duration_alternative" in note for note in notes)


def test_later_diagnostic_field_stays_beside_a_numerical_match() -> None:
    differences, notes = scientific_field_report(
        {"lower_mean_expected_months": 2.0},
        {
            "lower_mean_expected_months": 2.0 + 1e-12,
            "minimum_duration_alternative": {
                "estimated": False,
                "adopted": False,
                "recession_label": False,
            },
        },
    )
    assert differences == ()
    assert any(note == "extra field minimum_duration_alternative" for note in notes)


def test_tolerance_does_not_absorb_a_reported_gap() -> None:
    differences, _notes = scientific_field_report(
        {"log_likelihood": -1590.5374990458229},
        {"log_likelihood": -1590.5371942126505},
    )
    assert differences == ("log_likelihood",)


def test_known_stock_watson_gain_stays_unadopted() -> None:
    adopted = adopt_parameter_version(
        maximum_likelihood_claimed=True,
        new_log_likelihood=-1590.5371942126505,
        stored_log_likelihood=-1590.5374990458229,
    )
    assert adopted is False


def test_preserved_stock_watson_specification_is_a_calculation() -> None:
    from aqil_research.contracts.observation import AnalysisMode
    from aqil_research.pipeline.models import ResearchRun

    stored = ResearchRun(
        run_id="3f8c7611-c2a1-44a0-8c7e-01bebbfe9a8a",
        executed_at=DECISION_AT,
        execution_status="completed",
        dataset_id="fed.g17.IP.B50001.S",
        source_id="federal_reserve_g17_total_ip",
        rights_record_id="federal_reserve_g17_total_ip",
        analysis_mode=AnalysisMode.LATEST_REVISED,
        analysis_type=SPECIFICATION_ID,
        decision_at=DECISION_AT,
        evaluation_period="2026-07-01",
        method_id=SPECIFICATION_ID,
        method_version="0.1.0",
        implementation_hash="0d8ac3fe405bcbb4",
        config_id="sw1988-modern-1997-2026m07",
        config_hash="1c9244eac3ac2da1",
        input_snapshot_hash="stored",
        data_sufficiency="sufficient",
        calculation={
            "loadings_ip_income_sales_payroll": [0.9, 0.5, 0.7, 0.8],
            "factor_ar": [0.2, -0.2],
            "idiosyncratic_ar": [[0.1, 0.0], [0.1, 0.0], [0.1, 0.0], [0.1, 0.0]],
            "idiosyncratic_scale": [0.4, 0.8, 0.6, 0.5],
            "log_likelihood": -1590.5374990458229,
        },
        statistical_interpretation="stored",
        causal_hypothesis="none",
        investment_implication="no_action",
        assumptions=["stored"],
        limitations=["stored"],
        observation_ids=[],
        reproduction={"method_id": SPECIFICATION_ID},
        narrative="stored",
        publication_allowed=False,
    )
    payload = stored_specification(stored, dict(ACCEPTED_CONFIG))
    assert payload["execution_mode"] == "calculate"
    assert payload["config_id"] == "sw1988-modern-1997-2026m07"
    parameters = payload["accepted_parameters"]
    assert parameters["loadings_ip_income_sales_payroll"] == [0.9, 0.5, 0.7, 0.8]
    assert "adopted_parameter_version" not in parameters
    assert stored.config_hash == "1c9244eac3ac2da1"
