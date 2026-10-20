import assert from "node:assert/strict";
import test from "node:test";

import { acceptJournalEvent, parseManualEntry, type ManualEntryInput } from "./journal-entry.ts";
import { replayJournal, type JournalEvent } from "./journal.ts";

const IDS = [
  "11111111-1111-4111-8111-111111111111",
  "22222222-2222-4222-8222-222222222222",
  "33333333-3333-4333-8333-333333333333",
  "44444444-4444-4444-8444-444444444444",
  "55555555-5555-4555-8555-555555555555",
  "66666666-6666-4666-8666-666666666666",
  "77777777-7777-4777-8777-777777777777",
];

function manual(partial: Partial<ManualEntryInput> & Pick<ManualEntryInput, "eventType" | "draftId">): JournalEvent {
  return parseManualEntry({
    eventType: partial.eventType,
    occurredOn: partial.occurredOn ?? "2024-01-02",
    accountId: partial.accountId ?? "account-a",
    currency: partial.currency ?? "SGD",
    cashAmount: partial.cashAmount ?? "",
    instrumentId: partial.instrumentId ?? "",
    quantity: partial.quantity ?? "",
    unitPrice: partial.unitPrice ?? "",
    splitNumerator: partial.splitNumerator ?? "",
    splitDenominator: partial.splitDenominator ?? "",
    draftId: partial.draftId,
  });
}

test("a manual deposit, buy, sell, fee, distribution and split reconcile in minor units", () => {
  const events = [
    manual({ eventType: "deposit", draftId: IDS[0] ?? "", cashAmount: "500.00" }),
    manual({
      eventType: "buy",
      draftId: IDS[1] ?? "",
      occurredOn: "2024-01-03",
      instrumentId: "fixture",
      quantity: "10",
      cashAmount: "100.00",
    }),
    manual({ eventType: "fee", draftId: IDS[2] ?? "", occurredOn: "2024-01-04", cashAmount: "5.00" }),
    manual({
      eventType: "distribution",
      draftId: IDS[3] ?? "",
      occurredOn: "2024-01-05",
      instrumentId: "fixture",
      cashAmount: "20.00",
    }),
    manual({
      eventType: "split",
      draftId: IDS[4] ?? "",
      occurredOn: "2024-01-06",
      instrumentId: "fixture",
      splitNumerator: "2",
      splitDenominator: "1",
    }),
    manual({
      eventType: "sell",
      draftId: IDS[5] ?? "",
      occurredOn: "2024-01-07",
      instrumentId: "fixture",
      quantity: "8",
      cashAmount: "60.00",
    }),
  ];
  let journal: JournalEvent[] = [];
  for (const event of events) {
    journal = acceptJournalEvent(journal, event, "SGD").events;
  }
  const result = replayJournal(journal, "SGD");
  assert.equal(result.positions[0]?.quantity, "12");
  assert.equal(result.positions[0]?.costMinor, 6000n);
  assert.equal(result.cash[0]?.amountMinor, 47500n);
  assert.equal(result.realisedProfit.status === "available" && result.realisedProfit.amountMinor, 2000n);
  assert.equal(result.netContributionsMinor, 50000n);
});

test("a repeated manual draft posts once", () => {
  const event = manual({ eventType: "deposit", draftId: IDS[0] ?? "", cashAmount: "10.00" });
  const first = acceptJournalEvent([], event, "SGD");
  const second = acceptJournalEvent(first.events, event, "SGD");
  assert.equal(second.added, false);
  assert.equal(second.events.length, 1);
  assert.equal(replayJournal(second.events, "SGD").cash[0]?.amountMinor, 1000n);
});

test("invalid currency and missing fields are rejected", () => {
  const draftId = IDS[0] ?? "";
  assert.throws(() => manual({ eventType: "deposit", draftId, currency: "XXX", cashAmount: "1.00" }), /invalid currency/);
  assert.throws(() => manual({ eventType: "deposit", draftId, currency: "US", cashAmount: "1.00" }), /invalid currency/);
  assert.throws(() => manual({ eventType: "deposit", draftId, currency: "", cashAmount: "1.00" }), /missing field/);
  assert.throws(() => manual({ eventType: "deposit", draftId, occurredOn: "2024-02-31", cashAmount: "1.00" }), /missing field/);
  assert.throws(() => manual({ eventType: "deposit", draftId, accountId: "", cashAmount: "1.00" }), /missing field/);
  assert.throws(() => manual({ eventType: "deposit", draftId, cashAmount: "" }), /missing field/);
  assert.throws(() => manual({ eventType: "deposit", draftId, cashAmount: "0" }), /invalid amount/);
  assert.throws(() => manual({ eventType: "deposit", draftId, cashAmount: "-5.00" }), /invalid amount/);
  assert.throws(() => manual({ eventType: "fee", draftId, cashAmount: "1.00", quantity: "1" }), /missing field/);
  assert.throws(() => manual({ eventType: "deposit", draftId, cashAmount: "1.00", instrumentId: "fixture" }), /missing field/);
  assert.throws(
    () => manual({ eventType: "buy", draftId, instrumentId: "fixture", quantity: "1" }),
    /missing field/,
  );
  assert.throws(
    () => manual({ eventType: "split", draftId, instrumentId: "fixture", splitNumerator: "2" }),
    /missing field/,
  );
  assert.throws(() => manual({ eventType: "transfer", draftId, cashAmount: "1.00" }), /missing field/);
});

test("a sell in another currency is rejected and does not change the journal", () => {
  const buy = manual({
    eventType: "buy",
    draftId: IDS[0] ?? "",
    instrumentId: "fixture",
    quantity: "1",
    cashAmount: "10.00",
  });
  const journal = acceptJournalEvent([], buy, "SGD").events;
  const sell = manual({
    eventType: "sell",
    draftId: IDS[1] ?? "",
    occurredOn: "2024-01-03",
    currency: "USD",
    instrumentId: "fixture",
    quantity: "1",
    cashAmount: "10.00",
  });
  assert.throws(() => acceptJournalEvent(journal, sell, "SGD"), /position currency does not match/);
  assert.equal(replayJournal(journal, "SGD").positions[0]?.quantity, "1");
});

test("a manual buy keeps the cash amount when the unit price does not match", () => {
  const event = manual({
    eventType: "buy",
    draftId: IDS[0] ?? "",
    instrumentId: "fixture",
    quantity: "10",
    cashAmount: "101.00",
    unitPrice: "10.00",
  });
  assert.equal(event.cashAmountMinor, -10100n);
  assert.equal(event.unitPriceMinor, null);
  assert.equal(replayJournal([event], "SGD").cash[0]?.amountMinor, -10100n);
});

test("a withdrawal reduces net contributions", () => {
  const journal = acceptJournalEvent(
    acceptJournalEvent([], manual({ eventType: "deposit", draftId: IDS[0] ?? "", cashAmount: "100.00" }), "SGD").events,
    manual({ eventType: "withdrawal", draftId: IDS[1] ?? "", occurredOn: "2024-01-03", cashAmount: "40.00" }),
    "SGD",
  ).events;
  const result = replayJournal(journal, "SGD");
  assert.equal(result.netContributionsMinor, 6000n);
  assert.equal(result.cash[0]?.amountMinor, 6000n);
});
