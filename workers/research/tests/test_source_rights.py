import csv
import inspect
from pathlib import Path

import pytest

from aqil_research.sources.rights import (
    FIRST_LIVE_OPERATIONS,
    REGISTER_COLUMNS,
    AttributionRequirement,
    M1Role,
    OperationalStatus,
    RightsOperation,
    SourceRightsError,
    SourceRightsRecord,
    load_source_rights,
    operation_allowed,
    source_usable,
)


def _write_register(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=REGISTER_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def _row(**overrides: str) -> dict[str, str]:
    base = {
        "source_id": "example_source",
        "dataset_id": "example.dataset",
        "provider_name": "Example provider",
        "publication_name": "Example publication",
        "geography": "US",
        "series_or_dataset_code": "EXAMPLE",
        "category": "test",
        "access_description": "Synthetic row for the rights gate.",
        "access_url": "https://example.com/access",
        "terms_url": "https://example.com/terms",
        "evidence_urls": "https://example.com/terms|https://example.com/access",
        "auth_requirement": "None",
        "automated_access": "permitted",
        "internal_computation": "permitted",
        "raw_data_retention": "unknown",
        "historical_archiving": "unknown",
        "redistribution": "prohibited",
        "commercial_publication": "unknown",
        "ai_processing": "unknown",
        "ai_model_training": "unknown",
        "attribution": "required",
        "m1_role": "unresolved",
        "operational_status": "enabled",
        "conditions": "Synthetic conditions.",
        "revision_behaviour": "Not a real series.",
        "unresolved_questions": "Synthetic uncertainty.",
        "evidence_note": "Synthetic evidence for the loader test.",
        "assessed_on": "2026-10-17",
    }
    base.update(overrides)
    return base


def test_register_loader_has_no_provider_client() -> None:
    import aqil_research.sources.rights as rights

    source = inspect.getsource(rights)
    assert "httpx" not in source
    assert "urlopen" not in source


def test_canonical_register_links_evidence_and_separates_datasets() -> None:
    records = load_source_rights()
    by_dataset = {record.dataset_id: record for record in records}

    assert set(by_dataset) == {
        "bls.ln.LNS14000000",
        "bls.empsit.archive",
        "fred.alfred.UNRATE",
        "treasury.xml.daily_treasury_yield_curve",
        "fiscal.avg_interest_rates",
        "board.h15.treasury_yields",
        "forward.fomc.schedule",
        "forward.bls.empsit.schedule",
        "forward.etf.vwra.holdings",
        "forward.etf.ishares.holdings",
        "forward.bls.selected_releases.schedule",
        "forward.bea.news.schedule",
        "forward.sec.edgar.completed_filings",
        "forward.company_ir.watchlist",
    }
    for record in records:
        assert record.terms_url in record.evidence_urls
        assert record.evidence_note
        if record.dataset_id.startswith("forward."):
            assert record.assessed_on.isoformat() == "2026-10-18"
        else:
            assert record.assessed_on.isoformat() == "2026-10-17"

    unemployment = by_dataset["bls.ln.LNS14000000"]
    assert unemployment.m1_role == M1Role.FIRST_LIVE_PROVIDER
    assert unemployment.series_or_dataset_code == "LNS14000000"
    assert source_usable(unemployment, RightsOperation.INTERNAL_COMPUTATION)
    assert source_usable(unemployment, RightsOperation.COMMERCIAL_PUBLICATION)
    assert not source_usable(unemployment, RightsOperation.AI_MODEL_TRAINING)
    assert not operation_allowed(unemployment, RightsOperation.AI_PROCESSING)

    fred = by_dataset["fred.alfred.UNRATE"]
    assert fred.m1_role == M1Role.INELIGIBLE
    assert fred.operational_status == OperationalStatus.ENABLED
    assert not source_usable(fred, RightsOperation.HISTORICAL_ARCHIVING)
    assert not source_usable(fred, RightsOperation.RAW_DATA_RETENTION)
    assert not source_usable(fred, RightsOperation.AI_PROCESSING)
    assert not source_usable(fred, RightsOperation.AI_MODEL_TRAINING)
    assert not operation_allowed(fred, RightsOperation.COMMERCIAL_PUBLICATION)

    treasury = by_dataset["treasury.xml.daily_treasury_yield_curve"]
    fiscal = by_dataset["fiscal.avg_interest_rates"]
    board = by_dataset["board.h15.treasury_yields"]
    assert treasury.dataset_id != fiscal.dataset_id
    assert treasury.dataset_id != board.dataset_id
    assert fiscal.m1_role == M1Role.NOT_A_MODEL_INPUT
    assert source_usable(fiscal, RightsOperation.COMMERCIAL_PUBLICATION)
    assert not source_usable(treasury, RightsOperation.COMMERCIAL_PUBLICATION)
    assert not source_usable(treasury, RightsOperation.AUTOMATED_ACCESS)
    assert board.m1_role == M1Role.YIELD_CURVE_CANDIDATE
    assert board.series_or_dataset_code == "unconfirmed"
    assert source_usable(board, RightsOperation.REDISTRIBUTION)
    assert not source_usable(board, RightsOperation.AI_MODEL_TRAINING)

    first_live = [record for record in records if record.m1_role == M1Role.FIRST_LIVE_PROVIDER]
    assert first_live == [unemployment]
    assert all(operation_allowed(unemployment, operation) for operation in FIRST_LIVE_OPERATIONS)
    assert unemployment.attribution == AttributionRequirement.REQUIRED


def test_unknown_or_prohibited_rights_block_only_that_operation() -> None:
    record = SourceRightsRecord.model_validate(
        {**_row(), "evidence_urls": ("https://example.com/terms", "https://example.com/access")},
    )
    assert source_usable(record, RightsOperation.INTERNAL_COMPUTATION)
    assert not source_usable(record, RightsOperation.RAW_DATA_RETENTION)
    assert not source_usable(record, RightsOperation.REDISTRIBUTION)
    assert not operation_allowed(record, RightsOperation.COMMERCIAL_PUBLICATION)


def test_disabled_source_blocks_use_and_leaves_another_source_usable(tmp_path: Path) -> None:
    _write_register(
        tmp_path / "rights.csv",
        [
            _row(source_id="kept", dataset_id="example.kept", raw_data_retention="permitted"),
            _row(
                source_id="paused",
                dataset_id="example.paused",
                operational_status="disabled",
                raw_data_retention="permitted",
                internal_computation="permitted",
            ),
        ],
    )
    records = {record.source_id: record for record in load_source_rights(tmp_path / "rights.csv")}
    assert source_usable(records["kept"], RightsOperation.INTERNAL_COMPUTATION)
    assert records["paused"].operational_status == OperationalStatus.DISABLED
    assert operation_allowed(records["paused"], RightsOperation.INTERNAL_COMPUTATION)
    assert not source_usable(records["paused"], RightsOperation.INTERNAL_COMPUTATION)


def test_future_provider_loads_without_a_loader_change(tmp_path: Path) -> None:
    _write_register(
        tmp_path / "rights.csv",
        [_row(source_id="future_provider_not_in_code", dataset_id="future.dataset")],
    )
    records = load_source_rights(tmp_path / "rights.csv")
    assert records[0].source_id == "future_provider_not_in_code"
    assert not source_usable(records[0], RightsOperation.HISTORICAL_ARCHIVING)


def test_missing_evidence_url_is_rejected(tmp_path: Path) -> None:
    _write_register(tmp_path / "rights.csv", [_row(evidence_urls="")])
    with pytest.raises(SourceRightsError, match="evidence"):
        load_source_rights(tmp_path / "rights.csv")


def test_first_live_role_requires_cleared_operations(tmp_path: Path) -> None:
    _write_register(
        tmp_path / "rights.csv",
        [_row(m1_role="first_live_provider", raw_data_retention="unknown")],
    )
    with pytest.raises(SourceRightsError, match="not cleared"):
        load_source_rights(tmp_path / "rights.csv")
