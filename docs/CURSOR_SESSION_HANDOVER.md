# Cursor session handover

**Status:** living continuity note  
**Last updated:** 23 October 2026, four macro readings integrated and run on stored observations  
**Parent:** `2a12389` on `work/aqil-autonomous-build` before the registry commit  
**Checkpoint:** local only. Not pushed. Production, hosted migrations and Saxo authorisation stay unchanged.

## Four macro readings on stored observations, 23 October 2026

Risk class R2. Prices `59edd3cf47e7fe76d656d1b1021f6a4167773b3a` and industrial production `61a88868b6e49fa5adc98c1e36086ca77a02f211` were already in history. Labour `591f7ac9e8a65112b17a0aae8f1c5824f0d24bfb` was merged with `--no-ff` as `f70e320`, reverted as `ddd753d`, and reapplied as `b63cdf0`. Credit `e3e9906da73332cdbb0455fd33d429fd6d27da98` was merged with `--no-ff` as `0246277`, reverted as `5a6fc02`, and reapplied as `2a12389`. That reapply used `credit_standards_and_volumes.py`. Commit `c82c697` restored `credit_standards_volumes.py` and `CreditStandardsVolumesMethod`. Commit `0094984` put the renamed module back, and `e18619d` reverted it. The baseline module is `credit_standards_volumes.py`. Sahm, period-level change, SLOOS, Census, and `MACRO_CONDITIONS_PANEL` were not edited. `publication_allowed` stays false. Nothing was pushed. Database `postgres` was not reset.

One append on `postgresql://research_worker:research_worker@127.0.0.1:55432/postgres` at 23 October 2026 05:06 UTC. Research runs moved from 20 to 25. Observation counts were unchanged before and after: unemployment 44, CPI-U 956, payrolls 1053, job openings 309, industrial production 1293, bank credit 2806, federal funds 867, 10-year yield 882, HICP 348, SLOOS 146. Publications stayed 12 Employment Situation, 12 CPI, 15 Board, and 3 ECB. Future BLS calendar rows stayed 27.

All four readings were sufficient. `investment_implication` is `no_action`. The causal text is “No causal mechanism is established.”

- Labour `LABOUR_MARKET_CONDITIONS` 1.1.0, run `f0f41b6f-9d18-4e7b-84fb-30e53df2e157`, evaluation 1 September 2026. Unemployment 4.2 percent (observation `bls-202609-5198b4a7b0aad73a40b4a985`), 12-month change -0.20 percentage points from 4.4 (`bls-202509-cc8721d9c3c2d3fb9baf3f35`). Level rank 26 of 44. Payrolls 159044 thousands (`ces-202609-9d4487fc69db9be21443c259`), change 496 thousands, 0.31 percent, from 158548 (`ces-202509-18f11e07860e34278eba4477`). Rank of overlapping 12-month percent changes 237 of 1041. Job openings 7079 thousands in August 2026 (`jolts-202608-b7aaeb1f178a92f9c90a4106`), change 160 thousands, 2.31 percent, from 6919 (`jolts-202508-e35de06bfe2b813d4fe6aa78`). Level rank 233 of 309. Joint month August 2026: unemployment 4.1 (`bls-202608-fdcea9af7cd7ebb6d4c76cf9`), payrolls 159015 (`ces-202608-a3d48c05a22580dc680787bd`), openings 7079.
- Prices `PRICES_AND_POLICY` 1.1.0, run `e6602b5b-f34a-445a-b7d8-13aab77e5726`. CPI-U 12-month change September 2025 to September 2026 is 3.7173 percent, index 324.245 to 336.298 (`cpi-202509-ec9c2cce960d323014fdadf2`, `cpi-202609-753cdadbfa3126d47809921d`). Rank of overlapping 12-month percent changes 632 of 944; 631 of those changes are strictly below. Federal funds 3.75 percent per year (`h15-ff-202609-1dc5524ff1fff25bde21e6d6`), one-month change 0.1200 percentage points from 3.63 (`h15-ff-202608-444fc01fbedefbd330b95b4e`). Level rank 380 of 867. The 10-year yield 4.99 percent per year (`h15-cm10-202609-090ed7483b700db554e068cb`), one-month change 0.3100 percentage points from 4.68 (`h15-cm10-202608-c76c2839fc1d3a08cc7b0bf5`). Level rank 462 of 882. HICP is not an input and ends December 2025.
- Industrial production `INDUSTRIAL_PRODUCTION_ACTIVITY` 1.1.0, run `2b1d1c28-56e3-47ab-920a-b0aa175d9a1d`. Index 103.9506 in September 2026 (`g17-202609-fa559535da3f00f4c368ba1c`) from 101.6680 in September 2025 (`g17-202509-2187ff7c019c25026718e60a`). 12-month percent change 2.2452. Rank of overlapping 12-month percent changes 546 of 1281. This is production, not GDP.
- Credit `CREDIT_STANDARDS_AND_VOLUMES` 1.0.0, run `5894b7a4-98e1-40c2-a503-b8e19cb77281`, evaluation 7 October 2026. SLOOS net tightening 0.0 for the quarter starting 1 July 2026 (`sloos-202607-f0aa32b315708b9091d3fa39`), prior quarter 8.1 (`sloos-202604-af51d0517cd479f5695baadf`), difference -8.1 percentage points. Bank credit 19948526.8 millions of dollars for the week of 7 October 2026 (`h8-20261007-e947103c6bee7f448244b806`), versus 18791290.7 on 8 October 2025 (`h8-20251008-e40a43a1bac7214b539242ec`). The 52-week change is 1157236.1 millions of dollars. The survey share is not converted into dollars.

Synthesis `MACRO_READING_SYNTHESIS` 1.0.0, run `d8ec09f0-719e-4b9f-ab88-772ea1c9ae8d`. The reading is internal. Labour, prices, production, and credit stay separate. No composite score is calculated. Agreement: unemployment, payrolls, CPI-U, federal funds, the 10-year yield, and industrial production share September 2026. A shared month is not a cause. Divergence: job openings and the joint labour month are August 2026, SLOOS is the quarter starting 1 July 2026, and bank credit is the week of 7 October 2026. The stored changes do not share one sign. Euro-area HICP is excluded and ends in December 2025. Job openings, the joint labour month, and SLOOS are behind September 2026. Bank credit on 7 October 2026 is later than the monthly readings.

A pytest run reported 362 passed while the registry import pointed at `credit_standards_and_volumes.py`. That figure belongs to the renamed-module tree, which is not this baseline. The run recorded for this baseline is in the ETF section below. GitHub Actions has not run. This session did not repeat the signed-in browser check.

**Last updated:** 23 October 2026, ETF intelligence tip merged into the macro baseline  
**Parent:** `0cf8d32` on `work/aqil-autonomous-build`, merged with `4929d96` on `work/aqil-etf-intelligence`  
**Checkpoint:** local only. Not pushed. Production, hosted migrations and Saxo authorisation stay unchanged.

## ETF intelligence merged into the macro baseline, 23 October 2026

Risk class R2. `work/aqil-etf-intelligence` at `4929d9662e52c48e26416916d758e9422af412fb` was merged into `work/aqil-autonomous-build` at `0cf8d3213abfef620d544218825eb1f9ac0d7310`. Merge-base `edea3a0c495c113ffb9052228805b555bf5c48a7`. Nothing was pushed. The preserved database `postgres` on port 55432 was not written and was not reset. Hosted Supabase was not migrated. `supabase db push` was not run. Migration `20261024120000_etf_instruments.sql` was not applied to `postgres`. Fixture VWRA rows were not copied into `instruments`. Macro code was not pointed at `instruments`. ETF code was not pointed at `research.economic_observations`.

Conflicts were only `apps/web/package.json` and this handover. `docs/07_BUILD_BACKLOG.csv` merged without a conflict marker. `.github/workflows/ci.yml` came from the ETF tip and adds `npm run test:etf` on the web job. `.cursor/permissions.json` came from the ETF tip and was kept.

`apps/web/package.json` keeps the macro `test:sourced-updates` entry for `present-prospective-assessment.test.ts` and the ETF `test:etf` script.

