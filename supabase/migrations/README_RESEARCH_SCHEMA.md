# Research schema (`research.*`)

Private persistence for the M1 intelligence engine. **Not** listed in `supabase/config.toml` `[api].schemas` (PostgREST does not expose these tables).

## Security model (grants-only, not RLS)

| Approach | M2 plan discussion | **Implemented (Phase 1)** |
|----------|-------------------|---------------------------|
| Row visibility | Optional RLS on research tables | **RLS disabled** — isolation via `REVOKE ALL` on `research` from `anon`, `authenticated`, and `service_role` |
| Worker access | `research_writer` least-privilege role | `INSERT` + `SELECT` on research tables; `EXECUTE` on `try_insert_observation` only |
| API clients | Must not read research history | No schema `USAGE` for `anon` / `authenticated` |

**Independent review:** pgTAP asserts role privileges on all six tables. This is intentionally **not** the same as `public.user_settings` (RLS + narrow grants).

**BYPASSRLS:** `BYPASSRLS` (e.g. Supabase `service_role`) bypasses **row-level security policies only**. It does **not** bypass ordinary table `GRANT`/`REVOKE` privileges. This migration does **not** grant `service_role` any rights on `research.*`, so the service role cannot read or write research tables unless a future migration explicitly grants it.

**Research execution:** No service-role key or credential is required by this migration. The worker should connect as a future `LOGIN` principal granted `research_writer`, not as `service_role`.

## Tables

1. `source_retrievals` — immutable fetch metadata (structured columns; no credential JSON keys)
2. `economic_observations` — append-only observations
3. `observation_conflicts` — rejected duplicate vintages
4. `research_runs` — immutable analytical runs
5. `research_run_datasets` — per-dataset rights/snapshot per run
6. `research_run_observations` — evidence links

## Transaction boundaries

- **Observations:** call `research.try_insert_observation(...)`. On `conflict`, the existing row is unchanged and a row is inserted into `observation_conflicts` in the **same** transaction. `COMMIT` persists both; `ROLLBACK` drops uncommitted inserts and conflict rows together.
- **Large batches:** to keep conflict evidence when aborting a batch, commit conflict outcomes (or each `try_insert_observation` call) before rolling back unrelated work.
- **Research runs:** insert `research_runs`, then `research_run_datasets`, then `research_run_observations` in one transaction.

## Functions

- All functions use fixed `search_path = research, pg_temp` and run as **SECURITY INVOKER** (default).
- Only `research.try_insert_observation` is executable by `research_writer`; helpers are invoked via constraints/triggers as the table owner.

## Worker identity (hosted)

- `research_writer` — `NOLOGIN` role with append-only table privileges.
- `research_worker_app` — `NOLOGIN` placeholder; a **deploy-specific** migration may add a `LOGIN` role, `GRANT research_writer`, and a password from Supabase secrets (never Git).
- `CREATE ROLE` in migrations is supported on Supabase hosted Postgres; roles are not recreated by `db reset` on remote — apply once via approved `supabase db push`.

## Test helpers

pgTAP helpers under `supabase/tests/database/` are **not** migrations and must never be applied to hosted databases (`supabase db push` uses `supabase/migrations/` only).
