import assert from "node:assert/strict";
import test from "node:test";

import { normaliseSaxoPortfolio, repairStoredPortfolio } from "./portfolio.ts";
import { decryptJson, encryptJson, saxoEncryptionKey } from "./token-crypto.ts";

test("portfolio keeps cash, buying power and broker value separate", () => {
  const view = normaliseSaxoPortfolio({
    environment: "live",
    retrievedAt: "2026-10-18T00:00:00.000Z",
    pagesComplete: true,
    accountsBody: {
      Data: [{ AccountKey: "key-1", AccountId: "SHOULD-NOT-APPEAR", DisplayName: "Main", Currency: "SGD" }],
    },
    clientBalance: { TotalValue: 999, CashBalance: 999, Currency: "SGD" },
    accountBalances: [
      {
        AccountKey: "key-1",
        Currency: "SGD",
        CashBalance: 25,
        CashAvailableForTrading: 80,
        TotalValue: 125,
      },
    ],
    positionsBody: {
      Data: [
        {
          DisplayAndFormat: { Symbol: "VWRA", Description: "World equity", Currency: "USD" },
          PositionBase: { AccountId: "SHOULD-NOT-APPEAR", Amount: 3, AssetType: "Etf", Uic: 1 },
          PositionView: { CurrentPrice: 10 },
        },
      ],
    },
  });
  const serialised = JSON.stringify(view);
  assert.equal(serialised.includes("SHOULD-NOT-APPEAR"), false);
  assert.equal(serialised.includes("key-1"), false);
  assert.equal(view.accounts[0]?.cashBalance, "25");
  assert.equal(view.accounts[0]?.buyingPower, "80");
  assert.equal(view.accounts[0]?.brokerReportedValue, "125");
  assert.equal(view.accounts.some((account) => account.brokerReportedValue === "999"), false);
  assert.equal(view.holdings[0]?.price, "10");
  assert.equal(view.holdings[0]?.marketValue, null);
  assert.equal(view.holdings[0]?.classification, "unclassified");
  assert.equal(serialised.includes("isin"), false);
});

test("closed-market zeros do not hide cash, the account total or a consolidated holding", () => {
  const lots = [9, 17, 27, 13, 38, 130].map((amount) => ({
    DisplayAndFormat: { Symbol: "VWRA:xlon", Description: "World", Currency: "USD" },
    PositionBase: { Amount: amount, AssetType: "Etf", Uic: 21 },
    PositionView: { CurrentPrice: 0, MarketValue: 0, MarketValueOpen: 999 },
  }));
  const view = normaliseSaxoPortfolio({
    environment: "live",
    retrievedAt: "2026-10-18T07:14:00.000Z",
    pagesComplete: true,
    accountsBody: { Data: [{ AccountKey: "key-1", AccountId: "hidden", Currency: "SGD" }] },
    clientBalance: null,
    accountBalances: [
      {
        Currency: "SGD",
        CashBalance: 40,
        TotalValue: 200,
        CashAvailableForTrading: 90,
        ExtendedTradingHoursData: { TotalValue: 209 },
        MarginCollateralNotAvailableDetail: {
          InstrumentCollateralDetails: [
            { Uic: 21, Symbol: "VWRA:xlon", MarketValue: 160 },
            { Uic: 22, Symbol: "OTHER:xnas", MarketValue: 10 },
          ],
        },
      },
    ],
    positionsBody: { Data: lots },
    netPositionsBody: {
      Data: [
        {
          DisplayAndFormat: { Symbol: "VWRA:xlon", Description: "World", Currency: "USD" },
          NetPositionBase: { Amount: 234, AssetType: "Etf", Uic: 21 },
          NetPositionView: {
            CurrentPrice: 0,
            MarketValueOpen: 999,
            ProfitLossOnTradeInBaseCurrency: 5,
            PositionCount: 6,
          },
        },
        {
          DisplayAndFormat: { Symbol: "OTHER:xnas", Description: "World", Currency: "USD" },
          NetPositionBase: { Amount: 2, AssetType: "Stock", Uic: 22 },
          NetPositionView: { CurrentPrice: 0, MarketValueOpen: 999, PositionCount: 1 },
        },
      ],
    },
  });
  assert.equal(view.accounts[0]?.cashBalance, "40");
  assert.equal(view.accounts[0]?.brokerReportedValue, "200");
  assert.equal(view.accounts[0]?.extendedReportedValue, "209");
  assert.equal(view.accounts[0]?.buyingPower, "90");
  assert.equal(view.holdings.length, 2);
  assert.equal(view.holdings[0]?.quantity, "234");
  assert.equal(view.holdings[0]?.price, null);
  assert.equal(view.holdings[0]?.marketValue, "160");
  assert.equal(view.holdings[0]?.currency, "SGD");
  assert.equal(view.holdings[0]?.valueBasis, "broker-market-value");
  assert.equal(view.holdings[0]?.lotCount, 6);
  assert.equal(view.holdings[1]?.uic, 22);
  assert.equal(view.coverage.livePrices, false);
  assert.equal(view.coverage.balances, true);
  assert.equal(view.coverage.netPositions, true);
  assert.equal(JSON.stringify(view).includes("999"), false);
});

