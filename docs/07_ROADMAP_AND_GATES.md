# AQIL — Execution Roadmap and Stage Gates

**Last reconciled:** 18 October 2026 · **Git baseline:** `main` @ `dd82e40` (PR #8 / M4 merged). Earlier “PR #1 is the latest milestone” and “M1 is next” wording below is historical. Current open work is PRs #9–#12.

## Current implementation snapshot (18 October 2026)

Statuses: implemented and verified · implemented but not fully verified · in progress · planned · blocked.

| Capability | Status | Where |
|------------|--------|--------|
| M1–M4 research engine, persistence, insight, forward fixture | Implemented and verified on `main` (`dd82e40`). Holdings weights and some events remain labelled synthetic. | Merged PRs #6–#8 |
| M5 live macro calendars | In progress. CI green on `a302053`. Not merged. | PR #9 → `main` |
| M6 SLOOS and Census methods | In progress. Web and database CI green; research worker CI failed on `2b5bd1e`. Stacked on M5. | PR #10 |
| Google auth and allow-list | Implemented but not fully verified. Engineering CI green on `9e449ee` (run 39080685298). No verified live Google round trip. Not merged. | PR #12 |
| My Wealth slice | In progress, and not safe to merge as-is. CI database job failed on `817b1f2`. Synthetic fixture when unsigned; mixed-currency sum; founder cookie still on that branch. | PR #11 |
| Hosted Supabase | Blocked pending founder approval | Not applied |
| Deploy Capital | Planned | This document; no code |
| US Employment Situation cycle (6 November 2026) | Planned operational evaluation, not a demonstrated forecast | Gate D |

**Deployed:** Vercel previews exist for the open PRs. Production on `main` does not include auth, M5, M6 or My Wealth. Hosted database migrations have not been applied.

## Integration gates (pass/fail)

**Gate A — Authentication.** Pass only when PR #12 is merged, a real Google sign-in and sign-out succeed, the founder allow-list or `access_grants` admits one identity and denies another, and the founder cookie/header path stays absent. Green CI alone is not a pass. ISO 27001 is not claimed.

**Gate B — Branch order.** Pass when merges follow: PR #12, then PR #9, then PR #10 after its research CI is green, then a rebased My Wealth branch that does not restore the founder cookie. No hosted `db push` in this gate.

**Gate C — My Wealth integrity.** Pass when the unsigned path does not return the synthetic book, unknown asset classes are rejected, mixed currencies are not summed without a dated FX rate, accounts separate simulation from live, valuations are append-only, and RLS covers read, insert, update and delete. Gains and returns stay unavailable until a journal exists.

**Gate D — First prospective cycle.** Pass when the baseline and Sahm threshold are frozen before **6 November 2026, 13:30 UTC** (October Employment Situation, 8:30 a.m. US Eastern). The existing BLS unemployment series and Sahm method are sufficient. M5 and M6 are not prerequisites. The record must say that no directional unemployment-rate forecast was made. Crossing the threshold is not forecasting skill.

**Gate E — Deploy Capital.** Pass for V1 when a signed-in founder can enter an amount in the reporting currency (default SGD) and receive a deterministic split across specific founder-approved ETFs, with an explicit “insufficient data” outcome. Asset-class totals alone are not V1. V2 adds overlap and costs. V3 may compare a signal-informed alternative only after a prospective evaluation exists. No automatic trading. Routine capture stays brokerage sync, then statement import, then a three-field manual trade.

## M1 — Completed on main (no longer the next milestone)

The acceptance list below remains the definition of the macro slice. It is **not** the next build. M1–M4 are on `main`. Remaining G0 items (hosted migration, UCITS/FX sample, rights for further series) are still open.

## Progress register

- **Authoritative item list:** `docs/07_BUILD_BACKLOG.csv` (columns include `verification_evidence`, `blockers`, `next_action`).
- **Statuses:** Not started · In progress · Blocked · Implemented — unverified · Verified · Deferred.
- **Session continuity:** `docs/CURSOR_SESSION_HANDOVER.md`.
- **Product chain (do not shortcut):** source acquisition → validation and provenance → deterministic analysis → causal interpretation → evidence verification → publication → longitudinal evaluation. Facts, statistical relationships, causal hypotheses, investment implications and demonstrated predictive value remain **distinct** (`docs/03_RESEARCH_ENGINE_AND_METHODS.md` §1).

## G0 foundation status (not gate-complete)

| Area | Status | Evidence / notes |
|------|--------|------------------|
| Next.js scaffold, tokens, shell, nav | **Verified** | CI web job: typecheck, lint, `check:tokens`, build, Playwright e2e |
| Python research worker scaffold | **Verified** | CI research job: ruff, pytest |
| Supabase migration + RLS/pgTAP | **Verified** | `20261017103000_create_user_settings.sql`; CI `supabase db reset` + `supabase test db`; types diff |
| Local Docker database workflow | **Verified** | `scripts/run-db-tests.ps1`, `npm run test:db` (documented; re-run after env changes) |
| GitHub CI (web / database / research) | **Verified** | Green on `main` post-merge |
| Versioned JSON schemas (files) | **Implemented — unverified** | `docs/schemas/` mirrored in `packages/contracts/`; **no CI schema validator yet** |
| Claim verifier fail-closed | **Implemented — unverified** | `workers/research/.../claim_verifier.py` + pytest; registry not built |
| Auth doctrine and implementation | **In progress** | Doctrine on `main`. PR #12 implements Google auth; CI green; live OAuth unverified; not merged |
| Information security standard | **Implemented — unverified** | `INFORMATION_SECURITY_STANDARD.md` + CI hardening **in working tree; not on `main` until merged** |
| Static synthetic research story (PR1) | **Not started** | Research page is placeholder only |
| Hosted Supabase | **Not started** | No migrations applied to hosted project; `db push` awaits explicit approval after CI pgTAP |
| G0 hard evidence (roadmap table) | **Not started** | Rights matrix, UCITS sample, macro source+revision, first hosted verify — see AQ-008–AQ-012 |

**G0 gate remains open.** PR1 repository foundation is largely **verified**; **G0 exit criteria** (data feasibility + hosted migration verification) are **not** satisfied.

## M1 acceptance record (met on main; not the next build)

**Goal:** Prove an economical, source-backed **macro data → deterministic analysis → evidence-linked output** path for a **small, founder-chosen set** of datasets and **one** established method — without claiming investment edge, without LLM publication, and without expanding to the full user journey in `docs/12_FIRST_VERTICAL_SLICE.md` (that remains the later end-to-end gate).

**Backlog anchor:** AQ-064 (parent); implements via AQ-008, AQ-012, AQ-013, AQ-014 and new subtasks as needed.

### M1 acceptance (product value, not “cron ran”)

1. **Rights and feasibility** — `SOURCE_RIGHTS.csv` (or equivalent register) records provider, licence class, permitted actions, cost notes and uncertainty for every dataset used; blocked if rights unknown for the intended use.
2. **Point-in-time source records** — each ingested observation links to `source_artifact_id`, `retrieved_at`, `as_of`, and `data_vintage` per `docs/03_RESEARCH_ENGINE_AND_METHODS.md` §2.
3. **Revision handling** — automated test proves a query at historical date **excludes** a later revision (matrix row: Method / retrospective macro revision).
4. **Deterministic computation** — one `MethodCard` at status ≥ `implemented` with version hash; same inputs reproduce identical outputs in CI.
5. **Bounded pipeline** — idempotent ingest job, retry/budget hooks or documented stubs (AQ-014); stale or partial feed **fails closed** (no silent fill).
6. **Evidence linkage** — outputs reference verified claim IDs or explicit `insufficient_evidence`; fail-closed verifier still blocks publication.
7. **Uncertainty and gaps** — missing series, revisions unknown or licence gaps surface as structured states, not interpolated narrative.
8. **Regression tests** — pytest (and future contract tests) cover parser, vintage rule, method replay and negative cases (bad vintage, missing field).
9. **Economical operation** — single-founder scheduling, no paid feed lock-in without documented approval; no agent framework (G0 guard).

**M1 does not require:** auth, portfolio ledger, causal graph UI, LLM agents, ETF eligibility, public launch, or an historical analogue model (`03` §3).

M1 acceptance was met by the engine now on `main`. Fixture tests do not verify a later live collection. Remaining G0 items (hosted migration, UCITS/FX sample) are still open.

## Strategic order
**Do not confuse feature completeness with research reliability.** Two tracks run in parallel: a small human-facing prototype to validate comprehension, and deep evidence/accounting infrastructure to validate correctness. Only combine them in a live research journey after gates pass.

| Gate | Objective | Hard evidence to proceed | Explicitly deferred |
|---|---|---|---|
| G0: Ground truth and feasibility | Verify data access/rights and trusted repo foundation | UCITS instrument/price/FX sample, primary macro source with a revision, rights matrix; **CI green**; **executable RLS tests (`supabase test db`) pass before first hosted migration**; token UI prototype; engineering doctrines documented | mass feeds, agents, prices, public launch |
| G1: Human understanding prototype | Test Today/Explore/Learn/Research presentation | Novices and experienced readers can explain same sample analysis and its uncertainties; mobile/a11y tests | investment signal automation |
| G2: Portfolio truth | Build manual account journal + deterministic benchmark | Reproducible multi-currency ledger, total return/flows, error states, XIRR/TWR limitations, two-tenant isolation | broker integrations |
| G3: Method foundation | Implement and reproduce baseline model(s) | documented method cards, verified dataset, named equations/assumptions, transparent benchmark | multiple agents |
| G4: One research causal pathway | Take one official event through end-to-end publication | verified claims, opposing interpretation, methodology results, human approval, layered story, frozen forecast | 30-domain live ingestion |
| G5: Laboratory and learning | Evaluate prospective paper outcomes and errors | frozen control/variant accounts, valid simulated execution, predetermined adjudication, corrections, challenger process | claims of proven alpha |
| G6: Private reliable service | Run as founder's daily tool and correct failures | backup restore, source outage handling, manageable spend, genuine personal utility | personalised public recommendations |
| G7: Public free multi-user | Add safe anonymous reading/accounts/peer challenge | privacy/rights/legal review, tenant isolation, moderation, accessibility and scale | subscriptions |
| G8: Subscription-readiness | Honor founder free cohort and paid entitlement | tested cutoff terms, anti-abuse, billing/security/legal, provider rights, cost viability | trade execution |

## First three pull requests
**PR1: Repository and truth primitives.** Next.js app skeleton and tokens, Supabase migration/RLS tests (**pgTAP green in CI before remote apply**), Python worker scaffold, versioned contracts, static synthetic research story, CI, no LLM. **Pass:** clean setup, CI and mobile story comprehension prototype.

**PR2: Data feasibility proof.** Verify 2–3 chosen UCITS share-class identities and history, documented FX and company/official fund pages, one official historical policy release with amendment, rights matrix. **Pass:** sample real source/quote records are accurately ingested and linked; unknown data blocks.

**PR3: Accounting and evidence validation.** Synthetic portfolio ledger and cashflow-matched benchmark; claim verification validator; negative tests for invalid citation, duplicated import, missing FX. **Pass:** replay correctness and rejected unsupported claim; published pages cannot bypass review.

## Research milestones and trade-offs
- 'Automated article pipeline' is not a milestone until verified claims and human editorial gating exist.
- 'Multi-agent network' is not a milestone. A bounded retrieval, analytical and adversarial role exists only if it improves evaluation relative to a simpler baseline.
- 'Self-learning' is not a one-time model feedback prompt. Must demonstrably preserve original forecasts and independently test changed rules.
- 'Mock accounts' need only a ledger engine, not broker paper logins, individual AI instances or simulated fake market feeds.
- Content and learning can launch while investment alpha is unproven. Never label the service an outperformer because of a profitable initial cohort.
- Historical analogue research is a later method family (`03` §3; AQ-066). It uses versioned similarity configuration, point-in-time inputs, contradictory precedents and out-of-sample evaluation. It is not M1 and it is not a universal score.

## Release KPIs: not vanity metrics
**Human value:** comprehension (conclusion + uncertainty), educational lesson clarity, voluntary helpful return visits, reported confidence in ability to understand (not market certainty). **Truth:** source support coverage, citation mismatch detection, correction time, unanswered challenges, data freshness. **Research:** preregistered trial status, outcomes and calibration vs baselines. **Money:** ledger reconciliation, total-return accuracy, FX coverage. **Reliability:** job success, restore drills, spend and security incidents.

## Scope guardrails
At most 1–3 verified causal domains during first complete slice; the extensive ontology is future coverage. At most 2–3 active quantitative methodologies until verified end to end. At most several controlled virtual experiment cohorts until evaluation is proven. Only build capabilities that directly support the end-to-end research trust chain, core wealth use or comprehension tests.

## Launch blocking criteria
Cannot launch publicly if: unsupported material investment facts render; unverifiable fund identity is treated eligible; any cross-tenant data leak is possible under tests; source-rights unverified for distribution; correction audit absent; method changes silently modify champion results; portfolio wrong when FX missing; privacy/terms/regulatory classification lacks review; founding entitlement contract not published before promotion.

## Founder discipline
Maintain `DECISIONS.md` (ADRs), `SOURCE_RIGHTS.csv`, `METHOD_REGISTER.csv`, `KNOWN_UNKNOWNS.md`, `INCIDENTS.md`, `MODEL_CHANGELOG.md`, and `RESEARCH_SCORECARD.md`. Update charter only on genuine strategic decision, not each passing idea. Small discoveries modify the appropriate subsystem spec, never erase earlier commitments.
