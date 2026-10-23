# ETF programme contract

Status: task ledger for Phase A. Owner: ETF orchestrator. Last updated: 23 October 2026.

This note is the file ledger for the ETF workstream on `work/aqil-etf-intelligence`. It is not a research conclusion and it does not clear any source. Product truth stays in the canonical docs and in the schema. If this note and the migration disagree, the migration wins.

Risk for this phase: R3 for the new schema and access controls, R2 for eligibility. Local only. No push, no hosted migration, no paid feed, and no reset of the preserved macro database `postgres` on port 55432.

## One ETF database

Agents must not create a second ETF database, a second instruments schema, or a parallel share-class table. The only ETF database name is the local database `aqil_etf`. Identity lives in schema `instruments`, created by `supabase/migrations/20261024120000_etf_instruments.sql`.

Do not extend `forward.etf_*`. Do not treat a `forward.etf_instrument_records.etf_id` string as a canonical key. Do not add `instruments` to the Supabase Data API schema list in `supabase/config.toml`. That list stays `public` and `graphql_public`. The migration revokes `instruments` from `anon`, `authenticated`, and `service_role` in the same way as schema `forward`.

## File owners

Later agents may add only the paths in their row. They import shared types from `workers/research/src/aqil_research/etf/contracts/`. They do not edit that package, the migration, the JSON schema, these ETF docs, or the rights fragments.

| Agent | May add | Must not add |
| --- | --- | --- |
| Identity and seed catalogue | `workers/research/src/aqil_research/etf/identity/` and `workers/research/tests/etf/test_identity.py` | A second share-class table, invented TER, AUM, holdings, spreads, NAV, or returns |
| Issuer facts and costs | `workers/research/src/aqil_research/etf/fundamentals/` and `workers/research/tests/etf/test_fundamentals.py` | An issuer scraper. Issuer-reported TER is not total cost. No live spreads |
| Holdings and overlap | `workers/research/src/aqil_research/etf/holdings/` and `workers/research/tests/etf/test_holdings.py` | A fetch when the rights fragment is `prohibited` or `unknown`. Top-ten overlap is partial |
| Returns and benchmarks | `workers/research/src/aqil_research/etf/performance/` and `workers/research/tests/etf/test_performance.py` | A fund return before share-class inception, or a benchmark series labelled as the fund's own return |
| Vetting | `workers/research/src/aqil_research/etf/vetting/` and `workers/research/tests/etf/test_vetting.py` | A weighted rank, a write to My Wealth, or `CORE` when hard evidence is missing |
| Adversarial checks | `workers/research/tests/etf/test_adversarial.py` | Production collectors, or a change to the frozen contract in order to make a test pass |

The orchestrator owns the migration, `docs/schemas/etf_share_class.v1.json` and its mirror under `packages/contracts/schemas/`, `aqil_research.etf.contracts`, `docs/sources/etf/`, the backlog rows AQ-009 and AQ-040, and the session handover on this branch. Explore stays unmounted in Phase A.

## Frozen paths

Do not edit these, in this worktree or in any sibling worktree:

- `docs/sources/SOURCE_RIGHTS.csv`
- `workers/research/src/aqil_research/contracts/` (the macro contracts; the ETF package is `etf/contracts/`)
- `workers/research/src/aqil_research/methods/`
- `workers/research/src/aqil_research/prospective/`
- `workers/research/src/aqil_research/forward/`
- Any Supabase migration other than `supabase/migrations/20261024120000_etf_instruments.sql`
- Today, Evidence (`/research`), and My Wealth
- `EconomicObservation` and `forward.etf_*`
- The preserved database `postgres` on port 55432
- Sibling trees: `aqil-read-labour`, `aqil-read-prices`, `aqil-read-production`, `aqil-read-credit`, and any `aqil-macro-*`, `aqil-sahm`, or `aqil-m6` tree

Rights fragments for this programme live under `docs/sources/etf/fragments/`. One file per newly assessed `source_id`. The header is `REGISTER_COLUMNS` from `workers/research/src/aqil_research/sources/rights.py`, in that order, with one data row. Do not merge them into `SOURCE_RIGHTS.csv` in this phase.

## Rights already closed

These rows are already in `docs/sources/SOURCE_RIGHTS.csv`. They are not copied into a fragment and their collectors stay unbuilt:

- `vanguard_uk_vwra_holdings`: `automated_access=prohibited`, `redistribution=prohibited`
- `ishares_ucits_holdings`: `automated_access=prohibited`, `redistribution=prohibited`

`assert_automated_collection_allowed` refuses a fragment whose `automated_access` is `prohibited` or `unknown`, and it refuses a disabled source. Unknown is not permission.

## Identity rules the schema enforces

Prefer ISIN over ticker. One umbrella may have many sub-funds. One sub-fund may have many share classes. One share class may have many listings. A ticker change appends `instruments.identifier_history`. It does not insert another share class.

Trading currency is a listing column. Base currency is a sub-fund column. Hedge status and distribution policy are share-class columns. They are not substitutes for each other.

`instruments.fund_returns` rejects a row when the share class has no inception date, and when the period starts before that date. `instruments.benchmark_returns` has no `share_class_id`. It is a different series and must not be labelled as the ETF's own return.

Holdings snapshots require `rights_gate=permitted`. A prohibited or unknown holdings source cannot be stored there.

Assessments are append-only. Eligibility is `CORE`, `CONDITIONAL`, `EXCLUDED`, or `UNKNOWN`. Insufficient evidence must be stored as `UNKNOWN`. There is no rank column.

No TER, AUM, holding, spread, NAV, or return is invented in this phase. A field stays unavailable until a permitted citation exists.

## Macro read contract

The fields macro may later query, and the fields it must not write or read, are in `docs/sources/etf/MACRO_ETF_READ_CONTRACT.md`. That note does not change macro code.

## Blockers

Issuer and index pages assessed on 23 October 2026 do not clear automated collection. Vanguard and iShares holdings collectors stay unbuilt. The instruments migration is local to this branch. It is not a hosted migration. AQ-009 and AQ-040 stay in progress until identities are cited from a permitted source and the database checks have actually passed.
