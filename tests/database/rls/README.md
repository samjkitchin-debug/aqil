# Row-level security tests

Future RLS tests will run against a disposable Supabase branch or local stack.

Planned layout:

- `cases/` — SQL or scripted scenarios per table policy
- `fixtures/` — anonymised seed data (no real financial information)
- `run-rls-tests.ps1` — orchestration script (to be added with Supabase CLI)

Do not enable RLS on production until policies and these tests are in place.
