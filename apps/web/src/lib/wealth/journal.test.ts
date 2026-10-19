import assert from "node:assert/strict";
import test from "node:test";

import {
  effectiveJournalEvents,
  replayJournal,
  type JournalEvent,
} from "./journal.ts";

function leg(
  partial: Partial<JournalEvent> & Pick<JournalEvent, "eventId" | "eventType" | "idempotencyKey">,
): JournalEvent {
  return {
    accountId: "account-a",
    occurredOn: "2024-01-02",
    instrumentId: null,
    quantity: null,
    unitPriceMinor: null,
    cashAmountMinor: null,
    currency: "SGD",
    correctionOf: null,
    transferGroupId: null,
    splitNumerator: null,
    splitDenominator: null,
    ...partial,
  };
}

const fixture = [
  leg({
    eventId: "buy-1",
    eventType: "buy",
    idempotencyKey: "buy-1",
    instrumentId: "fixture-equity",
    quantity: "10",
    cashAmountMinor: -100000n,
  }),
  leg({
    eventId: "fee-1",
    eventType: "fee",
    idempotencyKey: "fee-1",
    occurredOn: "2024-01-03",
    cashAmountMinor: -500n,
  }),
  leg({
    eventId: "distribution-1",
    eventType: "distribution",
    idempotencyKey: "distribution-1",
    occurredOn: "2024-01-04",
    instrumentId: "fixture-equity",
    cashAmountMinor: 2000n,
  }),
  leg({
    eventId: "split-1",
    eventType: "split",
    idempotencyKey: "split-1",
    occurredOn: "2024-01-05",
    instrumentId: "fixture-equity",
    splitNumerator: 2,
    splitDenominator: 1,
  }),
  leg({
    eventId: "sell-1",
    eventType: "sell",
    idempotencyKey: "sell-1",
    occurredOn: "2024-01-06",
    instrumentId: "fixture-equity",
    quantity: "-8",
    cashAmountMinor: 60000n,
  }),
  leg({
    eventId: "cash-out",
    eventType: "transfer",
    idempotencyKey: "cash-out",
    occurredOn: "2024-01-07",
    cashAmountMinor: -10000n,
    transferGroupId: "group-cash",
  }),
  leg({
    eventId: "cash-in",
    eventType: "transfer",
    idempotencyKey: "cash-in",
    occurredOn: "2024-01-07",
    accountId: "account-b",
    cashAmountMinor: 10000n,
    transferGroupId: "group-cash",
  }),
];

test("buy, sell, fee, transfer, distribution and split reconcile in minor units", () => {
  const result = replayJournal(fixture, "SGD");
  assert.deepEqual(result.positions, [
    {
      accountId: "account-a",
      instrumentId: "fixture-equity",
      quantity: "12",
      costMinor: 60000n,
      currency: "SGD",
    },
  ]);
  assert.deepEqual(result.cash, [
    { accountId: "account-a", currency: "SGD", amountMinor: -48500n },
    { accountId: "account-b", currency: "SGD", amountMinor: 10000n },
  ]);
  assert.deepEqual(result.realisedProfit, {
    status: "available",
    currency: "SGD",
    amountMinor: 20000n,
  });
  assert.equal(result.netContributionsMinor, 0n);
  assert.deepEqual(result.reportingCash, {
    status: "available",
    currency: "SGD",
    amountMinor: -38500n,
  });
  assert.deepEqual(result.unbalancedTransferGroupIds, []);
});

test("an open position without a quote has no market value", () => {
  const result = replayJournal(fixture, "SGD", [], []);
  assert.deepEqual(result.marketValue, { status: "unavailable" });
});

test("a repeated idempotency key posts once and keeps the original identity", () => {
  const original = fixture[0];
  if (!original) throw new Error("missing buy");
  const effective = effectiveJournalEvents([original, { ...original }]);
  assert.deepEqual(effective.map((event) => event.eventId), ["buy-1"]);
  const result = replayJournal([original, { ...original }], "SGD");
  assert.deepEqual(result.cash, [
    { accountId: "account-a", currency: "SGD", amountMinor: -100000n },
  ]);
  assert.equal(result.positions[0]?.quantity, "10");
});

test("the same idempotency key cannot identify a different posting", () => {
  const original = fixture[0];
  if (!original) throw new Error("missing buy");
  assert.throws(
    () => replayJournal([original, { ...original, cashAmountMinor: -90000n }], "SGD"),
    /idempotency key already identifies a different event/,
  );
});

test("a correction replaces the original event and leaves contributions unchanged", () => {
  const original = fixture[0];
  if (!original) throw new Error("missing buy");
  const replacement = leg({
    eventId: "buy-2",
    eventType: "buy",
    idempotencyKey: "buy-2",
    instrumentId: "fixture-equity",
    quantity: "10",
    cashAmountMinor: -80000n,
    correctionOf: "buy-1",
  });
  const effective = effectiveJournalEvents([original, replacement]);
  assert.deepEqual(effective.map((event) => event.eventId), ["buy-2"]);
  const result = replayJournal([original, replacement], "SGD");
  assert.equal(result.positions[0]?.costMinor, 80000n);
  assert.equal(result.cash[0]?.amountMinor, -80000n);
  assert.equal(result.netContributionsMinor, 0n);
});

test("voiding an event removes it without inventing a reversing cash amount", () => {
  const original = fixture[0];
  if (!original) throw new Error("missing buy");
  const result = replayJournal(
    [
      original,
      leg({
        eventId: "void-1",
        eventType: "correction",
        idempotencyKey: "void-1",
        correctionOf: "buy-1",
      }),
    ],
    "SGD",
  );
  assert.deepEqual(result.positions, []);
  assert.deepEqual(result.cash, []);
  assert.deepEqual(result.realisedProfit, {
    status: "available",
    currency: "SGD",
    amountMinor: 0n,
  });
});

