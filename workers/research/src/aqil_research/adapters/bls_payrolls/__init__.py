"""BLS total nonfarm payrolls from the official CE flat file.

The current file is stored as latest_revised with availability_precision unknown.
A preliminary footnote on a printed number stays an observed current value.
It is not an earlier vintage. Blank months are omitted and are never stored as zero.

None of Sahm, SLOOS, Census advance orders, MACRO_CONDITIONS_PANEL, or
PERIOD_LEVEL_CHANGE consume dataset id bls.ce.CES0000000001. Sahm and
PERIOD_LEVEL_CHANGE require bls.ln.LNS14000000. SLOOS requires
fed.sloos.SUBLPDCILS_N.Q. Census advance orders requires census.m3.adv.MDM.NO.
MACRO_CONDITIONS_PANEL requires those three dataset ids.
"""

from aqil_research.adapters.bls_payrolls.adapter import BlsPayrollsAdapter

__all__ = ["BlsPayrollsAdapter"]
