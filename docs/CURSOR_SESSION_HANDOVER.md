# Cursor session handover (template)

**Latest session:** 18 October 2026, alignment. Read the last block first. Earlier blocks are history and include superseded allow-list instructions.

Copy this block at the **end** of a substantive session (or into the PR description). Keep it factual; no completion claims without evidence.

```text
## Session handover — [YYYY-MM-DD]

### Current objective
[One sentence: what this session was trying to achieve]

### Authoritative docs consulted
- [e.g. 03_RESEARCH_ENGINE_AND_METHODS.md, 07_BUILD_BACKLOG.csv AQ-xxx]

### Git
- Branch: [name]
- Commit: [short SHA] ([main | feature])

### Files changed (high level)
- [paths or areas]

### Decisions made
- [Decision] — [why]

### Tests and verification
| Command / check | Result |
|-----------------|--------|
| [e.g. CI run URL or npm run test:db] | [pass/fail/not run] |

### Progress register
- Backlog IDs updated: [AQ-xxx → status]
- Evidence recorded in: [verification_evidence column / PR / CI link]

### Unverified assumptions
- [Anything not executed or not reviewed]

### Blockers
- [Or “none”]

### Next recommended step
- [Single concrete action for the next session]
```

**Rules:** Update `docs/07_BUILD_BACKLOG.csv` when a backlog item’s status or evidence changes. Do not duplicate the full project history here or in chat summaries.

## Session handover — 2026-10-17

### Current objective
Record historical analogues as a later method-family requirement, then implement the M1 Phase 0 source-rights register and fail-closed tests.

### Authoritative docs consulted
- docs/03_RESEARCH_ENGINE_AND_METHODS.md
- docs/07_ROADMAP_AND_GATES.md
- docs/07_BUILD_BACKLOG.csv AQ-008, AQ-064, AQ-066
- docs/AGENT_OPERATING_RULES.md
- BLS, FRED, Treasury.gov, Fiscal Data and Board H.15 terms pages reviewed on 2026-10-17. No data APIs were called.

### Git
- Branch: main
- Commit: not created in this session

### Files changed (high level)
- docs/03_RESEARCH_ENGINE_AND_METHODS.md — historical analogue subsection
- docs/07_ROADMAP_AND_GATES.md — M1 exclusion and later-milestone bullet
- docs/07_BUILD_BACKLOG.csv — AQ-008, AQ-064, new deferred AQ-066
- docs/sources/SOURCE_RIGHTS.csv
- workers/research/src/aqil_research/sources/rights.py
- workers/research/tests/test_source_rights.py

### Decisions made
- First live provider is BLS LNS14000000. The current LN file is latest-revised, not a vintage panel.
- First methodology remains the Sahm rule, to be implemented after the vintage store, on fixtures shaped like that series.
- FRED/ALFRED UNRATE is ineligible for retention, archiving, redistribution, commercial publication and AI use.
- H.15 is the yield-curve candidate. Treasury.gov daily yield-curve XML has no recorded licence. Fiscal Data average interest rates are a different dataset and are not that model’s input.
- Historical analogues are required later (AQ-066) and are not M1.

### Tests and verification
| Command / check | Result |
|-----------------|--------|
| uv run pytest (workers/research) | 9 passed |
| uv run ruff check . | clean |
| uv run ruff format --check . | clean |
| GitHub CI | not re-run |

### Progress register
- Backlog IDs updated: AQ-008 → Implemented — unverified; AQ-064 remains Not started; AQ-066 added as Deferred
- Evidence recorded in: AQ-008 and AQ-064 verification_evidence

### Unverified assumptions
- H.15 series codes for the 10-year yield and the 3-month bill are unconfirmed.
- Treasury.gov site policies contain no data licence for the yield-curve XML feed.
- BLS terms do not name AI use, so AI operations stay unknown.
- CI has not run on these files.

### Blockers
- None for Phase 1 fixture work. Live collection still needs the H.15 series map before that method, and a Treasury licence before that feed.

### Next recommended step
- Implement observation.v1 with period, provider vintage date, release timestamp when known, earliest defensible model-availability time, and collection time. A date-only vintage is available only after that date. Then add an in-memory append-only vintage store and as-of tests. Then implement the Sahm rule on fixture observations shaped like LNS14000000. Do not call live APIs in that step.

