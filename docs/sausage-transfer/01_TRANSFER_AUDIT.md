# Deep engineering transfer audit: The Sausage → Aqil

## Executive verdict

The Sausage's most reusable asset is **operational discipline developed after encountering real failures**, not its product code or complicated recovery machinery. Aqil's existing architecture already captures much of the philosophy; what it still needs are precise auth/PWA ownership boundaries, a disposable database verification gate, documentation authority rules, and regression tests targeted at known failure modes. Preserve Aqil's crown-jewel investment research architecture and human-centred design; these are engineering additions, not a pivot.

## Evidence reviewed

- `docs/README.md`, `docs/archive/README.md`, `docs/canon/stable-core.md`, `docs/canon/debt.md`
- `docs/design/{manifesto,enforcement,tokens,layout,components,navigation-and-actions}.md`
- `docs/canon/{auth,auth-session,production-pwa-nextjs,drift-locks,sausage-elo,ingest}.md`
- `docs/auth-session-architecture.md`, `docs/auth-session-reliability-audit.md`
- `docs/architecture/resilience.md`, `docs/ops/{auth-resolution,auth-client-correlation-telemetry,production-runbook,guardrails,rls-and-rpc,db-verify,fixture-ingest}.md`
- `docs/testing/{smoke-tests,v3-release-manual-test-script}.md`, `docs/RELEASE_VERSIONING.md`, `docs/product/sausage-elo-operations.md`

Historical/auth audit documents may describe superseded flows. The final Sausage auth doctrine sits in `docs/canon/auth-session.md` and `docs/canon/production-pwa-nextjs.md`; older writeups explicitly defer to them.

## Transfer matrix

| Sausage lesson | Failure prevented | Aqil adaptation | When |
|---|---|---|---|
| One authoritative document per invariant; archive superseded history | Cursor adopts contradictory old behaviour | Keep Aqil numbered specs; add an authority index, canon for auth/session and portfolio/research invariants, ops runbooks and a history status | Now |
| Design manifesto enforced mechanically | Drift in colours, spacing, interaction affordances | Keep semantic CSS tokens and CI token check; later check component vocabulary, touch semantics and no finance state conveyed by colour alone | Existing; extend with real UI |
| Disposable DB migration replay and executable RPC assertions | Valid-looking SQL fails at runtime, wrong grants | Add `db:verify` using real disposable PG/Supabase and pgTAP; test actual `anon` and `authenticated` claims, not `postgres` bypassing RLS | **Before first remote migration** |
| `PUBLIC` and `anon` function permissions checked separately | SEC. DEFINER function callable anonymously | Review default ACLs, RLS, SECURITY DEFINER search paths, explicit EXECUTE grants; test matrices for sensitive RPCs | Before user-facing RPCs |
| Single authoritative auth resolver per request | Duplicate `getUser` calls, inconsistent redirects | Resolve identity once at server request boundary; pass user/tenant/client to downstream data functions | Before auth UI |
| Conservative session persistence and token-refresh ownership | Wake-induced refresh-token reuse, false logouts | Browser client handles session; server validates access; bounded refresh/recovery, no random component auth probes | Before auth UI |
| Separate transient auth problems from genuine sign-out | Overnight/mobile outage becomes unnecessary forced login | Explicit `authenticated`, `signed_out`, `transient` states; only classified terminal conditions force login | Before auth UI |
| Shared client refresh gate | Visibility/focus/online generate concurrent refreshes | One refresh coordinator; coalesce/limit non-user refresh and data freshness by route | Before PWA release |
| PWA service worker optional to core truth | Stale build/cached authenticated state breaks login | No cached private portfolios or sessions; offline public content optional; service worker never owns auth | Existing constraint; test later |
| Bounded stale-build reload | Installed PWA resumes on an incompatible deployment | Build-id comparison, one guarded reload with cooldown; no infinite retry | When SW/deployment added |
| Structured auth incident correlation | Logs show many incidents for one request | Trace id per auth resolution, classification, cause and deduplicated counters; no token logging | With auth |
| Immutable canonical writes vs derived scoring | Background refresh erases confirmed data | Journal entries/forecast originals append-only; derived holdings, analytics and research summaries recomputable | Finance/research gates |
| Versioned model, fixed evaluation and replay proof | Silent model drift and hindsight bias | Preserve source vintage, method code/config hash, champion/challenger version; compare replay to stored outputs | First research vertical slice |
| Field authority and ingest deletion protections | Incomplete upstream data deletes trusted state | Source ownership by field; partial/error feeds never delete authoritative observations or user records | Source ingestion |
| Adaptive cadence and overlap gates | Expensive provider/API storms | Data-source-aware schedules, cooldown on 403, leases/idempotency, per-run logs and budgets | Scheduled agents |
| CI layered with change-sensitive gates | Slow tests ignored or critical migrations escape scrutiny | Fast checks each PR, DB/security on migration paths, full E2E pre-release, smoke post-deploy | Now/next |
| Build identity and curated release notes | Can't tie incidents to exact shipped code | Semver/build SHA, deploy environment, research-method version; human-readable changelog | Before public beta |
| Operational runbooks and known-debt register | Rediscovery of incidents, repeated bad fixes | Incident response, rollback, known issues, freshness and job-health playbooks | Before recurring jobs |
| UX: one surface one concern / primary task visible | Wall of metrics becomes unusable | Today/Explore/Wealth/Research/ learn layered reading; no misleading fake zeros | Continue UX track |

