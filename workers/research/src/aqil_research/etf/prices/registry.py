"""Replaceable price-source slot. No vendor is selected unless a proof says so.

Saxo may occupy the primary slot only when the Saxo proof file records that
InfoPrices is entitled, daily charts are entitled, and retention is permitted.
A missing file, a 403, or a silent file leaves the slot unresolved. This module
does not invent a price and does not mark a gate passed.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict

SAXO_SOURCE_ID = "saxo_sim_infoprices"
UNRESOLVED_PRIMARY = "unresolved"
REPLACEABLE_PROVIDERS = ("saxo", "eodhd", "twelve_data")
PROOF_NAME = "SAXO_MARKET_DATA_PROOF_2026-11-02.md"


class PrimarySlot(BaseModel):
    """The selected price source. ``unresolved`` means none is selected."""

    model_config = ConfigDict(extra="forbid")

    provider_id: str
    reason: str
    infoprices_entitled: bool | None
    daily_charts_entitled: bool | None
    retention_permitted: bool | None


def default_proof_path() -> Path:
    """Path of the Saxo proof. Absence is a fact. The file is not created here."""

    for parent in Path(__file__).resolve().parents:
        candidate = parent / "docs" / "sources" / "etf" / PROOF_NAME
        if parent.name == "aqil" or candidate.is_file() or (parent / "docs").is_dir():
            if (parent / "docs" / "sources").is_dir():
                return candidate
    return Path(PROOF_NAME)


def resolve_primary(proof_text: str | None) -> PrimarySlot:
    """Choose a primary only from recorded Saxo facts. Otherwise stay unresolved."""

    if proof_text is None:
        return PrimarySlot(
            provider_id=UNRESOLVED_PRIMARY,
            reason=(
                "The Saxo proof file is absent. No price vendor is selected. "
                "EODHD and Twelve Data are replaceable adapters, not the primary."
            ),
            infoprices_entitled=None,
            daily_charts_entitled=None,
            retention_permitted=None,
        )
    infoprices = _fact(proof_text, "infoprices")
    charts = _fact(proof_text, "daily chart")
    retention = _fact(proof_text, "retention")
    if infoprices is True and charts is True and retention is True:
        return PrimarySlot(
            provider_id=SAXO_SOURCE_ID,
            reason=(
                "The Saxo proof records entitled InfoPrices, entitled daily charts, "
                "and permitted retention. Saxo occupies the primary slot."
            ),
            infoprices_entitled=True,
            daily_charts_entitled=True,
            retention_permitted=True,
        )
    return PrimarySlot(
        provider_id=UNRESOLVED_PRIMARY,
        reason=(
            "The Saxo proof does not record entitled InfoPrices, entitled daily charts, "
            "and permitted retention together. No vendor is selected."
        ),
        infoprices_entitled=infoprices,
        daily_charts_entitled=charts,
        retention_permitted=retention,
    )


def current_primary(path: Path | None = None) -> PrimarySlot:
    """Read the proof if it exists. A missing file is unresolved, not a price."""

    proof = path or default_proof_path()
    if not proof.is_file():
        return resolve_primary(None)
    return resolve_primary(proof.read_text(encoding="utf-8"))


def _fact(text: str, subject: str) -> bool | None:
    """True only when a line records the subject as entitled or permitted.

    A negation on that line wins. A line that merely names the subject stays
    unknown. HTTP 403 on that line is not entitlement.
    """

    seen_true = False
    for line in text.splitlines():
        lowered = line.lower()
        if subject not in lowered:
            continue
        if any(
            marker in lowered
            for marker in (
                "not entitled",
                "not permitted",
                "unentitled",
                "forbidden",
                "http 403",
                " 403",
            )
        ):
            return False
        if any(marker in lowered for marker in ("entitled", "permitted")):
            seen_true = True
    if seen_true:
        return True
    return None