test("individual lots group by instrument when net positions are absent", () => {
  const view = normaliseSaxoPortfolio({
    environment: "live",
    retrievedAt: "2026-10-18T07:14:00.000Z",
    pagesComplete: false,
    accountsBody: { Data: [{ AccountKey: "key-1", Currency: "SGD" }] },
    clientBalance: { Currency: "SGD", CashBalance: 4, TotalValue: 30 },
    accountBalances: [{ Currency: "SGD", CashBalance: 4 }],
    positionsBody: {
      Data: [9, 17, 27, 13, 38, 130].map((amount) => ({
        DisplayAndFormat: { Symbol: "VWRA:xlon", Description: "World", Currency: "USD" },
        PositionBase: { Amount: amount, AssetType: "Etf", Uic: 21 },
        PositionView: { CurrentPrice: 0, MarketValue: 0 },
      })),
    },
  });
  assert.equal(view.holdings.length, 1);
  assert.equal(view.holdings[0]?.quantity, "234");
  assert.equal(view.holdings[0]?.lotCount, 6);
  assert.equal(view.accounts[0]?.brokerReportedValue, "30");
  assert.equal(view.coverage.netPositions, false);
  assert.match(view.limitations.join(" "), /not the full list/);
});

test("a fresh snapshot is not replaced by the legacy zero repair", () => {
  const fresh = normaliseSaxoPortfolio({
    environment: "live",
    retrievedAt: "2026-10-18T07:20:00.000Z",
    pagesComplete: true,
    accountsBody: { Data: [{ AccountKey: "key-1", Currency: "SGD" }] },
    clientBalance: null,
    accountBalances: [
      {
        Currency: "SGD",
        CashBalance: 2,
        TotalValue: 12,
        MarginCollateralNotAvailableDetail: { InstrumentCollateralDetails: [{ Uic: 21, MarketValue: 10 }] },
      },
    ],
    positionsBody: { Data: [] },
    netPositionsBody: {
      Data: [
        {
          DisplayAndFormat: { Symbol: "VWRA:xlon", Description: "World" },
          NetPositionBase: { Amount: 234, AssetType: "Etf", Uic: 21 },
          NetPositionView: { CurrentPrice: 0, MarketValue: 0, MarketValueOpen: 999 },
        },
      ],
    },
  });
  assert.equal(repairStoredPortfolio(fresh).holdings[0]?.marketValue, "10");
  const legacy = {
    ...fresh,
    coverage: undefined,
    holdings: [{ ...fresh.holdings[0], price: "0", marketValue: "0", valueBasis: null }],
  } as unknown as typeof fresh;
  assert.equal(repairStoredPortfolio(legacy).holdings[0]?.marketValue, null);
  assert.equal(repairStoredPortfolio(fresh).retrievedAt, fresh.retrievedAt);
});

test("token payload round-trips and rejects a changed ciphertext", () => {
  const key = saxoEncryptionKey(Buffer.alloc(32, 7).toString("base64"));
  assert.ok(key);
  const encrypted = encryptJson({ accessToken: "secret-token" }, key);
  assert.equal(encrypted.includes("secret-token"), false);
  assert.deepEqual(decryptJson(encrypted, key), { accessToken: "secret-token" });
  assert.equal(decryptJson(`${encrypted}x`, key), null);
  assert.equal(saxoEncryptionKey("too-short"), null);
});
