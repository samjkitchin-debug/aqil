# AQIL — System Architecture, Tech Stack and Stable Data Contracts
**Baseline:** modular monolith, clearly isolated research worker. Design for future users/tenants now; do not buy distributed-system complexity before necessary.

## Topology
```text
Browser / installable PWA (Next.js App Router + TypeScript + Tailwind)
  ├─ Public Today, Explore, Learn, Research pages (server-rendered reviewed research)
  ├─ Private My Wealth, saved items, profile, founder entitlements
  └─ Server routes (validated auth, safe reads/writes, import initiation, reviewer actions)
          │
          ▼
Supabase Auth + PostgreSQL (single authoritative record; RLS/grants)
  ├─ research, methods, sources, claims, policy, causal graph, editorial, challenges
  ├─ instrument registry, market observations, user financial ledger, entitlements
  ├─ experiment journal, model registry, evaluations, corrections, job leases
  └─ raw documents: rights-controlled object storage / link + hash when cannot retain
          ▲
          │ schema-versioned, least-privilege worker access
          │
Scheduled Python worker(s) (uv, Pydantic, Polars or pandas, NumPy, pytest)
  ├─ source-specific fetch/parse and permission checks
  ├─ deterministic verification, signals, methodology calculations
  ├─ bounded LLM research adapter, human-review queue
  ├─ paper strategy fills, valuation, forecast evaluation
  └─ audit/outage/cost/detection reporting
```

**No FastAPI required initially.** Next.js server handlers provide UI APIs. When interactive heavy Python inference and trusted external integrations demand a separately scalable API, add FastAPI *behind the existing versioned contracts*, not through a total rewrite. PostgreSQL is not a search index for huge raw corpus; use object storage and selective full text; search/vector index only after measured need. No graph DB for v1: causal edges in PostgreSQL relational tables.

## Recommended baseline stack (validate current compatibility before installing)
- **Frontend:** Next.js App Router, TypeScript `strict`, React, Tailwind design aliases, semantic CSS tokens, accessible primitive components, PWA manifest + controlled service worker, SSR/ISR for public reading where appropriate.
- **Database/auth:** Supabase managed PostgreSQL, Supabase Auth, RLS + explicit schema grants, SQL migrations, pgTAP/Supabase SQL policy tests; use separate schemas for private holdings vs public research. No secret/service-role key client-side.
- **Financial/research calculation:** Python 3.x supported current stable, `uv` lockfile, `pydantic` for validated typed payloads, `decimal.Decimal` for monetary arithmetic, pandas/NumPy for analytics, DuckDB optional for columnar local research when data proves necessary. `pytest`, `ruff`, type checker.
- **Persistence/contract:** versioned JSON Schema (source-of-truth cross-language contracts), generated/validated Pydantic and Zod types as feasible, ISO-8601 UTC and timezone ID fields, migrations reviewed.
- **Scheduling:** one durable worker with source-specific poll cadences and Postgres queue/lease semantics. Platform cron only triggers work; jobs retained in DB with idempotency keys. Multiple workers only after proven throughput. Don't rely on volatile cron invocation as evidence of completion.
- **AI:** one model gateway with provider abstraction, structured responses, bounded token/web-search budgets, fixed tool allowlists, contextual sanitisation, source ID verification. AI agent is a bounded research task rather than a persistent digital employee.
- **Testing/ops:** Vitest, Playwright, axe-core, SQL RLS tests, pytest fixtures, OWASP-aligned application checks, structured logs, error alerts, restored backup rehearsals.
- **Deployment:** provider-neutral frontend host, Supabase DB and smallest always-available scheduled worker sufficient; never assume free tiers permit commercial workloads or high-uptime tasks. Separate preview/staging/production.

## Domain modules with enforced boundaries
1. `identity_billing`: auth user, plan, immutable founding entitlement, audit; no investment calculations.
2. `instruments`: issuer, fund/legal share class, ISIN, MIC/trading line, listing, corporate action, verification status.
3. `market_data`: historical quotes, FX, calendars, data rights, prices, distributions, staleness, corrections.
4. `portfolio`: ledger, cash accounts, holdings projection, valuation, TWR/MWR, benchmarks, import review.
5. `sources`: source registry, rights, ingestion, document evidence, revisions and event clustering.
6. `methods_signals`: versioned research methods, factor indicators, reproducible calculation results.
7. `causal`: policy lifecycle, economic relationships, horizon/scenario and contestable assumptions.
8. `hypotheses`: forecast registration, frozen revisions, adjudication, independent evaluation.
9. `lab`: shadow portfolios, experiment pre-registration, simulated orders and outcome tracking.
10. `editorial`: story multi-depth outputs, claim mappings, publish approval, errata, reading feeds.
11. `peer_review`: evidence-backed challenges, triage, abuse control and response.
12. `ops`: job registry, budgets, trace IDs, incidents, quality and observability.