Three reading commits were outside both tips before the integration merge. `git merge-base --is-ancestor` exited 1 for each against `0cf8d32` and `4929d96`. They were not cherry-picked into `4c2f14b`. Later commits merged them back in. `c82c697` restored the integration-commit text, `0094984` put the credit rename and labour determinism lines back, and `e18619d` reverted `0094984`. Those three changes are not in the baseline files.

- `work/read-credit` `e3e9906da73332cdbb0455fd33d429fd6d27da98`. Credit module rename. Merged as `0246277`, reverted as `5a6fc02`, reapplied as `2a12389`, and put back again by `0094984`. `e18619d` reverted that last commit. The module on this baseline is `credit_standards_volumes.py`.
- `work/read-labour` `591f7ac9e8a65112b17a0aae8f1c5824f0d24bfb`. It touches labour tests the macro tip also edits. Merged as `f70e320`, reverted as `ddd753d`, and reapplied as `b63cdf0`. `c82c697` removed those determinism lines from `workers/research/tests/test_labour_market.py`, and `e18619d` keeps them out.
- `work/fwd-evidence` `df8b8aadc3474ce7d27845d54203191fc3a101b8`. It touches prospective-assessment TypeScript files the macro tip continued. Merged as `24cbf72`. Those three TypeScript files match `4c2f14b`.

`work/fwd-snapshot` `fedbc19`, merged as `c4e57e4`, is not one of those three. It remains. It copies observation ids and values into the prospective assessment capture.

The research CI job is not verified. `docs/07_ROADMAP_AND_GATES.md` still marks the Python research worker scaffold as verified because of the CI research job. The operating baseline does not claim that this tip's research job is verified, so that roadmap section was not rewritten. AQ-002 no longer calls the job verified.

Checks this session, on the disposable database only:

- `npm run test:research` prepares `aqil_research_test` with `scripts/prepare-research-test-db.ps1` and does not reset database `postgres`. One run, while a credit rename was briefly on the branch, stopped at collection with 33 import errors. The run on this tree was 358 passed. That includes `test_schema_contracts.py` (6) and the ETF package tests. `ruff check` then reported 4 existing line-length errors in `test_industrial_production_activity.py`, `test_labour_market.py`, and `test_prices_and_policy.py`. `ruff format --check` reported 8 files that would be reformatted. Those format findings were already present and were not rewritten. The PowerShell script does not fail the npm exit code when ruff fails. GitHub Actions has not run. This is not a green research CI job.
- `npm run test:etf` passed 2.
- `uv run pytest tests/etf tests/test_etf_share_class_contract.py` passed 60. Those tests do not open a database.

Not run: GitHub Actions, `npm run test:db`, pgTAP, a browser session, `supabase db push`, and any write to preserved `postgres` or to `aqil_etf`. Migration `20261024120000_etf_instruments.sql` was not applied. The isolation guard in `test_database.py` was not weakened. An uncommitted edit that would have allowed a development-database insert was discarded and was not committed.

**Last updated:** 23 October 2026, internal macro synthesis on Evidence  
**Parent:** `77b51d4` on `work/aqil-autonomous-build`  
**Checkpoint:** local only. Not pushed. Production, hosted migrations and Saxo authorisation stay unchanged.

## Internal macro synthesis on Evidence, 23 October 2026

Risk class R2. The reading shown on Evidence is run `1049ea65-03de-4072-be8c-1f0b3108a1c1`, method `MACRO_READING_SYNTHESIS` 1.0.0. `publication_allowed` is false. It reads the stored 1.1.0 labour run `5f012de3-67e3-4877-88d9-5b8804ce3e78`, prices run `c1e49875-be03-4749-9148-e25df01905f2`, and industrial-production run `63ed1907-0f36-44d3-8ef8-f79c2e59e653`, plus credit 1.0.0 run `62425957-93fe-4b0c-af39-0829059591ce`. Earlier synthesis rows were not deleted.

Agreement: unemployment, payrolls, CPI-U, federal funds, the 10-year yield, and industrial production share September 2026. A shared month is not a cause. Divergence: job openings and the joint labour month are August 2026, SLOOS is the quarter starting 1 July 2026, and bank credit is the week of 7 October 2026. The stored changes do not share one sign, and the windows are not the same length. Euro-area HICP is excluded and ends in December 2025. No composite score, funds-minus-yield spread, real rate, or GDP figure is calculated.

Live counts on database `postgres` were unchanged: unemployment 44, CPI-U 956, payrolls 1053, job openings 309, industrial production 1293, bank credit 2806, federal funds 867, 10-year yield 882, HICP 348, SLOOS 146. Publications remain 12 Employment Situation, 12 CPI, 15 Board, and 3 ECB. Future BLS calendar rows remain 27. Research runs are 20.

Re-checked after that append: research pytest on `aqil_research_test` was 294 passed. Web presentation tests were 19 passed. Typecheck passed. Lint passed with the existing unused `_searchParams` warning. Token check passed. Production build passed. pgTAP was not run. GitHub Actions has not run. Signed-in Evidence at `http://localhost:3000/research` showed “The reading is internal” and the September 2026 agreement, on a desktop width and at 390 pixels with no horizontal overflow. Today still shows sourced publications, the 44-month unemployment series, and the next confirmed release. It does not show the macro reading.

## Prospective assessment integration, 23 October 2026

Risk class R2. Four local branches merged in order onto `work/aqil-autonomous-build` from `edea3a0`, with no conflicts: method `d381e76`, snapshot `ba4f4ae`, hypothesis `67aecc8`, Evidence `6f555f2`. The registry already constructed the current labour, prices, and industrial-production classes, which report `1.1.0`. Credit remains `1.0.0`. Sahm remains `1.0.1`. `MACRO_CONDITIONS_PANEL` remains `1.0.0`. `publication_allowed` was not opened.

Version 1.1.0 ranks overlapping 12-month percent changes for payrolls, CPI-U, and industrial production. Unemployment, job openings, the federal funds rate, and the 10-year yield keep a rank of the level, and the stored copy names the series. The historical distribution uses today's revised file. October 2025 was not interpolated. No HICP month was added. The price method does not take HICP as an input.

`supabase/migrations/20261023120000_prospective_assessments.sql` was applied to local Postgres at `127.0.0.1:55432`, database `postgres`, because `research.prospective_assessments` was absent. Nothing was dropped. The hosted project was not changed. pgTAP was not run. `scripts/prepare-research-test-db.ps1` then dropped and recreated only `aqil_research_test`.

Queried on database `postgres` after that pytest. Live counts were unchanged: unemployment 44, CPI-U 956, payrolls 1053, job openings 309, industrial production 1293, bank credit 2806, federal funds 867, 10-year yield 882, HICP 348, SLOOS 146. Research runs are now 17. The earlier 1.0.0 labour, prices, and industrial-production runs remain two each. Credit 1.0.0 is now three, including new run `62425957-93fe-4b0c-af39-0829059591ce`. The two `MACRO_READING_SYNTHESIS` 1.0.0 runs remain, including `ce6eb7e8-7fa1-4a5e-b603-218cdc466e23`. Every new run has `publication_allowed` false.

Stored 1.1.0 narratives, evaluation month 1 September 2026:

- Labour run `5f012de3-67e3-4877-88d9-5b8804ce3e78`. Payrolls (`bls.ce.CES0000000001`) were 159044 thousands. The 12-month change from 1 September 2025 (158548 thousands) is 496 thousands (0.31 percent). The rank of overlapping 12-month percent changes is 237 of 1041. Unemployment stays a level rank, 26 of 44. Job openings stay a level rank, 233 of 309, latest stored month 1 August 2026.
- Prices run `c1e49875-be03-4749-9148-e25df01905f2`. CPI-U (`bls.cu.CUSR0000SA0`) 12-month percent change from 1 September 2025 to 1 September 2026 is 3.7173 percent, index 324.245 to 336.298. The rank of overlapping 12-month percent changes is 632 of 944. The change uses those two endpoints only. Federal funds stay a level rank, 380 of 867. The 10-year yield stays a level rank, 462 of 882.
- Industrial production run `63ed1907-0f36-44d3-8ef8-f79c2e59e653`. The index (`fed.g17.IP.B50001.S`) moved from 101.6680 on 1 September 2025 to 103.9506 on 1 September 2026. The 12-month percent change is 2.2452. The rank of overlapping 12-month percent changes is 546 of 1281. The change uses those two endpoints only.

