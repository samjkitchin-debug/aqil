# Cursor session handover

**Status:** living continuity note  
**Last updated:** 18 October 2026  
**Release commit:** pending the close-out commit on `main`

## Current state

- Branch before the release push: `alignment/2026-10-18`, based on `origin/main` `6f47bdb`.
- One shared shell. Primary navigation is Today, My Wealth and Intelligence. Content width is 78rem.
- Local Saxo is read-only. The stored live snapshot reconciles: cash is present, the standard total matches cash plus holding market values, the extended-hours total is separate, four net holdings, no duplicate symbols, closed-market zeros are not prices. Holdings stay unclassified.
- Production does not offer Connect Saxo. Tokens and snapshots are gitignored local files, not hosted storage.
- The local live refresh token returned HTTP 401. `GET /hist/v4/performance/timeseries` is allow-listed and documented. This account's series was not retrieved. The current portfolio does not depend on it.
- Hosted Supabase `ojvswermsbbaltjohqph` still has five migrations. `20261018200000` and `20261018210000` are local only. Do not apply them without founder approval, and do not apply older M5 timestamps after them.

## Commands

- Web: `npm run typecheck`, `npm run lint`, `npm run test:saxo`, `npm run test:wealth`, `npm run test:auth`, `npm run build` in `apps/web`.
- Tokens: `npm run check:tokens`.
- Browser: `npx playwright test e2e/responsive.spec.ts e2e/auth.spec.ts` in `apps/web`.
- Research: `npm run test:research`.
- Database: `npm run test:db` cannot bind the default Windows-excluded ports. This session moved the local stack to 54520–54529, excluded analytics, ran the tests, stopped the stack and restored `supabase/config.toml`.

## Tests this close-out

| Check | Result |
|---|---|
| `npm run typecheck`, `npm run lint` | pass. Lint warned only on a gitignored probe script |
| `npm run test:saxo` | 17 pass |
| `npm run test:wealth` | 10 pass |
| `npm run test:auth` | 13 pass |
| `npm run check:tokens` | pass |
| `npm run build` | pass |
| Playwright auth and responsive | 105 pass, including 320 and 390 |
| `npm run test:research` | 85 pass, 7 skipped. Ruff clean. Freeze file not edited |
| Local `supabase test db` | 81 pass, including `my_wealth_rls` and `verified_prospective_assessment` |
| Signed-in My Wealth with the live snapshot | not opened. The agent browser had no Google session |
| Saxo history request | not completed. Refresh token expired |

## Blockers

- Reconnect Saxo on localhost before another refresh. Do not treat the stored snapshot as newly retrieved.
- Hosted token vault and wealth tables are not applied.
- The live Saxo application credential can still trade at Saxo. Aqil does not send trading requests. Replace it with a trading-disabled application before hosted token storage.

## Next action

Reconnect the local Saxo account, then design hosted encrypted token storage. Do not start Deploy Capital or another research milestone until that persistence decision is made.
