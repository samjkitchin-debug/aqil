import assert from "node:assert/strict";
import test from "node:test";

import { saxoEncryptionKey } from "./token-crypto.ts";
import {
  createMemoryVaultStore,
  rotateHostedTokens,
  sealTokens,
  type VaultStore,
} from "./hosted-rotation.ts";
import type { SaxoTokens } from "./sim-guard.ts";

const key = saxoEncryptionKey("11".repeat(32));
if (!key) throw new Error("test key");

const original: SaxoTokens = {
  accessToken: "access-old",
  refreshToken: "refresh-old",
  expiresIn: 1200,
  refreshExpiresIn: 3600,
};

function storeWith(ciphertext: string): VaultStore {
  return createMemoryVaultStore({
    userId: "owner-1",
    environment: "live",
    ciphertext,
    generation: 1,
    status: "idle",
  });
}

test("two callers produce one Saxo refresh and the loser persists nothing", async () => {
  const store = storeWith(sealTokens(original, key));
  let calls = 0;
  const refresh = async () => {
    calls += 1;
    await new Promise((resolve) => setTimeout(resolve, 30));
    return {
      ok: true as const,
      tokens: {
        accessToken: "access-new",
        refreshToken: "refresh-new",
        expiresIn: 1200,
        refreshExpiresIn: 3600,
      },
    };
  };
  const [first, second] = await Promise.all([
    rotateHostedTokens({
      sessionUserId: "owner-1",
      ownerUserId: "owner-1",
      environment: "live",
      store,
      encryptionKey: key,
      refresh,
    }),
    rotateHostedTokens({
      sessionUserId: "owner-1",
      ownerUserId: "owner-1",
      environment: "live",
      store,
      encryptionKey: key,
      refresh,
    }),
  ]);
  const outcomes = [first, second];
  assert.equal(calls, 1);
  assert.equal(outcomes.filter((item) => item.ok).length, 1);
  assert.equal(outcomes.filter((item) => !item.ok && item.reason === "conflict").length, 1);
  const saved = await store.read("owner-1", "live");
  assert.equal(saved?.status, "idle");
  assert.equal(saved?.generation, 2);
  assert.equal(saved?.ciphertext.includes("access-new"), false);
  assert.equal(saved?.ciphertext.includes("refresh-new"), false);
  assert.match(saved?.ciphertext ?? "", /^v1\./);
});

test("a mismatched session does not read the vault", async () => {
  let reads = 0;
  const store: VaultStore = {
    async read() {
      reads += 1;
      return null;
    },
    async claim() {
      return { ok: false };
    },
    async commit() {
      return false;
    },
    async abort() {
      return undefined;
    },
  };
  const result = await rotateHostedTokens({
    sessionUserId: "other-user",
    ownerUserId: "owner-1",
    environment: "live",
    store,
    encryptionKey: key,
    refresh: async () => {
      throw new Error("Saxo must not be called");
    },
  });
  assert.deepEqual(result, { ok: false, reason: "owner" });
  assert.equal(reads, 0);
});

test("a failed refresh aborts the claim and keeps the previous ciphertext", async () => {
  const ciphertext = sealTokens(original, key);
  const store = storeWith(ciphertext);
  const result = await rotateHostedTokens({
    sessionUserId: "owner-1",
    ownerUserId: "owner-1",
    environment: "live",
    store,
    encryptionKey: key,
    refresh: async () => ({ ok: false, status: 400, errorCode: "invalid_grant" }),
  });
  assert.deepEqual(result, { ok: false, reason: "refresh_failed" });
  const saved = await store.read("owner-1", "live");
  assert.equal(saved?.status, "idle");
  assert.equal(saved?.ciphertext, ciphertext);
  assert.equal(saved?.generation, 2);
});

test("a commit that loses the generation discards the new tokens", async () => {
  const ciphertext = sealTokens(original, key);
  const store = storeWith(ciphertext);
  const result = await rotateHostedTokens({
    sessionUserId: "owner-1",
    ownerUserId: "owner-1",
    environment: "live",
    store: {
      read: store.read.bind(store),
      claim: store.claim.bind(store),
      abort: store.abort.bind(store),
      async commit() {
        return false;
      },
    },
    encryptionKey: key,
    refresh: async () => ({
      ok: true,
      tokens: { ...original, accessToken: "should-not-persist", refreshToken: "should-not-persist" },
    }),
  });
  assert.deepEqual(result, { ok: false, reason: "discarded" });
  const saved = await store.read("owner-1", "live");
  assert.equal(saved?.ciphertext, ciphertext);
  assert.equal(saved?.ciphertext.includes("should-not-persist"), false);
});
