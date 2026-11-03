# Point-in-time vintage record

**Status:** research record. This is not a verified investment result and it is not a GitHub Actions result.  
**Date:** 3 November 2026  
**Branch:** `research/macro-etf-discovery`

The discovery files already in this directory were not rewritten. This note sits beside them.

## What was retrieved

These are retrievals on 3 November 2026. A blocked source is a finding. No vintage was invented.

| Source | What was requested | Result | Storage |
| --- | --- | --- | --- |
| FRED and ALFRED `fred.alfred.UNRATE` | Unauthenticated observations request. The body was discarded. `FRED_API_KEY` was unset. | HTTP 400. The rights row still prohibits retention, historical archiving, redistribution, and commercial publication. | Not stored. |
| BLS LN flat file | Header of `ln.data.1.AllData`, and `ln.series` was reachable. | HTTP 200. Columns are series id, year, period, value, and footnote codes. There is no vintage column. | Not stored as a vintage. The existing latest-revised rows were left in place. |
| BLS Employment Situation archive | The archive index page. | HTTP 200. The page says data in archived news releases may have been revised in subsequent releases. | Not stored. The page does not establish an original vintage. |
| BLS CPI feed | `cpi.rss`. | HTTP 200. The word vintage was absent. This is a current release feed, not a vintage panel. | Not stored. |
| BEA previously published estimates index | `apps.bea.gov/histdatacore/histChildLevels.html?HMI=2`. | The response was the BEA archive shell and did not list release files. | Not stored. |
| BEA vintage history workbook | `https://apps.bea.gov/national/xls/gdp-gdi-vintage-history.xlsx`. | HTTP 200, 75,271 bytes, workbook. Sheet `Vintage History` prints release dates. | Real GDP percent change was stored. See below. |
| Board G.17 package | First lines of the registered CSV package. | HTTP 200, `text/csv`. The header is a current series with month columns from 1919-01. | Not stored again. It is not a vintage panel. |
| Board H.15 package | HEAD of the registered zip. | HTTP 200, zip. The package was not unpacked in this pass. The live count test still fails: it expects 867 federal-funds rows and the file now has 868. | Not relabelled as a vintage. |

FAQ 147 was read the same day. It says that, unless stated otherwise, information on the BEA website is in the public domain and may be used or reproduced without specific permission. That is why the vintage workbook could be archived. The FRED row is a different right, and it still blocks storage.

## What was stored

One series, on local `postgres` only:

- Source `bea_gdp_gdi_vintage_history`.
- Dataset `bea.vintage.real_gdp.pct_preceding`.
- Measure: real GDP percent change from the preceding period, as printed in the Real GDP column.
- This is not Table 1.1.6 account `A191RX`. That level series is still `latest_revised`, 319 quarters, and was not rewritten.
- Provenance `provider_vintage`. Availability precision `date`. `earliest_model_available_at` is null. The existing date rule makes the value usable at 00:00 UTC on the next calendar day. The workbook prints a date and no clock time. `source_release_at` is 00:00 UTC on the printed date so the vintage identity is stable. That midnight value is an identity anchor, not an observed publication time, and it is not an exchange-session calendar.
- Seasonal adjustment is `unknown`. The header and the read-me do not say whether the percent change is a seasonally adjusted annual rate. That label was not added.
- 1,077 rows. 99 quarters, 2002 Q1 through 2026 Q3, with no missing quarter in that span. 293 distinct printed release dates, from 2002-04-26 to 2026-10-29. The sheet says it was last updated 29 October 2026.
- Unpublished real GDP cells in this file: 0. A dotted cell is skipped. The test excerpt uses one synthetic dotted cell to prove that skip. The live file did not need it.
- Current-dollar GDP, GDI, and real GDI columns were not stored.
- File SHA-256 `127ef3a7e7c9923e7962dd43693139d44865acbb4e3a6db9b8c52b6de87b4a58`.
- Series checksum `f3f4a4242d32007fedf34d751f1675e6be80270d76f44f073d894e8016a64be1`.
- First import inserted 1,077 rows. The second import inserted 0 and left 1,077 unchanged.
- The series is not on the daily refresher. `refresh.py` was not edited.

## As-of checks on the stored rows

