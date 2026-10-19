import assert from "node:assert/strict";
import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import test from "node:test";

import { latestVerified, readAcquisitionManifest } from "./archive.ts";
import { captureCurrentAccount } from "./current-account.ts";
import { attemptClassified } from "./errors.ts";
import { saxoConnectAllowed } from "./sim-guard.ts";
import { saxoEncryptionKey } from "./token-crypto.ts";

const key = saxoEncryptionKey(Buffer.alloc(32, 4).toString("base64"));

test("current capture keeps every account, paginated lots and a second archive version", async () => {
  assert.ok(key);
  const root = await mkdtemp(path.join(tmpdir(), "aqil-current-"));
  const seen: string[] = [];
  try {
    const first = await captureCurrentAccount({
      userId: "user-a",
      environment: "live",
      accessToken: "token",
      encryptionKey: key,
      archiveRoot: root,
      nowMs: 1_000,
      fetchImpl: (url) => respond(url, seen, false),
      sleep: async () => undefined,
    });
    assert.equal(first.outcome, "complete");
    assert.equal(Array.isArray((first.positionsBody as { Data?: unknown[] }).Data), true);
    assert.equal((first.positionsBody as { Data: unknown[] }).Data.length, 2);
    assert.equal(first.accountBalances.length, 2);
    assert.equal(seen.some((url) => url.includes("FieldGroups=PositionBase,PositionView,DisplayAndFormat,Costs,ExchangeInfo")), true);
    assert.equal(seen.some((url) => url.includes("AccountKey=account-b")), true);
    assert.equal(seen.some((url) => url.includes("/ref/v1/instruments/details/21/Etf")), true);

    const secondRoot = await mkdtemp(path.join(tmpdir(), "aqil-current-other-"));
    await captureCurrentAccount({
      userId: "user-b",
      environment: "live",
      accessToken: "token",
      encryptionKey: key,
      archiveRoot: secondRoot,
      nowMs: 2_000,
      fetchImpl: (url) => respond(url, [], false),
      sleep: async () => undefined,
    });
    const userA = await readAcquisitionManifest(root, key);
    const userB = await readAcquisitionManifest(secondRoot, key);
    assert.equal(userA.entries.some((entry) => entry.scope === "user-b"), false);
    assert.equal(userB.entries.some((entry) => entry.scope === "user-a"), false);

    await captureCurrentAccount({
      userId: "user-a",
      environment: "live",
      accessToken: "token",
      encryptionKey: key,
      archiveRoot: root,
      nowMs: 3_000,
      fetchImpl: (url) => respond(url, [], false),
      sleep: async () => undefined,
    });
    const versioned = await readAcquisitionManifest(root, key);
    const latest = latestVerified(versioned, { dataset: "positions", scope: "user-a", window: "current" });
    assert.equal(latest?.version, 2);
    assert.equal(versioned.entries.filter((entry) => entry.dataset === "positions" && entry.status === "complete").length, 2);
    await rm(secondRoot, { recursive: true, force: true });
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});

test("a looped continuation does not become a complete portfolio and a long retry waits outside the request", async () => {
  assert.ok(key);
  const root = await mkdtemp(path.join(tmpdir(), "aqil-current-partial-"));
  const sleeps: number[] = [];
  try {
    const looped = await captureCurrentAccount({
      userId: "user-a",
      environment: "live",
      accessToken: "token",
      encryptionKey: key,
      archiveRoot: root,
      nowMs: 4_000,
      fetchImpl: (url) => respond(url, [], true),
      sleep: async (ms) => {
        sleeps.push(ms);
      },
    });
    assert.equal(looped.outcome, "partial");
    const manifest = await readAcquisitionManifest(root, key);
    assert.equal(latestVerified(manifest, { dataset: "positions", scope: "user-a", window: "current" }), null);

    const deferred = await attemptClassified({
      endpointFamily: "/port/v1/positions",
      call: async () => ({ status: 429, body: null, retryAfter: "120" }),
      sleep: async (ms) => {
        sleeps.push(ms);
      },
      refresh: async () => false,
    });
    assert.equal(deferred.deferredMs, 120_000);
    assert.equal(sleeps.includes(120_000), false);
    assert.equal(
      saxoConnectAllowed({
        environment: "live",
        nodeEnv: "production",
        requestHost: "aqil-tau.vercel.app",
        redirectUri: "https://aqil-tau.vercel.app/auth/saxo/callback",
      }),
      false,
    );
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});

function respond(url: string, seen: string[], loop: boolean): Promise<{ status: number; headers: { get(name: string): string | null }; text: () => Promise<string> }> {
  seen.push(url);
  const path = new URL(url).pathname;
  let body: unknown = {};
  if (path.endsWith("/port/v1/clients/me")) body = { ClientKey: "client-a" };
  if (path.endsWith("/port/v1/accounts/me")) {
    body = {
      Data: [
        { AccountKey: "account-a", AccountId: "A", ClientKey: "client-a", Currency: "SGD" },
        { AccountKey: "account-b", AccountId: "B", ClientKey: "client-a", Currency: "USD" },
      ],
      __count: 2,
    };
  }
  if (path.endsWith("/port/v1/balances/me")) body = { Currency: "SGD", CashBalance: 1, TotalValue: 10 };
  if (path.endsWith("/port/v1/balances")) body = { Currency: "SGD", CashBalance: 1, TotalValue: 10 };
  if (path.endsWith("/port/v1/positions/me")) {
    const skip = new URL(url).searchParams.get("$skip");
    const nextPage = "https://gateway.saxobank.com/openapi/port/v1/positions/me?$top=50&$skip=1";
    body = skip
      ? { Data: [lot("lot-2", 3)], __count: 2, ...(loop ? { __next: "https://gateway.saxobank.com/openapi/port/v1/positions/me?$skip=1&$top=50" } : {}) }
      : { Data: [lot("lot-1", 4)], __count: 2, __next: nextPage };
  }
  if (path.endsWith("/port/v1/netpositions/me")) {
    body = { Data: [lot("net-1", 7)], __count: 1 };
  }
  if (path.includes("/exposure/") || path.endsWith("/port/v1/orders")) body = { Data: [], __count: 0 };
  if (path.includes("/closedpositions/")) body = { Data: [], __count: 0 };
  if (path.includes("/instruments/details/")) body = { Uic: 21, AssetType: "Etf", Symbol: "VWRA:xlon" };
  if (path.endsWith("/trade/v1/infoprices")) body = { Quote: { Bid: 1, Ask: 2 }, LastUpdated: "2026-10-19T00:00:00Z" };
  return Promise.resolve({
    status: 200,
    headers: { get: () => null },
    text: async () => JSON.stringify(body),
  });
}

function lot(positionId: string, amount: number): unknown {
  return {
    PositionId: positionId,
    DisplayAndFormat: { Symbol: "VWRA:xlon", Currency: "USD" },
    PositionBase: { PositionId: positionId, Amount: amount, AssetType: "Etf", Uic: 21, OpenPrice: 9 },
    PositionView: { MarketValueInBaseCurrency: amount, CurrentPrice: 10 },
    NetPositionBase: { Amount: amount, AssetType: "Etf", Uic: 21 },
    NetPositionView: { MarketValueInBaseCurrency: amount },
  };
}
