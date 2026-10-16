# First Cursor prompt — paste after creating an empty Git repository

You are building **Aqil**, a human-centred long-horizon investment research, education and wealth PWA. Read every file in `/docs` in numeric order before touching code. The binding policies are `/docs/01_PRODUCT_CHARTER.md`, `/docs/03_RESEARCH_ENGINE_AND_METHODS.md`, `/docs/04_ARCHITECTURE_AND_DATA.md`, `/docs/05_HUMAN_EXPERIENCE_AND_DESIGN.md` and `/docs/06_ENGINEERING_DISCIPLINE.md`. Do not pivot the vision toward trading alerts or autonomous trades.

**Goal for first pull request:** initialise a working monorepo layout with Next.js/TypeScript strict, a token-only Aptos-first white/navy/gold design system, accessible public app shell and static synthetic demonstration of a layered source-linked research article; add PostgreSQL migration scaffolding, schema contracts, RLS deny-by-default tests and Python research worker project scaffolding. Do NOT connect live APIs, generate production financial claims, wire broker accounts, integrate LLMs or payments.

First inspect existing files and present: proposed file tree, decisions, realistic scope and acceptance checklist. Then implement in one bounded change. Use the provided `/design/tokens.css` as the only literal colour source. For any simulated amounts, stories, dates or results, mark as **illustrative synthetic fixture**.

Acceptance: builds; typecheck/lint pass; 320–430 px and desktop screenshot checks; keyboard accessibility; no tokens hardcoded in components; empty/error/unsupported claim states; no client service secrets; one fake source-claim ID rejected by validator; two-tenant access tests designed (and executable if DB running). Summarise executed tests and unresolved blockers. No claim the production research engine works yet.
