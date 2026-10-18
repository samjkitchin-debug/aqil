import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import { createServerClient } from "@supabase/ssr";

import {
  callbackOrigin,
  oauthCallbackDestination,
  oauthCallbackUrl,
  oauthRedirectStaysOnOrigin,
} from "./oauth-callback.ts";
import { isPublicPath } from "./paths.ts";
import { applyAuthCookies, hasPkceVerifierCookie } from "./pkce-cookie.ts";
import { safeNextPath } from "./safe-next.ts";
import {
  classifyAuthFailure,
  configuredAppOrigin,
  documentCacheControl,
  hasAuthSessionCookie,
  isPrefetchRequest,
  isProviderEnabled,
  shouldContactAuthServer,
} from "./session-policy.ts";

test("ordinary access does not consult an allow-list or access grants", () => {
  const access = readFileSync(new URL("./access.ts", import.meta.url), "utf8");
  const proxy = readFileSync(new URL("../../proxy.ts", import.meta.url), "utf8");
  for (const source of [access, proxy]) {
    assert.equal(source.includes("access_grants"), false);
    assert.equal(source.includes("AQIL_AUTHORISED_USER_IDS"), false);
    assert.equal(source.includes("isAllowlisted"), false);
  }
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
    /^http:\/\/localhost:3000\/login\?error=rejected_redirect$/,
  );
  assert.equal(
    oauthCallbackDestination({
      ...base,
      configuredOrigin: "https://aqil-sams-projects-ea6a4d7b.vercel.app",
      code: null,
      exchangeOk: false,
    }),
    "http://localhost:3000/login?error=rejected_redirect",
  );
  assert.equal(oauthCallbackUrl("http://localhost:3000"), "http://localhost:3000/auth/callback");
  assert.equal(callbackOrigin("http://localhost:3000", "https://aqil-tau.vercel.app"), "http://localhost:3000");
  assert.equal(
    oauthRedirectStaysOnOrigin(
      "https://example.supabase.co/auth/v1/authorize?redirect_to=http%3A%2F%2Flocalhost%3A3000%2Fauth%2Fcallback",
      "http://localhost:3000",
    ),
    true,
  );
  assert.equal(
    oauthRedirectStaysOnOrigin(
      "https://example.supabase.co/auth/v1/authorize?redirect_to=https%3A%2F%2Faqil-sams-projects-ea6a4d7b.vercel.app%2Flogin",
      "http://localhost:3000",
    ),
    false,
  );
  assert.match(oauthCallbackDestination({ ...base, providerError: "access_denied", exchangeOk: false }), /provider_denied/);
  assert.match(oauthCallbackDestination({ ...base, code: null, exchangeOk: false }), /missing_code/);
  assert.match(oauthCallbackDestination({ ...base, exchangeOk: false }), /exchange_failed/);
  assert.equal(
    oauthCallbackDestination({ ...base, next: "https://evil.example" }),
    "http://localhost:3000/",
  );
});

test("missing auth configuration is one stable unavailable state", () => {
  assert.equal(classifyAuthFailure({ name: "AuthRetryableFetchError" }), "temporarily_unavailable");
  assert.equal(classifyAuthFailure({ status: 429, message: "rate limit" }), "temporarily_unavailable");
  assert.equal(classifyAuthFailure({ status: 503, message: "upstream unavailable" }), "temporarily_unavailable");
  assert.equal(
    classifyAuthFailure({ message: "Invalid Refresh Token: Already Used" }),
    "terminal_invalid_session",
  );
  assert.equal(classifyAuthFailure({ code: "refresh_token_not_found", status: 401 }), "terminal_invalid_session");
  assert.equal(classifyAuthFailure({ status: 401, message: "unauthorized" }), "signed_out");
  assert.equal(classifyAuthFailure({ status: 403, message: "forbidden" }), "signed_out");
  assert.equal(classifyAuthFailure(null), "signed_out");
});

