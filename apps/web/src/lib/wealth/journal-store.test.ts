import assert from "node:assert/strict";
import { mkdtemp, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import test from "node:test";

import { parseManualEntry } from "./journal-entry.ts";
import {
  emptyJournalFile,
  journalPath,
  readJournalFile,
  writeJournalFile,
} from "./journal-store.ts";

const USER_A = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
const USER_B = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb";

function deposit(draftId: string) {
  return parseManualEntry({
    eventType: "deposit",
    occurredOn: "2024-01-02",
    accountId: "account-a",
    currency: "sgd",
    cashAmount: "10.00",
    instrumentId: "",
    quantity: "",
    unitPrice: "",
    splitNumerator: "",
    splitDenominator: "",
    draftId,
  });
}

async function withRoot(run: (root: string) => Promise<void>): Promise<void> {
  const root = await mkdtemp(path.join(tmpdir(), "aqil-journal-"));
  try {
    await run(root);
  } finally {
    await rm(root, { recursive: true, force: true });
  }
}

test("a journal file is stored under apps/web/.local and keyed by user id", async () => {
  await withRoot(async (root) => {
    const upper = USER_A.toUpperCase();
    assert.equal(journalPath(root, upper), path.join(root, ".local", "journal", `${USER_A}.json`));
    assert.throws(() => journalPath(root, "../secret"), /invalid user/);
    const missing = await readJournalFile(USER_A, root);
    assert.deepEqual(missing, emptyJournalFile());
    const file = {
      ...emptyJournalFile(),
      events: [deposit("11111111-1111-4111-8111-111111111111")],
      prices: [
        {
          instrumentId: "fixture",
          currency: "SGD",
          unitPriceMinor: 1100n,
          asOf: "2024-01-02",
          source: "supplied" as const,
        },
      ],
      rates: [
        {
          baseCurrency: "USD",
          quoteCurrency: "SGD",
          rate: "1.35",
          asOf: "2024-01-02",
          source: "supplied" as const,
        },
      ],
    };
    await writeJournalFile(USER_A, file, root);
    await writeJournalFile(USER_B, emptyJournalFile(), root);
    const read = await readJournalFile(upper, root);
    assert.equal(read.events[0]?.cashAmountMinor, 1000n);
    assert.equal(read.prices[0]?.unitPriceMinor, 1100n);
    assert.equal(read.rates[0]?.rate, "1.35");
    assert.equal((await readJournalFile(USER_B, root)).events.length, 0);
  });
});

test("a corrupt journal file and a non-positive price stay unreadable", async () => {
  await withRoot(async (root) => {
    const target = journalPath(root, USER_A);
    await writeJournalFile(USER_A, emptyJournalFile(), root);
    await writeFile(target, "{", "utf8");
    await assert.rejects(readJournalFile(USER_A, root), /unreadable/);
    await writeFile(
      target,
      `${JSON.stringify({
        schemaVersion: 1,
        reportingCurrency: "SGD",
        events: [],
        prices: [
          { instrumentId: "fixture", currency: "SGD", unitPriceMinor: "0", asOf: "2024-01-02", source: "supplied" },
        ],
        rates: [],
        previewCsv: null,
      })}\n`,
      "utf8",
    );
    await assert.rejects(readJournalFile(USER_A, root), /unreadable/);
  });
});
