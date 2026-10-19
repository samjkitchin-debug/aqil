import assert from "node:assert/strict";
import test from "node:test";

import type { BrokerPortfolioView } from "../saxo/portfolio.ts";
import { deploymentFromPortfolio } from "./from-portfolio.ts";
import { brokerHoldingKey } from "./holding-key.ts";

function broker(overrides: Partial<BrokerPortfolioView> = {}): BrokerPortfolioView {
  return {
    environment: "live",
    retrievedAt: "2026-10-18T07:35:05.317Z",
    coverage: { accounts: true, balances: true, netPositions: true, livePrices: false },
    accounts: [
      {
        label: "Main",
        currency: "SGD",
        cashBalance: "10",
        brokerReportedValue: "110",
        extendedReportedValue: null,
        buyingPower: "999",
      },
    ],
    holdings: [
      {
        accountLabel: "Main",
        name: "World equity ETF",
        symbol: "VWRA:xlon",
        assetType: "Etf",
        uic: 1,
        quantity: "4",
        currency: "SGD",
        tradingCurrency: "USD",
        price: "20",
        marketValue: "80",
        valueBasis: "broker-market-value",
        profitLoss: "5",
        lotCount: 1,
        classification: "unclassified",
      },
    ],
    limitations: [],
    ...overrides,
  };
}

const none = { targets: null, fx: [], instruments: null, additionalCashMinor: null, holdingClasses: {} };

test("reported cash is used and unclassified holdings are left out", () => {
  const result = deploymentFromPortfolio(broker(), none);
  assert.equal(result.available, true);
  assert.deepEqual(result.input.classValues, [
    { assetClass: "cash_investable", currency: "SGD", amountMinor: 1000n },
  ]);
  assert.equal(result.input.classValues.some((row) => row.amountMinor === 8000n), false);
  assert.equal(result.input.targets, null);
  assert.equal(result.input.additionalCashMinor, null);
  assert.equal(result.input.instruments, null);
  assert.equal(result.observedHoldings[0]?.name, "World equity ETF");
  assert.match(result.observedHoldings[0]?.reason ?? "", /Unclassified/);
});

test("buying power is not treated as cash", () => {
  const result = deploymentFromPortfolio(
    broker({
      accounts: [
        {
          label: "Main",
          currency: "SGD",
          cashBalance: "0",
          brokerReportedValue: "10",
          extendedReportedValue: null,
          buyingPower: "50",
        },
      ],
    }),
    none,
  );
  assert.equal(result.input.classValues[0]?.amountMinor, 0n);
});

test("a missing snapshot does not invent an account", () => {
  const result = deploymentFromPortfolio(null, none);
  assert.equal(result.available, false);
  assert.equal(result.input.classValues.length, 0);
  assert.match(result.limitations[0] ?? "", /No saved Saxo snapshot/);
});

test("a classified holding is included in the class total", () => {
  const holding = broker().holdings[0];
  assert.ok(holding);
  const key = brokerHoldingKey(holding);
  const result = deploymentFromPortfolio(broker(), {
    ...none,
    holdingClasses: { [key]: "global_equity" },
  });
  assert.equal(result.input.classValues.some((row) => row.assetClass === "global_equity" && row.amountMinor === 8000n), true);
  assert.match(result.observedHoldings[0]?.reason ?? "", /included/);
});
