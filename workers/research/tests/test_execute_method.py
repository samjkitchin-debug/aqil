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
from aqil_research.persistence.reproduce import reproduction_config
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
        assert dependency.depends_on_method_ids == ()
        assert dependency.new_observation_requires_recalculation is True
        assert dependency.refit_is_different_command is False
        assert dependency.parameter_policy != "refit_separate"
        parsed = method.parse_config(method.accepted_config_payload())
        assert parsed.config_id
    stock_watson = registry.get(SPECIFICATION_ID)
    assert stock_watson.dependency().parameter_policy == "fixed_accepted"
    assert "37" in stock_watson.dependency().minimum_history


def test_refit_is_rejected_for_every_registered_method(capsys) -> None:
    for method in default_method_registry().registered():
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


def test_stock_watson_calculation_does_not_open_the_database(monkeypatch, capsys) -> None:
    def opened(*_args, **_kwargs):
        raise AssertionError("database opened")

    monkeypatch.setattr("aqil_research.persistence.connection.research_connection", opened)
    code = main(["execute-method", "--method-id", SPECIFICATION_ID])
    captured = capsys.readouterr()
    assert code == 2
    assert "will not append an estimate" in captured.err
    assert "will not replace the preserved parameter version" in captured.err


def test_stored_config_ids_resolve_for_reproduction() -> None:
    registry = default_method_registry()
    for config_id, method_id, stored_hash in STORED_CONFIGS:
        payload = reproduction_config(config_id)
        method = registry.get(method_id)
        parsed = method.parse_config(payload)
        assert parsed.config_id == config_id
        if stored_hash is not None:
            assert method.config_hash(parsed) == stored_hash
    with pytest.raises(ValueError, match="unknown config_id"):
        reproduction_config("not-a-stored-config")


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
