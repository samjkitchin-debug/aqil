"""AQ-030 — incomplete method cards are rejected from the registry."""

from __future__ import annotations

from pathlib import Path

import pytest

from aqil_research.contracts.method_card import EvidenceStage, LicenceStatus, MethodCard
from aqil_research.methods.card_registry import (
    MethodCardRegistryError,
    MethodologyCardRegistry,
    assert_evidence_stage_advance,
    validate_method_card_for_registry,
)


def _complete_sahm_card() -> MethodCard:
    path = Path(__file__).parent / "fixtures" / "sahm_method_card.v1.json"
    card = MethodCard.model_validate_json(path.read_text(encoding="utf-8"))
    return card.model_copy(update={"licence_status": LicenceStatus.PERMITTED_PRIVATE})


def test_complete_method_card_registers() -> None:
    card = _complete_sahm_card()
    validate_method_card_for_registry(card)
    registry = MethodologyCardRegistry()
    registry.register(card)
    assert registry.evidence_stage(card.method_id) == EvidenceStage.IMPLEMENTED


def test_missing_rights_rejected() -> None:
    path = Path(__file__).parent / "fixtures" / "sahm_method_card.v1.json"
    card = MethodCard.model_validate_json(path.read_text(encoding="utf-8"))
    assert card.licence_status == LicenceStatus.UNKNOWN
    with pytest.raises(MethodCardRegistryError, match="rights"):
        validate_method_card_for_registry(card)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("primary_reference", ""),
        ("original_universe", "  "),
        ("formula_specification", None),
        ("limitations", []),
        ("limitations", [""]),
    ],
)
def test_incomplete_method_card_rejected(field: str, value: object) -> None:
    card = _complete_sahm_card().model_copy(update={field: value})
    with pytest.raises(MethodCardRegistryError):
        validate_method_card_for_registry(card)


def test_evidence_stage_cannot_skip_forward() -> None:
    with pytest.raises(MethodCardRegistryError, match="skip"):
        assert_evidence_stage_advance(
            EvidenceStage.DOCUMENTED,
            EvidenceStage.REPLICATED,
        )


def test_evidence_stage_allows_single_step() -> None:
    assert_evidence_stage_advance(EvidenceStage.DOCUMENTED, EvidenceStage.IMPLEMENTED)


def test_duplicate_method_id_rejected() -> None:
    card = _complete_sahm_card()
    registry = MethodologyCardRegistry()
    registry.register(card)
    with pytest.raises(MethodCardRegistryError, match="duplicate"):
        registry.register(card)
