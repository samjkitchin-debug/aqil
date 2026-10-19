# Cursor session handover

**Status:** living continuity note  
**Last updated:** 20 October 2026, local Phase 2 slice  
**Parent:** `2481fa862d2ff38fe1b79d5cabc1835cbd22c891` on `work/aqil-autonomous-build`  
**Checkpoint:** local only. Not pushed. Production, hosted migrations and Saxo LIVE stay unchanged.

## 1. Repository

- Branch `work/aqil-autonomous-build`. Do not push, merge to GitHub `main`, or deploy until the founder asks.
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
- Deploy Capital V1: `deployCapital` in `apps/web/src/lib/capital/deploy.ts`. It reuses `monetaryGaps` and `allocateExternalContribution`. Missing targets, a zero or missing budget, an empty approved list, or a missing foreign-exchange rate stay unconfigured or unavailable. Whole units leave a remainder. No order is created. `/my-wealth/deploy` shows a labelled example and a not-configured block. Those figures are not the founder's account and the page does not read the Saxo snapshot.
- Hosted vault: `saxo_token_vault` and append-only `saxo_source_units` in unapplied migration `20261020120000_saxo_hosted_vault.sql`. Ciphertext is granted to `service_role` only. `rotateHostedTokens` claims a generation before calling Saxo; the loser does not refresh or persist. The local file vault is still the running store. Nothing in the OAuth routes was switched over, and no archive was copied.
- Review fixes: a thrown refresh or commit releases the vault claim. A one-unit top-up that integer gaps cannot assign stays in the unallocated amount. A foreign-currency buy is sized from the converted total, so per-unit rounding cannot spend more than the budget.
- Wealth valuation and event inserts in that same unapplied migration now require the instrument to belong to the same owner. This was a cross-owner reference hole in `20261018210000`. It is not applied on the host.

## 6. Tests this session

| Check | Result |
|---|---|
| `npm run test:capital` | 11 pass, 0 fail |
| `npm run test:wealth` | 20 pass, 0 fail |
| `npm run test:saxo` | 42 pass, 0 fail |
| `npm run typecheck` | pass |
| `npm run lint` | pass after `prefer-const` in `deploy.ts` |
| `npm run check:tokens` | pass |
| `npm run build` | pass. Route `/my-wealth/deploy` is in the build |
| Browser | Agent browser opened `/my-wealth` and `/my-wealth/deploy` and was redirected to Google sign-in. The example was not rendered. Saxo authorisation was not opened |
| `supabase test db` | not run. Docker was not running. The new pgTAP file is unexecuted |

Node printed `MODULE_TYPELESS_PACKAGE_JSON` while loading the tests. That is an existing runtime notice. Do not add `"type": "module"` to silence it.

Not re-run: `test:auth`, Playwright, research tests.

## 7. Security and engineering

- No Saxo call, token refresh, hosted migration, push or production deployment was made.
- The in-process refresh map still does not protect two server processes. The new hosted claim does, and it is not wired to the live session.
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

Read this note. Do not refresh Saxo or resume the eight aggregated months unless that is the task. The next useful product step is to sign in locally and judge the cockpit and the deploy-capital example. The next security step is a local database test of the unapplied migrations, still without `db push`.

## Commands

From `apps/web`: `npm run typecheck`, `npm run lint`, `npm run test:saxo`, `npm run test:wealth`, `npm run test:capital`, `npm run test:auth`, `npm run build`.  
From the repo root: `npm run check:tokens`, `npm run test:research`.  
Database tests need a running local Supabase. Do not apply hosted migrations.
