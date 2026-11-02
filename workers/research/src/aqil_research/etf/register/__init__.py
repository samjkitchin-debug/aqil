"""Frozen founder register ETF_UNIVERSE_V1_2026-11-03.

The supplied file is the decision. This package does not add instruments and
does not treat research approval as permission to trade.
"""

from aqil_research.etf.register.universe import (
    RegisterError,
    UniverseInstrument,
    load_universe_v1,
)

__all__ = ["RegisterError", "UniverseInstrument", "load_universe_v1"]
