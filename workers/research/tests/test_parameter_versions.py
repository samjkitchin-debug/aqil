"""The accepted parameter artifact is not a historical calculation."""

from aqil_research.methods.stock_watson_accepted import (
    LOADINGS,
    REJECTED_LOADINGS,
    accepted_parameter_checksum,
    accepted_parameter_values,
    parameter_identity_ok,
)


def test_accepted_checksum_is_stable_and_excludes_a_path() -> None:
    values = accepted_parameter_values()
    assert "filtered_factor" not in values
    assert "smoothed_factor" not in values
    assert values["loadings_ip_income_sales_payroll"] == list(LOADINGS)
    assert values["loadings_ip_income_sales_payroll"] != list(REJECTED_LOADINGS)
    assert accepted_parameter_checksum() == accepted_parameter_checksum()
    assert parameter_identity_ok(values) is True


def test_rejected_refit_is_not_the_accepted_identity() -> None:
    values = accepted_parameter_values()
    values["loadings_ip_income_sales_payroll"] = list(REJECTED_LOADINGS)
    assert parameter_identity_ok(values) is False


def test_missing_moment_blocks_identity() -> None:
    values = accepted_parameter_values()
    moments = values["moments"]
    assert isinstance(moments, dict)
    del moments["sales"]
    assert parameter_identity_ok(values) is False
