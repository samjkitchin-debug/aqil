# Hosted operations

**Status:** schema applied. Live dashboard observations were loaded on 30 October 2026. Bry–Boschan and Stock–Watson stay unpublished.  
**Project:** Supabase `ojvswermsbbaltjohqph`, Vercel `aqil` (`prj_EcU4I2q7iDMeqHmcQybO3TG9WwQ5`), production `https://aqil-tau.vercel.app`  
**Application:** 0.2.0, tag `v0.2.0`

Exposures has no cited share class. Deploy Capital is not an order screen. Vanguard and iShares holdings rows stay `automated_access=prohibited` and `redistribution=prohibited`. Do not set `publication_allowed=true` for Bry–Boschan or Stock–Watson.

## Deploy

One fast-forward push of `main` deploys the existing GitHub integration. Do not run `vercel deploy` and do not create a second project. Root directory is `apps/web`. Production branch is `main`.

The deployment that was aliased before this release is the rollback target:

- URL `https://aqil-tau.vercel.app`
- Deployment `dpl_CUs9qafAXXyEC8cDLmJHu9rKmWot`
- SHA `c9ea596afbcdb1e81a995fd592cdf9d73a6c58ba`

Rollback the site with `vercel promote` of that deployment, or the Vercel rollback of that deployment. Do not invert database migrations to roll the site back.

## Verify

Signed-out landing, Google sign-in, callback, Today, My Wealth, Dashboard accordions, Methodologies with no login loop, one methodology detail, Insights unavailable state, sign-out and sign-in again. Desktop and about 390 pixels. Honest empty research data is a pass. A crash, an auth loop, or another person's wealth data is a fail.

## Environment

Values are not recorded here. Production target only.

| Name | State |
| --- | --- |
| `NEXT_PUBLIC_APP_URL` | Set. Public value `https://aqil-tau.vercel.app`. |
| `NEXT_PUBLIC_SUPABASE_URL` | Set. Public value `https://ojvswermsbbaltjohqph.supabase.co`. |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Set. Matches the project anon key. |
| `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` | Set. |
| `SUPABASE_URL` | Set. Same project URL. |
| `SUPABASE_ANON_KEY` | Set. |
| `SUPABASE_PUBLISHABLE_KEY` | Set. |
| `SUPABASE_JWT_SECRET` | Set by the integration. No application route reads it. |
| `POSTGRES_URL` | Set, sensitive. Host `db.ojvswermsbbaltjohqph.supabase.co`, user `postgres`, database `postgres`. Not used by application code. |
| `POSTGRES_PRISMA_URL` | Set, sensitive. Not used by application code. |
| `POSTGRES_URL_NON_POOLING` | Set, sensitive. Value was not returned by the API. |
| `POSTGRES_USER` | Set. `postgres`. |
| `POSTGRES_HOST` | Set. `db.ojvswermsbbaltjohqph.supabase.co`. |
| `POSTGRES_PASSWORD` | Set, sensitive. Not readable through the API. Not reused. |
| `POSTGRES_DATABASE` | Set. `postgres`. |
| `RESEARCH_DATABASE_URL` | Set, sensitive, production only. Role `research_reader` on the session pooler, port 5432, `uselibpqcompat=true&sslmode=require`. Not the `postgres` user. |
| `ETF_DATABASE_URL` | Unset. |
| `SUPABASE_SERVICE_ROLE_KEY` | Removed from the project on 25 October 2026. |
| `SUPABASE_SECRET_KEY` | Removed from the project on 25 October 2026. |
| `SAXO_LIVE_APP_KEY` | Removed. |
| `SAXO_LIVE_APP_SECRET` | Removed. |
| `SAXO_LIVE_REDIRECT_URI` | Removed. |
| `SAXO_SIM_APP_KEY` | Removed. |
| `SAXO_SIM_APP_SECRET` | Removed. |
| `SAXO_SIM_REDIRECT_URI` | Removed. |
| `SAXO_TOKEN_ENCRYPTION_KEY` | Removed. |
| `AQIL_ALLOW_RESEARCH_FIXTURE` | Unset. |
| `BLS_API_KEY` | Unset. |
| `CENSUS_API_KEY` | Unset. |
| `AQIL_SEC_USER_AGENT` | Unset. |
| `AQIL_AUTHORISED_USER_IDS` | Unset. Obsolete under ADR 020. |

