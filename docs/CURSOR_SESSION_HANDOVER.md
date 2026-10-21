# Cursor session handover

**Status:** living continuity note  
**Last updated:** 22 October 2026, sourced releases and confirmed calendar  
**Parent:** `c306f1f` on `work/aqil-autonomous-build`  
**Checkpoint:** local only. Not pushed. Production, hosted migrations and Saxo authorisation stay unchanged.

## Sourced releases and confirmed calendar, 22 October 2026

The Employment Situation feed at `https://www.bls.gov/feed/empsit.rss` returns HTTP 403 to the default `python-httpx` agent and HTTP 200 to `AqilResearch/1.0`. That is the same registered source. The client now sends that name. Live ingest stored 12 sourced updates. The newest publication is 2 October 2026, 11:51 UTC, title “Both payroll employment (+29,000) and unemployment rate (4.2%) change little in September”, source `bls_employment_situation_archive`, retrieved 21 October 2026, 20:37 UTC. A second ingest reported `publications_outcome=unchanged`. Signed-in Today and Evidence showed the 12 releases, with the September release first. The historical series remains retrieval `acb7a909-2650-4d50-8fc2-89be29aff7aa`, 44 observations.

The official BLS iCalendar states start times with `TZID=US-Eastern`. Twenty-seven future confirmed entries were stored in the existing `forward.catalyst_events` table. Employment Situation is scheduled 6 November 2026, 08:30 Eastern Time, last verified 21 October 2026, 20:38 UTC. A second ingest stored 0 new calendar rows and refreshed the verification time. Entries with no clock time were not stored. Migration `20261022120000_catalyst_verification_update.sql` grants update of the verification and schedule columns only. It was applied on a disposable database at port 56532, where `research_writer` could update `last_verified_at` and could not update `title`, and anon could not read the table. The same file was then applied to the preserved database on port 55432. `npm run test:db` was not run. The 44 observations remained.

Signed-in Intelligence Upcoming listed those confirmed times. Desktop and a 390px Today view showed the releases and the series, with no horizontal overflow.

## Today acceptance, 21 October 2026

Signed-in Today at `http://localhost:3000/` showed the persisted retrieval `acb7a909-2650-4d50-8fc2-89be29aff7aa`. The panel read: 44 monthly observations, January 2023 to September 2026, latest observation September 2026 at 4.2 percent, October 2025 not published, retrieved 21 Oct 2026, 08:11 UTC. Source `bls_cps_unemployment_rate`, dataset `bls.ln.LNS14000000`. The sourced briefing said no sourced updates have been retrieved. The database still has that one live retrieval, 44 observations, and 0 `research.sourced_updates` rows. It was not reset.

Intelligence Upcoming says no validated catalyst date has been retrieved. Evidence says no sourced updates have been retrieved. Exposures says no authoritative exposure mapping has been retrieved. Learn is labelled an illustration. Desktop and a 390px viewport both showed the series, with primary navigation at the bottom on the narrow width. No horizontal overflow. The Cursor browser console reported hydration mismatches on `data-cursor-ref`. Those attributes are not in the application source.

SLOOS and Census advance-orders methods from `m6/research-methods` are now on this branch, including their rights-register rows. The freshness gate still blocks a partial live series fetch. Fixture collection is allowed only when `collection_mode` is `fixture`. The macro-conditions integration test rolls back, so it did not add fixture rows beside the live retrieval. Those methods are not rendered on Today.

M5 is not merged. Its calendar page loads a forward-horizon bundle that can be a fixture, which would replace the current sourced-date gate. Its migrations `20261018100000` and `20261018140000` sort before `20261018200000` and must not be applied in that order. The integration path is a later additive migration, after `20261021110000`, containing only the constraint changes and `forward.collection_runs`, followed by collectors that persist `verified_schedule` rows. Do not run `npm run test:db` until that work is ready to reset a disposable database. This preserved database stays as it is.

