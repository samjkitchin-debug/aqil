import assert from "node:assert/strict";
import test from "node:test";

import { isAllowlisted, isForeignUserId, parseAuthorisedUserIds } from "./allowlist.ts";
import { oauthCallbackDestination } from "./oauth-callback.ts";
import { isPublicPath } from "./paths.ts";
import { safeNextPath } from "./safe-next.ts";

const FOUNDER = "11111111-1111-4111-8111-111111111111";
const OTHER = "22222222-2222-4222-8222-222222222222";

test("empty allow-list authorises nobody", () => {
  const allow = parseAuthorisedUserIds(undefined);
  assert.equal(isAllowlisted(FOUNDER, allow), false);
  assert.equal(parseAuthorisedUserIds("not-a-uuid").size, 0);
});

test("allow-list accepts only explicit uuids", () => {
  const allow = parseAuthorisedUserIds(` ${FOUNDER.toUpperCase()}, ${OTHER} `);
  assert.equal(isAllowlisted(FOUNDER, allow), true);
  assert.equal(isAllowlisted("33333333-3333-4333-8333-333333333333", allow), false);
});

test("foreign user ids are rejected", () => {
  assert.equal(isForeignUserId(OTHER, FOUNDER), true);
  assert.equal(isForeignUserId(FOUNDER, FOUNDER), false);
  assert.equal(isForeignUserId(null, FOUNDER), false);
});

test("safe next rejects open redirects", () => {
  assert.equal(safeNextPath("/my-wealth"), "/my-wealth");
  assert.equal(safeNextPath("https://evil.example/steal"), "/");
  assert.equal(safeNextPath("//evil.example"), "/");
  assert.equal(safeNextPath("/login"), "/");
  assert.equal(safeNextPath("/auth/callback"), "/");
});

test("oauth callback rejects mismatched origins and failed exchanges", () => {
  const base = {
    requestOrigin: "http://localhost:3000",
    configuredOrigin: "http://localhost:3000",
    providerError: null,
    code: "abc",
    next: "/research",
    exchangeOk: true,
  };
  assert.equal(
    oauthCallbackDestination(base),
    "http://localhost:3000/research",
  );
  assert.match(
    oauthCallbackDestination({ ...base, requestOrigin: "https://evil.example", configuredOrigin: "http://localhost:3000" }),
    /rejected_redirect/,
  );
  assert.match(oauthCallbackDestination({ ...base, providerError: "access_denied", exchangeOk: false }), /provider_denied/);
  assert.match(oauthCallbackDestination({ ...base, code: null, exchangeOk: false }), /missing_code/);
  assert.match(oauthCallbackDestination({ ...base, exchangeOk: false }), /exchange_failed/);
  assert.equal(
    oauthCallbackDestination({ ...base, next: "https://evil.example" }),
    "http://localhost:3000/",
  );
});

test("public routes stay reachable without a session", () => {
  assert.equal(isPublicPath("/login"), true);
  assert.equal(isPublicPath("/privacy"), true);
  assert.equal(isPublicPath("/tos"), true);
  assert.equal(isPublicPath("/auth/callback"), true);
  assert.equal(isPublicPath("/research"), false);
  assert.equal(isPublicPath("/my-wealth"), false);
});
