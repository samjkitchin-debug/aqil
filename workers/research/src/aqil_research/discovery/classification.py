"""Classification of the executable registry. This is not a second method register."""

from __future__ import annotations

from aqil_research.methods.registry import default_method_registry

# Roles are the four names required by the discovery plan.
SPECS: dict[str, dict[str, object]] = {
    "SAHM_UNEMPLOYMENT_GAP": {
        "role": "supporting_indicator",
        "full_sample_look_ahead": False,
        "predictive_status": "retrospective_eligible",
        "reason": "The Sahm gap uses the evaluation month and earlier months only.",
    },
    "PERIOD_LEVEL_CHANGE": {
        "role": "supporting_indicator",
        "full_sample_look_ahead": False,
        "predictive_status": "not_in_catalogue",
        "reason": "A period change is a transform. It is not a separate first-pass signal.",
    },
    "SLOOS_CIL_LENDING_STANDARDS": {
        "role": "supporting_indicator",
        "full_sample_look_ahead": False,
        "predictive_status": "not_in_catalogue",
        "reason": "The lending-standards reading is not in the first-pass ETF family.",
    },
    "CENSUS_ADV_DURABLE_ORDERS": {
        "role": "unavailable",
        "full_sample_look_ahead": False,
        "predictive_status": "unavailable",
        "reason": "No Census advance-orders observations are stored.",
    },
    "MACRO_CONDITIONS_PANEL": {
        "role": "supporting_indicator",
        "full_sample_look_ahead": False,
        "predictive_status": "not_in_catalogue",
        "reason": "The conditions panel is a reading, not a first-pass ETF signal.",
    },
    "LABOUR_MARKET_CONDITIONS": {
        "role": "supporting_indicator",
        "full_sample_look_ahead": False,
        "predictive_status": "not_in_catalogue",
        "reason": "The labour-market reading is not in the first-pass ETF family.",
    },
    "PRICES_AND_POLICY": {
        "role": "supporting_indicator",
        "full_sample_look_ahead": False,
        "predictive_status": "not_in_catalogue",
        "reason": "The prices-and-policy reading is not in the first-pass ETF family.",
    },
    "INDUSTRIAL_PRODUCTION_ACTIVITY": {
        "role": "supporting_indicator",
        "full_sample_look_ahead": False,
        "predictive_status": "not_in_catalogue",
        "reason": "The industrial-production reading is not a separate first-pass signal.",
    },
    "CREDIT_STANDARDS_AND_VOLUMES": {
        "role": "supporting_indicator",
        "full_sample_look_ahead": False,
        "predictive_status": "not_in_catalogue",
        "reason": "The credit reading is not in the first-pass ETF family.",
    },
    "BRY_BOSCHAN_SPENCER15_VARIANT": {
        "role": "executable_historical_methodology",
        "full_sample_look_ahead": True,
        "predictive_status": "blocked_full_sample",
        "reason": (
            "The centred Spencer smoother and the full-sample endpoint ban are not an "
            "expanding-window confirmation delay."
        ),
    },
    "STOCK_WATSON_COINCIDENT_1988_MODERN_REFIT": {
        "role": "executable_historical_methodology",
        "full_sample_look_ahead": True,
        "predictive_status": "blocked_full_sample",
        "reason": (
            "The factor parameters are a full-sample fit. This pass does not rewrite the estimator."
        ),
    },
    "RESTRICTED_COINCIDENT_DIFFUSION": {
        "role": "supporting_indicator",
        "full_sample_look_ahead": False,
        "predictive_status": "retrospective_eligible",
        "reason": (
            "The diffusion share at a month uses that month and the level three months earlier."
        ),
    },
    "HARDING_PAGAN_CHARACTERISTICS": {
        "role": "diagnostic",
        "full_sample_look_ahead": True,
        "predictive_status": "blocked_full_sample",
        "reason": "The characteristics describe a full-sample chronology. They stay a diagnostic.",
    },
    "HAMILTON_MONTHLY_REGIME_SWITCHING": {
        "role": "executable_historical_methodology",
        "full_sample_look_ahead": True,
        "predictive_status": "blocked_full_sample",
        "reason": "The regime fit uses the full sample. This pass does not rewrite the estimator.",
    },
    "BAI_PERRON_MEAN_SHIFTS": {
        "role": "executable_historical_methodology",
        "full_sample_look_ahead": True,
        "predictive_status": "blocked_full_sample",
        "reason": "Break selection uses the full sample. This pass does not rewrite the estimator.",
    },
    "AUTOREGRESSIVE_BENCHMARK": {
        "role": "executable_historical_methodology",
        "full_sample_look_ahead": True,
        "predictive_status": "blocked_full_sample",
        "reason": "The lag is chosen on the full sample. No expanding window is implemented here.",
    },
    "CPI_U_INFLATION_AUTREGRESSION": {
        "role": "executable_historical_methodology",
        "full_sample_look_ahead": True,
        "predictive_status": "blocked_full_sample",
        "reason": "The autoregressive lag is chosen on the full sample.",
    },
    "EX_POST_REAL_FEDERAL_FUNDS_RATE": {
        "role": "executable_historical_methodology",
        "full_sample_look_ahead": False,
        "predictive_status": "not_in_catalogue",
        "reason": "The trailing identity is not in the first-pass family.",
    },
    "INFLATION_AUTOREGRESSION": {
        "role": "executable_historical_methodology",
        "full_sample_look_ahead": True,
        "predictive_status": "blocked_full_sample",
        "reason": (
            "The stored holdout is already insufficient, and the lag is not an expanding window."
        ),
    },
    "EX_POST_REAL_FUNDS_RATE": {
        "role": "executable_historical_methodology",
        "full_sample_look_ahead": True,
        "predictive_status": "blocked_future_cpi",
        "reason": (
            "Subsequent CPI is not known at the funds-rate month. "
            "The signal would have to wait for that window plus the CPI lag."
        ),
    },
    "IP_GROWTH_CUSUM": {
        "role": "diagnostic",
        "full_sample_look_ahead": True,
        "predictive_status": "blocked_full_sample",
        "reason": "The CUSUM boundary uses the full sample. It stays a diagnostic.",
    },
    "ESTRELLA_MISHKIN_TERM_SPREAD": {
        "role": "supporting_indicator",
        "full_sample_look_ahead": False,
        "predictive_status": "retrospective_eligible",
        "reason": "The spread is the same-month difference of the two stored yields.",
    },
    "LEAD_LAG_CROSS_CORRELATION": {
        "role": "diagnostic",
        "full_sample_look_ahead": True,
        "predictive_status": "blocked_full_sample",
        "reason": "The cross-correlation is a full-sample description. It stays a diagnostic.",
    },
    "ENGLE_GRANGER_COINTEGRATION": {
        "role": "diagnostic",
        "full_sample_look_ahead": True,
        "predictive_status": "blocked_full_sample",
        "reason": "The residual test uses the full sample. It stays a diagnostic.",
    },
    "CUSUM_RECURSIVE_RESIDUALS": {
        "role": "diagnostic",
        "full_sample_look_ahead": True,
        "predictive_status": "blocked_full_sample",
        "reason": "The CUSUM boundary uses the full sample. It stays a diagnostic.",
    },
    "CONSTANT_MATURITY_SPREAD_RECESSION_PROBIT": {
        "role": "executable_historical_methodology",
        "full_sample_look_ahead": True,
        "predictive_status": "blocked_full_sample",
        "reason": (
            "The probit coefficients are fit on the declared sample. "
            "No expanding window is implemented here."
        ),
    },
}


def classification_rows() -> list[dict[str, object]]:
    """One row per executable registration, with inputs taken from that registration."""
    rows: list[dict[str, object]] = []
    registry = default_method_registry()
    for method in sorted(registry.registered(), key=lambda item: item.method_id):
        spec = SPECS[method.method_id]
        dependency = method.dependency()
        rows.append(
            {
                "method_id": method.method_id,
                "role": spec["role"],
                "full_sample_look_ahead": spec["full_sample_look_ahead"],
                "predictive_status": spec["predictive_status"],
                "parameter_policy": dependency.parameter_policy,
                "warm_up": dependency.minimum_history,
                "required_inputs": " ".join(method.required_dataset_ids()),
                "reason": spec["reason"],
            }
        )
    return rows


def role_counts(rows: list[dict[str, object]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        role = str(row["role"])
        counts[role] = counts.get(role, 0) + 1
    return counts
