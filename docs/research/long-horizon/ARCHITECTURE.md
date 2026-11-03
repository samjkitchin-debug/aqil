# Long-horizon research architecture

**Status:** research record. This is not an investment claim and it is not Verified.

## What already existed

The research schema already had append-only `research.research_runs`, `research.prospective_assessments`, and `research.research_cycles`. `research.research_runs.investment_implication` allows only `no_action` or `insufficient_evidence`, and `analysis_mode` allows only `point_in_time` or `latest_revised`. A portfolio simulation is not one of those runs. `research.prospective_assessments` records a capture at a time, and its revision class stays `latest_revised`. It is not a scientific claim. The migration file `supabase/migrations/20261102140000_parameter_versions.sql` describes an unpublished parameter artefact. That table is not present on the local development database, so this package does not apply that unrelated migration and the pilot leaves `parameter_version_id` null.

The macro and ETF discovery notes in `docs/research/macro-etf` stay as they are. The coverage matrix remains 960 cells. This package does not relabel any of those cells point-in-time.

## Why these tables were added

The existing tables do not link a versioned hypothesis, a frozen experiment specification, an immutable execution, inspectable evidence, and a scientific claim. Overloading `research.research_runs` would either break its checks or invent a macro run for a price-only comparison. The new tables are in the same `research` schema, on the same local database, and they use the existing `research.deny_row_mutation()` trigger. There is no second research database and no second task ledger.

## Verified baseline differences

These were checked on the local databases. They are not assumed from an earlier note.

- Branch `research/macro-etf-discovery` was at `6fffff18d640949aceb28045a8e0a82106280166` and tracked the same commit on `origin/research/macro-etf-discovery`. `origin/main` was `f52a888f6bbedf96e528ca3bccf6df751e3c8896`. The research branch was not an ancestor of `origin/main`.
- The only dirty worktree file at the start was `apps/web/public/icons/icon.svg`. It stays unstaged and out of every commit.
- Local Postgres and `aqil_etf` on `127.0.0.1:55432` were not reset. Inside the database container the server port is 5432. The host mapping is 55432. A check of `inet_server_port()` must not be used as proof of the host port.
- Live `latest_revised` observations: 38,653. The `bea.vintage.real_gdp.pct_preceding` series: 1,077 `provider_vintage` rows, 99 quarters. Seasonal adjustment is `unknown`. Every `source_release_at` time in that series is midnight UTC. That timestamp is an identity anchor, not an observed publication time. `bea.nipa.T10106.A191RX` remains a separate `latest_revised` series with 319 rows.
- All `provider_vintage` rows, including fixtures, were 1,092. That is the 1,077 live GDP rows plus 15 fixture rows. The figures are not a disagreement about the live series.
- `aqil_etf` had 42,931 adjusted closes, 19 symbols, no INRG, and no foreign-exchange observations. `research.research_runs` had 54 rows and `publication_allowed` was false on all of them.
- `research.research_reader` does not exist on the local database. Grants to that role are conditional.
- `supabase_migrations.schema_migrations` does not list `20261023120000` even though `research.prospective_assessments` exists. `20261029212358_research_reader.sql` and `20261102140000_parameter_versions.sql` are also not applied. This package records that bookkeeping gap and does not rewrite it. Only the new migration is inserted into `schema_migrations` after a successful local apply.

## What this package adds

`supabase/migrations/20261103170000_long_horizon_research_registry.sql` adds append-only hypotheses, experiment specifications, executions, evidence, claims, status events, dependency links, candidate design rows, and family gates. Views `research.current_scientific_status` and `research.long_horizon_progress` separate the latest status from the immutable evidence. The progress view has counts and no completion percentage. `publication_allowed` is constrained false. Category C cannot be statistically supported, economically useful, or forward-validated. A portfolio execution whose vintage list contains `bea.vintage.real_gdp.pct_preceding` is rejected.

The migration is applied to the local development database only. It is not applied to a hosted project. Risk class is R2. Rollback is to leave the additive tables in place. They are not dropped on the preserved database.

The Python package `aqil_research.long_horizon` holds the simulator, the frozen category C specification, the catalogue reader, and the registry writer. Methodology mathematics, `refresh.py`, allocation, the investment-policy statement, and Saxo behaviour are not edited.

The certification pass adds `aqil_research.certification` beside that package. The stored code hash on `LH-X-001` covers only the `long_horizon` modules, so the audit can import the simulator without replacing the execution. Reproduction remains `uv run python -m aqil_research.long_horizon.reproduce` from `workers/research`.
