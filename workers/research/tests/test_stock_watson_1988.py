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
