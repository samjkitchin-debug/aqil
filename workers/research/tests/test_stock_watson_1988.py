from datetime import date

from aqil_research.methods.stock_watson_1988 import (
    FACTOR_AR_ORDER,
    FACTOR_INNOVATION_VARIANCE,
    IDIOSYNCRATIC_AR_ORDER,
    PUBLICATION_ALLOWED,
    SPECIFICATION_ID,
    StockWatsonPanelBlocked,
    assert_real_panel_available,
    gaussian_log_likelihood,
    simulate_coincident_path,
)
from aqil_research.methods.stock_watson_1988_fit import (
    DEFAULT_STARTS,
    GRADIENT_NORM_LIMIT,
    NOT_THE_CITIBASE_SPECIFICATION,
    OPERATIONALLY_ACCEPTED,
    _filtered_factor,
    claims_maximum_likelihood,
    fit_coincident_factor,
    smoothed_factor,
)
from aqil_research.methods.stock_watson_1988_fit import (
    SPECIFICATION_ID as MODERN_REFIT_ID,
)
from aqil_research.workflow.stock_watson_reading import (
    PRESERVED_ESTIMATION_RUN_ID,
    _filter_update_locked,
    adopt_parameter_version,
    parameter_row_is_adopted,
)

LOADINGS = (0.7, 0.5, 0.45, 0.6)
FACTOR_AR = (0.5, 0.2)
IDIOSYNCRATIC = ((0.2, 0.0), (-0.1, 0.0), (0.1, 0.0), (0.3, 0.1))
SCALES = (0.4, 0.5, 0.45, 0.35)


def test_specification_constants_match_the_1988_paper() -> None:
    assert SPECIFICATION_ID == "STOCK_WATSON_COINCIDENT_1988"
    assert FACTOR_AR_ORDER == 2
    assert IDIOSYNCRATIC_AR_ORDER == 2
    assert FACTOR_INNOVATION_VARIANCE == 1.0
    assert PUBLICATION_ALLOWED is False


def test_real_panel_is_blocked_without_real_sales() -> None:
    stored = {"fed.g17.IP.B50001.S", "bls.ce.CES0000000001"}
    try:
        assert_real_panel_available(stored)
    except StockWatsonPanelBlocked as error:
        assert "census.mtis.TOTBUS.SM.real_1982" in str(error)
    else:
        raise AssertionError("estimation must not start")


def test_true_parameters_fit_the_simulated_path_better_than_a_wrong_factor() -> None:
    draw = simulate_coincident_path(
        periods=80,
        loadings=LOADINGS,
        factor_ar=FACTOR_AR,
        idiosyncratic_ar=IDIOSYNCRATIC,
        idiosyncratic_innovation_scale=SCALES,
        seed=1988,
    )
    true_likelihood = gaussian_log_likelihood(
        draw.observations,
        loadings=LOADINGS,
        factor_ar=FACTOR_AR,
        idiosyncratic_ar=IDIOSYNCRATIC,
        idiosyncratic_innovation_scale=SCALES,
    )
    wrong_likelihood = gaussian_log_likelihood(
        draw.observations,
        loadings=LOADINGS,
        factor_ar=(0.0, 0.0),
        idiosyncratic_ar=IDIOSYNCRATIC,
        idiosyncratic_innovation_scale=SCALES,
    )
    assert true_likelihood > wrong_likelihood
    assert true_likelihood > -10_000


def test_publication_flag_is_not_a_date() -> None:
    assert date(1988, 11, 1).year == 1988


def test_known_gradient_does_not_claim_maximum_likelihood() -> None:
    assert GRADIENT_NORM_LIMIT < 0.415
    assert (
        claims_maximum_likelihood(
            gradient_norm=0.415,
            gradient_norm_wide_step=0.415,
            log_likelihood=-1590.5374990458229,
            starts_evaluated=4,
        )
        is False
    )
    assert (
        claims_maximum_likelihood(
            gradient_norm=1e-6,
            gradient_norm_wide_step=1e-5,
            log_likelihood=-10.0,
            starts_evaluated=3,
        )
        is True
    )
    assert OPERATIONALLY_ACCEPTED is False
    assert "Payroll headcount is not employee-hours" in NOT_THE_CITIBASE_SPECIFICATION
    assert "2017 chained dollars are not 1982 dollars" in NOT_THE_CITIBASE_SPECIFICATION
    assert "CITIBASE 1959–87" in NOT_THE_CITIBASE_SPECIFICATION
    assert MODERN_REFIT_ID == "STOCK_WATSON_COINCIDENT_1988_MODERN_REFIT"
    assert "pca" not in MODERN_REFIT_ID.lower()
    assert len(DEFAULT_STARTS) >= 3