One assessment row was inserted: `pa-09812e2a-f340-455d-a16c-794b14f511b0`. `lifecycle_status` is `not_qualified`. `horizon_months` is null. `publication_allowed` is false. `revision_class` is `latest_revised`. It cites the three 1.1.0 run ids above, copies 5404 observation ids and values, 5404 retrieval timestamps, and 5360 source-release timestamps. All 44 unemployment observations in that copy have no `source_release_at`. The capture note contains “not a reconstruction of dates before captured_at”. The stored reasons are no vintage panel, no identified mechanism, and the stored windows do not share one horizon. The uncertainty text states that no direction, probability, return, or recommendation is stated. An owner `UPDATE` was rejected: `research.prospective_assessments is append-only; UPDATE is not permitted`. The live row was not deleted. On `aqil_research_test`, the persistence tests reproduced the stored hashes and rejected update and delete. Those tests are inside the 294 passed.

Research pytest on `aqil_research_test` was 294 passed. Web presentation tests were 19 passed. Typecheck passed. Lint passed with the existing unused `_searchParams` warning. Token check passed. Production build passed. pgTAP was not run. GitHub Actions has not run.

Signed-in Evidence at `http://localhost:3000/research` showed “The reading is internal. No 6- or 12-month hypothesis qualified.” with the three reasons, the capture sentence, and publication closed. The desktop client width was 1265 pixels and did not overflow. At 390 pixels the section was 358 pixels wide and the page did not overflow. Today showed sourced publications, the unemployment series, and the next confirmed release. It did not show the assessment.

These files still cannot answer a historical-date query that excludes a later revision. That remains M1 acceptance item 3. Sahm stays ineligible through December 2026 because October 2025 is absent. Census stays blocked without a key.

## Prospective assessment lifecycle, 23 October 2026

Risk class R2. The live decision is `not_qualified`. No 6- or 12-month hypothesis qualifies: there is no vintage panel, no identified mechanism, and the stored windows do not share one horizon. `horizon_months` stays null. `publication_allowed` stays false. The capture note includes “not a reconstruction of dates before captured_at”. Evaluation is refused before the due date, when the outcome observation is missing, and when every available observation id was already inside the original snapshot. A `proposed_internal` row may be superseded only by a new payload that points at the earlier assessment id. The earlier row is not rewritten.

The migration, `registry.py`, the three reading methods, and `apps/web` were not edited. The preserved database was not opened. `npm run test:db` was not run. Full research pytest was not run. Web checks were not run.

`PYTHONPATH` was `workers/research/src`. `python -m pytest tests/test_prospective_lifecycle.py -q` was 12 passed. `ruff check` passed on the lifecycle module and its tests.

## ETF integration, 23 October 2026

The six domain branches were merged locally into `work/aqil-etf-intelligence`. Nothing was pushed. The preserved database `postgres` was not written and was not reset. `npm run test:db` was not run, because that script drops `aqil_pgtap_test` and recreates it from the `postgres` schema, which does not contain `instruments`.

`aqil_etf.instruments` still has zero rows. A share class was not inserted. `instruments.sub_funds` requires a legal name and a three-letter base currency, and neither has a permitted citation. The in-memory catalogue has 39 unverified exposure slots. The only stored ISIN is `IE00BK5BQT80`, with ticker `VWRA`, and that pair is an internal anchor, not a permitted issuer citation. Costs, holdings, fund returns, and benchmark returns stay unavailable. Holdings are not fetched when the rights gate is prohibited or unknown. The anchor quality assessment is UNKNOWN across identity, structure, cost, benchmark, holdings, scale, and performance. There is no rank. Investor fit is UNKNOWN and is not personal advice.

Signed-in `/explore` now reads only local database `aqil_etf`. With no stored share class it shows that empty state. ETF research is not broker holdings and not personal advice. Today, Evidence, and My Wealth were not redesigned. A signed-in browser check was not run: this worktree has no web env file. Typecheck passed. Lint passed with the existing unused `_searchParams` warning. Token check passed. `npm run test:etf` passed 2. Direct pgTAP of `etf_instruments.test.sql` on `aqil_pgtap_test` passed 16. Research pytest of the etf package passed 60. Ruff check and format check passed. GitHub Actions has not run. This is not Verified.

## ETF Phase A, 23 October 2026

Branch `work/aqil-etf-intelligence` was created from committed HEAD `edea3a0` on `work/aqil-autonomous-build`. The worktree is `C:\Users\gamer\aqil-etf-intelligence`. Untracked files on the integration tree were not copied. Sibling macro and reading worktrees were not edited. `/explore` was not mounted. The six domain agents were not started.

The preserved database `postgres` on port 55432 was not reset and was not migrated. Its live observation count stayed 8704 before and after. A new local database `aqil_etf` received `supabase/migrations/20261024120000_etf_instruments.sql` only. Schema `instruments` is not on `postgres`. The same migration was applied to disposable database `aqil_pgtap_test`, and the `pgtap` extension was created there because it was available but not installed. The isolation marker remained `disposable-pgtap-test`. `npm run test:db` was not run, because that path recreates the disposable database from `postgres` and this migration is not on `postgres`.

`supabase/tests/database/etf_instruments.test.sql` passed 16 tests on `aqil_pgtap_test`. `workers/research/tests/test_etf_share_class_contract.py` passed 4. Ruff check and format check passed on the ETF package and that test. GitHub Actions has not run. This is not Verified.

Nine rights fragments were added under `docs/sources/etf/fragments/`. None has `automated_access=permitted`. `vanguard_uk_vwra_holdings` and `ishares_ucits_holdings` stay on their existing prohibited rows in `SOURCE_RIGHTS.csv`, which was not edited. TER, AUM, holdings, spreads, NAV, fund returns, and benchmark returns stay unavailable. No collector was built.

## Four internal readings, 23 October 2026

The prices correction `59edd3c` was already committed on `work/read-prices` and merged as `c8a148c`. It keeps federal funds and the 10-year yield as separate levels, does not calculate a real rate, does not take HICP as an input, and fails a window whose endpoint is missing. The four methods are registered at 1.0.0. Sahm, period-level change, SLOOS C&I, Census, and `MACRO_CONDITIONS_PANEL` 1.0.0 were not edited.

Queried on `postgresql://research_worker:research_worker@127.0.0.1:55432/postgres` after the disposable research tests. Database name `postgres`. Live counts were unchanged: unemployment 44, CPI-U 956, payrolls 1053, job openings 309, industrial production 1293, bank credit 2806, federal funds 867, 10-year yield 882, HICP 348, SLOOS 146. October 2025 is still absent for unemployment and CPI-U. HICP still ends 1 December 2025. Job openings still end 1 August 2026. Both H.15 series still have seasonal adjustment `unknown`. Research runs are now 13. `publication_allowed` is false on every new run. The database was not reset.

Evidence shows the later synthesis, run `ce6eb7e8-7fa1-4a5e-b603-218cdc466e23`, executed 23 October 2026 01:27 UTC. An earlier append at 01:01 UTC remains. It used the previous prices field name and the same CPI-U 12-month change, 3.7173 percent. It was not deleted.

Signed-in Evidence at `http://localhost:3000/research` showed the internal macro reading on a desktop width and at 390px. The 390px section did not widen the page. Today did not show the reading. Research pytest on `aqil_research_test` was 273 passed. Presentation tests were 15 passed. Typecheck passed. Lint passed with the existing unused `_searchParams` warning. Token check passed. Production build passed. pgTAP was not run. GitHub Actions has not run.

A later conditional forward reading still cannot treat these files as a vintage panel, fill October 2025, run Sahm through December 2026, or satisfy `MACRO_CONDITIONS_PANEL` 1.0.0 while Census is absent. The next milestone remains M1 acceptance item 3: a historical-date query that excludes a later revision.

