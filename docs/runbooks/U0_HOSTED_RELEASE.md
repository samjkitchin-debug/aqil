# Hosted U0 release checklist

**Status:** no-go  
**Date:** 25 October 2026  
**Owner:** founder  

This is the sequence a founder would execute later. It is not approval to run it now. Local checks in this note are not GitHub Actions results.

Exposures has no cited share class. Deploy Capital is not an order screen. The internal VWRA anchor stays unverified. Vanguard and iShares holdings rows stay `automated_access=prohibited` and `redistribution=prohibited`. Do not set those cells to permitted. A saved brokerage line has no ISIN. Do not match it by ticker.

## Sequence

1. Back up the hosted project `ojvswermsbbaltjohqph`.
2. Apply the ten local migrations below, in filename order, after the five hosted files through `20261017180000_forward_intelligence.sql`. A code rollback will not undo them.
3. Check grants. Leave research row-level security off until policies exist. Do not weaken wealth row-level security.
4. Set server-only `RESEARCH_DATABASE_URL` and the ETF database URL on Vercel. Production must fail closed when either is missing or is a loopback address.
5. Populate research with one manual `npm run research:refresh` after the URL exists. No schedule.
6. Smoke the signed-in app at `https://aqil-tau.vercel.app`: Today, Intelligence, Evidence, Exposures, and My Wealth. Empty ETF and policy states stay empty.
7. One push to `main` so the existing GitHub to Vercel integration deploys. No Vercel CLI deploy.

U0 remains no-go until the founder approves the backup, the apply, the server-only URLs, the one manual refresh, and the one push.

## Ten migrations

1. `20261018200000_verified_prospective_assessment.sql`
2. `20261018210000_my_wealth.sql`
3. `20261020120000_saxo_hosted_vault.sql`
4. `20261020143000_wealth_journal_events.sql`
5. `20261021110000_research_sourced_updates.sql`
6. `20261022120000_catalyst_verification_update.sql`
7. `20261022140000_research_refresh_runs.sql`
8. `20261023120000_prospective_assessments.sql`
9. `20261024120000_etf_instruments.sql`
10. `20261024150000_research_macro_events_themes.sql`

## Local rehearsal

On 25 October 2026 a new disposable database, `aqil_u0_ten`, was created from `template1` on the local cluster. The five hosted files were applied first. Representative rows were inserted: one `user_settings` row (`en-GB`, `Asia/Singapore`), one fixture retrieval with a null response fingerprint, observation `rehearsal-obs-1` (`1.5`, monthly), run `rehearsal-run-1` with `publication_allowed` false and investment implication `no_action`, one observation link, catalyst `rehearsal-event-1` titled `Rehearsal release` with evidence class `synthetic_demonstration`, and a matching synthetic scenario and outcome.

The ten files were then applied, including `20261024150000_research_macro_events_themes.sql`. Those rows were still present. `public.wealth_allocation_targets`, `public.saxo_token_vault`, `research.sourced_updates`, `research.refresh_runs`, `research.prospective_assessments`, `instruments.share_classes`, and `research.macro_events` existed. `anon`, `authenticated`, and `service_role` had no usage on `research`, `forward`, or `instruments`. `research_writer` did. Direct selects on observations, catalyst events, and share classes were denied for those three roles. `anon` was denied for wealth accounts and the token vault. The vault has row-level security and no policy. An authenticated session saw its own settings row and zero rows for another identity. `research_writer` could update `last_verified_at`; that update was rolled back. An update of `title` was denied.

Git migration files were not edited. In the replay stream only, `create role` for `research_writer` and `research_worker_app` was made duplicate-safe, and `grant connect on database postgres` was redirected to `aqil_u0_ten`. The database was then dropped. It is not in `pg_database`. Preserved databases `postgres` and `aqil_etf` were not written. After the drop, `postgres` still had 23 operational series, 34,859 operational periods, 789 OECD rows, and 87 fixture rows. `instruments` was still absent from `postgres`. `aqil_etf.instruments.share_classes` was still 0.

The earlier rehearsal on `aqil_u0_upgrade` covered nine files and did not include the events migration. That database was already gone. It is not this proof.

## Cited document

`cite-etf` is the operator command. It calls the existing persist function. It still refuses a source unless acquire, retain, extract, and display are already permitted. `founder_supplied` does not permit those uses. `postgres` and `aqil_etf` are refused. Citation tests stay on the disposable database. Do not write a real cited document into `aqil_etf` or `postgres`.

The founder input, when one exists, is a document they may retain and display, its URL and date, a new source id whose four uses are permitted, and only the fields that document states: legal name, ISIN, domicile, distribution policy, hedge status, base currency, inception, listings, ongoing charge and date, benchmark, and exposure weights. Trading currency is a listing fact, not an exposure. Holdings files stay out of this path.

## Policy dependency

Do not switch Deploy Capital’s save path in this release. `wealth_allocation_targets` is the intended store. The gitignored JSON file is not. Both are empty. Saxo holdings are not classified into that table. The later read switch needs targets totalling 10,000 basis points, a classification for each holding, foreign exchange, and an explicit budget. The current read-only missing state stays in place.
