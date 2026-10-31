"""Historical replay on the disposable database.

A missing observation link stays blocked. A later field can sit beside a
numerical match. A changed figure does not become a pass, and a stored hash
is not rewritten.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from uuid import uuid4

import psycopg
import pytest

from aqil_research.contracts.observation import AnalysisMode
from aqil_research.methods.restricted_coincident_diffusion import METHOD_ID as DIFFUSION_ID
from aqil_research.methods.stock_watson_1988 import gaussian_log_likelihood
from aqil_research.methods.stock_watson_1988_fit import (
    SPECIFICATION_ID,
    _filtered_factor,
    log_difference,
    standardise,
)
from aqil_research.persistence.reproduce import classify_historical_replay
from aqil_research.persistence.runs import load_research_run, save_research_run
from aqil_research.persistence.test_database import resolve_connection_url
from aqil_research.pipeline.models import ResearchRun
from db_guard import open_isolated_test_database
from test_stock_watson_lifecycle import (
    DATASETS,
    FACTOR_AR,
    IDIOSYNCRATIC,
    LOADINGS,
    SCALES,
    _insert,
    _months,
)

pytestmark = pytest.mark.integration

HISTORICAL_HASH = "1c9244eac3ac2da1"


@pytest.fixture(scope="module")
def require_db() -> str:
    return open_isolated_test_database()


@contextmanager
def _uncommitted_connection() -> Iterator[psycopg.Connection]:
    """Keep replay fixtures off the shared disposable database."""
    conn = psycopg.connect(resolve_connection_url(None))
    try:
        yield conn
    finally:
        conn.rollback()
        conn.close()


def test_diffusion_without_observation_links_is_blocked(require_db: str) -> None:
    del require_db
    run_id = str(uuid4())
    with _uncommitted_connection() as conn:
        save_research_run(
            conn,
            _bare_run(
                run_id, DIFFUSION_ID, "restricted-coincident-diffusion", datetime.now(tz=UTC)
            ),
        )
        classified = classify_historical_replay(conn, run_id)
        stored = load_research_run(conn, run_id)
    assert classified.outcome == "blocked"
    assert classified.missing_field == "observation_ids"
    assert stored.config_hash == HISTORICAL_HASH
    assert stored.publication_allowed is False


def test_stock_watson_replay_uses_frozen_links_and_keeps_the_stored_hash(require_db: str) -> None:
    del require_db
    periods = _months(40)
    columns = [[100.0 + index + series for index in range(len(periods))] for series in range(4)]
    values = {
        "production": columns[0],
        "income": columns[1],
        "sales": columns[2],
        "payroll": columns[3],
    }
    when = datetime.now(tz=UTC)
    with _uncommitted_connection() as conn:
        _insert(conn, periods, values, when)
        linked = conn.execute(
            """
            select observation_id, dataset_id
            from research.economic_observations
            where retrieved_at = %s
            """,
            (when,),
        ).fetchall()
        by_dataset: dict[str, list[str]] = {}
        for observation_id, dataset_id in linked:
            by_dataset.setdefault(dataset_id, []).append(observation_id)
        partial_id = str(uuid4())
        partial_ids = by_dataset["fed.g17.IP.B50001.S"] + by_dataset["bls.ce.CES0000000001"]
        save_research_run(
            conn,
            _factor_run(partial_id, periods, columns, partial_ids, when, likelihood_offset=0.0),
        )
        partial = classify_historical_replay(conn, partial_id)
        assert partial.outcome == "blocked"
        assert partial.missing_field is not None
        assert "bea.nipa.T20600.W875RX" in partial.missing_field
        assert "bea.nipa.U002BU.KPMT" in partial.missing_field

        complete_id = str(uuid4())
        complete_ids = [observation_id for observation_id, _dataset in linked]
        save_research_run(
            conn,
            _factor_run(complete_id, periods, columns, complete_ids, when, likelihood_offset=0.0),
        )
        complete = classify_historical_replay(conn, complete_id)
        stored = load_research_run(conn, complete_id)
        assert complete.outcome == "replayable", complete.differences
        assert complete.differences == ()
        assert complete.tolerance == 1e-8
        assert any("config hash" in note for note in complete.notes)
        assert stored.config_hash == HISTORICAL_HASH
        assert stored.calculation is not None
        assert "adopted_parameter_version" not in stored.calculation
        assert stored.publication_allowed is False

        tampered_id = str(uuid4())
        save_research_run(
            conn,
            _factor_run(tampered_id, periods, columns, complete_ids, when, likelihood_offset=1.0),
        )
        tampered = classify_historical_replay(conn, tampered_id)
        assert tampered.outcome == "executable-but-historically-unmatched"
        assert "log_likelihood" in tampered.differences
        assert load_research_run(conn, tampered_id).config_hash == HISTORICAL_HASH


def _bare_run(run_id: str, method_id: str, config_id: str, when: datetime) -> ResearchRun:
    return ResearchRun(
        run_id=run_id,
        executed_at=when,
        execution_status="completed",
        dataset_id="fed.g17.IP.B50001.S",
        source_id="federal_reserve_g17_total_ip",
        rights_record_id="federal_reserve_g17_total_ip",
        analysis_mode=AnalysisMode.LATEST_REVISED,
        analysis_type=method_id,
        decision_at=when,
        evaluation_period="2026-07-01",
        method_id=method_id,
        method_version="0.1.0",
        implementation_hash="historical",
        config_id=config_id,
        config_hash=HISTORICAL_HASH,
        input_snapshot_hash="historical",
        data_sufficiency="sufficient",
        calculation={"publication_allowed": False},
        statistical_interpretation="historical",
        causal_hypothesis="none",
        investment_implication="no_action",
        assumptions=["historical"],
        limitations=["historical"],
        observation_ids=[],
        reproduction={"method_id": method_id},
        narrative="historical",
        publication_allowed=False,
    )


def _factor_run(
    run_id: str,
    periods: list,
    columns: list[list[float]],
    observation_ids: list[str],
    when: datetime,
    *,
    likelihood_offset: float,
) -> ResearchRun:
    growth = [log_difference(column) for column in columns]
    moments: dict[str, dict[str, float]] = {}
    panel: list[list[float]] = []
    for name, values in zip(("production", "income", "sales", "payroll"), growth, strict=True):
        standardised, mean, scale = standardise(values)
        moments[name] = {"mean": mean, "scale": scale}
        panel.append(standardised)
    observations = tuple(
        tuple(panel[series][time] for series in range(4)) for time in range(len(panel[0]))
    )
    likelihood = gaussian_log_likelihood(
        observations,
        loadings=LOADINGS,
        factor_ar=FACTOR_AR,
        idiosyncratic_ar=IDIOSYNCRATIC,
        idiosyncratic_innovation_scale=SCALES,
    )
    path = _filtered_factor(
        observations,
        loadings=LOADINGS,
        factor_ar=FACTOR_AR,
        idiosyncratic_ar=IDIOSYNCRATIC,
        idiosyncratic_innovation_scale=SCALES,
    )
    return ResearchRun(
        run_id=run_id,
        executed_at=when,
        execution_status="completed",
        dataset_id=DATASETS[0][0],
        input_dataset_ids=[item[0] for item in DATASETS],
        source_id=DATASETS[0][1],
        rights_record_id=DATASETS[0][1],
        analysis_mode=AnalysisMode.LATEST_REVISED,
        analysis_type=SPECIFICATION_ID,
        decision_at=when,
        evaluation_period=periods[-1].isoformat(),
        method_id=SPECIFICATION_ID,
        method_version="0.1.0",
        implementation_hash="historical",
        config_id="sw1988-modern-1997-2026m07",
        config_hash=HISTORICAL_HASH,
        input_snapshot_hash="historical",
        data_sufficiency="sufficient",
        calculation={
            "loadings_ip_income_sales_payroll": list(LOADINGS),
            "factor_ar": list(FACTOR_AR),
            "idiosyncratic_ar": [list(pair) for pair in IDIOSYNCRATIC],
            "idiosyncratic_scale": list(SCALES),
            "log_likelihood": likelihood + likelihood_offset,
            "filtered_factor": list(path),
            "moments": moments,
            "sample_levels": [periods[0].isoformat(), periods[-1].isoformat()],
            "publication_allowed": False,
        },
        statistical_interpretation="historical calculation",
        causal_hypothesis="none",
        investment_implication="no_action",
        assumptions=["The calculation uses the stored parameter vector."],
        limitations=["publication_allowed is false."],
        observation_ids=observation_ids,
        reproduction={"method_id": SPECIFICATION_ID},
        narrative="historical calculation",
        publication_allowed=False,
    )