## Eight stored series, 23 October 2026

Docker Desktop was not running, so port 55432 had no listener. Starting Docker brought the existing container `supabase_db_ojvswermsbbaltjohqph` back as healthy. The database was not reset. Before ingest it held 44 live unemployment observations, 146 live SLOOS observations, 12 Employment Situation publications, 12 CPI publications, 15 Board press publications, 3 ECB press publications, 27 future BLS calendar rows, 87 fixture observations and 3 research runs. No advisory lock was held.

The first live pass stored seven series and refused CPI-U. `download.bls.gov` returned HTTP 406 when the CPI client sent `Accept: text/plain`. The client now sends only the existing BLS user agent, matching the payroll client. The retry stored 956 CPI-U months. A second pass of all eight sources inserted 0 rows.

Stored live rows, all `latest_revised`, queried on the preserved database:

| Dataset | Count | Span | Unit | Adjustment |
| --- | --- | --- | --- | --- |
| `bls.cu.CUSR0000SA0` | 956 | January 1947–September 2026 | 1982–84=100 | seasonally adjusted |
| `bls.ce.CES0000000001` | 1053 | January 1939–September 2026 | thousands | seasonally adjusted |
| `bls.jt.JTS000000000000000JOL` | 309 | December 2000–August 2026 | thousands | seasonally adjusted |
| `fed.g17.IP.B50001.S` | 1293 | January 1919–September 2026 | index, 2017=100 | seasonally adjusted |
| `fed.h8.B1001NCBA` | 2806 | 3 January 1973–7 October 2026 | millions of US dollars | seasonally adjusted, weekly |
| `fed.h15.RIFSPFF_N.M` | 867 | July 1954–September 2026 | percent per year | not stated by the file |
| `fed.h15.RIFLGFCY10_N.M` | 882 | April 1953–September 2026 | percent per year | not stated by the file |
| `ecb.icp.M.U2.Y.000000.3.INX` | 348 | January 1997–December 2025 | index, 2015=100 | seasonally adjusted |

Inside those spans, the only missing months are October 2025 for CPI-U and for the unemployment rate. Payrolls include October 2025. Job openings include October 2025 and stop at August 2026. Euro-area HICP includes October 2025 and the stored file ends in December 2025; 2026 months were not in the response and were not invented. Bank credit has no gap longer than seven days. None of these files is a vintage panel. The web tree was not changed. `npm run test:db` was not run because no migration was added. Research pytest on `aqil_research_test` was 253 passed. `ruff check` passed on the files edited for this ingest. `ruff format --check` on the whole tree still fails on five files that were already unformatted, including `collect_bls_calendar.py`, `build_macro_conditions.py`, `macro_conditions.py` and `orchestrate.py`. `tests/test_ecb_sdw.py` was reformatted. GitHub Actions has not run.

## Method eligibility, 22 October 2026

Checkpoint `0d59cf4` records the Census key gate and the stored SLOOS move from 8.1 percent to 0.0 percent.

October 2025 is a permanent CPS absence, not an outstanding release. The Sahm formula is unchanged. Evaluation months from October 2025 through December 2026 include that absence and are permanently invalid. September 2025 can be a complete historical window, but it is not treated as the current month. January 2027 is the next evaluation month that excludes October 2025. It stays ineligible until the real observations through that month exist. Nothing is interpolated.

A Census response with one vintage of the prior month is insufficient for the initial-versus-revised comparison. Successive official releases must be stored as separate vintages. Historical vintages are not fabricated. The API key is still absent, and the endpoint was not called again.

Evidence now counts the stored latest-revised SLOOS quarters: 146 quarters, 71 net tightening, 68 net easing and 7 zero. The latest 0.0 percent share is at or below 75 of those 146 quarters. A later quarter above or below zero would replace the balanced reading. Those counts are not a point-in-time history and not a probability. The publication gate stays closed: the orchestrator keeps `publication_allowed` false, the file is not a vintage panel, claim verification is incomplete, and the method has no historical evaluation or human publication approval. Signed-in Today names October 2025 as permanently missing. Research pytest was 188 passed. Web presentation tests were 12 passed. Typecheck, lint and the production build passed. Lint still warns about the existing unused `_searchParams`.

No additional method was executed. Period-level change remains an interface demonstration. Macro-conditions still lacks a sufficient Sahm window and any Census observations.

## Census blocker and multi-signal readiness, 22 October 2026

Census advance durable goods remains blocked. A keyless request to both `https://api.census.gov/data/timeseries/eits/m3/adv` and the current dataset `https://api.census.gov/data/timeseries/eits/advm3` returned HTTP 302 to `https://api.census.gov/data/missing_key.html`. Census states that every Data API query requires a key. `CENSUS_API_KEY` is absent from the shell and from `apps/web/.env.local`. No Census observations were stored. The client now refuses the call before any request when the key is missing. The `advm3` dataset page lists vintage as not applicable, so one response would be the current series, not a historical vintage panel. The method's initial-versus-revised comparison stays unavailable until a later release is stored as a second vintage.

Founder action, and then stop: request and activate a free key at `https://api.census.gov/data/key_signup.html`, set `CENSUS_API_KEY` in the local environment, and do not commit it. The collection parameters remain category `MDM`, data type `NO`, seasonally adjusted, geography US.

No second production method was run. `PERIOD_LEVEL_CHANGE` describes itself as an interface demonstration, not a production investment model, so it was not used. The Sahm window is still insufficient because October 2025 unemployment was not published. `MACRO_CONDITIONS_PANEL` 1.0.0 requires labour, SLOOS and Census to be sufficient together. SLOOS is sufficient for the quarter starting 1 July 2026. Labour is not. Census is absent. The panel was not executed. Publication headlines were not treated as method inputs.

Evidence now separates the method result from the stored movement. The quarter starting 1 April 2026 is 8.1 percent. The quarter starting 1 July 2026 is 0.0 percent. The calculated difference is 8.1 percentage points lower. That arithmetic is not the method calculation, not a forecast, and not an investment conclusion. Publication remains closed.

## First verified macro reading, 22 October 2026

Census advance durable-goods orders were not usable. The later section records that both the old path and `advm3` require a key. No Census observations were stored. The macro-conditions method needs Census as well as labour and SLOOS, so it was not run. The unemployment series still has the October 2025 gap, so Sahm was not forced through.

The Senior Loan Officer Opinion Survey method `SLOOS_CIL_LENDING_STANDARDS` 1.0.0 was selected. It needs one quarterly net-tightening observation. The old JSON address `https://www.federalreserve.gov/data/sloos/sloos-series.json` returned HTTP 404. The Board package `https://www.federalreserve.gov/datadownload/Output.aspx?rel=SLOOS&filetype=zip` returned HTTP 200. Series `SUBLPDCILS_N.Q` is the net percentage of domestic banks tightening standards for commercial and industrial loans to large and middle-market firms.

The development database, which was not reset, now holds 146 live observations for dataset `fed.sloos.SUBLPDCILS_N.Q`, source `federal_reserve_sloos_cil`, provider `federal_reserve_board`. The span is 1990-Q2 through 2026-Q3 with no missing quarter. Retrieval was 21 October 2026, 22:19 UTC, host `www.federalreserve.gov`. Provenance is `latest_revised`. The package does not carry a historical vintage for each quarter, so this is not a point-in-time reconstruction. An unchanged value keeps its stored identity. A changed value is a new observation and a new research run. A second collect on the same file stored 0 new rows and did not add a second run.

Run `fe62b229-c3ac-47b0-b8fd-d3c7982653b0`, payload hash `62829dc9bdf860e68f19ceeb175534034c4b3fcb5fd08c5c6efaa6c83a4ee26d`, cites observation `sloos-202607-f0aa32b315708b9091d3fa39`. The quarter starting 1 July 2026 has a net tightening share of 0.0 percent. That means the share of banks reporting tighter standards equals the share reporting easier standards. It does not mean every bank left standards unchanged. The previous stored quarter, starting 1 April 2026, is 8.1 percent. That comparison is another stored observation, not a method forecast. `publication_allowed` is false. `investment_implication` is `no_action`. The causal statement is that no causal mechanism is asserted. Intelligence Evidence shows the reading. Today does not. The 44 unemployment observations, 12 Employment Situation rows, 12 CPI rows, 15 Board press rows, 3 ECB rows and 27 future BLS calendar rows remained.

