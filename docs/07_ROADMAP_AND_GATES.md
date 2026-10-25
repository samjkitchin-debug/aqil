# AQIL — Execution Roadmap and Stage Gates

**Last reconciled:** 25 October 2026 · **Git baseline:** local `main` after the Intelligence merge `060ef3f`, with the consolidation note in `docs/CURSOR_SESSION_HANDOVER.md`. Not pushed. `origin/main` remains `c9ea596`.

## Operating baseline (24 October 2026)

This section supersedes older sentences below that say authentication, hosted Supabase or broker access has not started. It also supersedes any sentence that treats a local test on this tip as a GitHub Actions result.

- Live app: `https://aqil-tau.vercel.app`. Google sign-in is the production access path. The running deployment is still `origin/main` at `c9ea596`.
- Ordinary access is any verified Google account. The allow-list and `access_grants` gate are removed. See ADR 020.
- Hosted project `ojvswermsbbaltjohqph` was last read on 24 October 2026 with exactly five migrations, through `20261017180000_forward_intelligence.sql`. This certification did not query or migrate the host. Ten later local files are not applied, from `20261018200000_verified_prospective_assessment.sql` through `20261024150000_research_macro_events_themes.sql`. The earlier upgrade rehearsal covered nine files and did not include the events migration. The 25 October 2026 local rehearsal on `aqil_u0_ten` did apply that file. The host was not queried.
- Hosted U0 remains **no-go** until the founder approves the batch in [`docs/runbooks/U0_HOSTED_RELEASE.md`](runbooks/U0_HOSTED_RELEASE.md). The local bar is the ten-file upgrade rehearsal, not a fresh replay of every file on an empty database. On 25 October 2026 disposable database `aqil_u0_ten` was created from the five-file state, given representative rows and an authentication stub, upgraded with the ten later files including `20261024150000_research_macro_events_themes.sql`, checked, and dropped. The earlier nine-file rehearsal did not include that events migration. Preserved databases `postgres` and `aqil_etf` were not written. Detail is in the handover. This is a local result, not GitHub Actions.
- Production web loaders do not fall back to `127.0.0.1`. A missing research or ETF database URL fails closed. Outside production, the local default remains. That behaviour is on local main and is not on `origin/main`. The running Vercel app is still `c9ea596`. The first private mode after a hosted upgrade is one manual `npm run research:refresh`, with freshness visible. No schedule exists. Automatic updates must not be claimed.
- Before any hosted apply: take a backup. A code rollback will not undo those local migrations. Then founder approval, apply, grant checks, the server-only research URL, one manual refresh, and only then one push to `main` so the existing GitHub to Vercel integration deploys. GitHub Actions has not run on `5bb2ca8`. No Vercel CLI deploy. Production Saxo stays off.
- Reading model: Today is the briefing and a compact pulse. Intelligence has three sections: Dashboard at `/conditions` shows stored observations; Methodologies at `/intelligence/methodologies` shows research outputs only when `publication_allowed` is true; Insights at `/intelligence/insights` states that no cross-method finding is published. The release calendar stays `/calendar`. Evidence stays `/research`. ETF exposures stay `/explore` and are not an Intelligence section. No fourth primary destination.
- Local Saxo reads are real and read-only. Production does not offer Connect Saxo until encrypted, owner-scoped token storage exists. See ADR 021–024.
- Workflow: localhost → local tests → reviewed commit → one push to `main` → the existing GitHub to Vercel integration. No Vercel CLI deploy, no second Vercel project, no preview build created for its own sake.
- Local macro store, 25 October 2026, not a GitHub Actions result: 23 operational series and 34,859 live periods, up from the 10-series, 8,704-period baseline. The Eurostat all-items HICP index adds 369 periods, January 1996 to September 2026. Every operational live row is `latest_revised`. A latest-revised row is not a vintage. The two ECB HICP series still end in December 2025 and were not overwritten. The BIS dollar credit stock still ends in the quarter starting 1 January 2026; a re-fetch inserted nothing. The OECD G20 leading indicator has 789 stored periods and is not operational. Existing US method versions still read only their original dataset ids. `PRICES_AND_POLICY` and `MACRO_READING_SYNTHESIS` do not consume the new HICP series. No composite, spread, or new method version was added. Detail is in `docs/sources/MACRO_COVERAGE.csv`, `docs/sources/etf/ETF_ECONOMIC_EVIDENCE.md`, and the handover.
- Next product order:
  1. Founder approval of the hosted backup, the ten-migration apply, the server-only database URLs, one manual refresh, and one push. The checklist is `docs/runbooks/U0_HOSTED_RELEASE.md`. U0 remains no-go.
  2. A permitted fund document and rights decision, then one run of `cite-etf`.
  3. An ISIN on one genuine holding so the resolver can match it by exact ISIN.
  4. Policy targets in `wealth_allocation_targets`, then the Deploy Capital read switch. The save path stays where it is until then.
  5. A rights-cleared benchmark return only after that cited share class names a benchmark.
  6. Identify a rights-cleared source for valuations and earnings, or record the block.
  7. Identify a rights-cleared credit-spread source, or record the block.
  8. Identify a rights-cleared dollar series, or record the block.
  9. Keep the United States reading separate from regional observation panels.
  10. Leave the AI-infrastructure theme and institutional-capital work on their existing gates. Do not open another geography collection wave. The macro research priority remains the methodology programme in `docs/macro/00_METHODOLOGY_PROGRAMME.md` (ADR 027). Monthly Bry–Boschan on stored industrial production is the engineering pilot. The Stock–Watson 1988 modern refit is a local read with publication closed. It is not operationally accepted. That programme does not wait on a further macro data wave.

