# Aqil — Authentication, Session Persistence & PWA Reliability Doctrine

**Proposed canon** | Derived from lessons in The Sausage's `docs/canon/auth-session.md`, `docs/canon/production-pwa-nextjs.md` and incident audits | **Not yet implemented in Aqil**

## User promise

An investor should be able to open Aqil on the same phone or browser, read a macro story or check their portfolio, and continue without being unexpectedly logged out after a normal night asleep. Sessions remain valid according to Supabase's configured session policy, user revocation, explicit sign-out and browser storage constraints; do not promise indefinite authentication. Private financial data must **never** appear to an unauthorised user, even transiently.

## Single ownership table

| Concern | Authority | Forbidden duplication |
|---|---|---|
| Browser session storage / browser SDK auto-refresh | One singleton Supabase browser client (using supported SSR integration) | New auth client instance per component; custom token stores |
| Cookie refresh on web request | Current Supabase-recommended Next.js server/proxy middleware pattern; non-authoritative | Middleware redirecting to login on ambiguous refresh failures |
| User identity / access decision | One request-scoped server resolver using verified Supabase user/session claims per current API guidance | `getUser` independently in each page, layout, repo helper, action |
| Protected-page/API guard | Consumes server resolution outcome; returns redirect/401/503 as appropriate | Client-side `getSession` used to grant or deny access |
| DB ownership | RLS and explicit roles/grants, independently verified | Trusting hidden UI or client-supplied `user_id` |
| Auth UI coordination | At most one lightweight event listener for explicit sign-in/refresh/profile updates | Listeners in every component; wake-based auth polling |
| Non-user route revalidation | One coalescing refresh gate with cooldown and in-flight dedupe | Independent `router.refresh` calls on focus + visibility + online |
| User logout | Explicit sign-out flow, updated cookies/server authority, clear private view immediately | Treating every incidental browser `SIGNED_OUT` as proof user intentionally logged out |
| Service worker | Static/public assets only and optional offline public reading, if permitted | Auth authority, secret storage, private portfolio response caching |

## Auth results (typed at server boundary)

- `authenticated`: valid verified server identity, user ID and scoped data access.
- `signed_out`: confirmed no usable session or explicit revocation/logout; preserve safe, validated return route to login.
- `transient_unavailable`: network, rate-limit, concurrent refresh or ambiguous auth transport failure; expose no private data, show calm bounded retry without erasing existing credentials on speculation.
- `terminal_invalid`: definitively unrecoverable session, after narrow checks and bounded recovery; clear **only** necessary Supabase auth state, not unrelated application/browser data.

The resolver must be a request-scoped singleton; cache **the whole classification/recovery lifecycle** for that request. Helpers accept resolved `userId`, tenant scope and authenticated DB context. Do not retry a consumed/stale refresh token from the same immutable incoming cookie within the same HTTP request.

**Important:** client `SIGNED_OUT` is not sufficient to classify an ambiguous server session as signed out. But explicit logout must work promptly and decisively. Do not suppress sign-out actions as a blanket policy.

## Mobile/PWA resume contract

1. Cold load, same-tab background/foreground, 8+ hour idle, browser hard reload and network reconnection must not generate duplicate simultaneous auth refreshers by design.
2. Visibility/online listeners are permitted for **route-owned data freshness** and flushing a pending request, not for global session `getSession` probes.
3. Service worker must not cache authenticated HTML, API/portfolio responses, cookies, OAuth callbacks or research data that breaches storage rights.
4. New builds may invalidate old PWA clients; check build-id on resume and use one guarded reload with cooldown only if proved necessary. No reload loops.
5. A protected route's requested `next` path must survive normal login and recoverable failures. Validate strictly as same-origin internal path to avoid open redirects.
6. Handle user-invoked sign-out, token revocation, clearing browser data, two tabs with differing states and concurrent mobile wakes.
7. Offline private financial screens should show an honest unavailable/loading state unless an explicitly reviewed secure offline model is introduced.

## No broad exception interception

Next.js navigation and redirect mechanisms can throw control-flow exceptions (`NEXT_REDIRECT`). Catch only known typed domain errors; rethrow unknown errors and framework redirects. Avoid checking `Error.name` strings where `instanceof` or typed result discriminants are available. Preserve the intended return destination.

## Logging and privacy

Every request auth resolution: correlation ID, path category, classification, attempts, cache reuse, duration, non-secret reason bucket, terminal/retry outcome. Never log access tokens, refresh tokens, cookies, raw auth headers, OAuth codes, portfolio balances or personal financial activity. Sample normal-success logs; deduplicate incident counts by resolution ID. Monitors: forced-login reason, login bounce, recovered transient, repeated refresh-token reuse and loops.

## Required negative/edge tests before authenticated public beta

| Test | Expected |
|---|---|
| Unauthenticated browser opens `/my-wealth` | Login required, no private response in server payload or cached page |
| Authenticated user A requests user B's data | Denied by DB RLS and route guard, even if URL/ID forged |
| Resume after 8+ hours with expired access token | Normal refresh or bounded soft recovery; not automatic forced login from one ambiguous error |
| Parallel requests during wake/resume | No duplicate auth resolution inside request; no uncontrolled refresher storm |
| No internet at PWA resume | Calm retry, no clearing of valid session as guess, no private data leak |
| Sign out deliberately | Protected pages become inaccessible; cached personal view not retained |
| Another tab signs out | Next authoritative navigation correctly reflects signed-out state |
| Terminal/revoked refresh token | Bounded cleanup, safe `next` route, login without loop |
| OAuth callback and return | Correct cookie exchange, safe same-origin redirect, no repeated callback execution |
| 2x browser zoom / touch / phone install | Core auth flow and error states remain usable |
| Stale installed build | Controlled update; no infinite reload or false logout |

## Implementation order

**NOW (before auth UI):** record doctrine, install official SSR library already scaffolded, design typed resolver API and RLS test strategy. **WHEN AUTH IS ADDED:** implement minimal officially supported flow with one owner and tested defaults. **ONLY IF INCIDENTS REQUIRE IT:** add targeted recovery rules like Sausage's specialised token-reuse recovery markers; don't port the old complexity speculatively.

## Distinction: fail-open vs fail-closed

A middleware cookie-refresh **transport failure** may allow the request to reach server auth validation (fail-open to the guard). The guard, database RLS and content delivery must fail **closed**: never render private information unless a valid identity is confirmed. This distinction must appear in code-review checklists.