Research pytest on `aqil_research_test` was 183 passed after the Census key-gate test was added. One amendment test used a fixed content hash and failed on a second run of the disposable database; it now uses a fresh hash and scopes its assertion to its own retrieval. Web presentation tests were 12 passed. Typecheck passed. Production build passed. Ruff was clean on the files edited after the SLOOS commit. `ruff format --check` on the whole tree was not made green. GitHub Actions has not run. Signed-in Evidence showed the 8.1 to 0.0 movement and the closed publication gate. Signed-in Today did not show the reading.

## Test isolation incident, 22 October 2026

`uv run pytest` ran the integration tests against the development database. Those tests called `research_database_url_or_local_default()`. With `RESEARCH_DATABASE_URL` unset, that function opens `postgresql://research_worker@127.0.0.1:55432/postgres` and `research_connection()` commits on success. The suite therefore wrote fixture observations, two research runs, and a frozen synthetic forward bundle into the database that holds the live BLS and Federal Reserve rows.

The rows were not deleted. `research.economic_observations`, `research.research_runs` and `forward.forward_scenarios` are append-only or frozen. Safe options, none of which were applied: leave the rows and keep them out of the product screens; a later founder-approved presentation flag that does not rewrite hashes; do not reset the database, because a reset would destroy the live series. Disabling the immutability triggers to delete rows is not a safe option.

What remains in the development database:

- Genuine: 44 live unemployment observations on retrieval `acb7a909-2650-4d50-8fc2-89be29aff7aa`; 12 Employment Situation publications; 15 Federal Reserve press publications; 27 future `bls_ics_schedule` calendar rows. CPI added 12 further live publications after the incident.
- Fixture observations: 87 rows with `collection_mode = 'fixture'`. Some pre-dated the incident. The suite increased that count. They are not shown on Today because the series loader requires `collection_mode = 'live'`.
- Research runs: `immutability-run-129d829287f7` (`completed`) and `workflow-e2e-1792616393` (`completed_insufficient`). Neither is rendered as an Aqil conclusion.
- Synthetic forward rows: `event:fixture:msft:fy26q2:earnings` (`synthetic_demonstration`, locator `synthetic://`) and one frozen scenario. Upcoming requires `bls_ics_schedule` and an `https://www.bls.gov/` locator, so the earnings fixture is not listed.
- Test-generated calendar row that used a real-looking class: `event:verified:fed:fomc:2025-09-17`, evidence class `verified_schedule`, scheduled 17 September 2025. It is in the past and its source id is not `bls_ics_schedule`, so Upcoming does not list it.

`test_collect_and_run_fixture_e2e` returned `completed_insufficient` because the shared store's latest month was the live September 2026 observation, and the October 2025 gap makes that Sahm window incomplete. The fallback flag does not choose an earlier month, and the gate correctly refused a sufficient result. On the disposable database `aqil_research_test` the same test passes. That was contamination, not a weaker gate.

Research tests now require `AQIL_RESEARCH_TEST_DATABASE_URL`, accept only the loopback database `aqil_research_test`, and check `research.test_isolation_marker` before any write. A missing URL, the development URL, a hosted host, or the database name `postgres` fails before connecting. `npm run test:research` prepares that disposable database from the schema only. It does not reset the database named `postgres`.

`npm run test:db` no longer calls `supabase db reset`. It requires `AQIL_PGTAP_DATABASE_URL` for loopback database `aqil_pgtap_test`, rejects the database named `postgres`, hosted hosts, and ports 5432 and 6543, then checks `research.pgtap_isolation_marker` before pgTAP. A deliberate development URL and a hosted URL failed before any drop. The suite on `aqil_pgtap_test` was 10 files, 159 tests, pass. Development live observations remained 44. CI may still reset its own ephemeral database.

## ECB policy coverage, 22 October 2026

The ECB press RSS `https://www.ecb.europa.eu/rss/press.html` returned HTTP 200 `application/rss+xml`. The file also contains speeches and interviews. Those paths are not stored. The copyright page permits free use of information taken directly from the site when it is reproduced accurately and the ECB is cited. Working papers and occasional papers still need written authorisation and are not in this selection.

The first refresh stored 3 live items, retrieved 21 October 2026, 21:46 UTC:

- “Meeting of 9-10 September 2026”, published 8 October 2026, 11:30 UTC, `https://www.ecb.europa.eu/press/accounts/2026/html/ecb.mg261008~a10153d090.en.html`
- “Results of the September 2026 survey on credit terms and conditions in euro-denominated securities financing and OTC derivatives markets (SESFOD)”, published 7 October 2026, 08:00 UTC
- “Decisions taken by the Governing Council of the ECB (in addition to decisions setting interest rates)”, published 2 October 2026, 13:00 UTC

Signed-in Today showed 42 sourced publications. The 8 October account is under “Published in the last 14 days”, labelled European Central Bank. Evidence shows source id `ecb_monetary_press`, retrieval `bc4f2855-9ae4-4e8b-b302-31c8f49b9d90`, and the official accounts URL. The speech “Diagnostic Challenges for ECB Monetary Policy” is not shown. The synthetic Microsoft fixture is not shown. The second refresh stored 0 new ECB rows. `correction_of` is empty because none of these pages changed. A later hash for the same official URL becomes a new row linked to the earlier row. The earlier row is not overwritten. No publisher correction was present in this feed.

## Source coverage

| Source | State |
| --- | --- |
| BLS Employment Situation publications | Connected and operational. 12 live rows. |
| BLS CPI publications | Connected and operational. 12 live rows. |
| BLS unemployment observations | Connected and operational. 44 live observations, January 2023 to September 2026. October 2025 is absent. |
| Federal Reserve monetary-policy press | Connected and operational. 15 live rows. |
| BLS release calendar | Connected and operational. 27 future confirmed rows. |
| ECB monetary-policy press | Connected and operational. 3 live rows. Speeches and interviews excluded. |
| SLOOS C&I standards | Connected. 146 live observations, 1990-Q2 to 2026-Q3. One unpublished reading for 2026-Q3 at 0.0 percent. Latest revised file, not a vintage panel. |
| Census advance durable-goods orders | Blocked. Both the old and current API paths require a Census key. No observations stored. Vintage is not supplied by one response. |
| BEA news schedule | Rights row exists. No machine-readable feed was identified. RSS returned HTTP 404. |
| FRED ALFRED UNRATE | Restricted. API terms prohibit retention. |
| Near-term forward spread | Blocked. Formula and input are unresolved. |
| Vanguard and iShares holdings | Restricted. Automated collection prohibited. |

## Readiness for interpretation

One internal SLOOS reading is now stored and shown on Intelligence Evidence. It is not published and it is not an investment conclusion. The unemployment method still has 44 live observations, but the latest month is not a sufficient Sahm window because October 2025 was not published. Census advance orders and the macro-conditions method have no live observations. Publication rows remain sourced records, not method inputs.

The next demonstration needs a Census API key before advance durable-goods orders can be collected. Do not add a forecast, and do not treat the SLOOS file as a historical vintage panel.

Recurring releases should later be shown as compact trends and comparable series. That presentation was not built.

Research pytest on `aqil_research_test` was 178 passed. Web presentation tests were 11 passed. Typecheck passed. ESLint reported the existing unused-argument warning in `today-story-tangent-path.ts`. GitHub Actions has not run.

## CPI coverage and refresh, 22 October 2026

The Consumer Price Index Atom feed `https://www.bls.gov/feed/cpi.rss` returned HTTP 200. It is registered as `bls_cpi_archive` / `bls.cpi.archive` under the existing BLS terms. The first refresh stored 12 releases. The newest is “CPI for all items increases 0.6% in September; gasoline rises”, published 14 October 2026, 11:50 UTC, at `https://www.bls.gov/news.release/archives/cpi_10142026.htm`, retrieved 21 October 2026, 21:27 UTC. The second refresh stored 0 new CPI rows. Signed-in Today places that September CPI release under “Published in the last 14 days”, with the 13 October Board minutes. Evidence shows `bls_cpi_archive` and the BLS archive URL. The 44 live observations and 27 BLS calendar rows remained.

