import assert from "node:assert/strict";
import { mkdtemp, readdir, readFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import test from "node:test";

import { readAcquisitionManifest, resumableEntries, writeEncryptedUnit } from "./archive.ts";
import { archiveWindow, collectDataset } from "./current-account.ts";
import { cappedWithoutContinuation, withSkip } from "./pagination.ts";
import { quotaPace } from "./errors.ts";
import { amountKind, duplicateIds, emptyWindowEndsHistory, futureLabels, historyAlreadyComplete, monthWindows, onlyIn, sharedIds } from "./history.ts";
import { saxoAllowsRequest } from "./sim-guard.ts";
import { indexSourceEvents } from "./source-identity.ts";
import { decryptJson, saxoEncryptionKey } from "./token-crypto.ts";

test("quote windows stay per instrument and account keys stay out of archive labels", () => {
  const first = archiveWindow("infoprice", "/trade/v1/infoprices?Uic=21&AssetType=Etf&AccountKey=secret-account", null, "secret-account");
  const second = archiveWindow("infoprice", "/trade/v1/infoprices?Uic=22&AssetType=Stock&AccountKey=secret-account", null, "secret-account");
  assert.equal(first, "21-Etf");
  assert.equal(second, "22-Stock");
  assert.equal(first.includes("secret-account"), false);
  const balance = archiveWindow("balances-account", "/port/v1/balances?ClientKey=secret-client&AccountKey=secret-account", "secret-client", "secret-account");
  assert.equal(/^[0-9a-f]{16}$/.test(balance), true);
  assert.equal(balance.includes("secret-client"), false);
  assert.equal(balance.includes("secret-account"), false);
  const aggregated = archiveWindow(
    "aggregated-amounts",
    "/cs/v1/reports/aggregatedAmounts/secret-client/2024-01-01/2024-01-31",
    "secret-client",
    null,
  );
  assert.equal(aggregated, "2024-01-01_2024-01-31");
  assert.equal(aggregated.includes("secret-client"), false);
});

test("a page of exactly the requested size without a next link is not complete", async () => {
  assert.equal(cappedWithoutContinuation({ Data: Array.from({ length: 50 }, (_, index) => ({ Date: "2024-11-13", AmountTypeId: index })), __count: 50 }, 50), true);
  assert.equal(cappedWithoutContinuation({ Data: [{ Date: "2024-11-30" }], __count: 1 }, 50), false);
  const root = await mkdtemp(path.join(tmpdir(), "aqil-agg-"));
  const key = saxoEncryptionKey(Buffer.alloc(32, 6).toString("base64"));
  assert.ok(key);
  const calls: string[] = [];
  try {
    const collected = await collectDataset({
      userId: "user-a",
      environment: "live",
      accessToken: "token",
      encryptionKey: key,
      archiveRoot: root,
      nowMs: 20,
      dataset: "aggregated-amounts",
      pathAndQuery: "/cs/v1/reports/aggregatedAmounts/client/2024-11-01/2024-11-30?$top=50",
      clientKey: null,
      accountKey: null,
      reports: [],
      sleep: async () => undefined,
      fetchImpl: async (url) => {
        calls.push(url);
        const skip = url.includes("skip=50");
        const rows = skip
          ? [{ Date: "2024-11-20", AmountTypeId: -4, BookingId: "later" }]
          : Array.from({ length: 50 }, (_, index) => ({ Date: "2024-11-13", AmountTypeId: -6, BookingId: `early-${index}` }));
        return {
          status: 200,
          headers: { get: () => null },
          text: async () => JSON.stringify({ Data: rows, __count: rows.length }),
        };
      },
    });
    assert.equal(calls.length, 2);
    assert.equal(collected.complete, true);
    assert.equal((collected.body as { Data: unknown[] }).Data.length, 51);
    assert.equal(withSkip("/cs/v1/reports/aggregatedAmounts/client/2024-11-01/2024-11-30?$top=50", 50, 50).includes("skip=50"), true);
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});

test("historical month windows, duplicates and empty pages do not invent coverage", () => {
  assert.deepEqual(monthWindows("2024-01-15", "2024-03-02"), [
    { from: "2024-01-15", to: "2024-01-31" },
    { from: "2024-02-01", to: "2024-02-29" },
    { from: "2024-03-01", to: "2024-03-02" },
  ]);
  assert.deepEqual(duplicateIds(["booking:1", "booking:2", "booking:1"]), ["booking:1"]);
  assert.deepEqual(sharedIds(["booking:1", "trade:9"], ["booking:1"]), ["booking:1"]);
  assert.equal(emptyWindowEndsHistory(200, 0), false);
  assert.equal(quotaPace(2, 80_000, 50_000).defer, true);
  assert.equal(quotaPace(20, null, 0).waitMs, 400);
  assert.deepEqual(futureLabels(["2026-10-16", "2026-12-31"], "2026-10-19"), ["2026-12-31"]);
  assert.equal(amountKind({ amountTypeId: -6, amountType: "Position Exposure", affectsBalance: false }), "constructed");
  assert.equal(amountKind({ amountTypeId: null, amountType: "Corporate Actions - Cash Dividends", affectsBalance: null }), "booked");
  assert.deepEqual(onlyIn(["trade-1", "trade-2"], ["trade-1"]), ["trade-2"]);
  assert.equal(saxoAllowsRequest("POST", "/port/v1/orders/me", "live"), false);
  assert.equal(saxoAllowsRequest("GET", "/hist/v1/transactions?ClientKey=abc&FromDate=2024-01-01&ToDate=2024-01-31", "live"), true);
});

test("an order and a transaction keep their source fields, and a partial window resumes", async () => {
  const key = saxoEncryptionKey(Buffer.alloc(32, 5).toString("base64"));
  assert.ok(key);
  const root = await mkdtemp(path.join(tmpdir(), "aqil-history-"));
  try {
    const order = { Status: "Working", ActivityTime: "2026-10-18T01:02:03Z", Amount: 1 };
    await writeEncryptedUnit({
      root,
      key,
      entry: { dataset: "orders", scope: "user-a", window: "current" },
      unitId: "order-1",
      body: { pages: [order] },
      complete: true,
    });
    const names = await readdir(path.join(root, "units"));
    const ciphertext = await readFile(path.join(root, "units", names[0] ?? ""), "utf8");
    assert.equal(ciphertext.includes("Working"), false);
    const revealed = decryptJson(ciphertext, key) as { body?: { pages?: Array<{ Status?: string; ActivityTime?: string }> } };
    assert.equal(revealed.body?.pages?.[0]?.Status, "Working");
    assert.equal(revealed.body?.pages?.[0]?.ActivityTime, "2026-10-18T01:02:03Z");

    const seen: string[] = [];
    const reports: Parameters<typeof collectDataset>[0]["reports"] = [];
    const collected = await collectDataset({
      userId: "user-a",
      environment: "live",
      accessToken: "token",
      encryptionKey: key,
      archiveRoot: root,
      nowMs: 10,
      dataset: "transactions",
      pathAndQuery: "/hist/v1/transactions?FromDate=2024-01-01&ToDate=2024-01-31",
      clientKey: "secret-client",
      accountKey: null,
      reports,
      sleep: async () => undefined,
      fetchImpl: async (url) => {
        seen.push(url);
        return {
          status: 200,
          headers: { get: () => null },
          text: async () =>
            JSON.stringify({
              Data: [
                {
                  TradeId: "trade-1",
                  Bookings: [{ BookingId: "book-1", AmountType: "Commission", Amount: -1 }],
                  Trades: [{ TradeId: "trade-1", TradedQuantity: 2 }],
                },
              ],
              __count: 1,
            }),
        };
      },
    });
    assert.equal(collected.complete, true);
    assert.equal(seen.some((url) => url.includes("secret-client")), false);
    const events = indexSourceEvents(collected.body);
    assert.equal(events.some((event) => event.id === "booking:book-1"), true);
    assert.equal(JSON.stringify(collected.body).includes("Commission"), true);
    const restarted = await readAcquisitionManifest(root, key);
    assert.equal(historyAlreadyComplete(restarted, "transactions", "user-a", "2024-01-01_2024-01-31"), true);
    await writeEncryptedUnit({
      root,
      key,
      entry: { dataset: "transactions", scope: "user-a", window: "2024-02-01_2024-02-29" },
      unitId: "partial",
      body: { pages: [] },
      complete: false,
    });
    const resumed = resumableEntries(await readAcquisitionManifest(root, key));
    assert.deepEqual(resumed.map((entry) => entry.window), ["2024-02-01_2024-02-29"]);
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});