## Session handover — 2026-10-17 (M1 Phases 1–2)

### Current objective
Deliver the first synthetic analytical pathway: observation validation → vintage as-of → Sahm rule → structured research result (publication still fail-closed).

### Authoritative docs consulted
- docs/schemas/observation.v1.json, method_card.v1.json
- docs/03_RESEARCH_ENGINE_AND_METHODS.md
- docs/07_BUILD_BACKLOG.csv AQ-002, AQ-008, AQ-012, AQ-064
- Claudia Sahm (2019) rule definition as implemented in code comments and MethodCard fixture

### Git
- Branch: main
- Commit: not created in this session

### Files changed (high level)
- docs/schemas/observation.v1.json and packages/contracts mirror
- workers/research/src/aqil_research/contracts/ (observation, method_card)
- workers/research/src/aqil_research/vintages/ (store, asof)
- workers/research/src/aqil_research/methods/ (sahm, configs)
- workers/research/src/aqil_research/pipeline/, interpret/
- workers/research/tests/ (observation, vintage, sahm, pipeline + fixtures)
- docs/07_BUILD_BACKLOG.csv, docs/10_ACCEPTANCE_TEST_MATRIX.csv

### Decisions made
- Date-only provider vintage availability: start of UTC day after `provider_vintage_date`.
- `latest_revised` rows have no model-availability time and are excluded from point-in-time selection.
- Sahm evidence_stage remains `implemented` (not `replicated`) until an independent reference example is matched.
- Two configs share one `run_sahm` implementation; identity via `config_hash` and `input_snapshot_hash`.

### Tests and verification
| Command / check | Result |
|-----------------|--------|
| uv run pytest (workers/research) | 25 passed |
| uv run ruff check . | clean |
| uv run ruff format --check . | clean |
| GitHub CI | not re-run |

### Progress register
- AQ-002, AQ-008, AQ-012, AQ-064 → Implemented — unverified (local evidence only)

### Unverified assumptions
- Sahm window wording matches every official Fed/Brookings worked example (hand-calculated fixture only).
- CI has not run on these files.
- No live BLS vintage history; LN file remains latest-revised until an adapter exists.

### Blockers
- None for continuing with a rights-checked BLS adapter on the same pipeline.

### Next recommended step
- Implement the first live BLS adapter for `bls.ln.LNS14000000`: rights gate → normalised `EconomicObservation` rows (`latest_revised` until true vintage history exists) → existing store and `run_research`. No Sahm logic changes.

## Session handover — 2026-10-17 (M1 Phase 3)

### Current objective
Prove modular provider and method interchangeability through executable tests and a single orchestration entry point.