## Methodology-first macro sequence (25 October 2026)

ADR 027 is the decision. `docs/macro/QUANTITATIVE_METHOD_REGISTER.csv` is the method status. `docs/07_BUILD_BACKLOG.csv` remains the only progress register.

The pilot is not the strategic intelligence product. Harding–Pagan quarterly BBQ is not applied to monthly G.17. The NBER chronology is a diagnostic, not an exact-match test. The worker still has no `jobs` table, no cron, and no pandas dependency. NumPy, SciPy, and statsmodels are research-worker dependencies for the Stock–Watson filter. That dependency does not make the modern refit operationally accepted, and `publication_allowed` stays false. `docs/04_ARCHITECTURE_AND_DATA.md` describes a job queue that migrations do not implement. The pilot must not pretend that queue exists.

Hosted U0 stays an operations no-go. It is not the research priority and it is not cancelled.

## Progress register

- **Authoritative item list:** `docs/07_BUILD_BACKLOG.csv` (columns include `product_milestone`, `verification_evidence`, `blockers`, `next_action`). `product_milestone` is U0, U1, U2, later, or none.
- **Statuses:** Not started · In progress · Blocked · Partial · Implemented — unverified · Verified · Deferred.
- **Maturity, in evidence rather than a second register:** operational end-to-end, implemented and locally verified, implemented but unverified, partial, blocked, not implemented. Local tests are not hosted or signed-in verification.
- **Session continuity:** `docs/CURSOR_SESSION_HANDOVER.md`.
- **Product chain (do not shortcut):** source acquisition → validation and provenance → deterministic analysis → causal interpretation → evidence verification → publication → longitudinal evaluation. Facts, statistical relationships, causal hypotheses, investment implications and demonstrated predictive value remain **distinct** (`docs/03_RESEARCH_ENGINE_AND_METHODS.md` §1).

## G0 foundation status (not gate-complete)

| Area | Status | Evidence / notes |
|------|--------|------------------|
| Next.js scaffold, tokens, shell, nav | **Implemented — unverified** on this tip | Older CI web job is not `5bb2ca8`. This session ran web typecheck only |
| Python research worker scaffold | **Implemented — unverified** | GitHub Actions has not run the research CI job, so ruff and pytest on this tip are not verified. |
| Supabase migration + RLS/pgTAP | **Implemented — unverified** on this tip | Older CI evidence is not `5bb2ca8`. The 24 October upgrade rehearsal is local and is not a GitHub Actions run |
| Local Docker database workflow | **Implemented — unverified** on this tip | `scripts/run-db-tests.ps1` exists. This session did not run `npm run test:db` |
| GitHub CI (web / database / research) | **Implemented — unverified** on this tip | GitHub Actions has not run on local `main` `5bb2ca8`. Older green runs are not this commit. Local tests are not that CI run |
| Versioned JSON schemas (files) | **Implemented — unverified** | `docs/schemas/` mirrored in `packages/contracts/`; **no CI schema validator yet** |
| Claim verifier fail-closed | **Implemented — unverified** | `workers/research/.../claim_verifier.py` + pytest; registry not built |
| Auth doctrine | **Superseded by the operating baseline** | Google sign-in is live. See ADR 020 and `AUTH_AND_SESSION_DOCTRINE.md` |
| Information security standard | **Implemented — unverified** | `INFORMATION_SECURITY_STANDARD.md` + CI hardening **in working tree; not on `main` until merged** |
| Static synthetic research story (PR1) | **Implemented — unverified** | The labelled synthetic story is mounted only at `/dev/story`. It is not Today, Evidence, or live intelligence |
| Hosted Supabase | **Superseded by the operating baseline** | Five foundation migrations are on `ojvswermsbbaltjohqph`. Later migrations are not applied |
| G0 hard evidence (roadmap table) | **Not started** | Rights matrix, UCITS sample, macro source+revision, first hosted verify — see AQ-008–AQ-012 |

**G0 gate remains open.** PR1 repository foundation is largely in place on older commits; **G0 exit criteria** (data feasibility + hosted migration verification) are **not** satisfied. GitHub Actions on this tip has not run.

## Operational milestones U0, U1 and U2

These sit beside G0–G8. They are cumulative. U1 includes U0. U2 includes U1. They do not replace Forward Intelligence, and they do not authorise orders or a required return-forecast model.

| Milestone | Product meaning | Not included |
|---|---|---|
| U0 | Signed-in macro product: real series, publications, catalysts, visible freshness, and honest empty ETF and wealth states | The Intelligence dashboard, a refresh schedule, hosted apply, Saxo in production |
| U1 | Cited funds, portfolio mapping, a saved policy in `public.wealth_allocation_targets`, and an implementation-ready playbook library | Issuer scraping, a second policy file as a permanent store, predictive models |
| U2 | A read-only, policy-based deployment assessment | Orders, and any requirement for a return-forecast model |

U0 is the engineering priority and is still no-go for the hosted project. The safe local work for the approval package is the upgrade rehearsal and the production fail-closed database URL. Neither has been applied to the host.

## M1 — Next active milestone (macro intelligence engine slice)

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

**When M1 is verified:** update AQ-064 and dependent rows; then either deepen toward `12_FIRST_VERTICAL_SLICE.md` (G4) or complete remaining G0 data items (PR2).

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
**PR1: Repository and truth primitives.** Next.js app skeleton and tokens, Supabase migration/RLS tests (**pgTAP green in CI before remote apply**), Python worker scaffold, versioned contracts, static synthetic research story mounted only at `/dev/story`, CI, no LLM. **Pass:** clean setup, CI and mobile story comprehension prototype. GitHub Actions has not run that pass on `5bb2ca8`.

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