An identical publication is unchanged. A changed title or link would be a new content hash and a new row. `correction_of` stays empty until a publisher identifies a correction. No correction was present in these feeds. BLS publication fetches retry transport failures and HTTP 5xx up to three times and do not retry HTTP 4xx. The Federal Reserve client now follows the same rule. The unemployment series stays on a weekly skip. Each source commits alone. A held advisory lock makes a second refresh return without writing.

`npm run research:status` reads the latest `research.refresh_runs` row per source and does not poll. Production scheduling, not activated: one daily run of `npm run research:refresh` on a private operator host that can reach the research database, with `npm run research:status` for the result. No Windows task, Vercel cron, hosted migration, or new paid service. Founder approval is required before any of those are turned on.

Recurring releases should later be shown as compact trends and comparable series rather than a long list of release cards. That redesign was not implemented.

The research suite on `aqil_research_test` was 176 passed. Web presentation tests were 11 passed. Typecheck passed. Production build passed. ESLint reported one existing unused-argument warning in `today-story-tangent-path.ts`. `ruff format --check` still fails on modules this sprint did not edit. GitHub Actions has not run.

## Repeatable refresh and a second source, 22 October 2026

`npm run research:refresh` is the one local entrypoint. It takes a Postgres advisory lock, polls each source in its own transaction, and writes one `research.refresh_runs` row per source. A failed source does not cancel the others. It does not install a Windows scheduled task. Cadence when someone runs it: Employment Situation publications, Federal Reserve monetary-policy press and the BLS calendar daily; the unemployment series weekly, and skipped when the last live retrieval is newer than seven days.

The first refresh stored 15 Federal Reserve press items from `https://www.federalreserve.gov/feeds/press_monetary.xml` (HTTP 200). Source `federal_reserve_monetary_press`, dataset `fed.press.monetary`. The newest is “Minutes of the Board's discount rate meetings on August 17, September 9, and September 16, 2026”, published 13 October 2026, 18:00 UTC, link `https://www.federalreserve.gov/newsevents/pressreleases/monetary20261013a.htm`, retrieved 21 October 2026, 20:58 UTC. The Board public-domain disclaimer is the rights basis, assessed 22 October 2026. A second refresh stored 0 new press items and left the 12 Employment Situation rows and 27 BLS calendar rows unchanged. The unemployment series was skipped as still fresh. The live series remains 44 observations, retrieval `acb7a909-2650-4d50-8fc2-89be29aff7aa`.

Signed-in Today puts only the 13 October Board minutes under “Published in the last 14 days”. The 2 October Employment Situation release is under “Earlier publications”. The historical series and the next confirmed BLS time, 28 October 2026, 10:00 Eastern Time, are separate. Evidence shows `federal_reserve_monetary_press` and the original Board URL. Upcoming lists 27 BLS calendar rows and does not show the synthetic earnings fixture. Exposures still says no authoritative exposure mapping has been retrieved. Desktop and a 390px Today view had no horizontal overflow. Primary navigation sat at the bottom on the narrow width.

The full research pytest run was pointed at the demonstration database. It appended fixture observations (36 to 87) and two `research.research_runs` rows, and it froze a synthetic forward scenario plus a past FOMC fixture event. Those scenario rows cannot be deleted. The 44 live observations, 12 BLS publications, 15 Board publications and 27 future BLS calendar rows remained. `test_collect_and_run_fixture_e2e` failed with `completed_insufficient`. `ruff format --check` still fails on files that were already unformatted. Web sourced-update tests: 9 passed. Typecheck passed. Production build passed. GitHub Actions has not run. Migration `20261022140000_research_refresh_runs.sql` was applied only to local port 55432.

The next holdings contract is still missing. Automated collection from Vanguard and iShares remains prohibited. A permitted holdings file, not a new scraper, is what Exposures needs before any mapping is shown.

## Sourced releases and confirmed calendar, 22 October 2026

The Employment Situation feed at `https://www.bls.gov/feed/empsit.rss` returns HTTP 403 to the default `python-httpx` agent and HTTP 200 to `AqilResearch/1.0`. That is the same registered source. The client now sends that name. Live ingest stored 12 sourced updates. The newest publication is 2 October 2026, 11:51 UTC, title “Both payroll employment (+29,000) and unemployment rate (4.2%) change little in September”, source `bls_employment_situation_archive`, retrieved 21 October 2026, 20:37 UTC. A second ingest reported `publications_outcome=unchanged`. Signed-in Today and Evidence showed the 12 releases, with the September release first. The historical series remains retrieval `acb7a909-2650-4d50-8fc2-89be29aff7aa`, 44 observations.

The official BLS iCalendar states start times with `TZID=US-Eastern`. Twenty-seven future confirmed entries were stored in the existing `forward.catalyst_events` table. Employment Situation is scheduled 6 November 2026, 08:30 Eastern Time, last verified 21 October 2026, 20:38 UTC. A second ingest stored 0 new calendar rows and refreshed the verification time. Entries with no clock time were not stored. Migration `20261022120000_catalyst_verification_update.sql` grants update of the verification and schedule columns only. It was applied on a disposable database at port 56532, where `research_writer` could update `last_verified_at` and could not update `title`, and anon could not read the table. The same file was then applied to the preserved database on port 55432. `npm run test:db` was not run. The 44 observations remained.

Signed-in Intelligence Upcoming listed those confirmed times. Desktop and a 390px Today view showed the releases and the series, with no horizontal overflow.

## Today acceptance, 21 October 2026

Signed-in Today at `http://localhost:3000/` showed the persisted retrieval `acb7a909-2650-4d50-8fc2-89be29aff7aa`. The panel read: 44 monthly observations, January 2023 to September 2026, latest observation September 2026 at 4.2 percent, October 2025 not published, retrieved 21 Oct 2026, 08:11 UTC. Source `bls_cps_unemployment_rate`, dataset `bls.ln.LNS14000000`. The sourced briefing said no sourced updates have been retrieved. The database still has that one live retrieval, 44 observations, and 0 `research.sourced_updates` rows. It was not reset.

Intelligence Upcoming says no validated catalyst date has been retrieved. Evidence says no sourced updates have been retrieved. Exposures says no authoritative exposure mapping has been retrieved. Learn is labelled an illustration. Desktop and a 390px viewport both showed the series, with primary navigation at the bottom on the narrow width. No horizontal overflow. The Cursor browser console reported hydration mismatches on `data-cursor-ref`. Those attributes are not in the application source.

SLOOS and Census advance-orders methods from `m6/research-methods` are now on this branch, including their rights-register rows. The freshness gate still blocks a partial live series fetch. Fixture collection is allowed only when `collection_mode` is `fixture`. The macro-conditions integration test rolls back, so it did not add fixture rows beside the live retrieval. Those methods are not rendered on Today.

M5 is not merged. Its calendar page loads a forward-horizon bundle that can be a fixture, which would replace the current sourced-date gate. Its migrations `20261018100000` and `20261018140000` sort before `20261018200000` and must not be applied in that order. The integration path is a later additive migration, after `20261021110000`, containing only the constraint changes and `forward.collection_runs`, followed by collectors that persist `verified_schedule` rows. Do not run `npm run test:db` until that work is ready to reset a disposable database. This preserved database stays as it is.

`my-wealth/portfolio-slice` is not merged. Its migration `20261018160000` would sort before the current wealth migrations, and its UI is an earlier slice beside the cockpit, journal and Deploy Capital already on this branch. `docs/consolidation-2026-10-18` would overwrite newer charter, roadmap and handover text. `auth/google-foundation` is patch-equivalent (`git cherry` marks all three commits `-`) and was not deleted. The Sahm worktree at `C:/Users/gamer/aqil-sahm` still shows a modified test file and was not touched. No remote branch was deleted and no pull request was closed.

