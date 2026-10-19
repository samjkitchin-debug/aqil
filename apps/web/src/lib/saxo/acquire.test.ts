import assert from "node:assert/strict";
import { mkdtemp, readdir, readFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import test from "node:test";

import { readAcquisitionManifest, resumableEntries, writeEncryptedUnit } from "./archive.ts";
import { attemptClassified, classifySaxoResponse, retryWaitMs } from "./errors.ts";
import { collectionTruncated, continuationPath, duplicateIdentityPage, pageCursors, performanceObjectComplete, windowComplete } from "./pagination.ts";
import { refreshSaxoTokens } from "./refresh-flight.ts";
import { saxoAllowsRequest, saxoConnectAllowed, saxoReadUrl, SAXO_SIM_REDIRECT_URI } from "./sim-guard.ts";
import { indexSourceEvents } from "./source-identity.ts";
import { decryptJson, saxoEncryptionKey } from "./token-crypto.ts";

const SENTINEL = "archive-sentinel-do-not-store-plain";

test("concurrent refresh persists the rotated token once before either waiter continues", async () => {
  let calls = 0;
  let persisted = 0;
  let persistedBeforeReturn = false;
  const pending: Array<() => void> = [];
  const refresh = refreshSaxoTokens({
    userId: "user-1",
    environment: "live",
    refreshToken: "old-refresh",
    appKey: "app",
    appSecret: "secret",
    redirectUri: "http://localhost:3000/auth/saxo/callback",
    fetchImpl: () =>
      new Promise((resolve) => {
        calls += 1;
        pending.push(() =>
          resolve({
            ok: true,
            status: 200,
            json: async () => ({
              access_token: "new-access",
              refresh_token: "new-refresh",
              expires_in: 1200,
              refresh_token_expires_in: 2400,
            }),
          }),
        );
      }),
    persist: async (tokens) => {
      persisted += 1;
      assert.equal(tokens.refreshToken, "new-refresh");
      persistedBeforeReturn = true;
    },
  });
  const second = refreshSaxoTokens({
    userId: "user-1",
    environment: "live",
    refreshToken: "old-refresh",
    appKey: "app",
    appSecret: "secret",
    redirectUri: "http://localhost:3000/auth/saxo/callback",
    fetchImpl: () => {
      throw new Error("second refresh must not call Saxo");
    },
    persist: async () => {
      throw new Error("second refresh must not persist");
    },
  });
  assert.equal(calls, 1);
  pending[0]?.();
  const [firstResult, secondResult] = await Promise.all([refresh, second]);
  assert.equal(persisted, 1);
  assert.equal(persistedBeforeReturn, true);
  assert.equal(firstResult.ok && firstResult.tokens.accessToken, "new-access");
  assert.equal(secondResult.ok && secondResult.tokens.accessToken, "new-access");
});

test("a rejected refresh does not persist and a malformed window is not retried", async () => {
  let persisted = 0;
  const rejected = await refreshSaxoTokens({
    userId: "user-2",
    environment: "live",
    refreshToken: "stale",
    appKey: "app",
    appSecret: "secret",
    redirectUri: "http://localhost:3000/auth/saxo/callback",
    fetchImpl: async () => ({
      ok: false,
      status: 401,
      json: async () => ({ error: "invalid_grant" }),
    }),
    persist: async () => {
      persisted += 1;
    },
  });
  assert.equal(rejected.ok, false);
  if (!rejected.ok) assert.equal(rejected.errorCode, "invalid_grant");
  assert.equal(persisted, 0);

  const malformed = classifySaxoResponse({
    status: 400,
    body: { ErrorCode: "InvalidRequest" },
    endpointFamily: "/hist/v1/transactions",
  });
  assert.equal(malformed.kind, "malformed");
  assert.equal(malformed.action, "stop");
  const wide = classifySaxoResponse({
    status: 400,
    body: { ErrorCode: "InvalidDateRange" },
    endpointFamily: "/hist/v1/transactions",
  });
  assert.equal(wide.kind, "invalid_window");
  assert.equal(wide.action, "stop");
  assert.equal(
    classifySaxoResponse({ status: 404, body: null, endpointFamily: "/hist/v3/perf" }).kind,
    "absent",
  );
  assert.equal(classifySaxoResponse({ status: 403, body: null, endpointFamily: "/ca/v2/events" }).action, "stop");
  assert.equal(retryWaitMs("1", 1), 1_000);
  assert.equal(retryWaitMs("120", 1), 120_000);
});

test("unauthorised calls refresh once and rate limits honour a bounded wait", async () => {
  let calls = 0;
  let refreshes = 0;
  const unauthorised = await attemptClassified({
    endpointFamily: "/port/v1/balances",
    call: async () => {
      calls += 1;
      return { status: 401, body: { ErrorCode: "InvalidToken" }, retryAfter: null };
    },
    sleep: async () => undefined,
    refresh: async () => {
      refreshes += 1;
      return false;
    },
  });
  assert.equal(calls, 1);
  assert.equal(refreshes, 1);
  assert.equal(unauthorised.classification.kind, "unauthorised");

  const waits: number[] = [];
  let rateCalls = 0;
  const limited = await attemptClassified({
    endpointFamily: "/hist/v1/transactions",
    call: async () => {
      rateCalls += 1;
      return rateCalls === 1
        ? { status: 429, body: null, retryAfter: "1" }
        : { status: 200, body: { Data: [] }, retryAfter: null };
    },
    sleep: async (ms) => {
      waits.push(ms);
    },
    refresh: async () => false,
  });
  assert.deepEqual(waits, [1_000]);
  assert.equal(limited.classification.kind, "ok");
  assert.equal(rateCalls, 2);
});

test("read allow-list admits history and refuses trading", () => {
  assert.equal(saxoAllowsRequest("GET", "/hist/v1/transactions?ClientKey=abc", "live"), true);
  assert.equal(saxoAllowsRequest("GET", "/hist/v3/positions/abc?StandardPeriod=AllTime", "live"), true);
  assert.equal(saxoAllowsRequest("GET", "/hist/v3/perf/abc?StandardPeriod=AllTime", "live"), true);
  assert.equal(saxoAllowsRequest("GET", "/cs/v1/audit/orderactivities?EntryType=All", "live"), true);
  assert.equal(saxoAllowsRequest("GET", "/port/v1/orders?Status=Working", "live"), true);
  assert.equal(saxoAllowsRequest("GET", "/cs/v1/reports/aggregatedAmounts/abc/2020-01-01/2020-02-01", "live"), true);
  assert.equal(saxoAllowsRequest("POST", "/port/v1/orders", "live"), false);
  assert.equal(saxoAllowsRequest("GET", "/trade/v2/orders", "live"), false);
  assert.equal(saxoReadUrl("/port/v1/positions/me/orders", "live"), null);
  assert.equal(saxoReadUrl("/chart/v3/charts/subscriptions", "live"), null);
  assert.equal(
    saxoConnectAllowed({
      environment: "live",
      nodeEnv: "production",
      requestHost: "aqil-tau.vercel.app",
      redirectUri: "https://aqil-tau.vercel.app/auth/saxo/callback",
    }),
    false,
  );
  assert.equal(SAXO_SIM_REDIRECT_URI, "http://localhost:3000/auth/saxo/callback");
});

test("continuation urls stay on the same environment, family and scope", () => {
  const next = continuationPath({
    next: "https://gateway.saxobank.com/openapi/hist/v1/transactions?ClientKey=client-a&$skip=50",
    environment: "live",
    endpointFamily: "/hist/v1/transactions",
    clientKey: "client-a",
    accountKey: null,
    seen: [],
  });
  assert.equal(next.ok, true);
  const repeated = continuationPath({
    next: "https://gateway.saxobank.com/openapi/hist/v1/transactions?$skip=50&ClientKey=client-a",
    environment: "live",
    endpointFamily: "/hist/v1/transactions",
    clientKey: "client-a",
    accountKey: null,
    seen: next.ok ? [next.normalised] : [],
  });
  assert.deepEqual(repeated, { ok: false, reason: "loop" });
  assert.equal(
    continuationPath({
      next: "https://evil.example/openapi/hist/v1/transactions?ClientKey=client-a",
      environment: "live",
      endpointFamily: "/hist/v1/transactions",
      clientKey: "client-a",
      accountKey: null,
      seen: [],
    }).ok,
    false,
  );
  assert.equal(
    continuationPath({
      next: "https://gateway.saxobank.com/sim/openapi/hist/v1/transactions?ClientKey=client-a",
      environment: "live",
      endpointFamily: "/hist/v1/transactions",
      clientKey: "client-a",
      accountKey: null,
      seen: [],
    }).ok,
    false,
  );
  assert.deepEqual(
    continuationPath({
      next: "https://gateway.saxobank.com/openapi/hist/v1/transactions?ClientKey=client-b",
      environment: "live",
      endpointFamily: "/hist/v1/transactions",
      clientKey: "client-a",
      accountKey: null,
      seen: [],
    }),
    { ok: false, reason: "scope" },
  );
  assert.equal(pageCursors({ __nextPoll: "/openapi/cs/v1/audit/orderactivities?$skiptoken=abc" }).poll?.includes("skiptoken"), true);
  assert.deepEqual(
    continuationPath({
      next: "https://gateway.saxobank.com/openapi/cs/v1/audit/orderactivities?__nextPoll=1",
      environment: "live",
      endpointFamily: "/cs/v1/audit/orderactivities",
      clientKey: "client-a",
      accountKey: null,
      seen: [],
    }),
    { ok: false, reason: "poll" },
  );
});

test("completeness is endpoint-aware and does not treat a short summary as truncated", () => {
  assert.equal(collectionTruncated({ Data: [{ KeyType: "Account" }], __count: 4, MaxRows: 1 }, false), true);
  assert.equal(
    windowComplete({ rowCount: 2, reportedCount: 2, cursorRemains: false, truncated: false, loop: false, duplicate: false }),
    true,
  );
  assert.equal(
    windowComplete({ rowCount: 1, reportedCount: 4, cursorRemains: false, truncated: true, loop: false, duplicate: false }),
    false,
  );
  assert.equal(duplicateIdentityPage(["booking:1"], new Set(["booking:1"])), true);
  assert.equal(performanceObjectComplete({ InceptionDay: "2015-11-24" }), true);
  assert.equal(performanceObjectComplete({}), false);
});

test("a new booking id stays independent unless Saxo names the corrected record", () => {
  const body = {
    Data: [
      {
        TradeId: "trade-9",
        CorporateActionId: "ca-1",
        Date: "2024-01-02",
        Bookings: [
          { BookingId: "book-1", Amount: 1 },
          { BookingId: "book-2", Amount: -1, CorrectsBookingId: "book-1" },
        ],
        Trades: [{ TradeId: "trade-9" }, { TradeId: "trade-10" }],
      },
    ],
  };
  const before = JSON.stringify(body);
  const events = indexSourceEvents(body);
  assert.equal(JSON.stringify(body), before);
  assert.equal(events.filter((event) => event.kind === "booking").length, 2);
  assert.equal(events.find((event) => event.id === "booking:book-2")?.corrects, "booking:book-1");
  assert.equal(events.find((event) => event.id === "booking:book-1")?.corrects, null);
  assert.equal(events.find((event) => event.id === "trade:trade-10")?.corrects, null);
  assert.equal(events.filter((event) => event.corporateActionId === "ca-1").length > 1, true);
});

test("encrypted units resume without replacing a complete window or leaving plaintext", async () => {
  const key = saxoEncryptionKey(Buffer.alloc(32, 9).toString("base64"));
  assert.ok(key);
  const root = await mkdtemp(path.join(tmpdir(), "aqil-saxo-archive-"));
  try {
    const entry = { dataset: "transactions", scope: "client-a", window: "2024-01" };
    assert.equal(
      await writeEncryptedUnit({
        root,
        key,
        entry,
        unitId: "unit-1",
        body: { Data: [{ BookingId: "book-1", note: SENTINEL }] },
        complete: true,
      }),
      "stored",
    );
    const names = await readdir(path.join(root, "units"));
    const storedName = names.find((name) => name.endsWith(".bin"));
    assert.ok(storedName);
    const ciphertext = await readFile(path.join(root, "units", storedName), "utf8");
    assert.equal(ciphertext.includes(SENTINEL), false);
    assert.equal(ciphertext.includes("book-1"), false);
    const revealed = decryptJson(ciphertext, key) as { body?: { Data?: Array<{ note?: string }> } };
    assert.equal(revealed.body?.Data?.[0]?.note, SENTINEL);
    assert.equal(
      await writeEncryptedUnit({
        root,
        key,
        entry,
        unitId: "unit-2",
        body: { Data: [{ BookingId: "book-2" }] },
        complete: false,
      }),
      "stored",
    );
    assert.equal(await readFile(path.join(root, "units", storedName), "utf8"), ciphertext);
    await writeEncryptedUnit({
      root,
      key,
      entry: { dataset: "transactions", scope: "client-a", window: "2024-02" },
      unitId: "unit-3",
      body: { Data: [] },
      complete: false,
    });
    const restarted = await readAcquisitionManifest(root, key);
    assert.deepEqual(
      resumableEntries(restarted).map((item) => item.window),
      ["2024-02"],
    );
    assert.equal(restarted.entries.find((item) => item.window === "2024-01")?.status, "complete");
    const leftovers = (await readdir(root)).filter((name) => name.endsWith(".tmp"));
    assert.deepEqual(leftovers, []);
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});