def test_preserved_run_is_not_replaced_by_an_unverified_gradient() -> None:
    assert PRESERVED_ESTIMATION_RUN_ID == "3f8c7611-c2a1-44a0-8c7e-01bebbfe9a8a"
    assert (
        adopt_parameter_version(
            maximum_likelihood_claimed=False,
            new_log_likelihood=-1590.0,
            stored_log_likelihood=-1590.537,
        )
        is False
    )
    assert (
        adopt_parameter_version(
            maximum_likelihood_claimed=True,
            new_log_likelihood=-1590.5371942126505,
            stored_log_likelihood=-1590.5374990458229,
        )
        is False
    )
    assert (
        adopt_parameter_version(
            maximum_likelihood_claimed=True,
            new_log_likelihood=-1589.0,
            stored_log_likelihood=-1590.5374990458229,
        )
        is True
    )
    assert parameter_row_is_adopted({"loadings_ip_income_sales_payroll": [1.0]}) is True
    assert (
        parameter_row_is_adopted(
            {"loadings_ip_income_sales_payroll": [1.0], "adopted_parameter_version": False}
        )
        is False
    )
    import inspect

    assert "adopted_parameter_version" in inspect.getsource(_filter_update_locked)


def test_filtered_factor_is_not_the_smoother() -> None:
    draw = simulate_coincident_path(
        periods=40,
        loadings=LOADINGS,
        factor_ar=FACTOR_AR,
        idiosyncratic_ar=IDIOSYNCRATIC,
        idiosyncratic_innovation_scale=SCALES,
        seed=11,
    )
    kwargs = {
        "loadings": LOADINGS,
        "factor_ar": FACTOR_AR,
        "idiosyncratic_ar": IDIOSYNCRATIC,
        "idiosyncratic_innovation_scale": SCALES,
    }
    filtered = _filtered_factor(draw.observations, **kwargs)
    smoothed = smoothed_factor(draw.observations, **kwargs)
    assert len(filtered) == len(smoothed)
    assert abs(filtered[-1] - smoothed[-1]) < 1e-8
    assert abs(filtered[0] - smoothed[0]) > 1e-4


def test_fit_evaluates_more_than_one_start(monkeypatch) -> None:
    draw = simulate_coincident_path(
        periods=40,
        loadings=LOADINGS,
        factor_ar=FACTOR_AR,
        idiosyncratic_ar=IDIOSYNCRATIC,
        idiosyncratic_innovation_scale=SCALES,
        seed=19,
    )
    panel = [[row[series] for row in draw.observations] for series in range(4)]
    seen: list[object] = []

    def fake(objective, start, method="L-BFGS-B", options=None):
        del method, options
        vector = [float(value) for value in start]
        seen.append(vector)
        value = float(objective(start))

        class _Result:
            fun = value
            x = start
            success = True
            message = "CONVERGENCE: RELATIVE REDUCTION OF F <= FACTR*EPSMCH"

        return _Result()

    monkeypatch.setattr(
        "aqil_research.methods.stock_watson_1988_fit.minimize",
        fake,
    )
    fitted = fit_coincident_factor(panel, maxiter=1)
    assert len(seen) >= 3
    assert fitted.starts_evaluated >= 4
    assert fitted.converged is True
    assert fitted.maximum_likelihood_claimed is False
    assert fitted.filtered_factor != fitted.smoothed_factor
    assert fitted.maximum_likelihood_claimed is claims_maximum_likelihood(
        gradient_norm=fitted.gradient_norm,
        gradient_norm_wide_step=fitted.gradient_norm_wide_step,
        log_likelihood=fitted.log_likelihood,
        starts_evaluated=fitted.starts_evaluated,
    )


def test_batch1_methods_are_registered_and_unpublished() -> None:
    from aqil_research.methods.harding_pagan_characteristics import (
        PUBLICATION_ALLOWED as characteristics_publication,
    )
    from aqil_research.methods.registry import (
        HARDING_PAGAN_CHARACTERISTICS,
        RESTRICTED_COINCIDENT_DIFFUSION_METHOD_ID,
        STOCK_WATSON_MODERN_REFIT_ID,
        default_method_registry,
    )
    from aqil_research.methods.restricted_coincident_diffusion import (
        PUBLICATION_ALLOWED as diffusion_publication,
    )
    from aqil_research.methods.stock_watson_1988_fit import (
        PUBLICATION_ALLOWED as refit_publication,
    )

    registry = default_method_registry()
    assert registry.get(STOCK_WATSON_MODERN_REFIT_ID).method_id == MODERN_REFIT_ID
    assert registry.get(RESTRICTED_COINCIDENT_DIFFUSION_METHOD_ID).method_id == (
        RESTRICTED_COINCIDENT_DIFFUSION_METHOD_ID
    )
    assert registry.get(HARDING_PAGAN_CHARACTERISTICS).method_id == HARDING_PAGAN_CHARACTERISTICS
    assert refit_publication is False
    assert OPERATIONALLY_ACCEPTED is False
    assert diffusion_publication is False
    assert characteristics_publication is False
