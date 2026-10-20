import assert from "node:assert/strict";
import test from "node:test";

import { JOURNAL_CSV_HEADER, previewJournalCsv } from "./journal-csv.ts";
import { replayJournal } from "./journal.ts";
import { emptyJournalFile } from "./journal-store.ts";
import { commitJournalCsv, stageJournalCsv } from "./journal-workflow.ts";

const HEADER = JOURNAL_CSV_HEADER;

function row(cells: readonly string[]): string {
  if (cells.length !== 11) throw new Error(`expected 11 cells, received ${cells.length}`);
  return cells.join(",");
}

const buy = row(["row-buy", "buy", "2024-01-02", "account-a", "SGD", "100.00", "fixture", "10", "10.00", "", ""]);
const duplicate = buy;
const mismatch = row(["row-bad", "buy", "2024-01-03", "account-a", "SGD", "50.00", "other", "10", "10.00", "", ""]);
const signed = row(["row-sign", "fee", "2024-01-04", "account-a", "SGD", "-1.00", "", "", "", "", ""]);
const invalidCurrency = row(["row-xxx", "fee", "2024-01-05", "account-a", "XXX", "1.00", "", "", "", "", ""]);

test("a CSV preview deduplicates on the idempotency key and holds ambiguous rows out of the replay", () => {
  const csv = [HEADER, buy, duplicate, mismatch, signed, invalidCurrency].join("\n");
  const preview = previewJournalCsv(csv, "SGD");
  assert.equal(preview.recognised, true);
  assert.equal(preview.accepted.length, 1);
  assert.equal(preview.accepted[0]?.idempotencyKey, "row-buy");
  assert.deepEqual(preview.duplicates.map((item) => item.idempotencyKey), ["row-buy"]);
  assert.equal(preview.held.length, 3);
  assert.match(preview.held.map((item) => item.reason).join(" "), /does not match the unit price/);
  assert.match(preview.held.map((item) => item.reason).join(" "), /signed amount/);
  assert.match(preview.held.map((item) => item.reason).join(" "), /currency is invalid/);
  assert.equal(preview.replay?.positions.length, 1);
  assert.equal(preview.replay?.positions[0]?.instrumentId, "fixture");
  assert.equal(preview.replay?.positions[0]?.quantity, "10");
  assert.equal(preview.replay?.positions.some((position) => position.instrumentId === "other"), false);
  const replay = replayJournal(preview.accepted, "SGD");
  assert.equal(replay.positions[0]?.quantity, "10");
  assert.equal(replay.cash[0]?.amountMinor, -10000n);
});

test("applying a preview is idempotent and does not import held rows", () => {
  const csv = [HEADER, buy, duplicate, mismatch, signed].join("\n");
  const staged = stageJournalCsv(emptyJournalFile(), csv);
  const once = commitJournalCsv(staged);
  const twice = commitJournalCsv(once);
  assert.equal(once.events.length, 1);
  assert.equal(twice.events.length, 1);
  assert.equal(once.events[0]?.idempotencyKey, "row-buy");
  assert.equal(once.events.some((event) => event.instrumentId === "other"), false);
  assert.equal(once.events.some((event) => event.idempotencyKey === "row-sign"), false);
  assert.equal(replayJournal(twice.events, "SGD").positions[0]?.quantity, "10");
});

test("a different body for the same idempotency key is held and leaves the journal unchanged", () => {
  const staged = stageJournalCsv(emptyJournalFile(), [HEADER, buy].join("\n"));
  const saved = commitJournalCsv(staged);
  const changed = buy.replace("2024-01-02", "2024-01-03");
  const preview = previewJournalCsv([HEADER, changed].join("\n"), "SGD", saved.events);
  assert.equal(preview.accepted.length, 0);
  assert.match(preview.held[0]?.reason ?? "", /different entry/);
  const next = commitJournalCsv(stageJournalCsv(saved, [HEADER, changed].join("\n")));
  assert.equal(next.events.length, 1);
  assert.equal(next.events[0]?.cashAmountMinor, -10000n);
});

test("an unrecognised file is not imported", () => {
  const file = stageJournalCsv(emptyJournalFile(), "not,a,journal\n1,2,3");
  const preview = previewJournalCsv(file.previewCsv ?? "", "SGD", file.events);
  assert.equal(preview.recognised, false);
  assert.equal(preview.replay, null);
  assert.equal(commitJournalCsv(file).events.length, 0);
});
