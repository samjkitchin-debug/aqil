"""JSONB calculation normalisation for replay."""

from aqil_research.persistence.calculation_normalize import normalize_calculation_payload


def test_normalize_coerces_jsonb_floats_to_strings() -> None:
    raw = {
        "gap_percentage_points": 0.5,
        "triggered": True,
        "months_used_for_average": ["2024-12-01", "2024-11-01"],
    }
    out = normalize_calculation_payload(raw)
    assert out is not None
    assert out["gap_percentage_points"] == "0.50"
    assert out["months_used_for_average"] == ["2024-11-01", "2024-12-01"]
