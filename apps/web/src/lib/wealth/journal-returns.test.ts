import assert from "node:assert/strict";
import test from "node:test";

import {
  moneyWeightedReturn,
  solveXirr,
  timeWeightedReturn,
  TWR_UNAVAILABLE,
  XIRR_UNAVAILABLE,
} from "./journal-returns.ts";
import { emptyJournalFile } from "./journal-store.ts";
import { appendManualEntry, recordSuppliedPrice, summariseJournal } from "./journal-workflow.ts";

const START = "11111111-1111-4111-8111-111111111111";
const BUY = "22222222-2222-4222-8222-222222222222";

function tenPercentFile(prices: string[]) {
  let file = emptyJournalFile();
  file = appendManualEntry(file, {
    eventType: "deposit",
    occurredOn: "2023-01-01",
    accountId: "account-a",
    currency: "SGD",
    cashAmount: "100.00",
    instrumentId: "",
    quantity: "",
    unitPrice: "",
    splitNumerator: "",
    splitDenominator: "",
    draftId: START,
  });
  file = appendManualEntry(file, {
    eventType: "buy",
    occurredOn: "2023-01-01",
    accountId: "account-a",
    currency: "SGD",
    cashAmount: "100.00",
    instrumentId: "fixture",
    quantity: "1",
    unitPrice: "",
    splitNumerator: "",
    splitDenominator: "",
    draftId: BUY,
  });
  for (const asOf of prices) {
    const unitPrice = asOf === "2023-01-01" ? "100.00" : "110.00";
    file = recordSuppliedPrice(file, { instrumentId: "fixture", currency: "SGD", unitPrice, asOf });
  }
  return file;
}

test("money-weighted return matches the one-year ten percent reference", () => {
  const solved = moneyWeightedReturn({
    contributions: [{ occurredOn: "2023-01-01", amountMinor: 10000n }],
    terminal: { asOf: "2024-01-01", amountMinor: 11000n },
  });
  assert.deepEqual(solved, { status: "available", rate: "0.10000000", from: "2023-01-01", to: "2024-01-01" });
  const summary = summariseJournal(tenPercentFile(["2024-01-01"]), "2024-01-01");
  assert.deepEqual(summary.xirr, solved);
  assert.equal(summary.unrealisedGain.status, "available");
  if (summary.unrealisedGain.status === "available") assert.equal(summary.unrealisedGain.amountMinor, 1000n);
});

test("money-weighted return stays unavailable when the cashflows do not solve", () => {
  assert.deepEqual(
    solveXirr([
      { occurredOn: "2023-01-01", amountMinor: -1000n },
      { occurredOn: "2024-01-01", amountMinor: -1000n },
    ]),
    { status: "unavailable", reason: XIRR_UNAVAILABLE },
  );
  assert.deepEqual(
    moneyWeightedReturn({
      contributions: [{ occurredOn: "2023-01-01", amountMinor: 10000n }],
      terminal: null,
    }),
    { status: "unavailable", reason: XIRR_UNAVAILABLE },
  );
  const summary = summariseJournal(tenPercentFile([]), "2024-01-01");
  assert.equal(summary.xirr.status, "unavailable");
  assert.equal(summary.market.status, "unavailable");
});

test("time-weighted return matches the one-year ten percent reference when both dates are valued", () => {
  const summary = summariseJournal(tenPercentFile(["2023-01-01", "2024-01-01"]), "2024-01-01");
  assert.deepEqual(summary.twr, {
    status: "available",
    rate: "0.10000000",
    from: "2023-01-01",
    to: "2024-01-01",
  });
});

test("time-weighted return stays unavailable without an interim valuation", () => {
  assert.deepEqual(
    timeWeightedReturn({
      points: [
        { asOf: "2023-01-01", amountMinor: 10000n },
        { asOf: "2024-01-01", amountMinor: 11000n },
      ],
      contributions: [{ occurredOn: "2023-06-01", amountMinor: 1000n }],
      asOf: "2024-01-01",
    }),
    { status: "unavailable", reason: TWR_UNAVAILABLE },
  );
  const summary = summariseJournal(tenPercentFile(["2024-01-01"]), "2024-01-01");
  assert.equal(summary.twr.status, "unavailable");
  if (summary.twr.status === "unavailable") assert.equal(summary.twr.reason, TWR_UNAVAILABLE);
});
