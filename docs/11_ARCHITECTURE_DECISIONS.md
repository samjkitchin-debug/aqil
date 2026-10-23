# AQIL — Architecture Decision Records (Summary)
**Status: accepted for v2 baseline, subject to explicit future ADR amendments.**

| ADR | Decision | Why | Revisit when |
|---|---|---|---|
| 001 | Next.js App Router + typed modular monolith | one coherent PWA, accessible UI and SSR | separate teams/interfaces or measurable performance bottlenecks |
| 002 | Scheduled Python research worker, no FastAPI in v1 | quant tooling without redundant service | interactive Python features need a separately scalable API |
| 003 | PostgreSQL authoritative store, Supabase Auth/RLS | relational audit data and multi-tenant readiness | measured demand for analytics warehouse/graph/search |
| 004 | Typed versioned contracts and immutable research origins | cross-stack reproducibility and forward compatibility | never revoke, only evolve version |
| 005 | Deterministic numeric methods; LLM synthesis bounded | reproducibility and source integrity | only change with evaluation and new ADR |
| 006 | Evidence verification and human editorial gate | cannot guarantee LLM/source truth; contain blast radius | limited low-risk template review automation proven safe |
| 007 | Researcher/challenger/champion role separation | prevent post-hoc overfit and silent self-rewriting | never revoke; implementation may evolve |
| 008 | ETF canonical identity by legal class + listing | avoid ticker/share class/currency errors | never revoke |
| 009 | Source and data rights recorded per permitted action | private/public/commercial licences differ | never revoke |
| 010 | Event journal, cashflow matched benchmark, independent lab ledger | accurate wealth and credible evidence | never revoke; implementations evolve |
| 011 | No trading, leverage or public personal reallocation advice | risk, philosophy and current compliance boundary | separately scoped legal/commercial mandate |
| 012 | Daily reading/editorial from same reviewed research object | coherent novice/expert experiences | if research content models genuinely diverge |
| 013 | Semantic tokens and Aptos-first white/navy/gold UI | consistent multi-year design | central design-system ADR |
| 014 | Private use → free signups → paid plans, grandfather entitlements | user mission + commercial optionality | legal/economics gate |
| 015 | Shared global research, private portfolio isolation | economic serving cost and privacy | later scale needs differentiated research cohorts |
| 016 | Optional anonymous reading and optional private wealth | inclusive product, consent minimisation | privacy UX evidence |
| 017 | No graph/vector DB at first | relational representation adequate for MVP | measured complexity/quality improvement |
| 018 | CI, migrations, security fixtures and restore drill from day one | prevent rebuild and data loss | never revoke |
| 019 | Server-side Supabase SSR session authority; doctrine in AUTH_AND_SESSION_DOCTRINE.md | prevent auth drift, refresh races and PWA logout bugs | only via ADR if identity model changes |
| 020 | Any verified Google account may open Aqil. Identity is `auth.users.id`. The founder allow-list and `access_grants` gate are superseded (18 October 2026) and must not be reintroduced for ordinary access | one user should sign in without an operator step; RLS still isolates private rows | a future explicit sharing or admin role, by a new ADR |
| 021 | Saxo is authoritative for Saxo positions and account values. Aqil normalises that source. Manual entry does not recreate the same brokerage account. Simulation is stored apart from live wealth and is never presented as live | one portfolio per real account; no synthetic rows in live wealth | a second broker needs its own source, not a copy of the Saxo snapshot |
| 022 | Ingest Saxo as snapshots first. Transactions, benchmarks, original-plan counterfactuals, model portfolios and long-term plans are future records and stay separate from observed values | the current read can be truthful without a speculative warehouse | historical events are added when the broker or statements actually support them |
| 023 | Keep observed broker values distinct from calculated metrics. Account-value change is not investment return. Broker time-weighted return is not that change. Price result, currency result and costs are separate and are omitted when the response did not include them | labels match the field that was retrieved | an independently calculated return needs its own method version and fixtures |
| 024 | Production broker connect requires encrypted, owner-scoped token storage and RLS. Gitignored local files are development only. The live Saxo credential can trade at Saxo; Aqil allow-lists read-only GETs and must not trade. A trading-disabled Saxo application is required before hosted tokens are kept | localhost must not be described as a production broker connection | hosted persistence after migration tests and an explicit founder approval |
| 025 | `public.wealth_allocation_targets` in `supabase/migrations/20261018210000_my_wealth.sql` is the single intended policy store. The gitignored file `apps/web/.local/investment-policy/{userId}.json` is development-only and is not a second permanent system (24 October 2026). The save path was not switched, founder financial data was not migrated, and the hosted wealth migration was not applied | one authoritative allocation policy, with the local file unable to diverge in production | switch the save path only after the hosted migration is approved and tested |
