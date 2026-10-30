"""Execution contract: dependencies, refit refusal, registry dispatch, replay ids."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from aqil_research.adapters.fixture_ln_csv import FixtureLnCsvAdapter
from aqil_research.cli import main
from aqil_research.methods.registry import default_method_registry
from aqil_research.methods.sahm import SAHM_METHOD_ID
from aqil_research.methods.stock_watson_1988_fit import SPECIFICATION_ID
from aqil_research.persistence.connection import research_connection
from aqil_research.persistence.ingest import ingest_adapter_to_postgres
from aqil_research.persistence.reproduce import replay_configuration, reproduction_config
from aqil_research.persistence.runs import load_research_run
from aqil_research.sources.rights import load_source_rights
from db_guard import open_isolated_test_database

PROVIDERS = Path(__file__).parent / "fixtures" / "providers"
STORED_CONFIGS = (
    ("restricted-coincident-diffusion", "RESTRICTED_COINCIDENT_DIFFUSION", None),
    (
        "sw1988-modern-1997-2026m07",
        "STOCK_WATSON_COINCIDENT_1988_MODERN_REFIT",
        None,
    ),
    (
        "sw1988-modern-multistart",
        "STOCK_WATSON_COINCIDENT_1988_MODERN_REFIT",
        None,
    ),
    (
        "hamilton_monthly_ip_v1",
        "HAMILTON_MONTHLY_REGIME_SWITCHING",
        "ac35490e07a1020cdffcde486f87d4d41f83e16e5709c0f8a62a944ccf8824ee",
    ),
    (
        "bai_perron_mean_shifts_v1",
        "BAI_PERRON_MEAN_SHIFTS",
        "3efce19ca7f8fbfc6182907600eccc331d5489c8427abab7e2889fb657f27f75",
    ),
    (
        "autoregressive-benchmark-v1",
        "AUTOREGRESSIVE_BENCHMARK",
        "d059e97c16a8cae36df5e4e272742f180fb6c8aafd8fd3ee43bdca3649e94bfd",
    ),
    (
        "lead-lag-cross-correlation-v1",
        "LEAD_LAG_CROSS_CORRELATION",
        "42247425902cc9b0bf95a167f67064e13fe89c0f452ebcea350aed527dfd8f40",
    ),
)


def test_every_registered_method_declares_a_dependency() -> None:
    registry = default_method_registry()
    methods = registry.registered()
    assert methods
    for method in methods:
        dependency = method.dependency()
        assert dependency.source_series == method.required_dataset_ids()
        assert dependency.frequency
        assert dependency.minimum_history.strip()
        assert dependency.vintage_class == "latest_revised"
        assert dependency.parameter_policy in {"none", "fixed_accepted", "refit_separate"}
        assert dependency.new_observation_requires_recalculation is True
        assert dependency.refit_is_different_command is (
            dependency.parameter_policy == "refit_separate"
        )
        parsed = method.parse_config(method.accepted_config_payload())
        assert parsed.config_id
        if method.method_id == "MACRO_CONDITIONS_PANEL":
            assert dependency.depends_on_method_ids == (
                "SAHM_UNEMPLOYMENT_GAP",
                "SLOOS_CIL_LENDING_STANDARDS",
                "CENSUS_ADV_DURABLE_ORDERS",
            )
        else:
            assert dependency.depends_on_method_ids == ()
    policies = {method.method_id: method.dependency().parameter_policy for method in methods}
    assert policies[SPECIFICATION_ID] == "refit_separate"
    assert all(
        policy == "none" for method_id, policy in policies.items() if method_id != SPECIFICATION_ID
    )
    stock_watson = registry.get(SPECIFICATION_ID)
    assert "37" in stock_watson.dependency().minimum_history


def test_refit_is_rejected_for_a_method_with_no_parameters(capsys) -> None:
    for method in default_method_registry().registered():
        if method.dependency().parameter_policy != "none":
            continue
        code = main(["execute-method", "--method-id", method.method_id, "--refit"])
        captured = capsys.readouterr()
        assert code == 2
        assert "Refit is not available" in captured.err
        assert method.method_id in captured.err


def test_execute_method_dispatches_through_the_default_registry(monkeypatch, capsys) -> None:
    calls: list[str] = []
    original = default_method_registry

    def wrapped():
        calls.append("default_method_registry")
        return original()

    monkeypatch.setattr("aqil_research.cli_ops.default_method_registry", wrapped)
    code = main(["execute-method", "--method-id", "not-a-registered-method"])
    captured = capsys.readouterr()
    assert code == 2
    assert calls == ["default_method_registry"]
    assert "unknown method_id" in captured.err


def test_stored_config_ids_resolve_for_reproduction() -> None:
    registry = default_method_registry()
    for config_id, method_id, stored_hash in STORED_CONFIGS:
        payload = reproduction_config(config_id)
        method = registry.get(method_id)
        parsed = method.parse_config(payload)
        assert parsed.config_id == config_id
        stored = _stored_run(method_id, config_id, stored_hash or "not-the-method-hash")
        if stored_hash is not None:
            assert method.config_hash(parsed) == stored_hash
            assert replay_configuration(registry, stored)["config_id"] == config_id
        else:
            with pytest.raises(ValueError, match="not sufficient to replay"):
                replay_configuration(registry, stored)
    with pytest.raises(ValueError, match="unknown config_id"):
        reproduction_config("not-a-stored-config")


def _stored_run(method_id: str, config_id: str, config_hash: str):
    from datetime import datetime

    from aqil_research.contracts.observation import AnalysisMode
    from aqil_research.pipeline.models import ResearchRun

    now = datetime(2026, 1, 1, tzinfo=UTC)
    return ResearchRun(
        run_id="00000000-0000-0000-0000-000000000001",
        executed_at=now,
        execution_status="completed",
        dataset_id="fed.g17.IP.B50001.S",
        source_id="federal_reserve_g17_total_ip",
        rights_record_id="federal_reserve_g17_total_ip",
        analysis_mode=AnalysisMode.LATEST_REVISED,
        analysis_type=method_id,
        decision_at=now,
        evaluation_period="2026-01-01",
        method_id=method_id,
        method_version="0.1.0",
        implementation_hash="test",
        config_id=config_id,
        config_hash=config_hash,
        input_snapshot_hash="test",
        data_sufficiency="sufficient",
        statistical_interpretation="test",
        causal_hypothesis="none",
        investment_implication="no_action",
        assumptions=["test"],
        limitations=["test"],
        observation_ids=[],
        reproduction={"method_id": method_id},
        narrative="test",
        publication_allowed=False,
    )


@pytest.fixture(scope="module")
def require_db() -> str:
    return open_isolated_test_database()


@pytest.mark.integration
def test_execute_method_loads_postgres_and_appends_a_run(require_db: str, capsys) -> None:
    del require_db
    rights = load_source_rights()
    record = next(row for row in rights if row.dataset_id == "bls.ln.LNS14000000")
    adapter = FixtureLnCsvAdapter(PROVIDERS / "unemployment_equivalent.csv")
    decision_at = datetime(2025, 2, 1, 12, 0, tzinfo=UTC)
    with research_connection() as conn:
        ingest_adapter_to_postgres(
            conn,
            adapter,
            record,
            retrieved_at=decision_at,
            collection_mode="fixture",
        )
    code = main(
        [
            "execute-method",
            "--method-id",
            SAHM_METHOD_ID,
            "--cutoff",
            "2024-12-01",
        ],
    )
    captured = capsys.readouterr()
    assert code == 0
    assert "publication_allowed=false" in captured.out
    run_id = next(
        line.removeprefix("run_id=")
        for line in captured.out.splitlines()
        if line.startswith("run_id=")
    )
    with research_connection() as conn:
        stored = load_research_run(conn, run_id)
        from aqil_research.persistence.reproduce import verify_stored_run_replay

        replay = verify_stored_run_replay(conn, run_id, stored=stored)
    assert replay.full_match
    assert stored.method_id == SAHM_METHOD_ID
    assert stored.publication_allowed is False
    assert stored.execution_status == "completed"
    assert stored.calculation is not None
    assert stored.evaluation_period == "2024-12-01"
    assert stored.input_dataset_ids == ["bls.ln.LNS14000000"]


@pytest.mark.integration
def test_execute_method_persists_an_insufficient_run(require_db: str, capsys) -> None:
    del require_db
    code = main(
        [
            "execute-method",
            "--method-id",
            SAHM_METHOD_ID,
            "--cutoff",
            "1900-01-01",
        ],
    )
    captured = capsys.readouterr()
    assert code == 0
    assert "execution_status=completed_insufficient" in captured.out
    assert "publication_allowed=false" in captured.out
    run_id = next(
        line.removeprefix("run_id=")
        for line in captured.out.splitlines()
        if line.startswith("run_id=")
    )
    with research_connection() as conn:
        stored = load_research_run(conn, run_id)
    assert stored.calculation is None
    assert stored.data_sufficiency == "insufficient"
    assert stored.publication_allowed is False


@pytest.mark.integration
def test_stock_watson_refit_appends_an_unadopted_run(require_db: str, monkeypatch, capsys) -> None:
    """Calculate uses the accepted vector. Refit appends a separate unadopted run.

    The inserts stay in one transaction and are rolled back, so later tests
    still see an empty method history.
    """
    del require_db
    from contextlib import contextmanager

    import psycopg

    from aqil_research.persistence.test_database import require_test_database_url
    from test_stock_watson_lifecycle import LOADINGS, _insert, _months, _seed_run

    periods = _months(40)
    columns = [[100.0 + index + series for index in range(len(periods))] for series in range(4)]
    values = {
        "production": columns[0],
        "income": columns[1],
        "sales": columns[2],
        "payroll": columns[3],
    }
    conn = psycopg.connect(require_test_database_url())

    @contextmanager
    def same_transaction(url: str | None = None):
        del url
        yield conn

    monkeypatch.setattr(
        "aqil_research.persistence.connection.research_connection",
        same_transaction,
    )
    try:
        _insert(conn, periods, values, datetime.now(tz=UTC))
        template_id = _seed_run(conn, periods, columns)
        template = load_research_run(conn, template_id)
        adopted_id = "00000000-0000-0000-0000-0000000003f8"
        unadopted_id = "00000000-0000-0000-0000-000000000940"
        _append_parameter_row(
            conn,
            template,
            run_id=adopted_id,
            executed_at=datetime(2099, 1, 1, tzinfo=UTC),
            loadings=list(LOADINGS),
            adopted=None,
        )
        _append_parameter_row(
            conn,
            template,
            run_id=unadopted_id,
            executed_at=datetime(2099, 6, 1, tzinfo=UTC),
            loadings=[0.2, 0.2, 0.2, 0.2],
            adopted=False,
        )
        code = main(["execute-method", "--method-id", SPECIFICATION_ID])
        captured = capsys.readouterr()
        assert code == 0, captured.err
        calculate_id = _printed_run_id(captured.out)
        calculated = load_research_run(conn, calculate_id)
        adopted = load_research_run(conn, adopted_id)
        rejected = load_research_run(conn, unadopted_id)
        assert calculated.publication_allowed is False
        assert calculated.run_id not in {adopted_id, unadopted_id}
        assert calculated.calculation is not None
        assert calculated.calculation["adopted_parameter_version"] is False
        assert calculated.calculation["loadings_ip_income_sales_payroll"] == list(LOADINGS)
        assert adopted.calculation is not None
        assert adopted.calculation["loadings_ip_income_sales_payroll"] == list(LOADINGS)
        assert "adopted_parameter_version" not in adopted.calculation
        assert rejected.calculation is not None
        assert rejected.calculation["adopted_parameter_version"] is False
        assert rejected.calculation["loadings_ip_income_sales_payroll"] == [0.2, 0.2, 0.2, 0.2]

        code = main(["execute-method", "--method-id", SPECIFICATION_ID, "--refit"])
        captured = capsys.readouterr()
        assert code == 0, captured.err
        refit_id = _printed_run_id(captured.out)
        refitted = load_research_run(conn, refit_id)
        adopted_after = load_research_run(conn, adopted_id)
        rejected_after = load_research_run(conn, unadopted_id)
        assert refit_id not in {adopted_id, unadopted_id, calculate_id}
        assert refitted.publication_allowed is False
        assert refitted.calculation is not None
        assert refitted.calculation["adopted_parameter_version"] is False
        assert refitted.calculation["update_kind"] == "reestimate"
        assert adopted_after.calculation == adopted.calculation
        assert rejected_after.calculation == rejected.calculation
    finally:
        conn.rollback()
        conn.close()


def _append_parameter_row(
    conn,
    template,
    *,
    run_id: str,
    executed_at: datetime,
    loadings: list[float],
    adopted: bool | None,
) -> None:
    from aqil_research.persistence.runs import save_research_run

    calculation = dict(template.calculation or {})
    calculation["loadings_ip_income_sales_payroll"] = loadings
    if adopted is None:
        calculation.pop("adopted_parameter_version", None)
    else:
        calculation["adopted_parameter_version"] = adopted
    save_research_run(
        conn,
        template.model_copy(
            update={
                "run_id": run_id,
                "executed_at": executed_at,
                "decision_at": executed_at,
                "calculation": calculation,
                "observation_ids": [],
            },
        ),
    )


def _printed_run_id(stdout: str) -> str:
    return next(
        line.removeprefix("run_id=") for line in stdout.splitlines() if line.startswith("run_id=")
    )