**Rules:** Domain modules own their write APIs; consumers use typed read models. Avoid direct UI calls into model internals. Financial arithmetic resides in one canonical code path, not duplicated on client.

## Minimum canonical data design
### Identity/commerce
`users` (auth provider ID), `profiles`, `user_preferences`, `entitlements` (type, start, cutoff cohort, version, scope, status, source/audit), `terms_acceptances`, `consents`, `billing_events` (future), `account_security_events`. Entitlements are server-authoritative and auditable; never derived only from signup timestamp in UI.

### Source and knowledge
`source_providers`, `source_rights`, `source_documents` (hash + retention class), `source_versions`, `source_claims` (span/field, unit, status), `independent_source_origins`, `event_clusters`, `observations` (vintages), `indicator_definitions`, `indicator_values`, `policy_actions` (status histories), `causal_nodes`, `causal_edges`, `causal_edge_evidence`.

### Methodology and research
`method_cards`, `method_implementations` (code/prompt/model/config hash), `method_evaluations`, `research_runs`, `forecast_contracts`, `forecast_versions`, `forecast_evidence_links`, `forecast_adjudications`, `outcome_reviews`, `research_incidents`, `research_challengers`, `model_promotions`.

### Funds and money
`funds`, `share_classes`, `exchange_listings`, `corporate_actions`, `fund_factsheet_versions`, `eligibility_assessments`, `quotes`, `fx_rates`, `distributions`, `broker_accounts`, `portfolio_journal_events`, `cashflows`, `holdings_projections`, `portfolio_valuations`, `benchmark_runs`, `import_batches`, `import_rows`, `reconciliation_issues`.

### Experiments and delivery
`experiment_families`, `experiment_definitions`, `virtual_account_journal`, `virtual_orders`, `virtual_fills`, `virtual_valuations`, `experiment_reviews`, `stories`, `story_versions`, `story_claim_links`, `story_corrections`, `peer_challenges`, `public_disclosures`, `audit_events`, `jobs`, `job_attempts`, `api_spend`.

Use DB constraints, foreign keys, unique scopes, checks and row-level policies. Public verified research and private user investment data should have disjoint access paths. Avoid making all tables publicly addressable through generated REST APIs.

## Four clocks + one market clock
For each real-world observation, store:
1. `effective_at` (economic / policy event time or observation period);
2. `published_at` (original source released it);
3. `retrieved_at` / `first_seen_at` (our system encountered it);
4. `available_to_model_at` (validated access time under actual processing/release lag);
5. price feed `exchange_timestamp` and timezone/market session for execution.

**Historical query for decision at T:** only records whose publication and availability timestamps were at or before T. Backfilled data are labelled retrospective and never used to falsely claim they were observed live. Version/revision tables preserve what was known then. Official FRED/ALFRED revisions illustrate this need.

## Immutable record model
Forecast origins, methodological approvals, original source hashes and journal events are append-only *at the application level*. Corrections append new superseding versions linked by `supersedes_id`; don't overwrite the past. Distinguish audit immutability from keeping personal data forever: user privacy deletion must support lawful deletion/crypto-shredding without falsifying public research history. Immutable public research **must not include personal account identifiers**. Use privacy-minimised public research results and explicit retention policy.

## Portfolio journal and financial correctness
- Journal entries include `event_id`, `tenant_id`, `account_id`, `event_type`, `trade_date`, `settlement_date`, `instrument_id`, `units`, `unit_price`, `price_ccy`, `fees`, `tax`, `fx_link`, `source_id`, `batch_id`, `idempotency_key`, `correction_of` and `created_at`.
- Fixed-point/decimal money arithmetic; signed journal legs if double-entry design chosen. Zero-sum cash/security transfer invariants; never derive net contributions from buys and sells.
- Canonical immutable events include deposit, withdrawal, internal transfer, buy, sell, fee, distribution, reinvestment, tax, split, symbol/share class migration and corrections.
- Positions always derived from journal; displayed valuations have as-of timestamp and coverage. Review ambiguous historical costs and FX instead of inventing defaults.
- Benchmark: same **external** flows and timing as portfolio, prescribed execution and FX/cost policy; broad global equity benchmark is a user-selected comparable strategy, not universally appropriate risk benchmark.
- Show portfolio return independently of deposits: since-inception XIRR with root/convergence checks; TWR only with sufficient interim valuations; realised/unrealised gains separate; inflation-adjusted scenarios not guarantees.
- Manual import then broker CSV then authorised read-only broker OAuth/statement integrations; do not request brokerage credentials in-app or allow trade execution.

