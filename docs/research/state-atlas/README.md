# Historical state atlas

**Status:** local research record. This is not an investment claim and it is not Verified.

## Freeze

Branch `research/macro-etf-discovery`. Specification commit `795d208d4d78103238f8c32228ad1d475f9c53ca` froze `ATLAS-DEF-001` version 1, the three JSON Schemas, and `LH-H-004` / `LH-E-004` before any score or state row was written. The schemas are mirrored in `docs/schemas/` and `packages/contracts/schemas/`. The materialiser then ran against that commit. `research.experiment_executions.git_commit` for `LH-X-004` is that specification commit. The atlas package hash on the execution is `cd131aa6ee1bd381fe37d5233cc816f12aa0c1253b8f445af1f7b7e90ea4ead4`.

`EVT-DEF-001` version 1 is unchanged. Its hash remains `3844aff160a7f6fac7fb4c966707a313b6e8c89f4bb04cee6a72cb4d97275114`.

## What was stored

Migration `20261104120000_historical_state_atlas.sql` was applied to local `postgres` only, after disposable pgTAP passed. It was not applied to hosted Supabase. `supabase_migrations.schema_migrations` has version `20261104120000`, name `historical_state_atlas`, statements null. `research_reader` is still absent, so the conditional select grant did not run. Row level security was not changed. `publication_allowed` is false. Local `postgres` and `aqil_etf` were not reset.

Live inputs, recounted on the same databases:

- 38,653 live `latest_revised` observations.
- 1,077 `bea.vintage.real_gdp.pct_preceding` provider-vintage rows.
- 42,931 adjusted closes.
- 0 foreign-exchange rows.
- 0 INRG adjusted closes.

The disposable pgTAP preparation reported 39,730 development live observations and left that count unchanged. That figure is the 38,653 latest-revised rows plus the 1,077 BEA vintage rows.

Stored atlas rows:

| Object | Rows |
|---|---|
| Decision anchors | 2,358 |
| Listing month-end anchors | 2,065 |
| BEA GDP release anchors | 293 |
| State observations | 618,007 |
| Market states | 76,405 |
| Retrospective economic states | 520,380 |
| Point-in-time GDP states | 21,222 |
| Outcome measures | 12,390 |
| Censored outcomes | 1,672 |
| Scientific inventory rows | 85 |
| Anchor-to-event links | 1,675 |
| Market episodes | 52 |
| Episode membership rows | 1,749 |
| Claim anchors | 1,700 |

Inventory rows are 28 economic series, 19 listings, 26 methods, and 12 unavailable dimensions. Content checksum `c65ce0d4ff48a9967c8916c66a5c983776db78e78fb01d60eb8b89fb15affe79`. Evidence artefact SHA-256 `88eba584b4bb8bcb6755f1008ea178c679b10afd9bb7a802cac158879f4e1a77`.

The reproduction command is `uv run python -m aqil_research.long_horizon.state_atlas` from `workers/research`. The second run printed `unchanged`, inserted 0 anchors, and matched that checksum.

## Clocks

Latest-revised rows keep `period_end` when it is stored. When it is null, the period bound is the last calendar day of a month or quarter, the stored week-ending day for a weekly series, the period start for a daily series, or 31 December for an annual series. That bound is not a release date. Those features stay `retrospective_latest_revised_release_lag_unknown` and `usable_as_decision_input` false. None of the 520,380 retrospective states is marked usable.

Point-in-time states use only `bea.vintage.real_gdp.pct_preceding`. The vintage kept for a quarter is the latest printed release date on or before the anchor, and a release on the anchor's calendar day is included. This is not the observation contract's next-day `model_available_at` rule. `source_release_at` on these rows is midnight UTC and is a date anchor. The value stays a percent change from the preceding period. It is not relabelled as a level of GDP. `bea.nipa.T10106.A191RX` stays a separate latest-revised series.

Year-on-year steps one year on the frequency grid: 12 months, 4 quarters (12 months), or 52 weeks. A missing period is not filled. Daily and annual series are `insufficient_frequency`. A trailing window that is short of the frozen count is `insufficient_lookback`. The anchor is kept.

Market features use stored sessions on or before the anchor. Horizons are 21, 63, 126, 252, 504, and 756 sessions, not calendar months. A missing forward session is censored, with a null value. The labelled advance used by the score is the existing 126-session outcome of at least 0.10. Split-adjusted closes are not relabelled as total returns. Relative performance against VWRA is USD only, with a five-session peer tolerance. EUNA is EUR. Its relative-performance values are null and the availability is `blocked_no_foreign_exchange`. No foreign-exchange conversion was applied. VWRA is not compared with itself.

