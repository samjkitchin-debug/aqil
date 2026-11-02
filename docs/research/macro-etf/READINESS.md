# Macro-to-ETF readiness

**Status:** Gate 0 was written before any correlation. The later-gates section records the run.  
**Branch:** `research/macro-etf-discovery`, cut from `5ef2913`  
**Catalogue hash:** `b7b9c2aa85eb9c343b0582f93b05fa57e26f46be57d4e3b8b25a831a20059491`

This note separates what was read from the local databases, what was classified, and what has not been estimated. No correlation in this file is a result. The correlations are not in this file because they had not been computed when it was written.

## What was read

Docker was up. Both databases were read on loopback port 55432 and were not reset. The backup file `C:\Users\gamer\aqil-release-backups\2026-11-03-etf-history\aqil_etf.dump` is 1,629,423 bytes. Its SHA-256 is `B7598DC08AEE375B4E29F66A0423075EAED2A6527B0DDBCBE1F1FE3C6BB96BEB`, which matches the expected hash.

Live `latest_revised` economic observations on `postgres` are 38,653. Fixture rows are 87. Provider-vintage rows are 15, and those 15 sit inside the fixture rows. No live row has a model-availability timestamp. `publication_allowed` is false on all 54 research runs.

`aqil_etf` holds 42,931 `adjusted_close` rows, 0 raw closes, and 0 foreign-exchange observations. Nineteen listings and nineteen share classes are stored. INRG has no listing. Every stored `inception_date` is null. VWRA has 1,838 sessions from 2019-07-25 to 2026-11-02. RBOT has 2,524 sessions and is the only stored listing without 2025-12-19. EUNA's 2,249 sessions are in euros. The other stored prices are in US dollars. The adjustment text on every price row is the TradingView split adjustment, which is not a raw close and not an issuer total-return index.

## Differences from the handover

The handover named `72cfe7d` as `HEAD`. That commit is the parent of `5ef2913`, which is the commit this branch was cut from. `origin/main` is `f52a888`. `72cfe7d` is not on `origin/main`.

The handover's 38,653 is the live count. The table also holds 87 fixture rows, so the unfiltered observation count is 38,740. The ETF price counts match the handover. The preservation paragraph did not state the share-class count. It is 19, and the legal inception date is null on each of them.

The combined unemployment table has 944 distinct months and is missing October 2025. January 2022 is present only as a fixture. The live panel used here has 943 months and is missing both January 2022 and October 2025. Those months were not filled. CPI-U has one live gap, October 2025. Industrial production, the federal funds rate, the 10-year yield, and the 3-month yield have no monthly gap in the stored span.

## Classification

`default_method_registry()` has 26 registrations. They are not one list of 26 investment signals.

| Role | Registrations |
| --- | --- |
| Executable historical methodology | 10 |
| Supporting indicator | 10 |
| Diagnostic | 5 |
| Unavailable | 1 |

The certification counts of 8 families, 10 variants, 3 indicators, and 4 diagnostics are a different grouping. They are not added to the 26. The programme register file has 31 method rows. Some of those rows are not executable registrations, and some executable registrations are condition panels rather than register rows.

Stock–Watson, Hamilton, Bai–Perron, the autoregressions, the probit, and Bry–Boschan stay blocked for a predictive test. Their parameters or centred smoothers use the full sample, and this pass does not rewrite them. The Sahm gap, restricted diffusion, and the term spread can be recomputed from past observations only. They remain retrospective because the inputs are latest revised. Census advance orders are unavailable. No point-in-time cell is ready.

## Coverage matrix

The matrix has 960 cells: 8 named features, 20 register listings, and 6 horizons. 568 are `retrospective_only`. 392 are blocked. 344 of the blocked cells miss the exploratory floor of 36 decision points and 8 non-overlapping windows. The other 48 are INRG, which has no stored price. There is no `ready` cell and no `point_in_time` cell.

A decision uses an assumed one-month lag. That lag is an assumption, not a stored release time. The entry is the first stored session on or after the decision, and a session more than 10 days later is a missing window rather than a filled one. The return bound is the first stored session because the legal inception date is null. EUNA is not pooled into a US-dollar result.

On the first-pass listings, every 1-month, 3-month, and 6-month cell is `retrospective_only`. Every 24-month and 36-month cell is blocked. Twelve-month cells are `retrospective_only` for CSPX, EIMI, and EUNA, and blocked for VWRA. The preregistered VWRA 12-month unemployment cell has 73 decision points and 7 non-overlapping windows, so it is below the exploratory floor. It will be estimated as a description and will not be labelled an exploratory finding.

Later gates run only on `retrospective_only` cells, and only on the four first-pass listings. The other listings stay in the matrix for coverage and are not a second search. The holdout date, 2023-01-01, is frozen in the catalogue. It has not been used to choose a cell.

## What this is not

`publication_allowed` stays false. No allocation, investment-policy, Saxo, or refresh file was edited. No production table was added. scikit-learn was not added. The forward-validated class is empty because nothing here was frozen before the outcomes.

## Later gates

The catalogue hash did not change after Gate 0. The trial ledger is `trials.jsonl`.

The pilot was estimated. Pearson r is 0.6976183057660493, Spearman r is 0.6036422349612018, and the Newey-West slope is 0.03587019471662332. It has 73 decision points and 7 non-overlapping windows, so it stays below the exploratory floor and is not an exploratory finding.

Seven training-window cells on EIMI meet the statistical rule, at the 1-month and 3-month horizons. The features are the unemployment level, the 12-month unemployment change, the 12-month CPI-U change, and the 12-month industrial-production change. They are not seven independent findings. The holdout slope kept the same sign. The predeclared cash rule did not beat immediate investment on the holdout under either the zero or the 10 basis-point assumption. The economically useful class is empty. The forward-validated class is empty.

Gate 2 recorded 45 rows and did not promote a combination. Gate 3 recorded 72 rows. No incremental test both met the training statistical floor and survived Benjamini-Hochberg, so Gate 4 did not combine methodology outputs. Gate 6 ran the holdout once.

`uv run pytest tests/discovery` passed 16. `uv run pytest tests/test_asof_selection.py` passed 7. `uv run pytest tests/etf/test_performance.py` passed 13. The same three paths together passed 36. `npm run test:research` was not re-run. The known failures were not re-run and were not weakened: the TradingView rights fragment in `test_restricted_sources_block_collection_holdings_and_ter`, `test_every_etf_fragment_blocks_cost_collection`, and `test_rights_fragments_refuse_automated_collection`, and the live H.15 count in `test_live_board_file_is_counted_in_memory`. This is not a GitHub Actions result and it is not Verified.

`publication_allowed` stayed false. The refresh, as-of, return, allocation, and investment-policy files were not edited.
