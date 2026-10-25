# Cursor collaboration workflow

Lightweight process for human + agent work on Aqil. **Non-negotiable agent rules:** `docs/AGENT_OPERATING_RULES.md`. Detailed engineering contract: `docs/06_ENGINEERING_DISCIPLINE.md`.

## Before starting

1. Read `docs/AGENT_OPERATING_RULES.md`, `docs/00_READ_ME_FIRST.md`, and docs listed for the task domain.
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
- Update **`docs/07_BUILD_BACKLOG.csv`** (status, `verification_evidence`, `blockers`, `next_action`) for any item materially advanced or blocked.
- Append a filled **`docs/CURSOR_SESSION_HANDOVER.md`** template to the PR or session notes when the change is non-trivial.

## Progress and status vocabulary

Authoritative register: **`docs/07_BUILD_BACKLOG.csv`** (see `docs/07_ROADMAP_AND_GATES.md` § Progress register). Status values:

| Status | Meaning |
|--------|---------|
| Not started | No implementation work |
| In progress | Active development |
| Blocked | Waiting on dependency, access or decision |
| Partial | A slice works in code or a local read, and the end-to-end path does not |
| Implemented — unverified | Code/docs exist; required tests or review not yet recorded |
| Verified | Evidence from executed tests, CI, or accepted review |
| Deferred | Consciously postponed with reason in `blockers` or roadmap |

## Prompt template

Use the template in `docs/06_ENGINEERING_DISCIPLINE.md` §10.

## Branch housekeeping

Ordinary work is local `main` in `C:\Users\gamer\aqil`. Push only when the founder asks. A push to GitHub `main` is a release: the existing GitHub to Vercel integration deploys it.

A branch or worktree needs a real concurrent-edit reason and a cleanup point. After the tested work is integrated:

1. Confirm the temporary branch is reachable from local `main`, or that its patch is already there.
2. Confirm the worktree has no uncommitted files that are not on local `main`.
3. Remove the temporary worktree, then delete the local branch with an ordinary `git branch -d`.
4. Do not force-delete a branch that still has a commit local `main` does not contain, unless a recovery bundle holds that commit and the handover states why it was superseded rather than merged.
5. Do not delete a remote branch, and do not create a new permanent branch for a routine milestone.

## Project rules

Repository enforcement: `.cursor/rules/aqil-engineering.mdc` (must stay aligned with this workflow).
