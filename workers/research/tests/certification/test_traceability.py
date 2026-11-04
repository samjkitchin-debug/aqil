"""Progress counts and the point-in-time gate. No vintage is manufactured."""

from __future__ import annotations

from aqil_research.certification.traceability import (
    EXECUTION_FIELDS,
    SPEC_FIELDS,
    classify_progress,
    missing_fields,
    progress_paragraph,
    shared_rows_are_independent,
)
from aqil_research.certification.vintage_gate import (
    ALFRED_DATASET,
    GDP_SERIES,
    MethodInputs,
    assess_gate5,
)
from aqil_research.long_horizon.spec import FROZEN_PILOT_SPECIFICATION


def test_frozen_specification_keeps_the_trace_fields() -> None:
    assert missing_fields(FROZEN_PILOT_SPECIFICATION, SPEC_FIELDS) == ()
    assert FROZEN_PILOT_SPECIFICATION["macro_vintage_ids"] == []
    assert FROZEN_PILOT_SPECIFICATION["publication_allowed"] is False


def test_progress_counts_do_not_treat_the_catalogue_as_results() -> None:
    counts = classify_progress(
        {
            "candidate_scenario_ids": 618,
            "candidate_signal_ids": 309,
            "succeeded_executions": 6,
            "claims_inconclusive_at_version": 1,
            "claims_rejected_at_version": 0,
            "claims_statistically_supported": 0,
            "claims_economically_useful": 0,
            "claims_forward_validated": 0,
            "candidate_rows_marked_as_results": 0,
            "registered_comparisons": 4,
            "executed_comparisons": 3,
            "refused_comparisons": 1,
            "retrospective_results": 2,
            "point_in_time_results": 0,
            "portfolio_simulations": 1,
            "scientifically_validated_findings": 0,
        }
    )
    assert counts["registered_scenarios"] == 618
    assert counts["portfolio_simulations"] == 1
    assert counts["portfolio_simulations"] != 6
    assert counts["registered_comparisons"] == 4
    assert counts["executed_comparisons"] + counts["refused_comparisons"] == 4
    assert counts["point_in_time_results"] == 0
    assert counts["scientifically_validated_findings"] == 0
    assert counts["scientifically_supported_conclusions"] == 0
    text = progress_paragraph(counts)
    assert text.startswith("Registered scenarios: 618.")
    assert "Portfolio simulations: 1." in text
    assert "Scientifically supported conclusions: 0." in text


def test_shared_prices_are_not_independent_confirmation() -> None:
    rows = [
        {"relation": "shares_dataset", "independent_confirmation": False},
        {"relation": "matched_control", "independent_confirmation": False},
        {"relation": "overlaps_period", "independent_confirmation": False},
    ]
    assert shared_rows_are_independent(rows) is False
    rows[0]["independent_confirmation"] = True
    assert shared_rows_are_independent(rows) is True


def test_an_execution_record_names_the_reproduction_fields() -> None:
    execution = {name: "present" for name in EXECUTION_FIELDS}
    execution["macro_vintage_ids"] = []
    assert missing_fields(execution, EXECUTION_FIELDS) == ()


def _sahm() -> MethodInputs:
    return MethodInputs("SAHM_UNEMPLOYMENT_GAP", ("bls.ln.LNS14000000",), "latest_revised")


def test_real_gdp_vintage_does_not_cover_unemployment() -> None:
    assessment = assess_gate5(
        (_sahm(),),
        archiving={"bls.ln.LNS14000000": "permitted", ALFRED_DATASET: "prohibited"},
        live_provider_vintages=frozenset({GDP_SERIES}),
    )
    assert assessment.eligible_method_ids == ()
    assert assessment.gate6_allowed is False
    assert assessment.gdp_is_required_by_any_method is False
    assert GDP_SERIES in (assessment.blocker or "")


def test_a_latest_revised_declaration_is_not_relabelled_when_a_vintage_exists() -> None:
    assessment = assess_gate5(
        (_sahm(),),
        archiving={"bls.ln.LNS14000000": "permitted", ALFRED_DATASET: "prohibited"},
        live_provider_vintages=frozenset({"bls.ln.LNS14000000"}),
        not_original={},
    )
    assert assessment.eligible_method_ids == ()
    assert assessment.gate6_allowed is False


def test_one_declared_vintage_method_would_open_gate_6() -> None:
    method = MethodInputs("FICTIONAL_UNEMPLOYMENT", ("bls.ln.LNS14000000",), "provider_vintage")
    assessment = assess_gate5(
        (method,),
        archiving={"bls.ln.LNS14000000": "permitted", ALFRED_DATASET: "prohibited"},
        live_provider_vintages=frozenset({"bls.ln.LNS14000000"}),
        not_original={},
    )
    assert assessment.eligible_method_ids == ("FICTIONAL_UNEMPLOYMENT",)
    assert assessment.blocker is None
    assert assessment.gate6_allowed is True


def test_partial_coverage_and_alfred_stay_blocked() -> None:
    labour = MethodInputs(
        "LABOUR_MARKET_CONDITIONS",
        ("bls.ln.LNS14000000", "bls.ce.CES0000000001", "bls.jt.JTS000000000000000JOL"),
        "provider_vintage",
    )
    partial = assess_gate5(
        (labour,),
        archiving={
            "bls.ln.LNS14000000": "permitted",
            "bls.ce.CES0000000001": "permitted",
            "bls.jt.JTS000000000000000JOL": "permitted",
            ALFRED_DATASET: "prohibited",
        },
        live_provider_vintages=frozenset({"bls.ln.LNS14000000"}),
        not_original={},
    )
    assert partial.eligible_method_ids == ()
    alfred = MethodInputs("ALFRED_COPY", (ALFRED_DATASET,), "provider_vintage")
    refused = assess_gate5(
        (alfred,),
        archiving={ALFRED_DATASET: "prohibited"},
        live_provider_vintages=frozenset({ALFRED_DATASET}),
        not_original={},
    )
    assert refused.eligible_method_ids == ()
    assert refused.alfred_historical_archiving == "prohibited"