test("public routes do not contact the auth server", () => {
  assert.equal(shouldContactAuthServer(isPublicPath("/login")), false);
  assert.equal(shouldContactAuthServer(isPublicPath("/auth/callback")), false);
  assert.equal(shouldContactAuthServer(isPublicPath("/research")), true);
  assert.equal(documentCacheControl(), null);
  assert.equal(hasAuthSessionCookie(["sb-project-auth-token"]), true);
  assert.equal(hasAuthSessionCookie(["other"]), false);
  assert.equal(configuredAppOrigin({ nodeEnv: "production" }).ok, false);
  assert.equal(configuredAppOrigin({ nodeEnv: "development" }).ok, true);
});

test("prefetch of a private route is recognisable and does not bounce", () => {
  assert.equal(isPrefetchRequest(new Headers({ "next-router-prefetch": "1" })), true);
  assert.equal(isPrefetchRequest(new Headers({ "next-router-segment-prefetch": "1" })), true);
  assert.equal(isPrefetchRequest(new Headers({ rsc: "1", "next-router-state-tree": "%5B%5D" })), false);
  assert.equal(isPrefetchRequest(new Headers({ "sec-fetch-mode": "navigate", "sec-purpose": "prefetch" })), false);
  assert.equal(isPrefetchRequest(new Headers({ "next-action": "abc", "next-router-prefetch": "1" })), false);
  assert.equal(isPrefetchRequest(new Headers()), false);
});

test("only google is enabled", () => {
  assert.equal(isProviderEnabled("google"), true);
  assert.equal(isProviderEnabled("apple"), false);
  assert.equal(isProviderEnabled("facebook"), false);
  assert.equal(isProviderEnabled("email"), false);
});

test("public routes stay reachable without a session", () => {
  assert.equal(isPublicPath("/login"), true);
  assert.equal(isPublicPath("/privacy"), true);
  assert.equal(isPublicPath("/tos"), true);
  assert.equal(isPublicPath("/auth/callback"), true);
  assert.equal(isPublicPath("/auth/google"), true);
  assert.equal(isPublicPath("/research"), false);
  assert.equal(isPublicPath("/my-wealth"), false);
});

test("oauth start keeps the pkce verifier on the same response the browser follows", async () => {
  const stored: { name: string; value: string }[] = [];
  const redirectCookies: { name: string; value: string }[] = [];
  const supabase = createServerClient("https://example.supabase.co", "public-anon-key", {
    cookies: {
      getAll() {
        return stored;
      },
      setAll(cookiesToSet) {
        applyAuthCookies(
          {
            set(name, value) {
              redirectCookies.push({ name, value });
              const index = stored.findIndex((item) => item.name === name);
              if (index >= 0) stored[index] = { name, value };
              else stored.push({ name, value });
            },
          },
          cookiesToSet,
        );
      },
    },
  });
  const started = await supabase.auth.signInWithOAuth({
    provider: "google",
    options: {
      redirectTo: "https://aqil-tau.vercel.app/auth/callback?next=%2F",
      skipBrowserRedirect: true,
    },
  });
  assert.equal(started.error, null);
  assert.equal(hasPkceVerifierCookie(redirectCookies.map((cookie) => cookie.name)), true);

  const callback = createServerClient("https://example.supabase.co", "public-anon-key", {
    cookies: {
      getAll() {
        return redirectCookies;
      },
      setAll() {},
    },
  });
  const exchanged = await callback.auth.exchangeCodeForSession("not-a-real-code");
  assert.notEqual(exchanged.error?.code, "pkce_code_verifier_not_found");
});

test("a callback without the pkce verifier fails before a session is created", async () => {
  const callback = createServerClient("https://example.supabase.co", "public-anon-key", {
    cookies: {
      getAll() {
        return [];
      },
      setAll() {},
    },
  });
  const exchanged = await callback.auth.exchangeCodeForSession("not-a-real-code");
  assert.equal(exchanged.error?.code, "pkce_code_verifier_not_found");
  assert.equal(exchanged.data.session, null);
});
