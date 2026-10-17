# Database

PostgreSQL schema for Aqil is managed via **Git-tracked** SQL in [`supabase/migrations/`](../supabase/migrations/).

- **Full local gate:** `npm run test:db` (start stack, reset migrations, pgTAP with localhost guard).
- **Replay only:** `npm run db:reset` (start stack, reset migrations).
- **pgTAP only:** `npm run db:test` (localhost guard; stack must already be up from `test:db` or `db:reset`).
- **Full G0 local gate:** `powershell -File scripts/verify-g0-local.ps1` (needs ~15+ GiB free on `C:` for Docker images).
- **Types:** `npm run db:types` generates `apps/web/src/types/database.generated.ts`.

Do not apply migrations to production without review. Development project ref: `ojvswermsbbaltjohqph`.

Hosted schema changes go through `supabase db push` of `supabase/migrations/` only. Do not run `supabase test db --linked`, and do not `db pull` or `db diff` a local database after pgTAP: `supabase/tests/database/00000_supabase_test_helpers.sql` creates `SECURITY DEFINER` helpers outside the test transaction.

Row-level security tests: `supabase/tests/database/` and `tests/database/rls/`.
