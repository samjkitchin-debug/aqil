"""Synthesis compares stored readings and does not invent a score."""

from aqil_research.methods.macro_reading_synthesis import (
    MacroReadingInput,
    build_synthesis_run,
    synthesize_macro_readings,
)


def _labour() -> MacroReadingInput:
    return MacroReadingInput(
        method_id="LABOUR_MARKET_CONDITIONS",
        sufficiency="sufficient",
        missing_reason=None,
        run_id="labour-run",
        calculation={
            "series": [
                {
                    "dataset_id": "bls.ln.LNS14000000",
                    "latest_period": "2026-09-01",
                    "level": "4.2",
                    "unit": "percent",
                    "observation_id": "ln-latest",
                    "rank": 10,
                    "history_count": 40,
                    "twelve_month_change": {
                        "window_start": "2025-09-01",
                        "window_end": "2026-09-01",
                        "start_observation_id": "ln-earlier",
                        "end_observation_id": "ln-latest",
                        "change_percentage_points": "-0.10",
                    },
                },
                {
                    "dataset_id": "bls.ce.CES0000000001",
                    "latest_period": "2026-09-01",
                    "level": "1000",
                    "unit": "thousands",
                    "observation_id": "ce-latest",
                    "rank": 20,
                    "history_count": 50,
                    "twelve_month_change": {
                        "window_start": "2025-09-01",
                        "window_end": "2026-09-01",
                        "start_observation_id": "ce-earlier",
                        "end_observation_id": "ce-latest",
                        "change_thousands": "10",
                        "percent_change": "1.00",
                    },
                },
                {
                    "dataset_id": "bls.jt.JTS000000000000000JOL",
                    "latest_period": "2026-08-01",
                    "level": "7000",
                    "unit": "thousands",
                    "observation_id": "jt-latest",
                    "rank": 5,
                    "history_count": 30,
                    "twelve_month_change": {
                        "window_start": "2025-08-01",
                        "window_end": "2026-08-01",
                        "start_observation_id": "jt-earlier",
                        "end_observation_id": "jt-latest",
                        "change_thousands": "-100",
                        "percent_change": "-1.50",
                    },
                },
            ],
            "joint": {
                "latest_common_period": "2026-08-01",
                "twelve_month_change": {
                    "window_start": "2025-08-01",
                    "window_end": "2026-08-01",
                },
            },
        },
    )


def _prices() -> MacroReadingInput:
    return MacroReadingInput(
        method_id="PRICES_AND_POLICY",
        sufficiency="sufficient",
        missing_reason=None,
        run_id="prices-run",
        calculation={
            "cpi_u": {
                "period": "2026-09-01",
                "comparison_period": "2025-09-01",
                "twelve_month_percent_change": "3.0000",
                "comparison_index_level": "300",
                "index_level": "309",
                "unit": "1982-84=100",
                "comparison_observation_id": "cpi-earlier",
                "observation_id": "cpi-later",
                "rank": 8,
                "values_strictly_below": 7,
            },
            "federal_funds": {
                "period": "2026-09-01",
                "prior_period": "2026-08-01",
                "level_percent_per_year": "3.50",
                "prior_level_percent_per_year": "3.75",
                "one_month_change_percentage_points": "-0.2500",
                "observation_id": "funds-latest",
                "prior_observation_id": "funds-prior",
                "rank": 4,
                "values_strictly_below": 3,
            },
            "treasury_10_year": {
                "period": "2026-09-01",
                "prior_period": "2026-08-01",
                "level_percent_per_year": "4.25",
                "prior_level_percent_per_year": "4.15",
                "one_month_change_percentage_points": "0.1000",
                "observation_id": "yield-latest",
                "prior_observation_id": "yield-prior",
                "rank": 6,
                "values_strictly_below": 5,
            },
        },
    )


def test_synthesis_states_agreement_divergence_and_keeps_series_separate() -> None:
    synthesis = synthesize_macro_readings(
        (_labour(), _prices(), _insufficient_production(), _insufficient_credit()),
        production_endpoints={"latest": "ip-latest", "earlier": "ip-earlier"},
    )
    text = " ".join(
        [
            synthesis.summary,
            *synthesis.cited_changes,
            *synthesis.limitations,
            *synthesis.agreements,
            *synthesis.divergences,
            *synthesis.stale_inputs,
        ],
    )

    assert synthesis.sufficiency == "sufficient"
    assert "The reading is internal." in synthesis.summary
    assert "No composite score is calculated." in text
    assert (
        "Unemployment, Payrolls, CPI-U, Federal funds, and 10-year yield share September 2026"
        in synthesis.summary
    )
    assert "Job openings August 2026" in synthesis.summary
    assert "Joint labour month August 2026" in synthesis.summary
    assert "Euro-area HICP is excluded and ends in December 2025." in text
    assert "Their difference is not calculated." in text
    assert "No real rate is calculated." in text
    assert "not a GDP figure" in text
    assert "not a cause" in text
    assert "0.75" not in text
    assert "near-term forward" not in text
    assert "The prices reading" not in synthesis.summary
    assert "The production reading is insufficient" in synthesis.summary
    assert "The credit reading is insufficient" in synthesis.summary
    assert any("Unemployment was 4.2 percent" in line for line in synthesis.cited_changes)
    assert "ln-latest" in synthesis.observation_ids
    assert "cpi-later" in synthesis.observation_ids
    assert "spread" not in text.lower()
    assert "October 2025 is absent" in text
    assert "H.15 seasonal adjustment is unknown." in text
    assert "not a vintage panel" in text
    assert synthesis.calculation()["composite_score"] is None


def test_synthesis_run_stays_unpublished() -> None:
    synthesis = synthesize_macro_readings((_labour(), _prices()))
    run = build_synthesis_run(
        synthesis,
        dataset_id="bls.ln.LNS14000000",
        source_id="bls_cps_unemployment_rate",
        input_dataset_ids=["bls.ln.LNS14000000"],
        evaluation_period="2026-09-01",
        run_id="synthesis-run",
    )
    assert run.publication_allowed is False
    assert run.method_id == "MACRO_READING_SYNTHESIS"
    assert run.investment_implication == "no_action"
    assert run.causal_hypothesis == "No causal mechanism is established."


def _insufficient_production() -> MacroReadingInput:
    return MacroReadingInput(
        method_id="INDUSTRIAL_PRODUCTION_ACTIVITY",
        sufficiency="insufficient",
        missing_reason="missing endpoint for window ending 2026-09-01",
        calculation=None,
        run_id="production-run",
    )


def _insufficient_credit() -> MacroReadingInput:
    return MacroReadingInput(
        method_id="CREDIT_STANDARDS_AND_VOLUMES",
        sufficiency="insufficient",
        missing_reason="no SLOOS observation on or before 2026-10-07",
        calculation=None,
        run_id="credit-run",
    )
