"""ETF share-class contract and fail-closed rights fragments."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from uuid import UUID

import jsonschema
import pytest
from pydantic import ValidationError

from aqil_research.etf.contracts import (
    BenchmarkReturn,
    EtfRightsError,
    EtfShareClass,
    FundReturn,
    assert_automated_collection_allowed,
    holdings_cleared_for_read,
    load_etf_rights_fragment,
    share_class_field_names,
)
from aqil_research.sources.rights import (
    AttributionRequirement,
    M1Role,
    OperationalStatus,
    RightsDecision,
    SourceRightsRecord,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
FRAGMENTS = REPO_ROOT / "docs" / "sources" / "etf" / "fragments"


def _schema() -> dict:
    return json.loads(
        (REPO_ROOT / "docs" / "schemas" / "etf_share_class.v1.json").read_text(encoding="utf-8")
    )


def _shape_fixture() -> EtfShareClass:
    """Shape only. This ISIN is not a verified fund."""
    return EtfShareClass(
        isin="IE00B0000009",
        base_currency="USD",
        distribution_policy="unknown",
        hedge_status="unknown",
        inception_date=None,
        evidence_status="unverified",
        benchmark_id=None,
        listings=[],
    )


def test_share_class_schema_mirror_and_model() -> None:
    schema = _schema()
    mirror = json.loads(
        (REPO_ROOT / "packages" / "contracts" / "schemas" / "etf_share_class.v1.json").read_text(
            encoding="utf-8"
        )
    )
    assert mirror == schema
    assert share_class_field_names() == tuple(schema["required"])
    assert tuple(EtfShareClass.model_fields) == tuple(schema["required"])
    payload = _shape_fixture().model_dump(mode="json")
    jsonschema.validate(payload, schema)
    payload.pop("isin")
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(payload, schema)


def test_fund_return_refuses_pre_inception_and_benchmark_is_separate() -> None:
    with pytest.raises(ValidationError):
        FundReturn(
            share_class_isin="IE00B0000009",
            inception_date=date(2020, 6, 1),
            period_start=date(2019, 1, 1),
            period_end=date(2019, 12, 31),
            currency="USD",
            return_type="total_return",
            reinvestment="reinvested",
            value_text="1.0",
            source_id="fixture",
            source_locator="synthetic://aqil/etf/fund-return",
        )
    benchmark = BenchmarkReturn(
        benchmark_id=UUID("88888888-8888-4888-8888-888888888888"),
        period_start=date(2010, 1, 1),
        period_end=date(2010, 12, 31),
        currency="USD",
        return_convention="price",
        reinvestment="not_reinvested",
        value_text="1.0",
        source_id="fixture",
        source_locator="synthetic://aqil/etf/benchmark-return",
    )
    assert "share_class_isin" not in BenchmarkReturn.model_fields
    assert benchmark.return_convention == "price"


def test_rights_fragments_refuse_automated_collection() -> None:
    paths = sorted(FRAGMENTS.glob("*.csv"))
    assert paths, "ETF rights fragments are missing"
    for path in paths:
        record = load_etf_rights_fragment(path)
        assert record.automated_access in {RightsDecision.PROHIBITED, RightsDecision.UNKNOWN}
        assert not holdings_cleared_for_read(record)
        with pytest.raises(EtfRightsError):
            assert_automated_collection_allowed(record)


def test_permitted_record_is_the_only_open_gate() -> None:
    cleared = _record(RightsDecision.PERMITTED, RightsDecision.PERMITTED, OperationalStatus.ENABLED)
    assert_automated_collection_allowed(cleared)
    assert holdings_cleared_for_read(cleared)
    unknown = _record(RightsDecision.UNKNOWN, RightsDecision.UNKNOWN, OperationalStatus.DISABLED)
    with pytest.raises(EtfRightsError):
        assert_automated_collection_allowed(unknown)
    assert not holdings_cleared_for_read(unknown)


def _record(
    automated_access: RightsDecision,
    redistribution: RightsDecision,
    status: OperationalStatus,
) -> SourceRightsRecord:
    return SourceRightsRecord(
        source_id="fixture_etf_rights",
        dataset_id="fixture.etf",
        provider_name="Fixture",
        publication_name="Fixture",
        geography="IE",
        series_or_dataset_code="fixture",
        category="etf_reference",
        access_description="In-memory fixture. No provider was contacted.",
        access_url="https://example.com/access",
        terms_url="https://example.com/terms",
        evidence_urls=("https://example.com/terms",),
        auth_requirement="None.",
        automated_access=automated_access,
        internal_computation=RightsDecision.UNKNOWN,
        raw_data_retention=RightsDecision.UNKNOWN,
        historical_archiving=RightsDecision.UNKNOWN,
        redistribution=redistribution,
        commercial_publication=RightsDecision.UNKNOWN,
        ai_processing=RightsDecision.UNKNOWN,
        ai_model_training=RightsDecision.UNKNOWN,
        attribution=AttributionRequirement.UNKNOWN,
        m1_role=M1Role.UNRESOLVED,
        operational_status=status,
        conditions="Fixture only.",
        revision_behaviour="None.",
        unresolved_questions="None.",
        evidence_note="Not a provider assessment.",
        assessed_on=date(2026, 10, 23),
    )