### Authoritative docs consulted
- docs/03_RESEARCH_ENGINE_AND_METHODS.md (modular pipeline subsection added)
- docs/schemas/*.v1.json
- docs/07_BUILD_BACKLOG.csv AQ-002, AQ-064

### Git
- Branch: main
- Commit: not created in this session

### Files changed (high level)
- workers/research/src/aqil_research/adapters/ (protocol, two fixture adapters, registry)
- workers/research/src/aqil_research/methods/ (protocol, registry, period_change, sahm_registered, parameters)
- workers/research/src/aqil_research/pipeline/ (orchestrate, ingestion, evidence, integrity)
- workers/research/tests/test_modularity_proofs.py, test_orchestration_failures.py, test_schema_contracts.py
- docs/schemas/observation.v1.json date-precision conditional fix (mirror updated)

### Tests and verification
| Command / check | Result |
|-----------------|--------|
| uv run pytest (workers/research) | 40 passed |
| uv run ruff check / format --check | clean |
| GitHub CI | not re-run |

### Progress register
- AQ-002, AQ-064 updated with Phase 3 evidence (unverified until CI)

### Next recommended step
- Live BLS adapter registered in `AdapterRegistry`, feeding `execute_research_run` with `collect=True`.

## Session handover — 2026-10-17 (M1 Phase 4)

### Current objective
Connect the modular engine to authorised live BLS unemployment data and produce a reproducible Sahm research run.

### Preflight
- Prior phases: pytest 40 passed before Phase 4 work.
- BLS rights row `bls_cps_unemployment_rate`: automated_access, internal_computation, raw_data_retention permitted; AI processing/training **unknown** (not used).

### Live execution (one bounded request)
| Field | Value |
|-------|--------|
| Endpoint | `https://api.bls.gov/publicAPI/v2/timeseries/data/` |
| Collection time (UTC) | 2026-10-17 (worker local run) |
| Series | LNS14000000 |
| Window | start_year=2022, end_year=2025 |
| Observations ingested | 47 |
| Analysis mode | `latest_revised` |
| Evaluation month | 2025-09-01 |
| Three-month average | 4.3333% |
| Prior 12-month low of 3-month averages | 4.1000% |
| Gap | 0.2333 pp |
| Published 0.50 threshold | **not met** |
| `BLS_API_KEY` | not set; request succeeded without registration key |
| Persistence | **execution-only** (`InMemoryObservationStore`); export via `--export` optional |
| Publication | **blocked** (fail-closed) |

### Tests and verification
| Check | Result |
|-------|--------|
| uv run pytest | 48 passed |
| uv run ruff check / format --check | clean |
| GitHub CI | not re-run |

### Operator command
```bash
cd workers/research
uv run aqil-research run --source bls --method sahm              # offline fixture (default)
uv run aqil-research run --source bls --method sahm --live      # opt-in live BLS API
```

### Recommended durable storage (next)
Append-only `economic_observations` (or equivalent) in `supabase/migrations/` with Git-reviewed schema, storing full observation rows keyed by vintage identity; retain collection snapshots rather than overwriting. No migration in this phase.

### Next recommended step
Design and approve a minimal Postgres observation snapshot table; back the existing `ObservationStore` protocol without changing Sahm logic.

## Session handover — 2026-10-17 (Grok M1 audit corrections F1–F9)

### Current objective
Surgically correct Grok 4.7 High M1 independent audit findings without redesigning the engine; establish a verified offline baseline before Postgres research storage.

### Audit findings addressed
| ID | Status | Summary |
|----|--------|---------|
| F1 | Corrected locally | `rights_gate.py` enforces ingest/analysis/replay at orchestrator and ingestion boundaries; pipeline negative tests in `test_audit_corrections.py` |
| F2 | Corrected locally | `EconomicObservation` rejects `earliest_model_available_at` before `source_release_at`; latest-revised excluded from PIT as-of |
| F3 | Corrected locally | Full observation canonical snapshot hash; payload hash excludes self; `verify_analytical_payload_hash`; Sahm `implementation_hash` from `sahm.py` bytes; method version **1.0.1** |
| F4 | Accepted | BLS latest-revised labelled in adapter/notes (no change to scope) |
| F5 | Corrected locally | Two-decimal rounding on 3-month averages before min/gap; one-decimal input validation; expanded Sahm boundary tests |
| F6 | Corrected locally | BLS parse raises on contradictory duplicate periods; orchestrator `failed_ingest` on vintage conflicts; CLI no silent eval walk-back without `--allow-evaluation-fallback` |
| F7 | Corrected locally | BLS client: no retry on 4xx; retry on 5xx/timeouts; 10/20 inclusive year caps |
| F8 | Corrected locally | `completed_insufficient` execution status; evidence assessment documented as non–claim-verification |
| F9 | Corrected locally | `MethodContext.inputs_by_dataset`, `ResearchRun.input_dataset_ids` |

### Tests and verification
| Command / check | Result |
|-----------------|--------|
| `npm run test:research` | **60 passed**; ruff check clean; ruff format clean (after format pass) |
| GitHub CI | **not re-run** |
| Live BLS | **not re-run** this session |
| Historical PIT market study on BLS | **not validated** (latest-revised collection only) |
| Academic Sahm replication certificate | **not claimed** |

### PostgreSQL readiness
Observation and research-run JSON shapes are **stable enough to draft** a migration, but durable storage should key on vintage identity (including release/retrieval discrimination) and store full observation payloads — not a single `dataset_id` FK on the run row.

### Git
- Branch: main
- Commit: **not created** (awaiting founder approval)

### Next recommended step
Founder review of diffs; then commit and run GitHub CI. Approve minimal `economic_observations` migration design when ready.

## Session handover — 2026-10-17 (M2 accelerated persistence vertical slice)

### Current objective
Complete durable research persistence: Postgres adapters, immutable runs, operator CLI, memory equivalence and immutability proofs, CI integration — without hosted Supabase deploy.

### Authoritative docs consulted
- docs/AGENT_OPERATING_RULES.md
- docs/07_BUILD_BACKLOG.csv AQ-012, AQ-064, AQ-067
- supabase/migrations/README_RESEARCH_SCHEMA.md

### Git
- Branch: `m2/research-persistence-schema`
- Commit: pending push (this session)

### Files changed (high level)
- `supabase/migrations/20261017110000_create_research_schema.sql` — grant execute on all `research` functions to `research_writer`
- `supabase/migrations/20261017120000_research_worker_login.sql` — `research_worker` LOGIN (local/CI password)
- `workers/research/src/aqil_research/persistence/` — connection, ingest, observations, runs, reproduce
- `workers/research/src/aqil_research/cli.py` — `--store postgres`, `retrieve-run --recompute`
- `.github/workflows/ci.yml` — Supabase start + integration pytest
- `workers/research/tests/test_persistence_integration.py`

### Decisions made
- Worker DB principal is `research_worker` (inherits `research_writer`); `service_role` rejected in Python connection guard.
- CHECK-constraint helper functions require explicit `EXECUTE` grants after default revoke-from-public.
- `attempt_count` coerced to ≥1 on retrieval insert when fixture diagnostics report 0.

### Tests and verification
| Command / check | Result |
|-----------------|--------|
| `npx supabase db reset --no-seed` | pass |
| `npm run db:test` | **55** pgTAP pass |
| `uv run pytest` (workers/research, `RESEARCH_DATABASE_URL` set) | **62** passed |
| `uv run aqil-research run ... --store postgres --run-id cli-demo-1` | completed; payload hash `88808a3e...` |
| `uv run aqil-research retrieve-run --run-id cli-demo-1 --recompute` | `recompute_calculation_match=True` |
| GitHub CI | pending after push |
| Hosted Supabase migration | **not applied** |

### Progress register
- Backlog: AQ-012, AQ-064, AQ-067 updated
- PR: #6 (same feature branch)

### Blockers
- none for local/CI; hosted deploy requires founder approval

### Next recommended step
Review and merge PR #6 after green CI; rotate `research_worker` password on hosted apply.

## Session handover — 2026-10-17 (M3 first investment-intelligence sprint)

### What Aqil can do now
- **Collect** permitted BLS unemployment data with rights checks, retrieval provenance, conflict handling and idempotent duplicate-response detection (`aqil-research collect`).
- **Collect and run** Sahm end-to-end into PostgreSQL with replay verification and structured insight export (`aqil-research collect-and-run`).
- **Founder web preview** on Today and Research via server-only `research_insight.v1.json` (fixture in CI; `.local/` from `npm run research:preview`).
- **Manual GitHub workflow** `.github/workflows/research-pipeline.yml` (fixture dry run; live mode blocked until secrets).

### Demonstrated (local)
| Item | Value |
|------|--------|
| Fixture | `workers/research/tests/fixtures/bls/api_lns14000000_success.json` |
| Run ID | `m3-e2e-run` |
| Sahm gap | 0.50 pp; threshold met |
| Insight export | `apps/web/fixtures/research-insight.v1.json` |
| Commands | `npm run research:preview`; `uv run aqil-research collect-and-run ... --export-insight` |

### Git
- M2: **merged** PR #6 → `main` @ `36681bb` (+ credential fix `70b03b8` on branch before merge)
- M3 branch: `m3/first-investment-intelligence` (PR URL after push)

### Tests
| Check | Result |
|-------|--------|
| `uv run pytest` | **67 passed**, 1 skipped |
| `npm run db:test` | **55** pgTAP |
| Web typecheck/lint | pass locally |
| GitHub CI | pending on M3 PR |

### Security / integrity
- `research_worker`: NOLOGIN in migrations; password only via `scripts/provision-research-worker-local.sql` (not for hosted).
- BLS data: **latest_revised**; UI labels internal preview; `publication_allowed` remains false.
- No browser access to `research` schema or worker credentials.

### Known limitations
- `recompute_match` CLI flag may be false when the DB contains observations beyond the frozen run set; calculation dict replay is tested in workflow integration.
- Treasury 10y–3m spread: assessed, **blocked** — see `docs/sources/TREASURY_YIELD_SPREAD_ASSESSMENT.md`.

### Grok High review (paste when ready)
Review M3 PR for: source rights, temporal integrity (latest-revised labelling), reproducibility, DB grants/function EXECUTE, secret handling, unpublished vs public research, Sahm insight wording. Do not reopen architecture.

### Next milestone
Hosted approval path: vault `research_worker` password, apply Git migrations, enable `research-pipeline` live mode with BLS key — then second macro source after Treasury licence resolution.

## Session handover — 2026-10-17 (M4 review corrections)

### Current objective
Close the four M4 review findings on PR #8, then merge once GitHub Actions is green on the corrected tip. No hosted migration. No live scheduling.

### Corrections
- Synthetic holdings, expectations, scenarios and outcomes are labelled `synthetic_demonstration`. VWRA ISIN stays verified instrument identity. FOMC schedule stays a verified calendar citation; materiality is `insufficient_evidence` because no holdings weight is linked.
- Identical imports conflict on content hash, not retrieval time. A changed holdings snapshot inserts a new row. Frozen scenarios are not updated.
- `forward-demo` loads the horizon from the stored scenario row. The web fixture is that export (`record_source: database`). Founder cookie gate unchanged. `forward` stays out of the Data API.
- Web rejects malformed or contradictory `forward_horizon.v1` payloads. pgTAP denies `service_role` on the forward schema.

### Idempotency evidence (local, two imports, different `recorded_at`)
Row counts stayed: instruments 1, holdings snapshots 1, holding lines 3, catalysts 2, exposures 1, expectations 1, scenarios 1, outcomes 1. Scenario `aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee` hash `6e04c5dbb50603fea66a64f724ee41a7fb54e7307e5c53b51bcaf698041a3943` unchanged. A later revised snapshot did not change that hash; the outcome still references the same scenario id.

### Tests (local)
| Check | Result |
|-------|--------|
| `supabase db reset` then `supabase test db` | 70 pgTAP passed |
| `uv run pytest` | 80 passed, 1 skipped |
| `uv run ruff check` / `ruff format --check` | pass |
| Web typecheck, lint, production build | pass |
| `npm run test:forward-contract` | 7 passed |
| Playwright on a fresh production server | forward-horizon specs passed; 68 passed, 2 failed on the unauthorised research empty-state strict-mode case (skipped in GitHub CI via `E2E_USE_DEV_SERVER`) |

### Remaining limitations
- Holdings weights and the Microsoft earnings path are demonstration data. The FOMC date is a calendar citation, not a measured market effect.
- Hosted Supabase is not migrated. Live scheduling is not enabled.

### Git
- **main:** PR #7 merged (`54c4a16`).
- **M4:** PR #8 `m4/forward-intelligence`. GitHub Actions on the correction commit is the merge gate.

## Session handover — 2026-10-18 (Google auth foundation)

### Current objective
Replace the founder-cookie gate with Supabase Google OAuth, explicit founder allow-listing, and fail-closed private routes.

### Git
- Branch: `auth/google-foundation` from `origin/main` (`dd82e40`)
- PR #11 (My Wealth) and M5/M6 were not merged

### Tests and verification
| Check | Result |
|-------|--------|
| `npm run test:auth` | 6 passed |
| typecheck, lint, `npm run build` | pass |
| `npm run db:test` | not run — Docker engine offline |
| Playwright | not run — browser binary missing in this environment |
| curl against `next start` on port 3010 | `/research` and `/my-wealth` returned 307 to `/login?error=unavailable` with `Cache-Control: private, no-store`; login HTML had the Google button and no research payload; `/auth/callback?error=access_denied` redirected to `error=provider_denied` |

### Unverified
- pgTAP `access_grants_rls.test.sql` (needs Docker / CI database job)
- Live Google OAuth round-trip (needs the founder's client id in the Supabase project and `AQIL_AUTHORISED_USER_IDS`)

### Next recommended step
- After this PR merges, rebase PR #11 and delete the unauthenticated synthetic portfolio fallback in `load-snapshot.ts`.

### Flicker follow-up (same branch)
- Dev log showed repeated `GET /login?error=unavailable` **200** document loads from Edge, with `Cache-Control: no-store`, not a 307 cycle. A fresh tab stayed idle.
- Public routes no longer call Auth. Private link prefetch returns 204 instead of a redirect to login. The login page no longer resolves a session on the server.
- After that change the document reload stopped (one 200, then silence on the dev server).
- Live Google round trip and pgTAP remain outstanding. Docker was offline.

## Session handover — 2026-10-18 (auth audit incorporation)

### Current objective
Stop the signed-out login loop and keep authentication reliable when Auth is slow, failing, or refreshing, without making the proxy the only authorisation authority.

### Confirmed root cause
The flicker was a document reload of `/login?error=unavailable`, not a 307 redirect loop. The dev server logged repeated `GET` 200 responses with `Cache-Control: no-store`. Two causes were confirmed in code:

- `proxy.ts` used to call `getUser()` before deciding that `/login` and `/auth/callback` are public. That is removed. Public routes return before any Auth call.
- The login shell still rendered a brand link to `/` with prefetch enabled, and primary navigation links to protected routes. A protected prefetch that redirected back to login gave the browser another document to load. Protected prefetches now return 204, and links in the shell use `prefetch={false}`.

### What changed
- No Auth call when there is no Supabase auth cookie. A terminal refresh failure signs out once, then redirects. HTTP 429 and 500–599 are temporary unavailability, not sign-out.
- Production sign-in and the OAuth callback require `NEXT_PUBLIC_APP_URL`. The callback does not exchange a code when the origin does not match.
- Allow-list and `access_grants` stay in `resolveAccess()` for the server render. The proxy does not inject an identity header. `getClaims()` is not in the installed Auth SDK. Founder cookie and header paths stay absent.
- Privacy copy no longer describes a founder cookie or development-only access. It does not claim portfolio rows exist in this branch.

### Tests and verification
| Check | Result |
|-------|--------|
| `node --experimental-strip-types --test src/lib/auth/auth.test.ts` | 10 passed |
| Browser, 32 seconds on `http://localhost:3000/login?error=unavailable` | Stayed on that URL. 1 navigation, 17 static resources, no protected-route request. Dev log had no further `GET /login` during the wait. |
| `npm run db:test` | not run — Docker engine offline |
| Real Google OAuth, expired-token rotation, two tabs, 429/503 against Auth, Playwright, production browser | not run |

### Blockers
- Docker is offline, so `access_grants` pgTAP and My Wealth RLS are unverified here. My Wealth RLS lives on PR #11, which was not merged.
- Google client configuration and `AQIL_AUTHORISED_USER_IDS` are outside Git, so a live OAuth round trip was not attempted.
- A session cookie still produces two sequential `getUser()` calls: proxy refresh, then one React-cached server authorisation. That is the supported cookie-propagation pattern. A live two-tab rotation test was not run.

### Next recommended step
Re-run `npm run db:test` when Docker is up, then one real Google sign-in once the dashboard client and allow-list are set. Do not merge PR #11 or apply hosted migrations until that evidence exists.

## Session handover — 2026-10-18 (auth final hardening)

### Current objective
Remove global sign-out from the proxy, correct privacy claims, and run the checks that can actually run on this machine.

### Confirmed findings still true at b662596, and what changed
- A bare HTTP 401 or 403 was classified as a terminal session, and the proxy then called `signOut()` (global by default in the installed SDK). That call is removed. Only a confirmed dead refresh token (`refresh_token_not_found`, `refresh_token_already_used`, `session_not_found`, or the matching message) is terminal, and the proxy only expires the local auth cookies.
- Explicit sign-out now uses `scope: "local"`.
- The installed GoTrue client refreshes inside the expiry margin only. A labelled mock fetch showed two `getUser()` calls on a current token make two user lookups and zero token refreshes. An expired token refreshed once. This is not a live rotation.
- A database grant error now keeps the `next` path.
- Next.js 16 prefetch is `next-router-prefetch` or `next-router-segment-prefetch`. A navigation (`sec-fetch-mode: navigate`) or a Server Action is not answered with 204.
- `getClaims()` is still absent. No identity header was added.

### Tests
| Check | Result |
|-------|--------|
| `npm run test:auth` | 13 passed (3 of them are mock Auth HTTP, labelled in the test name) |
| Production `next build` | passed |
| Local `supabase test db` on 127.0.0.1 | 75 pgTAP passed, including `access_grants_rls.test.sql`. Windows had reserved ports 54321–54329, so the stack was started on temporary local ports and `config.toml` was restored afterwards. |
| Playwright laptop project against `next start` on port 3010 | 25 passed, 1 failed. The failure is `/auth/callback?error=access_denied` landing on `error=unavailable` because this build had no `NEXT_PUBLIC_APP_URL`. CI bakes that URL in at build time. |
| Production login idle, 300 seconds | Stayed on `/login?error=unavailable`. 1 document request. Footer prefetch of `/privacy` and `/tos` only. No protected-route request. |
| Dev login via 127.0.0.1 | 6 document loads. The dev log shows Next blocked HMR from 127.0.0.1. That is not an Auth redirect loop. |
| Client static chunks | no `SERVICE_ROLE`, `client_secret` or `sb_secret_` match |
| Real Google OAuth, second identity, two tabs, live 429/503, revoked refresh | not run. No `.env` or `.env.local` is present, so there is no configured Google client or allow-list. |
| My Wealth RLS | not on this branch |

### PR #11 rebase, not done here
- `load-snapshot.ts` still returns the synthetic fixture when `getUser()` has no user, after the old founder-cookie gate.
- That branch's `founder-access.ts` still accepts the founder cookie, the founder header, and a non-production open gate.
- `my_wealth_rls.test.sql` has 3 tests (cross-user read, cross-user insert, anon select). It does not cover update, delete, or the other wealth tables.
- There is no portfolio mutation server action on that branch.

### Verdict
Not safe for real founder financial data. Do not merge PR #11 onto this until the fixture fallback and founder cookie are gone and the wealth RLS file has been run. Do not apply hosted migrations.

### Next recommended step
Merge PR #12 only after its CI is green. Then rebase PR #11, delete the fixture fallback and cookie gate, and re-run wealth pgTAP. A live Google round trip still needs the dashboard client and `AQIL_AUTHORISED_USER_IDS`.

---

## Session handover — 2026-10-18 alignment

This block supersedes the allow-list instructions above. PR #12 is already merged. Google sign-in works on the live site. The founder confirmed that sign-in.

### Current objective
Consolidate the repository around the live app without a new feature, a GitHub push, or a Vercel deployment.

### Git
- Local branch: `alignment/2026-10-18`, parent `origin/main` `6f47bdb`.
- `origin/main`: `6f47bdb781a544edbdc68275bf3f11276589cd70`.
- Live site still serves that commit. This alignment commit is local only.
- No push. No Vercel deployment. No hosted migration.

### What changed
- Removed the unused allow-list module, the unapplied `20261018180000_access_grants` migration, its pgTAP file, and the generated `access_grants` type.
- Added a regression test that `access.ts` and `proxy.ts` do not consult an allow-list or `access_grants`.
- Recorded the live workflow, ADR 020, the three product pillars, and the five hosted migrations in the existing docs.
- Replaced a gitignored env example that contained a service-role JWT and a Google client secret with placeholders, and allowed `.env.example` to be committed.

### Hosted migrations
`list_migrations` on `ojvswermsbbaltjohqph` returned only:
`20261017103000`, `20261017110000`, `20261017120000`, `20261017140000`, `20261017180000`.

### Tests this session
| Check | Result |
|---|---|
| `npm run typecheck` | pass |
| `npm run lint` | pass |
| `npm run test:auth` | 13 pass |
| `npm run check:tokens` | pass |
| `npm run build` | pass |
| Playwright `e2e/auth.spec.ts` desktop-wide against localhost:3000 | 9 pass, signed-out only |
| `uv run ruff check`, `ruff format --check`, `pytest` in `workers/research` | ruff pass; 74 passed, 7 skipped |
| `npm run test:db` | fail. Local container `supabase_db_ojvswermsbbaltjohqph` cannot bind TCP 54322 |

### Not verified here
A fresh local Google round trip, refresh, navigation and sign-out were not repeated. The founder already completed live sign-in. Two Google identities were not compared in the browser.


