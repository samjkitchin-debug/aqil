"""Catalogue family gates. Every founding family must appear here."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FamilyGate:
    family_name: str
    gate: str
    reason: str


def _blocked(name: str, reason: str) -> FamilyGate:
    return FamilyGate(name, "blocked", reason)


def _design(name: str, reason: str) -> FamilyGate:
    return FamilyGate(name, "design_only_not_executed", reason)


FAMILY_GATES: tuple[FamilyGate, ...] = (
    _design(
        "Absolute price momentum",
        (
            "Not executed. At least one input is a macro regime. No price-only subset of the 618 "
            "scenarios is carved out."
        ),
    ),
    _design(
        "Contribution timing policies",
        (
            "Not executed. Cash rates, VIX, and macro regimes are not decision inputs in this "
            "package. The pilot calendar is a new specification."
        ),
    ),
    _blocked(
        "Credit & lending",
        "Blocked. No point-in-time credit vintage is available for a portfolio decision.",
    ),
    _blocked(
        "Cross-macro interactions",
        (
            "Blocked. The named macro series do not have a vintage that covers a registered "
            "portfolio method."
        ),
    ),
    _design(
        "Drawdown & dip buying",
        "Not executed. The family mixes prices with CPI, credit, and unemployment inputs.",
    ),
    _blocked(
        "Earnings & profitability",
        "Blocked. Earnings revisions and profit margins are not stored.",
    ),
    _blocked(
        "FX & currency",
        (
            "Blocked. No foreign-exchange observations are stored, and the simulator refuses an "
            "unsupported conversion."
        ),
    ),
    _blocked(
        "Growth & production",
        (
            "Blocked. Do not replay a method on bea.vintage.real_gdp.pct_preceding. Other "
            "production vintages named here are not stored for a portfolio decision."
        ),
    ),
    _blocked(
        "Inflation & prices",
        "Blocked. No CPI vintage covers a registered portfolio method.",
    ),
    _blocked(
        "Labour & employment",
        "Blocked. Latest-revised labour observations are not an execution clock.",
    ),
    _blocked(
        "Liquidity & funding",
        "Blocked. Funding vintages and a cash-rate series for interest are not stored.",
    ),
    _blocked(
        "Macro methodology outputs",
        (
            "Blocked. No registered method is point-in-time on its own inputs. Do not replay one "
            "on the real GDP growth vintage."
        ),
    ),
    _blocked(
        "Macro plus market confirmation",
        "Blocked. The macro leg has no eligible point-in-time vintage for a portfolio decision.",
    ),
    _blocked(
        "Market breadth & participation",
        "Blocked. Constituent breadth is not stored.",
    ),
    _blocked(
        "Market structure and concentration",
        "Blocked. Historical holdings, NAV, and index weights are not stored.",
    ),
    _blocked(
        "Policy & interest rates",
        "Blocked. No point-in-time policy-rate vintage is tied to a registered portfolio method.",
    ),
    _blocked(
        "Rates & yield curve",
        "Blocked. Stored yields are not a point-in-time curve for a portfolio decision.",
    ),
    _design(
        "Rebalancing policies",
        (
            "Not executed. Holdings, covariance, and point-in-time regimes are not stored. The "
            "pilot rebalance is a separate specification."
        ),
    ),
    _blocked(
        "Regional and structural cycles",
        "Blocked. Regional vintages, foreign exchange, and total returns are not available.",
    ),
    _design(
        "Relative performance & rotation",
        (
            "Not executed. Some scenarios name stored tickers and some require a credit spread or "
            "an index that is not a stored listing."
        ),
    ),
    _blocked(
        "Risk control & exposure budgets",
        "Blocked. Holdings overlap and covariance inputs are not stored.",
    ),
    _design(
        "Sequence and lifecycle",
        "Not executed. Income paths are not stored. The pilot does not model a lifecycle.",
    ),
    _design(
        "Strategy governance & behavioural",
        (
            "Not executed. This family is a governance checklist. The investment-policy files were "
            "not edited."
        ),
    ),
    _blocked(
        "Structural transitions & shocks",
        (
            "Blocked. Macro releases and a recession chronology are not treated as point-in-time "
            "portfolio inputs."
        ),
    ),
    _blocked(
        "Valuation & earnings yield",
        "Blocked. Earnings and valuation histories are not stored.",
    ),
    _blocked(
        "Volatility & left-tail risk",
        (
            "Blocked. VIX history beyond the stored adjusted closes is not a licensed input "
            "in this package."
        ),
    ),
)


def gates_by_name() -> dict[str, FamilyGate]:
    return {gate.family_name: gate for gate in FAMILY_GATES}