## Virtual portfolio and evaluation correctness
`experiment_definition` locks methodology, universe, weights and decision rules, market as-of, fees, FX, cashflows and evaluation before first simulated fill. Fill model: first valid executable subsequent market session, no lookahead, account for spreads, fees, slippage/rounding, holidays and missing quotes. Do not invent a fill if data missing. Evaluations reproduce from versioned price/provider inputs; freeze old results, append evaluation revisions on source corrections.

## Research job orchestration
`jobs` have `job_type`, `idempotency_key`, `owner`, `status`, `lease_until`, `attempt`, `max_attempts`, `scheduled_at`, `started_at`, `completed_at`, `cost_budget`, `trace_id`, `input_hash`, `output_ref`, `error_code`, `blocked_reason`. On worker failure, lease expiry allows replay; unique idempotency prevents duplicate story or paper trade. Exponential backoff, queue inspection, dead-letter/triage, provider circuit-breaker.

## Data rights as first-class capability
For each feed classify **per action**: permitted private download, storage, derived research, private display, public display, paid-subscriber display, historical caching and redistribution. Also retention duration, attribution, user-level rate limits and provider access credentials. Rights uncertainty means data cannot be publicly displayed or used in commercial derived content where prohibited. Don't cache copyrighted full articles without permission; source-link and permitted short excerpts/metadata where lawful.

## Agent security
Treat all news, PDFs and peer submissions as hostile content. Read-only retrieval roles, domain/tool allowlists, bounded context and output schemas, prompt-injection separation, no arbitrary shell/DB write/secret access for LLM, safe link handling, SSRF protections for fetchers, rate/cost caps, human-reviewed publication. Model providers receive minimised non-private evidence by default; user wealth sent only under explicit documented opt-in and minimum sufficient abstraction.

## Multi-tenant and scale-readiness
- `tenant_id` or `user_id` on every private asset and owned job. Private access guarded by DB RLS/grants, enforced again in server routes and tested against direct DB requests, storage, views and exports.
- Shared global research computed once and cached; **do not** spawn individual geopolitical agents for each subscriber.
- Separate account preferences from entitlement, editorial reading from private portfolio, public research from unreleased experiments; reduce migration/regulatory blast radius.
- Make subscriptions provider-agnostic and versioned. Prepare lifecycle states (free-founder, free-standard, trial, paid, grace, cancelled, banned) but do not integrate payments until public monetisation milestone.
- Horizontal scaling later: move bounded worker roles onto independent queue consumers, dedicated API only when metrics show need; no need to change canonical contracts.

## Reliability/operations
- Source outage/staleness shown as such; jobs alert if missed scheduled releases; research can be `paused_missing_data`, `blocked_rights`, `awaiting_review`, `suspended_due_to_cost`, not falsely 'up to date'.
- Research incident blast radius: source→claim→edge→thesis→story→virtual experiment dependency links allow bulk quarantine and targeted corrections.
- Database migrations tested from clean setup and backup restore. Encrypted backups in separate location, restore exercise and periodic reconciliation. Production access least privilege, change approvals, secrets scanning, log redaction, vendor downtime plan, delete/export rights.
- Define cost categories: API/data licences, LLM, search/browser, worker, hosting, storage, support/legal and operational monitoring. Enforce budgets and degrade gracefully.

## Contract versioning
All cross-language interfaces are JSON Schema versioned with semantic compatibility rules. Additive optional fields can remain compatible; type/meaning changes require version bump, migration, replay fixtures and ADR. Use IDs and labels rather than front-end interpretation of model prose. A `published_story` stores research version IDs, so refreshed pages don't silently change findings.

## Decisions to revisit with evidence, not taste
- FastAPI only if interactive/specialised Python endpoints cannot be supported economically through worker tasks.
- Vector store only if search quality is demonstrably inadequate using relational full text and curated links.
- Graph database only if multi-hop traversal and scale truly exceed Postgres graph edges.
- Paid fund/quote feeds only after a documented private/public rights and coverage trial.
- Extra autonomous agents only when they outperform simpler bounded research workflows on accuracy, cost or review time.
- Push alerts only when people explicitly want them, opt in, and they do not incentivise trading urgency.

## First hard data feasibility gate
Prove with actual provider samples: reliable 2–3 relevant UCITS ETF share class identities, official factsheets, historical adjusted total-return/price series plus corporate actions, correct close timestamps, SGD base FX, and permissible private use. Separately demonstrate public/commercial-rights path; don't confuse the two. Prove one official policy document with amendment and one revised macro release. The source catalogue is incomplete until then.