`my-wealth/portfolio-slice` is not merged. Its migration `20261018160000` would sort before the current wealth migrations, and its UI is an earlier slice beside the cockpit, journal and Deploy Capital already on this branch. `docs/consolidation-2026-10-18` would overwrite newer charter, roadmap and handover text. `auth/google-foundation` is patch-equivalent (`git cherry` marks all three commits `-`) and was not deleted. The Sahm worktree at `C:/Users/gamer/aqil-sahm` still shows a modified test file and was not touched. No remote branch was deleted and no pull request was closed.

## Consolidation, 21 October 2026

The audited HEAD was `2f8a353`. This note is the consolidation on that parent.

Live BLS series request window was 2023 through 2026. The response was HTTP 200, `REQUEST_SUCCEEDED`, 45 monthly points and no annual rows. Parsed usable observations: 44. `missing_months` had been `missing value for 2025-10-01` because the value is `-` with footnote code 9, "Data unavailable due to the 2025 lapse in appropriations." That is an official absence, not a pagination failure and not an unreleased month. September 2026 is the latest returned month. October 2026 is not yet due. The freshness gate still rejects a genuinely partial or stale payload. An officially unavailable month no longer sets `partial`. After the correction, the same live read is `partial=false` with 44 observations. October 2025 is not stored as a number.

Local Supabase now uses database port 55432, API port 55421, and shadow port 55420. Those ports sit outside the Windows exclusion 54253–54352. `npm run test:db` passed first: 10 files, 159 tests, on disposable local Postgres only. The live ingest then stored retrieval `acb7a909-2650-4d50-8fc2-89be29aff7aa` at `2026-10-21T08:11:51.888853Z`, HTTP 200, `REQUEST_SUCCEEDED`, window 2023–2026, 44 observations from January 2023 to September 2026. October 2025 has no row. Unit percent, latest revised, seasonally adjusted, monthly, observed, geography US. A second ingest reported `unchanged=44` and `new=0`. The database was not reset after that retrieval. Do not use `supabase test db --linked`.

The Employment Situation RSS still returns HTTP 403. The existing parser accepts RSS and Atom only, so the HTML archive was not scraped. `research.sourced_updates` has 0 rows. Today now also reads the latest live `research.economic_observations` retrieval and presents it as a historical monthly series, with the October 2025 gap named and nothing filled in. On 21 October 2026 the founder signed in through Cursor’s browser. Today showed the historical series: 44 observations from January 2023 to September 2026, October 2025 not published, retrieved 21 Oct 2026, 08:11 UTC. The sourced briefing remained empty. Intelligence showed no validated catalyst date.

`npm run test:db` on port 55432 passed: 10 files, 159 tests. BLS adapter tests: 11 passed. Series briefing tests: 2 passed. Sourced-update presentation tests: 4 passed. Web typecheck passed. GitHub Actions has not run. Do not reset this local database.

Branches retained: `m5/live-intelligence-coverage` is an ancestor of `m6/research-methods`. The M6 method code is integrated on development. The M5 calendar UI and both historical migrations are not. `research/employment-situation-2026-11` stays checked out at `C:/Users/gamer/aqil-sahm`. Its migration file matches development. The worktree status shows a modified test file whose blob equals HEAD `ff959c35a41d3ad57ac842c5bec9ed625bc55502`; it was not touched. `auth/google-foundation` is patch-equivalent and was not merged. `my-wealth/portfolio-slice` and `docs/consolidation-2026-10-18` were not merged. No remote branch was deleted. `apps/web/apps web.zip` is gitignored. It contains `.env.local`. The live `apps/web/.env.local` also exists. The zip was not opened for values and was not deleted.

## Today and Intelligence proof, 21 October 2026

The slice is not operational. No new source was added.

`npm run research:ingest` ran from the repo root against local Postgres `127.0.0.1:54322` as `research_worker`. It was a live attempt, not a fixture. The command printed `ingest_mode=live`, `bls_outcome=failed_fetch`, `received=0`, `new=0`, `unchanged=0`, `publications_outcome=failed_fetch`, and `Series fetch unusable; inspect provider payload`. It wrote no new `research.source_retrievals` row, so this run has no stored retrieval timestamp.

Queried as `research_worker` before `npm run test:db` reset the local database:

