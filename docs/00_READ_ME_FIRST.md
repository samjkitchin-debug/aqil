# AQIL — Final Ground-Zero Baseline v2.0
**16 October 2026 | Decision status: proposed build baseline, not validated investing alpha | Owner: founder**

## What this is
A coordinated specification for Aqil: a calm, evidence-led, long-horizon wealth and global-intelligence application. This supersedes prior Agent Macro and Aqil drafts **for implementation decisions**, without discarding their history. Previous drafts remain historical inputs, not parallel product truth.

**Read in this order:**
1. `01_PRODUCT_CHARTER.md` — why, who, what, what not.
2. `02_CRITICAL_REVIEW.md` — decisions, holes, failure modes, boundaries.
3. `03_RESEARCH_ENGINE_AND_METHODS.md` — crown jewel and scientific contract.
4. `04_ARCHITECTURE_AND_DATA.md` — implementation architecture and stable contracts.
5. `05_HUMAN_EXPERIENCE_AND_DESIGN.md` — people-first UX, Aptos/navy/gold design tokens; `RESPONSIVE_LAYOUT_CONTRACT.md` — shell and PWA layout gates.
6. `06_ENGINEERING_DISCIPLINE.md` — how to instruct Cursor, test, review, release.
7. `INFORMATION_SECURITY_STANDARD.md` — security-by-design requirements, threat model and control tiers (not certification).
8. `AUTH_AND_SESSION_DOCTRINE.md` — server-side auth, SSR cookies, PWA session recovery. Google sign-in is live.
9. `DOCUMENTATION_AUTHORITY.md` — canonical vs reference docs; `sausage-transfer/` is historical only.
10. `AGENT_OPERATING_RULES.md` — non-negotiable rules for every agent session.
11. `CURSOR_COLLABORATION_WORKFLOW.md` — agent workflow summary.
12. `07_ROADMAP_AND_GATES.md` plus `07_BUILD_BACKLOG.csv` — gates and **authoritative progress register**; `CURSOR_SESSION_HANDOVER.md` — session continuity.
13. `08_GOVERNANCE_AND_BUSINESS.md` — editorial accountability, future billing and compliance gates.
14. `09_EVIDENCE_AND_METHOD_SOURCE_REGISTER.md` — references and source audit rules.
15. `schemas/` and `reference/` — implementation examples and **unverified research catalogues**.
16. `sausage-transfer/` — **historical investigations only**; see `sausage-transfer/README.md`.

## Non-negotiable distinctions
- **Facts** are not **inferences**; **scenarios** are not **predictions**; **investment theses** are not **demonstrated alpha**; **paper outcomes** are not **real fills**; **wealth growth from contributions** is not **investment return**.
- Generative AI cannot guarantee zero errors. Aqil's enforceable promise is **no unsupported consequential claim is intentionally published**, plus controls that block, flag, correct and transparently audit failures. No system can guarantee zero false statements, including source-origin errors.
- A published academic model is not automatically proven suitable for Singapore investors using Irish-domiciled accumulating ETFs at current prices and fees.
- 1,027 candidate factors do **not** equal 1,027 verified feeds. The inherited ontology is unverified and must not be surfaced as live coverage.
- The application begins private. Designing multi-tenancy from day one does not authorise public personalised financial advice, redistribution of licensed market data, or promises of permanent subscriptions without operational readiness.

## Build decisions frozen at ground zero
- One repository; Next.js/TypeScript responsive web/PWA; Supabase Auth + PostgreSQL with row-level security; separate scheduled Python research/analytics worker; schema-first contracts; no separate FastAPI service until a measured need.
- Shared curated research records feed Today, Explore, Learn, Wealth and Research. No direct LLM generation at page-render time.
- Source-first collection; verified typed observations and claims; deterministic calculations; AI restricted to bounded investigations, structured synthesis and contradiction search; human publication approval initially.
- Append-only primary research forecasts, portfolio journal events and outcome reviews with amendments rather than destructive edits; named promotion/rollback gates for research methodology.
- Manual portfolio ledger and CSV later; broker read-only much later. No automatic trading.
- Design tokens, component reuse, responsive/a11y tests, editorial review and financial fixtures are mandatory from first commit.

## Ground-zero decisions deliberately *not* made
Exact price-data provider and licence, full ETF coverage, public launch date, paid tier price, legal classification of future personalised features, actual predictive performance and long-term subscription economics. These are **gates**, not assumptions.

## First Cursor task
Create repository skeleton and CI, `tokens.css`, one accessible shell and research-story mock fixture, shared versioned JSON schemas, database migrations and RLS tests, and a failing-by-default evidence validator. Do **not** connect an LLM or populate live financial analytics until canonical source/instrument contracts and permission rules exist.
