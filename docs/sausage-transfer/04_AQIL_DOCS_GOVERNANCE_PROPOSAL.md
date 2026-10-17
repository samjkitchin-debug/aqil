# Aqil — Documentation Authority and Drift-Control Proposal

## Why

The Sausage acquired a sizeable documentation set over extensive iterative development. The valuable late-stage correction was to establish a **single authority per invariant**, distinguish living operations from historical investigations, and make superseded files point to current canon. Aqil should take this discipline from its first implementation months, without creating 150 documents now.

## Keep the existing Aqil v2 documents

- `00_READ_ME_FIRST.md` — canonical index and reading order; update it as new authoritative docs are introduced.
- `01_PRODUCT_CHARTER.md` — why the product exists; change only for genuine product decisions.
- `03_RESEARCH_ENGINE_AND_METHODS.md` — research truth and reproducibility, methodology approval, forecast and claim correctness.
- `04_ARCHITECTURE_AND_DATA.md` — system topology, data authority, RLS/tenancy, interfaces.
- `05_HUMAN_EXPERIENCE_AND_DESIGN.md` and `design/tokens.css` — usability, responsive UI language, tokens.
- `06_ENGINEERING_DISCIPLINE.md` — change controls, CI, documentation and review requirements.
- `07_ROADMAP_AND_GATES.md` — acceptance criteria, not a second authority for implementation details.

Add the auth doctrine as a link in `00_READ_ME_FIRST.md`, without duplicating its detailed rules into six separate briefs.

## Minimal future structure (create as needed)

```text
docs/
  00_READ_ME_FIRST.md
  01_PRODUCT_CHARTER.md ... 12_FIRST_VERTICAL_SLICE.md
  canon/
    auth-session.md            # authoritative once reviewed
    portfolio-integrity.md     # later, when accounting code exists
    research-integrity.md      # only if extracted from existing methods doc, not duplicated
  ops/
    database-migrations.md     # current running method and recovery
    auth-incidents.md          # later
    provider-ingestion.md      # later
  design/
    tokens.css
  decisions/
    ADR-0001-*.md
  investigations/             # dated, explicitly NOT canon
  archive/                    # superseded, preserved
```

## Required front matter for new living documents

```text
Title:
Status: canonical | living-ops | proposal | investigation | superseded
Owner: feature/domain (not only person's name)
Last verified: YYYY-MM-DD (against code/tests where relevant)
Authority: path of the owning canon
Supersedes: path(s) when applicable
Change triggers: code/migration/docs event requiring review
```

Use a stable pointer from an old location to the new canon when moving files. Keep historical evidence; do not erase a wrong prediction or post-mortem to simplify the docs tree. Separate product `why`, contract `must`, ops `how`, investigation `what we observed` and release evidence `what ran`.

## Change rules

1. Before Cursor edits code, identify the authoritative document and living code path.
2. When changing an invariant, update **one** canonical rule, then links, tests, migrations and operations notes; no contradictory copies.
3. Record what is **verified** vs hypothesised; dated investigations never override current canon.
4. No broad doc rewrite as a side effect of a small bug fix; use a focused addendum or an ADR.
5. Stable core contract changes need explicit founder approval: session/access boundaries, ledger and cashflow maths, entitlement rules, source provenance, forecast immutability, model evaluation and version promotion.
6. Keep a live `KNOWN_DEBT.md` with reason, owner, risk and deferred trigger—not a pile of contradictory TODOs.
7. Do not copy The Sausage's sports-specific files. Its docs are archived **reference material**, not part of Aqil's production authority.

## Drift gates worth automating

- Check links from `00_READ_ME_FIRST.md` exist.
- Check active documents have one canonical owner for each named invariant (some human review required).
- SQL migration directory is unique (`supabase/migrations/`), schema snapshots/types match migrations.
- Design tokens in source match documented central tokens and no new hardcoded visual constants appear in components.
- Research schema contract tests reject unsupported, retracted or postdated claims.
- Changelog/version/build identity can identify exactly what was deployed or which method generated a forecast.

## Cursor handover form

**Scope:** one bounded task + exclusions. **Source:** exact canon paths and code files. **Changes:** file list and why. **Tests:** commands and actual results, including skipped/blocked. **Risk:** auth/DB/user isolation/financial/research rights. **Remaining uncertainty:** real unknowns. **Next action:** one small approved task. **No claims of success without execution.**