test("a sell without booked cash or a unit price leaves realised profit unavailable", () => {
  const result = replayJournal(
    [
      leg({
        eventId: "buy-unknown",
        eventType: "buy",
        idempotencyKey: "buy-unknown",
        instrumentId: "fixture-equity",
        quantity: "5",
      }),
      leg({
        eventId: "sell-unknown",
        eventType: "sell",
        idempotencyKey: "sell-unknown",
        occurredOn: "2024-02-01",
        instrumentId: "fixture-equity",
        quantity: "-5",
      }),
    ],
    "SGD",
  );
  assert.deepEqual(result.realisedProfit, { status: "unavailable" });
  assert.deepEqual(result.cash, [
    { accountId: "account-a", currency: "SGD", amountMinor: null },
  ]);
  assert.deepEqual(result.positions, []);
  assert.deepEqual(result.marketValue, {
    status: "available",
    currency: "SGD",
    amountMinor: 0n,
  });
});

test("foreign cash without an FX rate stays unavailable", () => {
  const result = replayJournal(
    [
      leg({
        eventId: "fee-usd",
        eventType: "fee",
        idempotencyKey: "fee-usd",
        currency: "USD",
        cashAmountMinor: -100n,
      }),
    ],
    "SGD",
    [],
  );
  assert.deepEqual(result.cash, [
    { accountId: "account-a", currency: "USD", amountMinor: -100n },
  ]);
  assert.deepEqual(result.reportingCash, { status: "unavailable" });
});

test("deposits and withdrawals are the only net contributions", () => {
  const result = replayJournal(
    [
      leg({
        eventId: "deposit-1",
        eventType: "deposit",
        idempotencyKey: "deposit-1",
        cashAmountMinor: 50000n,
      }),
      leg({
        eventId: "buy-contrib",
        eventType: "buy",
        idempotencyKey: "buy-contrib",
        occurredOn: "2024-01-03",
        instrumentId: "fixture-equity",
        quantity: "10",
        cashAmountMinor: -10000n,
      }),
      leg({
        eventId: "withdrawal-1",
        eventType: "withdrawal",
        idempotencyKey: "withdrawal-1",
        occurredOn: "2024-01-04",
        cashAmountMinor: -20000n,
      }),
    ],
    "SGD",
  );
  assert.equal(result.netContributionsMinor, 30000n);
  assert.equal(result.cash[0]?.amountMinor, 20000n);
  assert.equal(result.positions[0]?.costMinor, 10000n);
});

test("a security transfer moves quantity and cost and does not realise profit", () => {
  const result = replayJournal(
    [
      leg({
        eventId: "buy-transfer",
        eventType: "buy",
        idempotencyKey: "buy-transfer",
        instrumentId: "fixture-equity",
        quantity: "10",
        cashAmountMinor: -100000n,
      }),
      leg({
        eventId: "transfer-in",
        eventType: "transfer",
        idempotencyKey: "transfer-in",
        occurredOn: "2024-01-08",
        accountId: "account-b",
        instrumentId: "fixture-equity",
        quantity: "4",
        transferGroupId: "group-units",
      }),
      leg({
        eventId: "transfer-out",
        eventType: "transfer",
        idempotencyKey: "transfer-out",
        occurredOn: "2024-01-08",
        instrumentId: "fixture-equity",
        quantity: "-4",
        transferGroupId: "group-units",
      }),
    ],
    "SGD",
  );
  assert.deepEqual(result.positions, [
    {
      accountId: "account-a",
      instrumentId: "fixture-equity",
      quantity: "6",
      costMinor: 60000n,
      currency: "SGD",
    },
    {
      accountId: "account-b",
      instrumentId: "fixture-equity",
      quantity: "4",
      costMinor: 40000n,
      currency: "SGD",
    },
  ]);
  assert.deepEqual(result.realisedProfit, {
    status: "available",
    currency: "SGD",
    amountMinor: 0n,
  });
  assert.deepEqual(result.unbalancedTransferGroupIds, []);
  assert.equal(result.netContributionsMinor, 0n);
});

test("a one-sided transfer is reported and is not a contribution", () => {
  const result = replayJournal(
    [
      leg({
        eventId: "orphan-transfer",
        eventType: "transfer",
        idempotencyKey: "orphan-transfer",
        cashAmountMinor: -1000n,
        transferGroupId: "group-orphan",
      }),
    ],
    "SGD",
  );
  assert.deepEqual(result.unbalancedTransferGroupIds, ["group-orphan"]);
  assert.equal(result.netContributionsMinor, 0n);
  assert.equal(result.cash[0]?.amountMinor, -1000n);
});

test("a split that does not divide the position is rejected", () => {
  assert.throws(
    () =>
      replayJournal(
        [
          leg({
            eventId: "buy-split",
            eventType: "buy",
            idempotencyKey: "buy-split",
            instrumentId: "fixture-equity",
            quantity: "10",
            cashAmountMinor: -100000n,
          }),
          leg({
            eventId: "split-odd",
            eventType: "split",
            idempotencyKey: "split-odd",
            occurredOn: "2024-01-05",
            instrumentId: "fixture-equity",
            splitNumerator: 2,
            splitDenominator: 3,
          }),
        ],
        "SGD",
      ),
    /split does not divide the position/,
  );
});

test("an event cannot correct itself", () => {
  assert.throws(
    () =>
      replayJournal(
        [
          leg({
            eventId: "loop",
            eventType: "fee",
            idempotencyKey: "loop",
            cashAmountMinor: -100n,
            correctionOf: "loop",
          }),
        ],
        "SGD",
      ),
    /cannot correct itself/,
  );
});
