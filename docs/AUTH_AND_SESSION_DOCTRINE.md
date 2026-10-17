# Authentication and session doctrine (canonical)

**Status:** engineering requirement for Aqil v2 baseline.  
**Stack:** Supabase Auth, `@supabase/ssr`, cookie-based sessions on Next.js App Router (see `docs/04_ARCHITECTURE_AND_DATA.md`).

This document states **principles and acceptance criteria**. It does not prescribe obsolete workarounds from other projects.

## 1. Ownership (one authority per concern)

| Concern | Authority | Do not duplicate |
|---------|-----------|------------------|
| Browser session and SDK refresh | One Supabase browser client | A new client or token store per component |
| Cookie update on a request | Current `@supabase/ssr` server pattern | Middleware that logs the user out on an ambiguous refresh failure |
| Identity and access | One request-scoped server resolution | Independent `getUser()` in layout, page and action |
| Private data | That resolution plus RLS | Client `getSession()` as the access grant |
| Wake / focus / online | Coalesced data refresh with cooldown | A session probe on every visibility event |
| Sign-out | Explicit sign-out flow | Treating every incidental `SIGNED_OUT` event as intentional logout |
| Service worker | Optional public assets only | Auth, cookies, or private portfolio/research responses |

Helpers accept the resolved user id. Do not refresh the same incoming refresh cookie twice inside one HTTP request.

## 2. Classification at the server boundary

- `authenticated` — verified identity; private reads allowed under RLS.
- `signed_out` — confirmed absence, revocation, or explicit logout. Preserve a same-origin internal return path (`next`); reject open redirects.
- `transient_unavailable` — network, rate limit, concurrent refresh, or ambiguous transport failure. Show a bounded retry. Do not clear credentials on a guess. Do not render private data.
- `terminal_invalid` — unrecoverable session after bounded recovery. Clear only Supabase auth state.

A client `SIGNED_OUT` event does not by itself reclassify an ambiguous server session as signed out. Explicit logout must still take effect immediately.

**Middleware transport vs authorisation:** a cookie-refresh transport failure may continue to the server guard (fail-open *to the guard*). The guard, RLS and private responses fail **closed**. Never render private information without a confirmed identity.

**Control flow:** rethrow framework redirects (`NEXT_REDIRECT` and equivalents). Catch only typed domain errors. A broad `catch` must not turn a redirect into a false logout or drop `next`.

## 3. Supabase SSR and cookies

- Use `@supabase/ssr` cookie adapters; cookies may be **written** only in Route Handlers or Server Actions.
- Public keys (`NEXT_PUBLIC_SUPABASE_*`) in the browser only; **never** the service role key client-side.
- Start with current library patterns. Add specialised recovery only after a reproduced incident. Do not port historical diagnostic query parameters or incident-specific helpers from other applications.

## 4. Token refresh concurrency

- At most one in-flight browser refresh (coalesce focus, visibility and online).
- Idempotent if refresh returns the same session.
- Correlation id on auth resolution. Never log access tokens, refresh tokens, cookies, OAuth codes or portfolio amounts.
- No silent downgrade of a private route to anonymous content.

## 5. PWA suspend and resume

An overnight idle or phone resume must not force login from one ambiguous error. Sessions follow Supabase policy, revocation, explicit sign-out and browser storage — not an indefinite promise.

- Cold load, background/foreground, long idle (including 8+ hours), reload and reconnect must not start duplicate refreshers.
- Visibility and online listeners may refresh **route data**, not probe `getSession` globally.
- No service worker cache of authenticated HTML, private APIs or research payloads that are rights-restricted.
- A newer deployment may prompt one guarded reload with cooldown. No reload loop and no logout as the update mechanism.
- Offline private screens show unavailable or loading. They do not invent balances.

## 6. Fail closed for private data

- Unconfirmed identity: no private rows, exports or cached financial payloads.
- HTTP `Cache-Control: private, no-store` on wealth and API routes.
- RLS is the database backstop; the route guard is still required.

## 7. Regression tests (required before private authenticated release)

| Test | Expected |
|------|----------|
| Unauthenticated `/my-wealth` | Login required; no private payload |
| User A requests User B's row | Denied by route and RLS |
| Resume after long idle with expired access token | Refresh or bounded retry; not forced login from one ambiguous error |
| Parallel wake requests | One resolution per request; no refresh storm |
| Offline at resume | Retry; session not cleared on a guess |
| Explicit sign-out | Private pages inaccessible; personal view not retained |
| Other tab signs out | Next server navigation is signed out |
| Revoked refresh token | Bounded cleanup; safe `next`; no redirect loop |
| OAuth return | One cookie exchange; same-origin redirect |
| Stale installed build | At most one guarded reload |

Use Playwright with test users. Do not treat a `postgres` connection as proof of RLS.

## 8. Out of scope for this doctrine

- OAuth provider-specific UI polish beyond Supabase-supported flows.
- Custom JWT formats or non-Supabase identity providers without ADR.
- Copying historical client-side session storage patterns from other apps.

## 9. Related documents

- `docs/06_ENGINEERING_DISCIPLINE.md` — risk class R3 for auth changes.
- `docs/10_ACCEPTANCE_TEST_MATRIX.csv` — auth rows.
- `docs/sausage-transfer/` — historical context only.
