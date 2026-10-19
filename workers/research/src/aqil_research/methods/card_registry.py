"""Methodology card registry with fail-closed completeness checks (AQ-030)."""

from __future__ import annotations

from aqil_research.contracts.method_card import EvidenceStage, LicenceStatus, MethodCard

EVIDENCE_STAGE_LADDER: tuple[EvidenceStage, ...] = (
    EvidenceStage.DOCUMENTED,
    EvidenceStage.IMPLEMENTED,
    EvidenceStage.REPLICATED,
    EvidenceStage.HISTORICALLY_EVALUATED,
    EvidenceStage.PROSPECTIVELY_TESTING,
    EvidenceStage.PROSPECTIVELY_SUPPORTED,
)


class MethodCardRegistryError(Exception):
    """Raised when a card cannot enter the methodology registry."""


def _non_empty(text: str | None) -> bool:
    return bool(text and text.strip())


def validate_method_card_for_registry(card: MethodCard) -> None:
    """Reject cards missing origin, universe, equation, limitations or rights."""
    missing: list[str] = []
    if not _non_empty(card.primary_reference):
        missing.append("origin")
    if not _non_empty(card.original_universe):
        missing.append("universe")
    if not _non_empty(card.formula_specification):
        missing.append("equation")
    if not card.limitations or not all(_non_empty(item) for item in card.limitations):
        missing.append("limitations")
    if card.licence_status == LicenceStatus.UNKNOWN:
        missing.append("rights")
    if missing:
        raise MethodCardRegistryError(
            f"method card {card.method_id} rejected; missing or empty: {', '.join(missing)}",
        )


def assert_evidence_stage_advance(
    current: EvidenceStage,
    proposed: EvidenceStage,
) -> None:
    """Scientific status ladder — no skipping forward; degraded/retired are explicit exits."""
    if proposed in (EvidenceStage.DEGRADED, EvidenceStage.RETIRED):
        return
    if current in (EvidenceStage.DEGRADED, EvidenceStage.RETIRED):
        raise MethodCardRegistryError(
            f"cannot advance from terminal stage {current.value} to {proposed.value}",
        )
    try:
        current_index = EVIDENCE_STAGE_LADDER.index(current)
        proposed_index = EVIDENCE_STAGE_LADDER.index(proposed)
    except ValueError as exc:
        raise MethodCardRegistryError(f"unknown evidence stage: {exc}") from exc
    if proposed_index > current_index + 1:
        raise MethodCardRegistryError(
            f"cannot skip evidence stages from {current.value} to {proposed.value}",
        )


class MethodologyCardRegistry:
    """In-memory methodology registry keyed by method_id."""

    def __init__(self) -> None:
        self._cards: dict[str, MethodCard] = {}

    def register(self, card: MethodCard) -> None:
        validate_method_card_for_registry(card)
        if card.method_id in self._cards:
            raise MethodCardRegistryError(f"duplicate method_id: {card.method_id}")
        self._cards[card.method_id] = card

    def get(self, method_id: str) -> MethodCard:
        card = self._cards.get(method_id)
        if card is None:
            raise MethodCardRegistryError(f"unknown method_id: {method_id}")
        return card

    def evidence_stage(self, method_id: str) -> EvidenceStage:
        return self.get(method_id).evidence_stage

    def method_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._cards))


__all__ = [
    "EVIDENCE_STAGE_LADDER",
    "MethodCardRegistryError",
    "MethodologyCardRegistry",
    "assert_evidence_stage_advance",
    "validate_method_card_for_registry",
]
