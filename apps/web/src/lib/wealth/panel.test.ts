import assert from "node:assert/strict";
import test from "node:test";

import type { BrokerPortfolioView } from "../saxo/portfolio.ts";

import { BROKERAGE_SHARE_CLASS_UNRESOLVED, buildWealthPanel } from "./panel.ts";

function portfolio(overrides: Partial<BrokerPortfolioView> = {}): BrokerPortfolioView {
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
        extendedReportedValue: "115",
        buyingPower: "10",
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
        price: null,
        marketValue: "80",
        valueBasis: "broker-market-value",
        profitLoss: "5",
        lotCount: 2,
        classification: "unclassified",
      },
      {
        accountLabel: "Main",
        name: "Example company",
        symbol: "EX:xnas",
        assetType: "Stock",
        uic: 2,
        quantity: "3",
        currency: "SGD",
        tradingCurrency: "USD",
        price: null,
        marketValue: "20",
        valueBasis: "broker-market-value",
        profitLoss: "-2",
        lotCount: 1,
        classification: "unclassified",
      },
    ],
    limitations: ["Holdings are unclassified until you classify them."],
    ...overrides,
  };
}

test("the headline is the standard account value when it matches cash plus holdings", () => {
  const panel = buildWealthPanel({ broker: portfolio(), link: "expired", error: "refresh_failed" });
  assert.equal(panel.headline?.amount, "110.00");
  assert.equal(panel.headline?.currency, "SGD");
  assert.equal(panel.headline?.basis, "Standard account value");
  assert.equal(panel.extended?.amount, "115.00 SGD");
  assert.equal(panel.freshness.connection, "reconnect");
  assert.equal(panel.freshness.connectionLabel, "Reconnect Saxo");
  assert.equal(panel.freshness.prices, "Live prices unavailable");
  assert.equal(panel.chart, null);
  assert.equal(panel.monthReturn, null);
});

test("open-position gain is the sum of trade results and is not labelled as a period return", () => {
  const panel = buildWealthPanel({ broker: portfolio(), link: "active", error: null });
  assert.equal(panel.openPosition?.label, "Open-position gain");
  assert.equal(panel.openPosition?.amount, "+3.00 SGD");
  assert.equal(panel.openPosition?.period, "Since these positions were opened");
  assert.equal(panel.openPosition?.tone, "positive");
  assert.equal(panel.openPosition?.percentOfCost, "+3.1%");
  assert.equal(panel.freshness.connectionLabel, "Saxo is connected");
});

test("a missing open-position figure is not filled in with zero", () => {
  const broker = portfolio();
  broker.holdings[1] = { ...broker.holdings[1], profitLoss: null };
  const panel = buildWealthPanel({ broker, link: "refreshable", error: null });
  assert.equal(panel.openPosition, null);
  assert.equal(panel.holdings[1]?.openAmount, null);
  assert.equal(panel.freshness.connection, "saved");
});

test("composition uses the standard account value and keeps an ETF as one holding", () => {
  const panel = buildWealthPanel({ broker: portfolio(), link: "unknown", error: null });
  assert.equal(panel.composition?.basis, "Share of the standard account value");
  assert.equal(panel.composition?.etfNote, true);
  assert.deepEqual(
    panel.composition?.segments.map((segment) => [segment.label, segment.kind, segment.weightLabel]),
    [
      ["VWRA", "ETF", "72.7%"],
      ["EX", "Stock", "18.2%"],
      ["Cash", "Cash", "9.1%"],
    ],
  );
  assert.equal(panel.largest?.kind, "ETF");
  assert.equal(panel.largest?.weightLabel, "72.7%");
  assert.equal(panel.holdings[0]?.tone, "positive");
  assert.equal(panel.holdings[1]?.tone, "negative");
  assert.equal(panel.holdings[1]?.openAmount, "-2.00 SGD");
});