Auth site URL is `https://aqil-tau.vercel.app`. The redirect allow-list includes `https://aqil-tau.vercel.app/**`, `https://aqil-tau.vercel.app/auth/callback`, and `http://localhost:3000/auth/callback`. Google is enabled. The Google provider redirect remains the Supabase callback.

## Migrate

Use one mechanism. This release used the Supabase management migration API. The API stamps a timestamp version. Those versions were then set to the git filename versions so a later CLI push sees the files as applied. Do not also `supabase db push` the same files.

Applied on 25 October 2026, in filename order, on top of the five-migration baseline. No `DROP TABLE` and no `TRUNCATE`.

After apply, `anon`, `authenticated`, and `service_role` have no usage on `research`, `forward`, or `instruments`. `research_writer` does. The Data API schema list is `public, graphql_public`. Public wealth and journal tables keep authenticated grants and owner row-level security. The token vault has row-level security and no policy, so an authenticated client cannot select it.

## Backup

Organisation plan: free. The backup list was empty. Point-in-time recovery was off. Free projects are told to export with `supabase db dump`. That dump needs the database password. Vercel stores `POSTGRES_PASSWORD` as a sensitive variable and did not return it. No other readable copy was found.

The pre-apply record outside Git is `C:\Users\gamer\aqil-release-backups\2026-10-25\`. It has the five already-applied migration files and the row counts. It is not a `pg_dump`. A later folder, `2026-10-30`, holds `PRE_IMPORT_COUNTS.txt`, import scripts, and password files for `research_reader` and the worker role, plus a pooler URL whose user is `research_reader`. Auth rows were not exported. Those files are not a logical dump and they are not the database owner.

On 1 November 2026 no `SUPABASE_DB_PASSWORD`, `POSTGRES_PASSWORD`, `SUPABASE_ACCESS_TOKEN`, or `RESEARCH_DATABASE_URL` was set in the user, machine, or process environment. `apps/web/.env.local` on the main worktree names the anon key and Saxo keys, not a database password. The Supabase CLI is not installed. The reader and worker files in `2026-10-30` were not used. `pg_dump` was not run. Gate 10 stays blocked.

The exact founder action is one of these, and then a restore check:

1. Supply the database-owner password for role `postgres` on project `ojvswermsbbaltjohqph`, out of band, not in Git and not in chat. The dump command is `supabase db dump --db-url` to a file under `C:\Users\gamer\aqil-release-backups`, using that direct owner URL. Do not use the `research_reader` or `research_worker` pooler URL.
2. Or approve a paid backup add-on and download that backup.

Restore the dump into a disposable database and check schemas, roles, and the research row counts. A Vercel rollback is not that backup. No hosted migration or research write happens before that restore.

Restore is a new project or a reviewed restore. Do not use `supabase db reset --linked`.

## What SQL cannot undo

The ten applied files create tables, constraints, policies, and grants. Replacing the two forward check constraints widened the allowed evidence classes. Dropping those new tables would delete any rows written after the apply. There were none at apply time. A site rollback does not remove them.

## Data

Do not copy local `postgres`, local research runs, fixtures, or Saxo tokens into the host. A worker password file is stored in `C:\Users\gamer\aqil-release-backups\2026-10-30`. It was not used on 1 November 2026. That role is not the database owner, so it is not a dump credential. One manual `npm run research:refresh` waits on a real research-worker URL. OECD and other non-operational series stay out of that refresh. Leave `publication_allowed=false`. Hosted BEA series `bea.nipa.T20600.W875RX` and `bea.nipa.U002BU.KPMT` were still absent, as was `fed.h15.RIFLGFCM03_N.M`. Those series are not copied from local `postgres`.

## Local rehearsal

On 25 October 2026 a disposable database, `aqil_u0_ten`, was created from `template1` on the local cluster. The five hosted files were applied first, then the ten files. Representative rows survived. `anon`, `authenticated`, and `service_role` had no usage on `research`, `forward`, or `instruments`. The database was then dropped. Preserved local databases `postgres` and `aqil_etf` were not written. That rehearsal is not this hosted apply.

## Cited document

`cite-etf` still refuses a source unless acquire, retain, extract, and display are already permitted. Do not write a real cited document into the hosted project in this release.

## Policy dependency

Do not switch Deploy Capital’s save path in this release. `wealth_allocation_targets` is the intended store and is empty. Saxo holdings are not classified into that table.