Surprise has no state row. The table rejects a feature id that contains `surprise` or starts with `outcome_`.

## Methods

The 26 registered methods are inventory rows only. Twenty-four are `not_historically_replayed`. `CENSUS_ADV_DURABLE_ORDERS` and `MACRO_CONDITIONS_PANEL` are `unavailable_input` because `census.m3.adv.MDM.NO` has no stored rows. `fred.alfred.UNRATE` is unstored. No historical method output was written. None of the 26 is point-in-time. The real GDP vintage is not a method input.

## LH-X-002

The atlas command recomputed the existing outcome catalogue and required the stored counts: 1,749 events, 1,700 eligible month-ends, 1,553 condition-false, 147 condition-true, 631 labelled advances, 62 both, 85 false positives, status `inconclusive`. Those counts matched. `LH-X-002` was cited and was not re-estimated.

## LH-H-004

`LH-H-004`, `LH-E-004`, `LH-X-004`, evidence `LH-V-004`, and claim `LH-C-004` are category C price-only research. The hypothesis initial status remains `proposed`. The current status, from the later status event, is `inconclusive`. Dependencies `LH-D-011` through `LH-D-014` record the shared atlas specification, the shared event definition, the overlapping `LH-E-002` period, and the standalone-bounce control. `independent_confirmation` is false on each. The portfolio simulator was not called. The 618 catalogue scenarios were not executed. `macro_vintage_ids` is an empty list.

Thirteen symbols met the minimum counts, so the status is not `insufficient_data`. Across those symbols the median incremental difference versus the standalone bounce is 0.1, which is greater than zero, so the status is not `no_incremental_information`. The median lift over the eligible-month base rate is 0.0375, which is greater than zero, and the median share of labelled advances preceded by the sequence is about 0.0789, which is below 0.70, so the status is not `rejected`. The frozen rule therefore leaves the result `inconclusive`. `statistically_supported`, `economically_useful`, and `forward_validated` are forbidden. This history is already inspected. It is not an untouched holdout.

Pooled eligible month-ends: 1,700. Sequence month-ends: 75, of which 38 were labelled advances. Standalone-bounce controls without a prior near-trough: 137, of which 58 were labelled advances. Standalone bounce on its own, including paths that also had the earlier condition: 172. Labelled advances: 631. False positives: 37. Missed advances: 593. Those dates are in the evidence body.

`LH-H-001` remains `proposed`. `LH-H-002` remains `proposed`. `LH-H-003` remains `retrospective_only`. `LH-X-003` remains `blocked` and was not estimated. `LH-X-001` remains `inconclusive`.

## Expansion boundary

This note is the boundary. It was not executed in this slice.

- New outcome families only as `EVT-DEF-002`. Volatility transitions, a distinct failed-recovery family, and a distinct trend-reversal family are absent from `EVT-DEF-001` version 1.
- Method-state time series only after a vintage covers that method's own inputs and passes `workers/research/src/aqil_research/certification/vintage_gate.py`.
- A category B macro association only as a new experiment that cannot be called a backtest.
- Portfolio tests only for a later validated condition, on the existing simulator, against immediate VWRA and the other stated controls. This history is already inspected, so it is not a holdout.
- The 618 scenarios stay unexecuted.

## Checks

These checks are on this tree. They are not a GitHub Actions run and they are not Verified.

`npm run test:db` passed 15 files and 244 tests, including `state_atlas.test.sql`, both before the migration was applied to `postgres` and again after the schema dump included it. Development live observations remained 39,730.

`npm run test:research` prepared disposable `aqil_research_test` and did not reset `postgres` or `aqil_etf`. It collected 838 tests: 834 passed and 4 failed. The four failures are `test_restricted_sources_block_collection_holdings_and_ter`, `test_every_etf_fragment_blocks_cost_collection`, `test_rights_fragments_refuse_automated_collection`, and `test_live_board_file_is_counted_in_memory` (868 federal-funds rows where the test expects 867). Those four tests were not weakened. Pytest exited before the script's Ruff steps. A separate `uv run ruff check` on the new atlas files and `tests/certification/test_live_ledger.py` passed. `uv run ruff format --check .` was not run, and the 13 pre-existing files were not reformatted.

The live progress snapshot now counts three succeeded executions and three inconclusive or rejected claims, because `LH-X-004` and `LH-C-004` are stored. The portfolio simulator was not called. Scientifically supported conclusions remain 0. Dependencies `LH-D-001` through `LH-D-014` are present, and none is an independent confirmation.

`npm run typecheck` in `apps/web` passed. The production build passed. No page changed, so there was no browser pass.
