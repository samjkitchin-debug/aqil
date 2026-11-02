"""Accepted Stock–Watson parameter artifact.

This is the preserved parameter vector. It is not a historical calculation,
not the rejected re-estimate, and not a filtered path. The values match the
25 October 2026 estimation that remained the parameter version on 30 October
2026, when the re-estimate likelihood gain stayed below 0.001.
"""

from __future__ import annotations

import json

from aqil_research.methods.parameters import MethodParameterDocument
from aqil_research.methods.stock_watson_1988_fit import ACCEPTED_CONFIG

PARAMETER_VERSION_ID = "sw1988-modern-1997-2026m07"
METHOD_ID = "STOCK_WATSON_COINCIDENT_1988_MODERN_REFIT"
METHOD_VERSION = "0.1.0"
PROVENANCE_RUN_ID = "3f8c7611-c2a1-44a0-8c7e-01bebbfe9a8a"
REJECTED_REFIT_RUN_ID = "940955f1-50d5-4c06-9d90-5ceebd05d352"
PUBLICATION_ALLOWED = False
OPERATIONALLY_ACCEPTED = False

LOADINGS = (
    0.9074156691709212,
    0.592332010645985,
    0.7468422714668663,
    0.8337971126257162,
)
FACTOR_AR = (0.21593139825856147, -0.20902512910372195)
IDIOSYNCRATIC_AR = (
    (-0.135055359330801, -0.1853845911590007),
    (-0.05395491262894935, -0.05349521674490646),
    (-0.17587617069890396, -0.10032913242621615),
    (-0.08764350781001158, 0.18173780298752065),
)
IDIOSYNCRATIC_SCALE = (
    0.3683167232210555,
    0.7875917515174838,
    0.5955094247543465,
    0.5045708876089342,
)
MOMENTS = {
    "production": {"mean": 0.0008033425850746714, "scale": 0.011064336267446366},
    "income": {"mean": 0.001975599763404268, "scale": 0.007219925312642885},
    "sales": {"mean": 0.0016277879067532449, "scale": 0.01203634056454773},
    "payroll": {"mean": 0.000761111337927729, "scale": 0.008280717783803826},
}
REJECTED_LOADINGS = (
    0.9075982525342208,
    0.5925042141374849,
    0.7468167432926492,
    0.8334881274252217,
)
ESTIMATION = {
    "sample_levels": ["1997-01-01", "2026-07-01"],
    "growth_months": 354,
    "optimiser": "L-BFGS-B",
    "maxiter": 40,
    "ftol": 1e-6,
    "factor_innovation_variance": 1,
    "factor_ar_order": 2,
    "idiosyncratic_ar_order": 2,
    "identification": (
        "industrial-production loading positive; factor innovation variance fixed at 1"
    ),
    "scaling": "standardised log differences using the stored training moments",
    "orientation": "positive industrial-production loading",
    "estimation_log_likelihood": -1590.5374990458229,
    "approval": (
        "Preserved parameter version 3f8c7611-c2a1-44a0-8c7e-01bebbfe9a8a. "
        "Re-estimate 940955f1-50d5-4c06-9d90-5ceebd05d352 improved the likelihood by about "
        "0.000305, below 0.001, and was not adopted. Not operationally accepted."
    ),
}


def accepted_parameter_values() -> dict[str, object]:
    """The vector a calculate run may apply. No filtered path is included."""
    return {
        "loadings_ip_income_sales_payroll": list(LOADINGS),
        "factor_ar": list(FACTOR_AR),
        "idiosyncratic_ar": [list(pair) for pair in IDIOSYNCRATIC_AR],
        "idiosyncratic_scale": list(IDIOSYNCRATIC_SCALE),
        "moments": {
            name: {"mean": moments["mean"], "scale": moments["scale"]}
            for name, moments in MOMENTS.items()
        },
    }


def accepted_parameter_checksum() -> str:
    """Deterministic checksum of the accepted vector. The path is not hashed."""
    encoded = json.dumps(accepted_parameter_values(), sort_keys=True, separators=(",", ":"))
    return MethodParameterDocument(
        config_id=str(ACCEPTED_CONFIG["config_id"]),
        label=str(ACCEPTED_CONFIG["label"]),
        scalars={"accepted_parameters": encoded},
    ).config_hash()


def parameter_identity_ok(values: dict[str, object]) -> bool:
    """True only for this vector, its dimensions, and its frozen moments."""
    loadings = values.get("loadings_ip_income_sales_payroll")
    factor_ar = values.get("factor_ar")
    idiosyncratic = values.get("idiosyncratic_ar")
    scales = values.get("idiosyncratic_scale")
    moments = values.get("moments")
    if loadings == list(REJECTED_LOADINGS):
        return False
    if (
        loadings != list(LOADINGS)
        or factor_ar != list(FACTOR_AR)
        or idiosyncratic != [list(pair) for pair in IDIOSYNCRATIC_AR]
        or scales != list(IDIOSYNCRATIC_SCALE)
    ):
        return False
    if not isinstance(moments, dict) or set(moments) != set(MOMENTS):
        return False
    for name, expected in MOMENTS.items():
        stored = moments.get(name)
        if not isinstance(stored, dict):
            return False
        if stored.get("mean") != expected["mean"] or stored.get("scale") != expected["scale"]:
            return False
        if float(stored["scale"]) <= 0:
            return False
    if float(LOADINGS[0]) <= 0:
        return False
    return True
