"""Federal Reserve H.8 bank-credit volumes.

This package reads one weekly level series. It does not read lending standards.
The Board file is latest-revised, not a vintage panel. None of Sahm, SLOOS,
Census advance orders, MACRO_CONDITIONS_PANEL, or PERIOD_LEVEL_CHANGE consumes
fed.h8.B1001NCBA.
"""

from aqil_research.adapters.fed_h8.adapter import FedH8Adapter, FedH8AdapterConfig

__all__ = ["FedH8Adapter", "FedH8AdapterConfig"]