- `research.economic_observations`: 36, all on retrieval `1fedaa87-f3e8-411d-ae14-d488ee3a262e`. That retrieval is `collection_mode=fixture`, `source_id=bls_cps_unemployment_rate`, `retrieved_at=2025-06-01T12:00:00Z`, `recorded_at=2026-10-20T22:28:12Z`. New observations from this run: 0.
- `research.sourced_updates`: 0. No `source_id`, title, canonical URL, `published_at` or `retrieved_at` was stored.

A later non-persisting read of the same adapters, at `2026-10-20T22:59:01Z`, was not written to the database. The series call returned HTTP 200, BLS status `REQUEST_SUCCEEDED`, 44 observations and `partial=true`. The gate raised `feed freshness is interrupted; ingest blocked (no silent backfill)`. The Employment Situation feed returned `fetch_failed` / HTTP 403, with 0 drafts. Those figures are not stored observations.

Signed-in rendering was not verified. Opening `http://localhost:3000` stopped at `http://localhost:3000/login?error=signed_out&next=%2F` with the heading Sign in and the button Continue with Google. Google login was not completed. `/auth/saxo` was not opened. What signed-in Today and Intelligence show was not seen.

Checks on `d667781`: research pytest 40 passed, 0 failed; `test:wealth` 57 passed, 0 failed; `test:capital` 17 passed, 0 failed; `test:auth` 13 passed, 0 failed; `test:sourced-updates` 4 passed, 0 failed; `npx tsc --noEmit` passed; lint passed with 1 warning and 0 errors (`today-story-tangent-path.ts` unused `_searchParams`); `check:tokens` passed; `npm run build` passed. `npm run test:db` then reset the local database and passed 10 files, 159 tests. That reset was local only. Hosted Supabase was not migrated. Production scheduling was not turned on.

## Product acceptance, 21 October 2026

Signed-in routes were not opened. The agent browser was redirected to Google sign-in for `/`, and at 390px the primary links sit in the bottom bar. Privacy and terms remain public links. Saxo authorisation was not opened.

Unit and build checks on `f391d71`: `test:wealth` 57, `test:capital` 17, `test:benchmark` 14, `test:saxo` 42, `test:auth` 13, `test:learn` 6, `test:story` 4, research pytest 48 on the touched files, typecheck, lint, token check and production build all passed. `npm run test:db` did not run because Docker was not running. The last local database pass was 9 files and 134 tests.

Usable only after Google sign-in, and not yet confirmed in this browser: My Wealth from the saved Saxo snapshot, Deploy Capital policy, the investment journal, Learn, and the synthetic story. The benchmark and passive baseline are tested functions and are not on a page. The hosted token vault is unapplied. A process crash after Saxo rotates a refresh token still loses that token.

## 1. Repository

- Branch `work/aqil-autonomous-build` at `f391d71`. Sprint 3 is integrated: the manual journal is `3295686`, merged as `45eda97`, and the cashflow-matched passive baseline is `071fd28`. Do not push or deploy until the founder asks.
- Local branch housekeeping on 20 October 2026 removed integrated agent and milestone branches. `main` was not moved. Branches with unmerged commits were kept: `auth/google-foundation`, `docs/consolidation-2026-10-18`, `m5/live-intelligence-coverage`, `m6/research-methods`, `my-wealth/portfolio-slice` and `research/employment-situation-2026-11`. The Sahm worktree still has an uncommitted test edit.
- Phase 1 remains the parent checkpoint `85427dd`. The My Wealth cockpit rework is `2481fa8` on `work/my-wealth-cockpit`.
- Deploy Capital is `6d0328b` on `work/deploy-capital`, merged as `b7589e6`.
- The hosted token vault is `11853b0` on `work/saxo-token-vault`, merged as `d2179bb`.
- Production stays the existing Vercel deployment from GitHub `main`. It was not touched.
- Hosted Supabase `ojvswermsbbaltjohqph` still has five migrations. `20261018200000`, `20261018210000` and `20261020120000` are local only. Do not apply them without founder approval.
- One shared shell. Primary navigation is Today, My Wealth and Intelligence. Deploy capital is `/my-wealth/deploy`, not a fourth destination.
- My Wealth still reads the saved snapshot and does not call Saxo on load. The headline is the standard account value when it matches cash plus holdings. Open-position gain is Saxo's result since the positions were opened, not a period return.

