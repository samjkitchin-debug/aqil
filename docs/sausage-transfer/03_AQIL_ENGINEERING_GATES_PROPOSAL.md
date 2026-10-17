# Aqil — Executable Engineering & Release Gates

**Proposed supplement** to Aqil `/docs/06_ENGINEERING_DISCIPLINE.md` and `/docs/07_ROADMAP_AND_GATES.md`. Does not change the chosen stack.

## Gate philosophy

Build output is not proof that schema, permissions, research arithmetic or user flows are correct. Every important invariant must have a **negative test** that demonstrates what is refused. A CI job that has not run is **unverified**, not passing.

## Gate A — Every scoped change / pull request (fast)

- TypeScript strict/typecheck; ESLint; build once in representative production mode.
- Python `pytest`, Ruff format/check; later type checking and deterministic numerical fixtures.
- Central CSS token scanner and documented-token/semantic-class coverage.
- JSON Schema validation against canonical cross-language contracts; include **rejected** invalid contracts and mismatched facts.
- Secret scan including tracked/untracked staged content; .env, logs, API keys and personal financial material excluded.
- Package risk check (`npm audit` findings recorded by dependency, severity and runtime vs CI exposure; no blind breaking `fix --force`).
- Changed-file dependency checks and docs updates; report PASS/FAIL/SKIPPED honestly.

## Gate B — When SQL, database functions, RLS or entitlements change

- Disposable **real** PostgreSQL/Supabase environment starts clean (prefer same major version as hosted; project currently PostgreSQL 17.x).
- Replay all forward migrations; ensure unique ordered filenames and no parallel migration sources.
- Run pgTAP role-accurate tests using `anon` and `authenticated` JWT claims/roles, not tests passing as `postgres` or `service_role`.
- Explicitly test cross-tenant SELECT/INSERT/UPDATE/DELETE, unauthenticated access, UUID spoofing, functions, views and storage policies where applicable.
- Inspect `SECURITY DEFINER` ownership/search_path and `EXECUTE` grants, including `PUBLIC` and separate `anon` grants.
- Generate DB types; fail if generated contracts drift unexpectedly.
- Execute changed database functions and triggers at least once with realistic valid AND invalid inputs. Detect unexpected function overloads after signature change.
- Verify clean migration replay, type diff and controlled rollback/restore procedure. Hosted dry-run and advisor scans are additional—not replacements.
- **No remote deployment if tests are blocked or not run**. Use an explicit approval checkpoint for remote writes; no automatic destructive database reset.

## Gate C — When auth, session, PWA or portfolio code changes

- Auth: cold load, sign-in, sign-out, OAuth redirect/return, expired token, mobile background/wake, offline/reconnect, multiple tabs, transient Supabase failure.
- Accessibility: axe smoke + manual keyboard/touch and reduced motion; functional 320/390/768/1280/1920 tests already exist. Ensure no hidden horizontal overspill.
- PWA: no authenticated private cache, no service-worker auth authority, no refresh storm, no stale deployment loop.
- Portfolio: approved decimal fixtures for deposits, transfers, FX, fees, splits, distributing/accumulating funds, negative/missing prices; benchmark cash-flow-matched. Test duplicate import idempotency, cross-account isolation, failed source data.
- Research: timestamp/source permission, model version and forecast freezes; wrong/unsupported input fails closed; champion predictions remain immutable when challenger promoted.

## Gate D — Before staged/public release

- SQL migrations rehearsed; backup/restore evidence for persistent data.
- Explicit release/version/build SHA; target environment, migration SHA, model/method version and curated release notes.
- Staging smoke on a non-founder test account, including private-data leak probes and unfriendly mobile conditions.
- Security, source rights, user consent and founder free-tier entitlement tests.
- Production rollout/rollback plan and telemetry for new risk; verify deployed live system **after** rollout.
- Clear operational owner for database, ingestion, financial ledger, auth, model evaluation and release approval.

## CI implementation staging

**Immediate**: maintain existing Next/TypeScript/lint/token/Playwright/axe + Python checks; add reliable `db:verify` execution before SQL deploy, basic contract validation, secret scan. **Next**: role/grant/RLS matrices, storage/tenant/entitlement tests as applicable. **Later**: full mobile auth/resume suites, provider source-retraction/drift tests, financial reconciliation fixtures, model replay comparisons, production deployment smoke. The first milestone should not add an enormous slow suite without relevant functionality.

### Risk-tagged change checklist

For each work item state: `risk level`, `owner`, `affected modules`, `source/canon`, `migration?`, `security?`, `research/financial correctness?`, `user path`, `expected failed and terminal states`, `tests actually run`, `observability`, `rollback` and `documentation changed`.

### G0 Supabase-specific instruction

Current `supabase/migrations/20260317103000_create_user_settings.sql` and 9 pgTAP cases **have not yet passed** locally. Get real disposable PG running or get a verified equivalent isolated CI run **before** approving hosted development application. A mock unit test or an MCP permissions inventory is not a substitute. Treat `docs/07_BUILD_BACKLOG.csv` checkmarks as evidence-based, not wishful.
