import type { WealthSnapshot } from "./types";

/** Synthetic founder fixture — technology concentration; no real portfolio values. */
export function syntheticTechConcentrationFixture(): WealthSnapshot {
  return {
    source: "fixture",
    profile: {
      baseCurrency: "SGD",
      emergencyReserveMinor: 150_000n,
    },
    positions: [
      {
        id: "fix-vwra",
        isin: "IE00BK5BQT80",
        symbol: "VWRA",
        name: "Vanguard FTSE All-World UCITS ETF (acc)",
        assetClass: "global_equity",
        thematicLabel: null,
        currency: "SGD",
        marketValueMinor: 420_000_00n,
        valuationDate: "2026-10-15",
      },
      {
        id: "fix-semis",
        isin: "IE00BMC38736",
        symbol: "SMH",
        name: "Synthetic semiconductor thematic fund (fixture)",
        assetClass: "thematic_technology",
        thematicLabel: "Semiconductors",
        currency: "SGD",
        marketValueMinor: 280_000_00n,
        valuationDate: "2026-10-15",
      },
      {
        id: "fix-bonds",
        isin: "IE00B4WXJJ64",
        symbol: "AGGU",
        name: "Synthetic investment-grade bond fund (fixture)",
        assetClass: "investment_grade_bonds",
        thematicLabel: null,
        currency: "SGD",
        marketValueMinor: 200_000_00n,
        valuationDate: "2026-10-15",
      },
    ],
    targets: [
      { assetClass: "global_equity", targetWeightBps: 7000 },
      { assetClass: "thematic_technology", targetWeightBps: 0 },
      { assetClass: "investment_grade_bonds", targetWeightBps: 3000 },
    ],
    contributionPlan: {
      amountMinor: 5_000_00n,
      currency: "SGD",
      cadence: "monthly",
      dayOfMonth: 1,
    },
    contributionHistory: [
      {
        id: "fix-c1",
        occurredAt: "2026-09-01T00:00:00.000Z",
        amountMinor: 5_000_00n,
        currency: "SGD",
        note: "Scheduled contribution (fixture)",
      },
      {
        id: "fix-c2",
        occurredAt: "2026-08-01T00:00:00.000Z",
        amountMinor: 5_000_00n,
        currency: "SGD",
        note: "Scheduled contribution (fixture)",
      },
    ],
    dataFreshness: {
      oldestValuationDate: "2026-10-15",
      missingValuationCount: 0,
    },
  };
}
