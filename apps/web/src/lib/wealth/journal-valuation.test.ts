import assert from "node:assert/strict";
import test from "node:test";

import { parseManualEntry } from "./journal-entry.ts";
import { replayJournal } from "./journal.ts";
import { explainMarketValue, type SuppliedPrice, type SuppliedRate } from "./journal-valuation.ts";
import { emptyJournalFile } from "./journal-store.ts";
import { recordSuppliedPrice, recordSuppliedRate } from "./journal-workflow.ts";

const DRAFT = "11111111-1111-4111-8111-111111111111";

function buy() {
  return parseManualEntry({
    eventType: "buy",
    occurredOn: "2024-01-02",
    accountId: "account-a",
    currency: "SGD",
    cashAmount: "100.00",
    instrumentId: "fixture",
    quantity: "10",
    unitPrice: "",
    splitNumerator: "",
    splitDenominator: "",
    draftId: DRAFT,
  });
}

function price(asOf: string, unit = "11.00", currency = "SGD"): SuppliedPrice {
  const minor = unit === "11.00" ? 1100n : unit === "10.00" ? 1000n : 1250n;
  return { instrumentId: "fixture", currency, unitPriceMinor: minor, asOf, source: "supplied" };
}

test("an open holding has no market value until a price is supplied for that date", () => {
  const events = [buy()];
  const missing = explainMarketValue(events, [], [], "SGD", "2024-01-03");
  assert.equal(missing.market.status, "unavailable");
  if (missing.market.status === "unavailable") {
    assert.equal(missing.market.reason, "No price was supplied for fixture as of 2024-01-03.");
  }
  assert.equal(replayJournal(events, "SGD", [], []).marketValue.status, "unavailable");
});

test("a price on another date does not fill the gap", () => {
  const explained = explainMarketValue([buy()], [price("2024-01-01"), price("2024-01-04")], [], "SGD", "2024-01-03");
  assert.equal(explained.market.status, "unavailable");
  if (explained.market.status === "unavailable") {
    assert.match(explained.market.reason, /2024-01-03/);
  }
});

test("a supplied price for that date is the market value", () => {
  const explained = explainMarketValue([buy()], [price("2024-01-02")], [], "SGD", "2024-01-02");
  assert.deepEqual(explained.market, {
    status: "available",
    currency: "SGD",
    amountMinor: 11000n,
    asOf: "2024-01-02",
    source: "supplied",
  });
});

test("a price in another currency stays unavailable", () => {
  const explained = explainMarketValue([buy()], [price("2024-01-02", "12.50", "USD")], [], "SGD", "2024-01-02");
  assert.equal(explained.market.status, "unavailable");
  if (explained.market.status === "unavailable") {
    assert.match(explained.market.reason, /does not match the holding currency SGD/);
  }
});

test("foreign value without an exchange rate stays unavailable", () => {
  const event = parseManualEntry({
    eventType: "buy",
    occurredOn: "2024-01-02",
    accountId: "account-a",
    currency: "USD",
    cashAmount: "100.00",
    instrumentId: "fixture",
    quantity: "10",
    unitPrice: "",
    splitNumerator: "",
    splitDenominator: "",
    draftId: DRAFT,
  });
  const explained = explainMarketValue([event], [price("2024-01-02", "12.50", "USD")], [], "SGD", "2024-01-02");
  assert.equal(explained.market.status, "unavailable");
  if (explained.market.status === "unavailable") {
    assert.equal(explained.market.reason, "No exchange rate was supplied from USD to SGD as of 2024-01-02.");
  }
});

test("a supplied rate on that date converts the market value", () => {
  const event = parseManualEntry({
    eventType: "buy",
    occurredOn: "2024-01-02",
    accountId: "account-a",
    currency: "USD",
    cashAmount: "100.00",
    instrumentId: "fixture",
    quantity: "10",
    unitPrice: "",
    splitNumerator: "",
    splitDenominator: "",
    draftId: DRAFT,
  });
  const rate: SuppliedRate = {
    baseCurrency: "USD",
    quoteCurrency: "SGD",
    rate: "1.35",
    asOf: "2024-01-02",
    source: "supplied",
  };
  const explained = explainMarketValue([event], [price("2024-01-02", "12.50", "USD")], [rate], "SGD", "2024-01-02");
  assert.equal(explained.market.status, "available");
  if (explained.market.status === "available") assert.equal(explained.market.amountMinor, 16875n);
});

test("a zero price and a non-reporting rate are rejected", () => {
  const file = emptyJournalFile();
  assert.throws(
    () => recordSuppliedPrice(file, { instrumentId: "fixture", currency: "SGD", unitPrice: "0", asOf: "2024-01-02" }),
    /invalid amount/,
  );
  assert.throws(
    () => recordSuppliedRate(file, { baseCurrency: "USD", quoteCurrency: "EUR", rate: "1.1", asOf: "2024-01-02" }),
    /invalid rate/,
  );
  assert.throws(
    () => recordSuppliedRate(file, { baseCurrency: "JPY", quoteCurrency: "SGD", rate: "1", asOf: "2024-01-02" }),
    /invalid rate/,
  );
});

function recordPriceOn(file: ReturnType<typeof emptyJournalFile>, asOf: string) {
  return recordSuppliedPrice(file, { instrumentId: "fixture", currency: "SGD", unitPrice: "11.00", asOf });
}

test("the same supplied price can be repeated and a different price conflicts", () => {
  const once = recordPriceOn(emptyJournalFile(), "2024-01-02");
  const twice = recordSuppliedPrice(once, { instrumentId: "fixture", currency: "SGD", unitPrice: "11.00", asOf: "2024-01-02" });
  assert.equal(twice.prices.length, 1);
  assert.throws(
    () => recordSuppliedPrice(once, { instrumentId: "fixture", currency: "SGD", unitPrice: "12.00", asOf: "2024-01-02" }),
    /conflict/,
  );
});
