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
| 020 | Deploy Capital: strategic baseline first; signal tilt only as a stored, bounded comparison | practical use of research without automatic target changes or invented conviction | founder approves a tilt method and its maximum weight |