## Consolidation, 21 October 2026

The audited HEAD was `2f8a353`. This note is the consolidation on that parent.

Live BLS series request window was 2023 through 2026. The response was HTTP 200, `REQUEST_SUCCEEDED`, 45 monthly points and no annual rows. Parsed usable observations: 44. `missing_months` had been `missing value for 2025-10-01` because the value is `-` with footnote code 9, "Data unavailable due to the 2025 lapse in appropriations." That is an official absence, not a pagination failure and not an unreleased month. September 2026 is the latest returned month. October 2026 is not yet due. The freshness gate still rejects a genuinely partial or stale payload. An officially unavailable month no longer sets `partial`. After the correction, the same live read is `partial=false` with 44 observations. October 2025 is not stored as a number.

Local Supabase now uses database port 55432, API port 55421, and shadow port 55420. Those ports sit outside the Windows exclusion 54253–54352. `npm run test:db` passed first: 10 files, 159 tests, on disposable local Postgres only. The live ingest then stored retrieval `acb7a909-2650-4d50-8fc2-89be29aff7aa` at `2026-10-21T08:11:51.888853Z`, HTTP 200, `REQUEST_SUCCEEDED`, window 2023–2026, 44 observations from January 2023 to September 2026. October 2025 has no row. Unit percent, latest revised, seasonally adjusted, monthly, observed, geography US. A second ingest reported `unchanged=44` and `new=0`. The database was not reset after that retrieval. Do not use `supabase test db --linked`.

The Employment Situation RSS still returns HTTP 403. The existing parser accepts RSS and Atom only, so the HTML archive was not scraped. `research.sourced_updates` has 0 rows. Today now also reads the latest live `research.economic_observations` retrieval and presents it as a historical monthly series, with the October 2025 gap named and nothing filled in. On 21 October 2026 the founder signed in through Cursor’s browser. Today showed the historical series: 44 observations from January 2023 to September 2026, October 2025 not published, retrieved 21 Oct 2026, 08:11 UTC. The sourced briefing remained empty. Intelligence showed no validated catalyst date.

`npm run test:db` on port 55432 passed: 10 files, 159 tests. BLS adapter tests: 11 passed. Series briefing tests: 2 passed. Sourced-update presentation tests: 4 passed. Web typecheck passed. GitHub Actions has not run. Do not reset this local database.

Branches retained: `m5/live-intelligence-coverage` is an ancestor of `m6/research-methods`. The M6 method code is integrated on development. The M5 calendar UI and both historical migrations are not. `research/employment-situation-2026-11` stays checked out at `C:/Users/gamer/aqil-sahm`. Its migration file matches development. The worktree status shows a modified test file whose blob equals HEAD `ff959c35a41d3ad57ac842c5bec9ed625bc55502`; it was not touched. `auth/google-foundation` is patch-equivalent and was not merged. `my-wealth/portfolio-slice` and `docs/consolidation-2026-10-18` were not merged. No remote branch was deleted. `apps/web/apps web.zip` is gitignored. It contains `.env.local`. The live `apps/web/.env.local` also exists. The zip was not opened for values and was not deleted.

## Today and Intelligence proof, 21 October 2026

The slice is not operational. No new source was added.

`npm run research:ingest` ran from the repo root against local Postgres `127.0.0.1:54322` as `research_worker`. It was a live attempt, not a fixture. The command printed `ingest_mode=live`, `bls_outcome=failed_fetch`, `received=0`, `new=0`, `unchanged=0`, `publications_outcome=failed_fetch`, and `Series fetch unusable; inspect provider payload`. It wrote no new `research.source_retrievals` row, so this run has no stored retrieval timestamp.

Queried as `research_worker` before `npm run test:db` reset the local database:

- `research.economic_observations`: 36, all on retrieval `1fedaa87-f3e8-411d-ae14-d488ee3a262e`. That retrieval is `collection_mode=fixture`, `source_id=bls_cps_unemployment_rate`, `retrieved_at=2025-06-01T12:00:00Z`, `recorded_at=2026-10-20T22:28:12Z`. New observations from this run: 0.
- `research.sourced_updates`: 0. No `source_id`, title, canonical URL, `published_at` or `retrieved_at` was stored.

A later non-persisting read of the same adapters, at `2026-10-20T22:59:01Z`, was not written to the database. The series call returned HTTP 200, BLS status `REQUEST_SUCCEEDED`, 44 observations and `partial=true`. The gate raised `feed freshness is interrupted; ingest blocked (no silent backfill)`. The Employment Situation feed returned `fetch_failed` / HTTP 403, with 0 drafts. Those figures are not stored observations.

Signed-in rendering was not verified. Opening `http://localhost:3000` stopped at `http://localhost:3000/login?error=signed_out&next=%2F` with the heading Sign in and the button Continue with Google. Google login was not completed. `/auth/saxo` was not opened. What signed-in Today and Intelligence show was not seen.

Checks on `d667781`: research pytest 40 passed, 0 failed; `test:wealth` 57 passed, 0 failed; `test:capital` 17 passed, 0 failed; `test:auth` 13 passed, 0 failed; `test:sourced-updates` 4 passed, 0 failed; `npx tsc --noEmit` passed; lint passed with 1 warning and 0 errors (`today-story-tangent-path.ts` unused `_searchParams`); `check:tokens` passed; `npm run build` passed. `npm run test:db` then reset the local database and passed 10 files, 159 tests. That reset was local only. Hosted Supabase was not migrated. Production scheduling was not turned on.

## Product acceptance, 21 October 2026

Signed-in routes were not opened. The agent browser was redirected to Google sign-in for `/`, and at 390px the primary links sit in the bottom bar. Privacy and terms remain public links. Saxo authorisation was not opened.

Unit and build checks on `f391d71`: `test:wealth` 57, `test:capital` 17, `test:benchmark` 14, `test:saxo` 42, `test:auth` 13, `test:learn` 6, `test:story` 4, research pytest 48 on the touched files, typecheck, lint, token check and production build all passed. `npm run test:db` did not run because Docker was not running. The last local database pass was 9 files and 134 tests.

Usable only after Google sign-in, and not yet confirmed in this browser: My Wealth from the saved Saxo snapshot, Deploy Capital policy, the investment journal, Learn, and the synthetic story. The benchmark and passive baseline are tested functions and are not on a page. The hosted token vault is unapplied. A process crash after Saxo rotates a refresh token still loses that token.

## 1. Repository

- Branch `work/aqil-autonomous-build` at `f391d71`. Sprint 3 is integrated: the manual journal is `3295686`, merged as `45eda97`, and the cashflow-matched passive baseline is `071fd28`. Do not push or deploy until the founder asks.
- Local branch housekeeping on 20 October 2026 removed integrated agent and milestone branches. `main` was not moved. Branches with unmerged commits were kept: `auth/google-foundation`, `docs/consolidation-2026-10-18`, `m5/live-intelligence-coverage`, `m6/research-methods`, `my-wealth/portfolio-slice` and `research/employment-situation-2026-11`. The Sahm worktree still has an uncommitted test edit.
- Phase 1 remains the parent checkpoint `85427dd`. The My Wealth cockpit rework is `2481fa8` on `work/my-wealth-cockpit`.
- Deploy Capital is `6d0328b` on `work/deploy-capital`, merged as `b7589e6`.
- The hosted token vault is `11853b0` on `work/saxo-token-vault`, merged as `d2179bb`.
- Production stays the existing Vercel deployment from GitHub `main`. It was not touched.
- Hosted Supabase `ojvswermsbbaltjohqph` still has five migrations. `20261018200000`, `20261018210000` and `20261020120000` are local only. Do not apply them without founder approval.
- One shared shell. Primary navigation is Today, My Wealth and Intelligence. Deploy capital is `/my-wealth/deploy`, not a fourth destination.
- My Wealth still reads the saved snapshot and does not call Saxo on load. The headline is the standard account value when it matches cash plus holdings. Open-position gain is Saxo's result since the positions were opened, not a period return.

## 2. Phase 1 completed

Accepted as the local foundation for current portfolio data, booked financial history and Saxo-reported historical performance.