## 2. Phase 1 completed

Accepted as the local foundation for current portfolio data, booked financial history and Saxo-reported historical performance.

- Saxo LIVE OAuth runs on localhost. Production Connect stays off.
- Holdings, balances and underlying lots are retrieved and kept.
- Source responses are encrypted local archive units. A later partial does not erase an earlier version.
- Historical acquisition can resume from the manifest. See the exception in section 4 before resuming aggregated amounts.
- My Wealth remains compatible with the current snapshot.
- Latest complete windows, checked by decrypting the local archive on 19 October 2026: 312 transactions, 628 nested bookings, 534 booking-report rows, 140 trade-report rows, 89 historical closed positions, 88 closed-position report rows, 501 account-value observations. Coverage begins 13 November 2024. The AllTime body includes Saxo's time-weighted block.

## 3. Where the local data is

All of this is gitignored under `apps/web/.local/`.

- `saxo-vault/` — encrypted OAuth session. This session did not refresh or replace it.
- `saxo-source/{owner}/live/manifest.bin` — encrypted acquisition manifest, 301 entries.
- `saxo-source/{owner}/live/units/` — 283 encrypted units.
- `saxo-portfolio/` — plaintext presentation snapshot for My Wealth. It has no OAuth token.
- `saxo-discovery/` — leftover plaintext discovery responses from the earlier catalogue.

Archive filenames use the owner id and, for an account balance, a 16-character hash. They do not contain account keys or tokens.

## 4. Incomplete, and why

Aggregated amounts: 16 of 24 monthly windows are latest-complete past the 50-row page. Those are November 2024 through July 2025, September 2025, and January through June 2026.

Eight windows still have the 50-row body as the latest complete marker:

- August 2025 stopped near 1,000 rows because the next page repeated rows already stored.
- October 2025 stopped near 1,000 rows on HTTP 429 `RateLimitExceeded`.
- July 2026 has a newer partial of 400 rows.
- November 2025, December 2025, August 2026, September 2026 and October 2026 have later partial versions with no additional rows. The earlier 50-row archives remain.

`historyAlreadyComplete` is true whenever a latest complete entry exists. A resume that trusts only that check will skip these eight. Keep every partial unit. Do not delete a 50-row version until a short final page has replaced it.

The QBTS NYSE/NASDAQ activity on 27 July 2026 is not fully reconciled between the historical position and the trade report. Do not include that disputed position in an independently calculated realised profit.

Money-weighted return was absent from the retrieved v4 performance response. Corporate-action events and chart history returned HTTP 403. Continuous daily instrument-level attribution is not validated. Two booking-report months contain exactly 50 rows, the old page size, so those two months should be rechecked before a hosted copy treats every booking-report window as fully paged. The accepted booking-report total remains 534 latest-complete rows.

## 5. What this session added

- My Wealth cockpit: standard account value and open-position or time-weighted result sit with cash, investment count, largest holding and connection. The Saxo account-value chart is full width only when at least two points exist.
- Deploy Capital can save an explicit investment policy for the signed-in user at `apps/web/.local/investment-policy/{userId}.json`. Targets must total 10,000 basis points. A blank budget stays unconfigured. A holding enters the class total only after the founder assigns its class. Reported cash remains investable cash. The example block stays labelled as made up. No order is sent. The hosted wealth tables are still not written.
- Hosted vault: `saxo_token_vault` and append-only `saxo_source_units` in unapplied migration `20261020120000_saxo_hosted_vault.sql`. Ciphertext is granted to `service_role` only. `rotateHostedTokens` claims a generation before calling Saxo; the loser does not refresh or persist. The local file vault is still the running store. Nothing in the OAuth routes was switched over, and no archive was copied.
- Review fixes: a thrown refresh or commit releases the vault claim. A one-unit top-up that integer gaps cannot assign stays in the unallocated amount. A foreign-currency buy is sized from the converted total, so per-unit rounding cannot spend more than the budget.
- `/my-wealth/journal` accepts manual entries and a CSV preview. Values appear only with a supplied price. Money-weighted return appears only when the cashflows solve. Time-weighted return stays unavailable without interim valuations. The benchmark comparison stays unavailable unless a series, foreign exchange and costs are supplied.
- Learn shows a labelled compounding illustration. The research page shows one synthetic story, with citations and a correction, when no founder insight is loaded. Research helpers fail closed on a stale feed, reject an incomplete method card, and collapse ten copies of one announcement into one cluster.

