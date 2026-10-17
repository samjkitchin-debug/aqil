# Row-level security tests

Executable pgTAP tests run via the Supabase CLI:

```bash
npm run test:db   # starts local Supabase, resets migrations, runs pgTAP
```

Implementation: [`supabase/tests/database/`](../../../supabase/tests/database/).  
`00000_supabase_test_helpers.sql` installs the `tests` schema helpers (usebasejump/supabase-test-helpers) before RLS cases run.

Tests use synthetic users (`user_a@aqil.test`, `user_b@aqil.test`) and `tests.authenticate_as` / `tests.clear_authentication` — not the `postgres` superuser role for RLS assertions. `current_user` is asserted as `authenticated` or `anon` on those paths.

`scripts/run-db-tests.ps1` refuses to run pgTAP unless the local database URL is `127.0.0.1:54322`.
