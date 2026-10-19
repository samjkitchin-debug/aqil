# Cursor session handover

**Status:** living continuity note  
**Last updated:** 19 October 2026, Phase 1 close-out  
**Parent:** `c9ea596afbcdb1e81a995fd592cdf9d73a6c58ba` on `alignment/2026-10-18`  
**Checkpoint:** this Phase 1 close-out is committed locally on `work/aqil-autonomous-build` and has not been pushed. Production, hosted migrations and Saxo LIVE stay unchanged.

## 1. Repository

- Branch `alignment/2026-10-18`. HEAD `c9ea596` is “Align generated database types with the local wealth schema.”
- Phase 1 Saxo modules, the My Wealth panel and these documentation edits are the local checkpoint on `work/aqil-autonomous-build`. Do not push, merge or deploy until the founder asks.
- Production stays the existing Vercel deployment from GitHub `main`. It was not touched.
- Hosted Supabase `ojvswermsbbaltjohqph` still has five migrations. `20261018200000` and `20261018210000` are local only. Do not apply them without founder approval.
- One shared shell. Primary navigation is Today, My Wealth and Intelligence. My Wealth is the instrument panel already in the working tree: the headline is the standard account value when it matches cash plus holdings. Open-position gain is Saxo’s result since the positions were opened, not a period return. The page reads the saved snapshot and does not call Saxo on load.

## 2. Phase 1 completed

Accepted as the local foundation for current portfolio data, booked financial history and Saxo-reported historical performance.

- Saxo LIVE OAuth runs on localhost. Production Connect stays off.
- Holdings, balances and underlying lots are retrieved and kept.
- Source responses are encrypted local archive units. A later partial does not erase an earlier version.
- Historical acquisition can resume from the manifest. See the exception in section 4 before resuming aggregated amounts.
- My Wealth remains compatible with the current snapshot.
- Latest complete windows, checked by decrypting the local archive on 19 October 2026: 312 transactions, 628 nested bookings, 534 booking-report rows, 140 trade-report rows, 89 historical closed positions, 88 closed-position report rows, 501 account-value observations. Coverage begins 13 November 2024. The AllTime body includes Saxo’s time-weighted block.

## 3. Where the local data is

All of this is gitignored under `apps/web/.local/`.

- `saxo-vault/` — encrypted OAuth session. This close-out did not refresh or replace it.
- `saxo-source/{owner}/live/manifest.bin` — encrypted acquisition manifest, 301 entries.
- `saxo-source/{owner}/live/units/` — 283 encrypted units. All 283 decrypted with the local key.
- `saxo-portfolio/` — plaintext presentation snapshot for My Wealth. It has no OAuth token.
- `saxo-discovery/` — leftover plaintext discovery responses from the earlier catalogue. The plaintext session file was removed. The vault remains the credential.

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

## 5. Tests this close-out

| Check | Result |
|---|---|
| `npm run test:saxo` | 36 pass, 0 fail |
| `npm run test:wealth` | 16 pass, 0 fail |
| `npm run typecheck` | pass |
| `npm run lint` | pass, no findings |

Node printed `MODULE_TYPELESS_PACKAGE_JSON` while loading the tests. That is an existing runtime notice. Do not add `"type": "module"` to silence it. The two earlier lint warnings belonged to a gitignored probe script, which was removed.

Not re-run: `test:auth`, `check:tokens`, `build`, Playwright, research tests, `supabase test db`.

## 6. Security and engineering

- No Saxo call, token refresh, migration, push or deployment was made.
- Refresh coalescing does not protect two server processes.
- The live Saxo application credential can still trade at Saxo. Aqil does not send trading requests.
- Plaintext discovery JSON remains on disk and is gitignored. It is not the source archive.
- Google sign-in and the My Wealth snapshot path were not changed.

## 7. Approved boundary of the next phase

Phase 2 is secure hosted Saxo connectivity and financial-data persistence. Do not start it inside a close-out. Do not enable production Saxo LIVE while investigating it.

Phase 2 is:

- Encrypted hosted OAuth token storage.
- Refresh-token rotation that is safe across server processes.
- Authenticated ownership enforcement and Supabase RLS.
- Secure account, financial-source and historical persistence.
- A review of the pending wealth migrations before any of them is applied.
- A controlled copy of verified local source data into hosted storage.
- Explicit verification before production Saxo LIVE is enabled.

Keep acquiring and preserving the full read-only financial record. Keep the presentation selective. The eight aggregated months are a resumable local item. They do not block Phase 2, and they are not complete.

## 8. First task when development resumes

Read this note and the Saxo section of `docs/04_ARCHITECTURE_AND_DATA.md`. Before any broker call, read the encrypted session expiry locally. If the refresh has lapsed, ask for one localhost sign-in at `http://localhost:3000/auth/saxo?environment=live` and do not start a second refresh beside it. Then start Phase 2 at hosted token storage. When the aggregated months are resumed, select the eight windows whose newest unit is partial, including those whose latest complete body is still 50 rows.

## Commands

From `apps/web`: `npm run typecheck`, `npm run lint`, `npm run test:saxo`, `npm run test:wealth`, `npm run test:auth`, `npm run build`.  
From the repo root: `npm run check:tokens`, `npm run test:research`.  
Database tests need the local Supabase ports recorded in the previous close-out. Do not apply hosted migrations.