test("a time-weighted series stays separate from open-position gain", () => {
  const panel = buildWealthPanel({
    broker: portfolio({
      performance: {
        status: "ok",
        source: "saxo",
        scope: "client",
        period: "Month",
        currency: "SGD",
        retrievedAt: "2026-10-18T07:35:05.317Z",
        fieldGroups: ["Balance_AccountValue", "TimeWeighted_Accumulated"],
        accountValue: [
          { date: "2026-10-01", value: "100" },
          { date: "2026-10-18", value: "110" },
        ],
        timeWeightedAccumulated: [{ date: "2026-10-18", value: "0.012" }],
        returnUnit: "fraction",
      },
    }),
    link: "active",
    error: null,
  });
  assert.equal(panel.monthReturn?.label, "Time-weighted return");
  assert.equal(panel.monthReturn?.period, "This month");
  assert.equal(panel.monthReturn?.text, "+1.2%");
  assert.equal(panel.chart?.from, "2026-10-01");
  assert.equal(panel.chart?.to, "2026-10-18");
  assert.equal(panel.openPosition?.label, "Open-position gain");
});

test("holdings that do not add up to the account value do not invent a composition", () => {
  const broker = portfolio();
  broker.accounts[0] = { ...broker.accounts[0], brokerReportedValue: "500" };
  const panel = buildWealthPanel({ broker, link: "active", error: null });
  assert.equal(panel.headline?.amount, "500.00");
  assert.equal(panel.composition, null);
  assert.equal(panel.largest, null);
  assert.equal(panel.holdings[0]?.weightLabel, null);
});

test("open-position loss uses negative tone and label", () => {
  const broker = portfolio();
  broker.holdings = broker.holdings.map((holding) => ({ ...holding, profitLoss: "-4" }));
  broker.holdings[0] = { ...broker.holdings[0], profitLoss: "-6" };
  const panel = buildWealthPanel({ broker, link: "active", error: null });
  assert.equal(panel.openPosition?.label, "Open-position loss");
  assert.equal(panel.openPosition?.tone, "negative");
  assert.match(panel.openPosition?.amount ?? "", /^-/);
  assert.equal(panel.holdings[0]?.tone, "negative");
});

test("account value chart is omitted when Saxo returns fewer than two points", () => {
  const panel = buildWealthPanel({
    broker: portfolio({
      performance: {
        status: "ok",
        source: "saxo",
        scope: "client",
        period: "Month",
        currency: "SGD",
        retrievedAt: "2026-10-18T07:35:05.317Z",
        fieldGroups: ["Balance_AccountValue"],
        accountValue: [{ date: "2026-10-18", value: "110" }],
        timeWeightedAccumulated: [],
        returnUnit: "fraction",
      },
    }),
    link: "active",
    error: null,
  });
  assert.equal(panel.chart, null);
});

test("reconnect is distinct from a saved snapshot", () => {
  const reconnect = buildWealthPanel({ broker: portfolio(), link: "expired", error: "no_session" });
  assert.equal(reconnect.freshness.connection, "reconnect");
  assert.equal(reconnect.freshness.connectionLabel, "Reconnect Saxo");

  const saved = buildWealthPanel({ broker: portfolio(), link: "refreshable", error: null });
  assert.equal(saved.freshness.connection, "saved");
  assert.equal(saved.freshness.connectionLabel, "Saved snapshot");

  const connected = buildWealthPanel({ broker: portfolio(), link: "active", error: null });
  assert.equal(connected.freshness.connection, "connected");
  assert.equal(connected.freshness.connectionLabel, "Saxo is connected");
});

test("a brokerage line stays unresolved without an ISIN", () => {
  assert.equal(
    BROKERAGE_SHARE_CLASS_UNRESOLVED,
    "The share class is unresolved because the saved line has no ISIN.",
  );
  assert.doesNotMatch(BROKERAGE_SHARE_CLASS_UNRESOLVED, /VWRA|ticker/i);
  const panel = buildWealthPanel({ broker: portfolio(), link: "active", error: null });
  assert.equal("isin" in panel.holdings[0], false);
});

test("simulation environment is labelled separately from live", () => {
  const panel = buildWealthPanel({
    broker: portfolio({ environment: "simulation" }),
    link: "active",
    error: null,
  });
  assert.equal(panel.simulation, true);
  assert.equal(panel.freshness.environment, "Simulation account");
});
