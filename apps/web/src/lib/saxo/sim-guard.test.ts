import assert from "node:assert/strict";
import test from "node:test";

import { requestSaxoToken } from "./sim-http.ts";
import {
  SAXO_SIM_REDIRECT_URI,
  openSaxoState,
  saxoAccountRefs,
  saxoAllowsRequest,
  saxoAuthorizeUrl,
  saxoConnectAllowed,
  saxoDiscoveryAllowed,
  saxoInstrumentRefs,
  saxoNextUrl,
  saxoReadUrl,
  sealSaxoState,
} from "./sim-guard.ts";

test("discovery stays on localhost development and the registered callback", () => {
  assert.equal(
    saxoDiscoveryAllowed({
      nodeEnv: "development",
      requestHost: "localhost:3000",
      redirectUri: SAXO_SIM_REDIRECT_URI,
    }),
    true,
  );
  assert.equal(
    saxoDiscoveryAllowed({
      nodeEnv: "production",
      requestHost: "localhost:3000",
      redirectUri: SAXO_SIM_REDIRECT_URI,
    }),
    false,
  );
  assert.equal(
    saxoDiscoveryAllowed({
      nodeEnv: "development",
      requestHost: "aqil-tau.vercel.app",
      redirectUri: SAXO_SIM_REDIRECT_URI,
    }),
    false,
  );
  assert.equal(
    saxoDiscoveryAllowed({
      nodeEnv: "development",
      requestHost: "localhost:3000",
      redirectUri: "https://aqil-tau.vercel.app/auth/saxo/callback",
    }),
    false,
  );
});

test("authorize url carries the state and omits the application secret", () => {
  const secret = "sim-secret-not-for-the-browser";
  const url = new URL(
    saxoAuthorizeUrl({
      appKey: "sim-app-key",
      state: "state-1",
      redirectUri: SAXO_SIM_REDIRECT_URI,
    }),
  );
  assert.equal(url.origin, "https://sim.logonvalidation.net");
  assert.equal(url.pathname, "/authorize");
  assert.equal(url.searchParams.get("response_type"), "code");
  assert.equal(url.searchParams.get("client_id"), "sim-app-key");
  assert.equal(url.searchParams.get("redirect_uri"), SAXO_SIM_REDIRECT_URI);
  assert.equal(url.searchParams.get("state"), "state-1");
  assert.equal(url.searchParams.has("client_secret"), false);
  assert.equal(url.toString().includes(secret), false);
});

test("state is bound to the Aqil user and expires", () => {
  const secret = "sim-secret";
  const sealed = sealSaxoState({ state: "abc", userId: "user-1", environment: "live", exp: 2_000 }, secret);
  assert.deepEqual(openSaxoState(sealed, secret, 1_000), {
    state: "abc",
    userId: "user-1",
    environment: "live",
    exp: 2_000,
  });
  assert.equal(openSaxoState(sealed, secret, 2_001), null);
  assert.equal(openSaxoState(sealed, "other-secret", 1_000), null);
  assert.equal(openSaxoState(`${sealed}x`, secret, 1_000), null);
});

test("live authorisation stays on the live host and cannot place orders", () => {
  const url = new URL(
    saxoAuthorizeUrl({
      environment: "live",
      appKey: "live-app-key",
      state: "state-1",
      redirectUri: "http://localhost:3000/auth/saxo/callback",
    }),
  );
  assert.equal(url.origin, "https://live.logonvalidation.net");
  assert.equal(url.toString().includes("sim.logonvalidation.net"), false);
  assert.equal(
    saxoReadUrl("/port/v1/accounts/me", "live"),
    "https://gateway.saxobank.com/openapi/port/v1/accounts/me",
  );
  assert.equal(saxoReadUrl("/port/v1/accounts/me", "live")?.includes("/sim/"), false);
  assert.equal(saxoAllowsRequest("POST", "/trade/v2/orders", "live"), false);
  assert.equal(saxoAllowsRequest("DELETE", "/port/v1/accounts/me", "live"), false);
  assert.equal(saxoAllowsRequest("GET", "/trade/v2/orders", "live"), false);
  assert.equal(
    saxoNextUrl("https://gateway.saxobank.com/openapi/port/v1/positions/me?$skip=50", "live"),
    "https://gateway.saxobank.com/openapi/port/v1/positions/me?$skip=50",
  );
  assert.equal(saxoNextUrl("/openapi/port/v1/positions/me?$skip=50", "live")?.includes("/sim/"), false);
});

