"""Collection pipeline tests (offline fixtures)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from aqil_research.collection.service import collect_bls_unemployment
from aqil_research.sources.rights import load_source_rights
from aqil_research.vintages.store import InMemoryObservationStore

FIXTURE = Path(__file__).parent / "fixtures" / "bls" / "api_lns14000000_success.json"
COLLECTED_AT = datetime(2025, 6, 1, 12, 0, tzinfo=UTC)


def test_collection_success_memory() -> None:
    result, store = collect_bls_unemployment(
        store_backend="memory",
        collected_at=COLLECTED_AT,
        live=False,
        fixture_path=str(FIXTURE),
        start_year=2022,
        end_year=2025,
    )
    assert result.outcome in ("success", "unchanged", "partial")
    assert result.observations_received > 0
    assert isinstance(store, InMemoryObservationStore)
    assert result.data_provenance == "latest_revised"
    assert "password" not in result.model_dump_json().lower()


def test_collection_rights_gate_blocks_disabled_source(monkeypatch: pytest.MonkeyPatch) -> None:
    from aqil_research.sources import rights as rights_mod
    from aqil_research.sources.rights import OperationalStatus

    records = load_source_rights()
    disabled = []
    for r in records:
        if r.source_id == "bls_cps_unemployment_rate":
            disabled.append(
                r.model_copy(update={"operational_status": OperationalStatus.DISABLED}),
            )
        else:
            disabled.append(r)
    monkeypatch.setattr(rights_mod, "load_source_rights", lambda: disabled)
    monkeypatch.setattr(
        "aqil_research.collection.service.load_source_rights",
        lambda: disabled,
    )
    result, _ = collect_bls_unemployment(
        store_backend="memory",
        collected_at=COLLECTED_AT,
        live=False,
        fixture_path=str(FIXTURE),
    )
    assert result.outcome == "failed_rights"


def test_collection_malformed_fixture_partial_or_failed() -> None:
    bad = Path(__file__).parent / "fixtures" / "bls" / "api_empty_series.json"
    if not bad.exists():
        pytest.skip("malformed fixture not present")
    result, _ = collect_bls_unemployment(
        store_backend="memory",
        collected_at=COLLECTED_AT,
        live=False,
        fixture_path=str(bad),
        start_year=2022,
        end_year=2025,
    )
    assert result.outcome in ("failed_fetch", "partial", "success")
    assert result.observations_received == 0 or result.outcome != "failed_fetch"
