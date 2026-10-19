# Cursor session handover

**Status:** living continuity note  
**Last updated:** 20 October 2026, local Phase 2 slice  
**Parent:** `2481fa862d2ff38fe1b79d5cabc1835cbd22c891` on `work/aqil-autonomous-build`  
**Checkpoint:** local only. Not pushed. Production, hosted migrations and Saxo LIVE stay unchanged.

## 1. Repository

- Branch `work/aqil-autonomous-build` at `3ca01da` plus the policy type fix. Do not push, merge to GitHub `main`, or deploy until the founder asks.
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
- Wealth valuation and event inserts in that same unapplied migration now require the instrument to belong to the same owner. This was a cross-owner reference hole in `20261018210000`. It is not applied on the host.

## 6. Tests this session

| Check | Result |
|---|---|
| `npm run test:capital` | 17 pass, 0 fail |
| `npm run test:wealth` | 20 pass, 0 fail |
| `npm run test:saxo` | 42 pass, 0 fail, including the hosted vault rotation tests |
| `npm run test:auth` | 13 pass, 0 fail |
| `npm run test:db` | pass. 7 files, 89 tests, including `saxo_token_vault_rls.test.sql`. Local disposable database only. Hosted Supabase was not changed |
| `npm run typecheck` | pass |
| `npm run lint` | pass |
| `npm run check:tokens` | pass |
| `npm run build` | pass. `/my-wealth` and `/my-wealth/deploy` are in the build |
| Browser | Signed-out agent browser. `/my-wealth` and `/my-wealth/deploy` redirect to Google sign-in. At 390px the primary links sit in the bottom bar. Signed-in holdings were not opened. Saxo authorisation was not opened |
| `supabase test db` | Passed locally as `npm run test:db`: 89 tests, 0 failures. Not applied to the hosted project |

Node printed `MODULE_TYPELESS_PACKAGE_JSON` while loading the tests. That is an existing runtime notice. Do not add `"type": "module"` to silence it.

Not re-run: `test:auth`, Playwright, research tests.

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

Read this note. Sign in once at `http://localhost:3000/my-wealth` with Google, then open Deploy capital, before treating the signed-in screens as checked. Do not refresh Saxo unless that is the task. Start Docker and run `supabase test db` before any hosted migration. Do not `db push`.

## Commands

From `apps/web`: `npm run typecheck`, `npm run lint`, `npm run test:saxo`, `npm run test:wealth`, `npm run test:capital`, `npm run test:auth`, `npm run build`.  
From the repo root: `npm run check:tokens`, `npm run test:research`.  
Database tests need a running local Supabase. Do not apply hosted migrations.