Read back from local `postgres` on 3 November 2026. Point-in-time mode:

| Decision instant (UTC) | 2026 Q3 | 2026 Q2 | 2002 Q1 | Rows returned |
| --- | --- | --- | --- | --- |
| 2026-10-29 23:00, the release date of the advance | unavailable | 2.2, vintage 2026-09-30 | 3.4, vintage 2023-09-28 | 98 |
| 2026-10-30 00:00, the next UTC day | 3.4, vintage 2026-10-29 | 2.2, vintage 2026-09-30 | 3.4, vintage 2023-09-28 | 99 |
| 2002-04-26 23:00, the advance release date | unavailable | unavailable | unavailable | 0 |
| 2002-04-27 00:00 | unavailable | unavailable | 5.8, vintage 2002-04-26 | 1 |
| 2003-12-24 00:00 | unavailable | unavailable | 4.7, vintage 2003-12-23 | 7 |

The 2002 Q1 advance of 5.8 and the later printed value of 4.7 are both in the workbook. The selector keeps the latest vintage whose availability is on or before the decision. A later synthetic value is excluded by the unit test. A `latest_revised` row mixed into the same dataset is refused by `recorded_series_class` before it can be labelled point-in-time.

## Methodology replay

`default_method_registry()` has 26 registrations. None lists `bea.vintage.real_gdp.pct_preceding` as a required dataset. The test `test_no_registered_method_depends_on_this_vintage` checks that.

No methodology was replayed. No method was labelled point-in-time capable. The GDP nowcast remains unimplemented. Methodology mathematics, `refresh.py`, allocation, the investment policy, and Saxo were not edited. No research run was added. `publication_allowed` is still false on all 54 runs.

## Compatibility

The original matrix in `COVERAGE_MATRIX.csv` is unchanged: 960 cells, 568 `retrospective_only`, 392 blocked, zero point-in-time. The eight features are unemployment, CPI-U, industrial production, and the other series named in the discovery catalogue. None of them is this real GDP growth vintage. A second 960-row matrix was not generated, because no feature's historical availability changed. Genuinely point-in-time eligible cells after this pass: 0.

## Research outcomes

The discovery trial ledger and `RESULTS.md` were not rerun and were not edited. The recorded retrospective result still stands: no demonstrated economic improvement over immediate investment, seven overlapping EIMI training associations, weak holdout confirmation, and no validated multivariate edge. This vintage pass did not estimate a new correlation, a holdout, or a benchmark. There is no new investment result, positive or negative, from the vintage series. Absence of a point-in-time replay is a data-coverage limit. It is not evidence that the earlier retrospective associations were wrong, and it is not evidence of an edge.

## Checks

On this tree, not GitHub Actions, and not Verified:

- `npm run test:research` prepared disposable `aqil_research_test` from the `postgres` schema and did not reset `postgres` or `aqil_etf`. Pytest collected 759 tests: 755 passed and 4 failed.
- The four failures are the known ones, and they were not weakened: `test_restricted_sources_block_collection_holdings_and_ter`, `test_every_etf_fragment_blocks_cost_collection`, `test_rights_fragments_refuse_automated_collection`, and `test_live_board_file_is_counted_in_memory` (868 federal-funds rows where the test expects 867).
- `uv run ruff check .` in `workers/research` passed.
- `uv run ruff format --check .` reported 13 pre-existing files. None of them is part of this vintage import. They were not reformatted.
- TypeScript typecheck, web lint, production build, browser tests, and `npm run test:db` were not re-run. No web file and no migration was changed.

## Counts after the import

Local `postgres`: 38,653 live `latest_revised` observations, 87 fixture rows, 1,077 live provider-vintage rows, and 15 fixture provider-vintage rows inside the 87. No live row has `earliest_model_available_at` set. `aqil_etf` was not written. The ETF backup hash is unchanged.

## Next package

One bounded package: a vintage panel for a series that a registered method already requires. Real GDP growth does not unlock Sahm, the term spread, industrial production, prices and policy, or Stock–Watson. ALFRED remains ineligible. The BLS archive page is not, on its own wording, an original vintage. The BEA previously published estimates index did not return files on this date. Do not relabel latest-revised rows. Do not buy a feed. Do not publish.
