# Database

PostgreSQL schema for Aqil is managed via SQL migrations in `migrations/`.

- Do not connect this repository to production data during initial setup.
- Apply migrations to a Supabase project only after reviewing `/docs` specifications.
- Row-level security policies will be added with tables; see `tests/` and `database/tests/`.
