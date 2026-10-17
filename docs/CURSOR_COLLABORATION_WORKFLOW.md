# Cursor collaboration workflow

Lightweight process for human + agent work on Aqil. Detailed rules remain in `docs/06_ENGINEERING_DISCIPLINE.md`.

## Before starting

1. Read `docs/00_READ_ME_FIRST.md` and docs listed for the task domain.
2. Confirm documentation tier (`docs/DOCUMENTATION_AUTHORITY.md`) — especially **not** treating `docs/sausage-transfer/` as build instructions.
3. State risk class (R0–R3), files in scope, and explicit **out of scope**.
4. For database work: migrations only in `supabase/migrations/`; RLS tests must pass before remote apply.

## During implementation

- Small diffs; match existing patterns.
- Run gates from `docs/06_ENGINEERING_DISCIPLINE.md` §7 applicable to the change.
- No secrets in client code; no service role in browser bundles.

## Before claiming done

- List commands run and results (build, typecheck, lint, tests).
- Note documentation files updated.
- For R3: migration replay + `supabase test db` when schema touched.

## Prompt template

Use the template in `docs/06_ENGINEERING_DISCIPLINE.md` §10.

## Project rules

Repository enforcement: `.cursor/rules/aqil-engineering.mdc` (must stay aligned with this workflow).