## 6. Tests this session

| Check | Result |
|---|---|
| `npm run test:capital` | 17 pass, 0 fail |
| `npm run test:wealth` | 33 pass, 0 fail, including 13 journal tests |
| `npm run test:learn` | 6 pass, 0 fail |
| `npm run test:story` | 4 pass, 0 fail |
| `npm run test:saxo` | 42 pass, 0 fail, including the hosted vault rotation tests |
| `npm run test:auth` | 13 pass, 0 fail |
| Research pytest | 24 pass, 0 fail, including schema contracts, feed freshness, method cards and event clusters |
| `npm run test:db` | pass. 9 files, 134 tests, including the journal and cross-user isolation files. Local disposable database only. Hosted Supabase was not changed |
| `npm run typecheck` | pass |
| `npm run lint` | pass |
| `npm run check:tokens` | pass, re-run 21 October 2026 |
| `npm run test:benchmark` | 14 pass, 0 fail, re-run 21 October 2026 |
| `npm run test:wealth` | 57 pass, 0 fail, re-run 21 October 2026 |
| `npm run build` | pass. `/my-wealth` and `/my-wealth/deploy` are in the build |
| Browser | Signed-out agent browser. `/my-wealth` and `/my-wealth/deploy` redirect to Google sign-in. At 390px the primary links sit in the bottom bar. Signed-in holdings were not opened. Saxo authorisation was not opened |
| `supabase test db` | Passed locally as `npm run test:db`: 89 tests, 0 failures. Not applied to the hosted project |

Node printed `MODULE_TYPELESS_PACKAGE_JSON` while loading the tests. That is an existing runtime notice. Do not add `"type": "module"` to silence it.

Not re-run on 21 October 2026: `test:research`, `test:db`, `build`, Playwright, and the signed-in browser. `test:auth` was re-run and passed.

## 7. Security and engineering

- No Saxo call, token refresh, hosted migration, push or production deployment was made.
- If the process dies after Saxo has rotated the refresh token and before the new ciphertext is stored, the claim stays `refreshing` and the new token is gone. The stored token is the previous one, which Saxo will reject. Recovery is a new localhost sign-in after the stuck row is set back to idle. The lost token cannot be reconstructed. A thrown error in a live process does release the claim. That path is tested. The crash path is not.
- The live Saxo application credential can still trade at Saxo. Aqil does not send trading requests.
- Plaintext discovery JSON remains on disk and is gitignored.
- Google sign-in behaviour was not changed. The agent browser had no session.

## 8. Still requires the founder

- Apply `20261018200000`, `20261018210000` and `20261020120000` only after a local `supabase test db` pass on those files.
- Decide when localhost OAuth should write the hosted vault instead of the file vault.
- Create a trading-disabled Saxo application before any hosted token is stored.
- Do not enable production Saxo LIVE.
- Do not copy `apps/web/.local` archives into the hosted source-unit table until that copy is explicitly approved.
- Supply allocation targets, an approved instrument list and a budget before Deploy Capital can describe the real account. The example must not be treated as that account.

## 9. First task when development resumes

The Today and Intelligence slice is not operational. The 21 October live ingest stored no publication and no new series observations. Do not schedule production ingest or apply the hosted migration until a live retrieval succeeds and its timestamp is recorded. AQ-009, AQ-010, AQ-018, AQ-019 and AQ-032 onward stay blocked. Do not open Saxo authorisation unless that is the task. Do not `db push`.

## Commands

From `apps/web`: `npm run typecheck`, `npm run lint`, `npm run test:saxo`, `npm run test:wealth`, `npm run test:benchmark`, `npm run test:capital`, `npm run test:learn`, `npm run test:story`, `npm run test:auth`, `npm run build`.  
From the repo root: `npm run check:tokens`, `npm run test:research`.  
Database tests need a running local Supabase. Do not apply hosted migrations.