test("production cannot start a broker connection", () => {
  assert.equal(
    saxoConnectAllowed({
      environment: "live",
      nodeEnv: "production",
      requestHost: "aqil-tau.vercel.app",
      redirectUri: "https://aqil-tau.vercel.app/auth/saxo/callback",
    }),
    false,
  );
  assert.equal(
    saxoConnectAllowed({
      environment: "live",
      nodeEnv: "development",
      requestHost: "aqil-tau.vercel.app",
      redirectUri: SAXO_SIM_REDIRECT_URI,
    }),
    false,
  );
  assert.equal(
    saxoConnectAllowed({
      environment: "live",
      nodeEnv: "development",
      requestHost: "localhost:3000",
      redirectUri: SAXO_SIM_REDIRECT_URI,
    }),
    true,
  );
});

test("performance timeseries is a read and mock data is refused", () => {
  assert.equal(
    saxoReadUrl("/hist/v4/performance/timeseries?StandardPeriod=Month", "live"),
    "https://gateway.saxobank.com/openapi/hist/v4/performance/timeseries?StandardPeriod=Month",
  );
  assert.equal(saxoReadUrl("/hist/v4/performance/timeseries?MockDataId=demo", "live"), null);
  assert.equal(saxoAllowsRequest("POST", "/hist/v4/performance/timeseries", "live"), false);
  assert.equal(saxoAllowsRequest("GET", "/trade/v2/orders", "live"), false);
});

test("read urls stay on documented simulation gets", () => {
  assert.equal(
    saxoReadUrl("/port/v1/positions/me?$top=50"),
    "https://gateway.saxobank.com/sim/openapi/port/v1/positions/me?$top=50",
  );
  assert.equal(saxoReadUrl("/trade/v2/orders"), null);
  assert.equal(saxoReadUrl("//evil.example/port/v1/accounts/me"), null);
  assert.equal(
    saxoNextUrl("/openapi/port/v1/positions/me?$top=50&$skip=50"),
    "https://gateway.saxobank.com/sim/openapi/port/v1/positions/me?$top=50&$skip=50",
  );
  assert.equal(saxoNextUrl("https://evil.example/sim/openapi/port/v1/positions/me"), null);
  assert.equal(saxoNextUrl("/openapi/trade/v2/orders"), null);
});

test("account and instrument refs come only from returned keys", () => {
  assert.deepEqual(
    saxoAccountRefs(
      { Data: [{ AccountKey: "account-key", Currency: "USD" }, { AccountKey: "second", ClientKey: "row-client" }] },
      "client-key",
    ),
    [
      { clientKey: "client-key", accountKey: "account-key" },
      { clientKey: "row-client", accountKey: "second" },
    ],
  );
  assert.deepEqual(
    saxoInstrumentRefs({
      Data: [{ PositionBase: { Uic: 31, AssetType: "FxSpot" } }, { PositionBase: { Uic: 31, AssetType: "FxSpot" } }],
    }),
    [{ uic: 31, assetType: "FxSpot" }],
  );
});

test("token exchange uses basic auth and does not put the secret in the body", async () => {
  let seenBody = "";
  let seenAuth = "";
  const result = await requestSaxoToken(
    {
      grant: "authorization_code",
      code: "auth-code",
      appKey: "sim-app-key",
      appSecret: "sim-secret",
      redirectUri: SAXO_SIM_REDIRECT_URI,
    },
    async (_url, init) => {
      seenBody = init.body;
      seenAuth = init.headers.authorization;
      return {
        ok: true,
        status: 200,
        json: async () => ({
          access_token: "access",
          refresh_token: "refresh",
          expires_in: 1200,
          refresh_token_expires_in: 3600,
          token_type: "Bearer",
        }),
      };
    },
  );
  assert.equal(result.ok, true);
  assert.equal(seenBody.includes("sim-secret"), false);
  assert.equal(seenBody.includes("client_secret"), false);
  assert.match(seenAuth, /^Basic /);
  assert.equal(seenBody.includes("grant_type=authorization_code"), true);
});