- Saxo LIVE OAuth runs on localhost. Production Connect stays off.
- Holdings, balances and underlying lots are retrieved and kept.
- Source responses are encrypted local archive units. A later partial does not erase an earlier version.
- Historical acquisition can resume from the manifest. See the exception in section 4 before resuming aggregated amounts.
- My Wealth remains compatible with the current snapshot.
- Latest complete windows, checked by decrypting the local archive on 19 October 2026: 312 transactions, 628 nested bookings, 534 booking-report rows, 140 trade-report rows, 89 historical closed positions, 88 closed-position report rows, 501 account-value observations. Coverage begins 13 November 2024. The AllTime body includes Saxo's time-weighted block.

## 3. Where the local data is

All of this is gitignored under `apps/web/.local/`.

- `saxo-vault/` — encrypted OAuth session. This session did not refresh or replace it.
- `saxo-source/{owner}/live/manifest.bin` — encrypted acquisition manifest, 301 entries.
- `saxo-source/{owner}/live/units/` — 283 encrypted units.
- `saxo-portfolio/` — plaintext presentation snapshot for My Wealth. It has no OAuth token.
- `saxo-discovery/` — leftover plaintext discovery responses from the earlier catalogue.

Archive filenames use the owner id and, for an account balance, a 16-character hash. They do not contain account keys or tokens.

## 4. Incomplete, and why

Aggregated amounts: 16 of 24 monthly windows are latest-complete past the 50-row page. Those are November 2024 through July 2025, September 2025, and January through June 2026.

Eight windows still have the 50-row body as the latest complete marker:

- August 2025 stopped near 1,000 rows because the next page repeated rows already stored.
- October 2025 stopped near 1,000 rows on HTTP 429 `RateLimitExceeded`.
- July 2026 has a newer partial of 400 rows.
- November 2025, December 2025, August 2026, September 2026 and October 2026 have later partial versions with no additional rows. The earlier 50-row archives remain.

`historyAlreadyComplete` is true whenever a latest complete entry exists. A resume that trusts only that check will skip these eight. Keep every partial unit. Do not delete a 50-row version until a short final page has replaced it.

The QBTS NYSE/NASDAQ activity on 27 July 2026 is not fully reconciled between the historical position and the trade report. Do not include that disputed position in an independently calculated realised profit.

Money-weighted return was absent from the retrieved v4 performance response. Corporate-action events and chart history returned HTTP 403. Continuous daily instrument-level attribution is not validated. Two booking-report months contain exactly 50 rows, the old page size, so those two months should be rechecked before a hosted copy treats every booking-report window as fully paged. The accepted booking-report total remains 534 latest-complete rows.

## 5. What this session added

- My Wealth cockpit: standard account value and open-position or time-weighted result sit with cash, investment count, largest holding and connection. The Saxo account-value chart is full width only when at least two points exist.
- Deploy Capital can save an explicit investment policy for the signed-in user at `apps/web/.local/investment-policy/{userId}.json`. Targets must total 10,000 basis points. A blank budget stays unconfigured. A holding enters the class total only after the founder assigns its class. Reported cash remains investable cash. The example block stays labelled as made up. No order is sent. The hosted wealth tables are still not written.
- Hosted vault: `saxo_token_vault` and append-only `saxo_source_units` in unapplied migration `20261020120000_saxo_hosted_vault.sql`. Ciphertext is granted to `service_role` only. `rotateHostedTokens` claims a generation before calling Saxo; the loser does not refresh or persist. The local file vault is still the running store. Nothing in the OAuth routes was switched over, and no archive was copied.
- Review fixes: a thrown refresh or commit releases the vault claim. A one-unit top-up that integer gaps cannot assign stays in the unallocated amount. A foreign-currency buy is sized from the converted total, so per-unit rounding cannot spend more than the budget.
- `/my-wealth/journal` accepts manual entries and a CSV preview. Values appear only with a supplied price. Money-weighted return appears only when the cashflows solve. Time-weighted return stays unavailable without interim valuations. The benchmark comparison stays unavailable unless a series, foreign exchange and costs are supplied.
- Learn shows a labelled compounding illustration. The research page shows one synthetic story, with citations and a correction, when no founder insight is loaded. Research helpers fail closed on a stale feed, reject an incomplete method card, and collapse ten copies of one announcement into one cluster.

## 6. Tests this session

| Check | Result |
|---|---|
| `npm run test:capital` | 17 pass, 0 fail |
| `npm run test:wealth` | 33 pass, 0 fail, including 13 journal tests |
| `npm run test:learn` | 6 pass, 0 fail |
| `npm run test:story` | 4 pass, 0 fail |
| `npm run test:saxo` | 42 pass, 0 fail, including the hosted vault rotation tests |
| `npm run test:auth` | 13 pass, 0 fail |
| Research pytest | 24 pass, 0 fail, including schema contracts, feed freshness, method cards and event clusters |
| `npm run test:db` | pass. 9 files, 134 tests, including the journal and cross-user isolation files. Local disposable database only. Hosted Supabase was not changed |
| `npm run typecheck` | pass |
| `npm run lint` | pass |
| `npm run check:tokens` | pass, re-run 21 October 2026 |
| `npm run test:benchmark` | 14 pass, 0 fail, re-run 21 October 2026 |
| `npm run test:wealth` | 57 pass, 0 fail, re-run 21 October 2026 |
| `npm run build` | pass. `/my-wealth` and `/my-wealth/deploy` are in the build |
| Browser | Signed-out agent browser. `/my-wealth` and `/my-wealth/deploy` redirect to Google sign-in. At 390px the primary links sit in the bottom bar. Signed-in holdings were not opened. Saxo authorisation was not opened |
| `supabase test db` | Passed locally as `npm run test:db`: 89 tests, 0 failures. Not applied to the hosted project |

Node printed `MODULE_TYPELESS_PACKAGE_JSON` while loading the tests. That is an existing runtime notice. Do not add `"type": "module"` to silence it.

Not re-run on 21 October 2026: `test:research`, `test:db`, `build`, Playwright, and the signed-in browser. `test:auth` was re-run and passed.

## 7. Security and engineering

- No Saxo call, token refresh, hosted migration, push or production deployment was made.
- If the process dies after Saxo has rotated the refresh token and before the new ciphertext is stored, the claim stays `refreshing` and the new token is gone. The stored token is the previous one, which Saxo will reject. Recovery is a new localhost sign-in after the stuck row is set back to idle. The lost token cannot be reconstructed. A thrown error in a live process does release the claim. That path is tested. The crash path is not.
- The live Saxo application credential can still trade at Saxo. Aqil does not send trading requests.
- Plaintext discovery JSON remains on disk and is gitignored.
- Google sign-in behaviour was not changed. The agent browser had no session.

## 8. Still requires the founder

- Apply `20261018200000`, `20261018210000` and `20261020120000` only after a local `supabase test db` pass on those files.
- Decide when localhost OAuth should write the hosted vault instead of the file vault.
- Create a trading-disabled Saxo application before any hosted token is stored.
- Do not enable production Saxo LIVE.
- Do not copy `apps/web/.local` archives into the hosted source-unit table until that copy is explicitly approved.
- Supply allocation targets, an approved instrument list and a budget before Deploy Capital can describe the real account. The example must not be treated as that account.

## 9. First task when development resumes

The Today and Intelligence slice is not operational. The 21 October live ingest stored no publication and no new series observations. Do not schedule production ingest or apply the hosted migration until a live retrieval succeeds and its timestamp is recorded. AQ-009, AQ-010, AQ-018, AQ-019 and AQ-032 onward stay blocked. Do not open Saxo authorisation unless that is the task. Do not `db push`.

## Commands

From `apps/web`: `npm run typecheck`, `npm run lint`, `npm run test:saxo`, `npm run test:wealth`, `npm run test:benchmark`, `npm run test:capital`, `npm run test:learn`, `npm run test:story`, `npm run test:auth`, `npm run build`.  
From the repo root: `npm run check:tokens`, `npm run test:research`.  
Database tests need a running local Supabase. Do not apply hosted migrations.
