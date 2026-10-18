/**
 * Mock Auth HTTP. This does not prove a live token rotation.
 * It checks the installed GoTrue client: getUser refreshes only inside the expiry margin.
 */
import assert from "node:assert/strict";
import test from "node:test";

import { GoTrueClient } from "@supabase/auth-js";

const USER_ID = "11111111-1111-4111-8111-111111111111";

function jwt(expSeconds: number): string {
  const header = Buffer.from(JSON.stringify({ alg: "HS256", typ: "JWT" })).toString("base64url");
  const body = Buffer.from(JSON.stringify({ sub: USER_ID, exp: expSeconds, role: "authenticated" })).toString(
    "base64url",
  );
  return `${header}.${body}.sig`;
}

function memoryStorage() {
  const values = new Map<string, string>();
  return {
    getItem: async (key: string) => values.get(key) ?? null,
    setItem: async (key: string, value: string) => {
      values.set(key, value);
    },
    removeItem: async (key: string) => {
      values.delete(key);
    },
  };
}

function userBody() {
  return {
    id: USER_ID,
    aud: "authenticated",
    role: "authenticated",
    email: "founder@example.com",
    app_metadata: { provider: "google", providers: ["google"] },
    user_metadata: {},
    created_at: "2026-01-01T00:00:00Z",
  };
}

test("mock fetch: two getUser calls do not refresh a current access token", async () => {
  const counts = { user: 0, token: 0 };
  const now = Math.floor(Date.now() / 1000);
  const client = new GoTrueClient({
    url: "http://auth.test/auth/v1",
    storageKey: "sb-mock-auth-token",
    autoRefreshToken: false,
    persistSession: true,
    detectSessionInUrl: false,
    storage: memoryStorage(),
    fetch: async (input) => {
      const url = String(input);
      if (url.includes("/token")) {
        counts.token += 1;
        return new Response(JSON.stringify({ error: "unexpected refresh", error_description: "not expired" }), {
          status: 500,
        });
      }
      counts.user += 1;
      return new Response(JSON.stringify(userBody()), { status: 200 });
    },
  });

  const saved = await client.setSession({
    access_token: jwt(now + 3600),
    refresh_token: "refresh-current",
  });
  assert.equal(saved.error, null);
  const before = { ...counts };
  const first = await client.getUser();
  const second = await client.getUser();
  assert.equal(first.data.user?.id, USER_ID);
  assert.equal(second.data.user?.id, USER_ID);
  assert.equal(counts.token - before.token, 0);
  assert.equal(counts.user - before.user, 2);
});

test("mock fetch: an expired access token refreshes once, then a later getUser does not", async () => {
  const counts = { user: 0, token: 0 };
  const now = Math.floor(Date.now() / 1000);
  let rotated = false;
  const client = new GoTrueClient({
    url: "http://auth.test/auth/v1",
    storageKey: "sb-mock-auth-token",
    autoRefreshToken: false,
    persistSession: true,
    detectSessionInUrl: false,
    storage: memoryStorage(),
    fetch: async (input) => {
      const url = String(input);
      if (url.includes("/token")) {
        counts.token += 1;
        rotated = true;
        return new Response(
          JSON.stringify({
            access_token: jwt(now + 3600),
            refresh_token: "refresh-rotated",
            token_type: "bearer",
            expires_in: 3600,
            expires_at: now + 3600,
            user: userBody(),
          }),
          { status: 200 },
        );
      }
      counts.user += 1;
      if (!rotated) {
        return new Response(JSON.stringify({ message: "expired", code: "bad_jwt" }), { status: 401 });
      }
      return new Response(JSON.stringify(userBody()), { status: 200 });
    },
  });

  const saved = await client.setSession({
    access_token: jwt(now - 120),
    refresh_token: "refresh-stale",
  });
  assert.equal(saved.error, null);
  assert.equal(counts.token, 1);
  const beforeUser = counts.user;
  const after = await client.getUser();
  assert.equal(after.data.user?.id, USER_ID);
  assert.equal(counts.token, 1);
  assert.equal(counts.user - beforeUser, 1);
});

test("mock fetch: 429 and 503 responses do not start a retry loop", async () => {
  for (const status of [429, 503]) {
    let calls = 0;
    const now = Math.floor(Date.now() / 1000);
    const client = new GoTrueClient({
      url: "http://auth.test/auth/v1",
      storageKey: `sb-mock-${status}-auth-token`,
      autoRefreshToken: false,
      persistSession: true,
      detectSessionInUrl: false,
      storage: memoryStorage(),
      fetch: async () => {
        calls += 1;
        return new Response(JSON.stringify({ message: "unavailable", code: "unexpected_failure" }), { status });
      },
    });
    const saved = await client.setSession({
      access_token: jwt(now + 3600),
      refresh_token: `refresh-${status}`,
    });
    assert.equal(saved.error === null, false);
    const before = calls;
    const result = await client.getUser();
    assert.equal(result.data.user, null);
    assert.ok(calls - before <= 2, `${status} produced ${calls - before} follow-up requests`);
    assert.ok(calls <= 4, `${status} produced ${calls} requests in total`);
  }
});