## The big auth lesson — preserve the user's session without weakening security

Sausage's documented March 2026 incident: after long idle, concurrent mobile/PWA requests carried the same stale refresh cookie; the first token refresh succeeded, another saw `refresh_token_already_used`; an auth-cookie clearing path and broad `catch` that swallowed `NEXT_REDIRECT` could redirect people to an error/login state and lose `next`. The fixes were concentrated, but several iterations were needed. This informs Aqil's acceptance tests from the beginning, not a mandate to port all Sausage custom auth machinery.

**Distinction:** "middleware fail-open" in Sausage refers to letting a request continue to the authoritative **server** guard on a transient refresh failure. **Never** fail-open authorisation, tenant isolation or DB RLS. On ambiguity, private data remains unavailable and a bounded retry can be shown without falsely declaring a sign-out.

## Specific upgrades missing in Aqil's current G0

1. **Auth doctrine**: Current v2 says 'Supabase Auth with SSR/RLS' but does not specify single request resolver, refresh ownership, session state classification, return destination preservation or overnight resume tests. Add a focused document before implementing auth.
2. **Runnable database tests**: Cursor wrote nine pgTAP cases but did not execute them; CI is still unobserved. Docker/local PG or an equivalently isolated and representative environment is a hard gate.
3. **Privilege tests**: RLS tests alone do not verify `EXECUTE` grants on new RPCs, default ACL, `search_path` and service-role boundaries; add before RPC rollout.
4. **Docs governance**: Numbered Aqil docs are useful. Avoid future dual sources of truth as research, portfolio, auth and editorial systems expand; add a small map and a `superseded`/`verified-at` convention.
5. **Auth/mobile reliability regression pack**: Five viewport tests are good, but neither auth nor actual mobile resume is under test yet. Add scenario tests **when auth exists**.
6. **CI trust**: Security advisories should be tracked with provenance and retested; do not assume 'dev-only' means irrelevant to CI. The existing five npm findings merit a recorded risk exception, not `--force` downgrade.
7. **Source ingest integrity**: Design a source-owned-vs-user-owned field registry, complete-snapshot criteria and no-delete-on-partial rule before any multi-source harvesting.

## What NOT to bring across

- The Sausage's full token-reuse recovery query parameter machinery, SAU diagnostic codes and legacy incident-specific helper names. Aqil should start with current `@supabase/ssr` recommended patterns and minimal controlled handling; add complexity only after observed defects.
- Tipping, ladders, sports score RPCs, league membership security shapes, match-oriented high-frequency polling, season versioning or AFL navigation taxonomies.
- Copy/pasted SQL functions, Supabase schema, service-role shortcuts or outdated Next.js middleware/proxy code from Sausage without verifying compatibility with Aqil's Next.js 16 and current Supabase packages.
- The Sausage's historic operating cadence. Aqil's economic factors are slower and source-specific; the research pipeline should be cheap and event-triggered.
- Treating documentation as evidence that actual code implements it; inspect Aqil's code and run tests.

## Current Supabase handover: release decision

**Migration:** `supabase/migrations/20260317103000_create_user_settings.sql` plus `supabase/tests/database/user_settings_rls.test.sql` (9 proposed pgTAP assertions). The prior placeholder was removed and `/database/migrations` now points to the authoritative CLI path. Good direction.

**Blockers to applying to hosted dev:**
- `npm run test:db` blocked by missing Docker. The CI job hasn't yet run; no demonstrated role-based negative RLS results.
- Check migration timestamp because `20260317...` is months older than this October 2026 work. If migration has never been applied anywhere, correct the name once before deploy and commit so chronology remains intelligible.
- Check pgTAP claims genuinely use request roles and synthetic test identities; `postgres` bypasses RLS and could yield false green.
- Migration `apply_migration` via MCP is permitted, but an MCP-only write must never become a second schema history. Prefer official CLI applying the repo versioned migration; if MCP is used, check byte-for-byte SQL identity and tracking against the file.

**Recommended:** install Docker Desktop with WSL2 (or arrange another real disposable PG environment), replay all migrations, run negative tests, then approve hosted development application. The dev project is disposable; the process still deserves proof before access to users' future portfolios.

## Final recommendation

Adopt this as a small supplement to Aqil's v2 architecture, prioritising an **auth/session doctrine** and **testable database release gate**. Do not reshape the product, create new services or rebuild the existing web shell. After integration, freeze the auth boundary and RLS test patterns as invariants. Everything else can be layered later as the corresponding feature develops.
