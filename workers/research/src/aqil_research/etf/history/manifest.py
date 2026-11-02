"""Dataset manifest for the frozen register. Prices are reported as absent."""

from __future__ import annotations

from aqil_research.etf.register.universe import (
    REGISTER_VERSION,
    TARGET_END,
    TARGET_START,
    UniverseInstrument,
    artifact_sha256,
)

SURVIVORSHIP_LIMIT = (
    "This is a founder-selected November 2026 universe. Funds that closed before "
    "selection are absent. A backtest of these instruments is not an unbiased "
    "historical ETF selection strategy."
)


def dataset_manifest(
    rows: tuple[UniverseInstrument, ...],
    *,
    stored_price_observations: int = 0,
    licensed_storage: str = "not established",
    histories: dict[str, str] | None = None,
) -> dict[str, object]:
    """Describe research dataset v1. Counts stay zero until rows are actually stored."""

    history_by_symbol = histories or {}
    return {
        "dataset_id": "aqil-etf-history-v1-2026-11",
        "register_version": REGISTER_VERSION,
        "register_sha256": artifact_sha256(),
        "target_start": TARGET_START,
        "target_end": TARGET_END,
        "instrument_count": len(rows),
        "approved_count": sum(1 for row in rows if row.investment_approved),
        "stored_price_observations": stored_price_observations,
        "licensed_storage": licensed_storage,
        "saxo_persistence": "refused",
        "fx_coverage": "absent",
        "distribution_treatment": {
            "accumulating": "do not add a dividend on top of an adjusted close",
            "distributing": (
                "INRG total return stays insufficient until a distribution series exists"
            ),
        },
        "survivorship": SURVIVORSHIP_LIMIT,
        "instruments": [
            {
                "symbol": row.research_symbol,
                "isin": row.isin,
                "mic": row.mic,
                "currency": row.listing_currency,
                "research_status": row.research_status,
                "inception_year": row.inception_year,
                "history": history_by_symbol.get(row.research_symbol, "not ingested"),
                "issuer_verified_at_import": False,
            }
            for row in rows
        ],
    }