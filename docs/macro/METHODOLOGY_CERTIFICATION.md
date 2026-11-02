# Methodology certification

**Date:** 30 October 2026  
**Risk class:** R2  
**Branch:** `research/quantitative-methods` in `C:\Users\gamer\aqil-quant-methods`  
**Publication:** closed. `publication_allowed` stays false on every run named here.

This report separates stored numerical results from conclusions the results do not support. It does not claim financial-market skill. Every historical run below uses `latest_revised` inputs. None of them is a real-time vintage.

## A. Inventory

Statuses stay separate. A method can be implemented without being numerically verified, historically evaluated, empirically qualified, operational, or approved for publication.

| Method | Implemented | Numerically verified | Historically evaluated on latest-revised data | Empirically qualified | Operational | Approved for publication |
| --- | --- | --- | --- | --- | --- | --- |
| Bry–Boschan 1971 listing | Refusal retained | Not a dating result | No dates produced | No | No | No |
| Spencer-15 labelled variant | Yes | Rules checked in tests | Yes | No acceptance gate | No | No |
| Harding–Pagan characteristics | Yes | Characteristics computed from Spencer-15 dates | Yes | No | No | No |
| Harding–Pagan quarterly BBQ | No | No | No | No | No | No |
| Sahm rule, short live sample | Yes, existing calculator | Existing rule | Yes, on the stored months | No long-history match | No | No |
| Stock–Watson 1988 payroll specification | Refusal retained | Synthetic checks only | No | No | No | No |
| Stock–Watson modern refit | Registered | Gradient condition met on a re-estimate that was not adopted | Yes, as a coincident factor | No | No | No |
| Restricted coincident diffusion | Yes | Share computed on the balanced panel | Yes | No | No | No |
| Hamilton monthly variant | Yes | Seeded parameter recovery | Yes | No | No | No |
| Bai–Perron intercept-only mean shifts | Yes | Seeded segmentation checks in tests | Yes | No paper reproduction | No | No |
| Autoregressive benchmark | Yes | Design checks in tests | Yes | No | No | No |
| Lead–lag cross-correlation | Yes | Bartlett standard-error checks in tests | Yes | No | No | No |
| Small VAR | No code | No | No | No | No | No |
| Estrella–Mishkin probit | No | No | No | No | No | No |
| US GDP nowcast | No | No | No | No | No | No |
| Financial conditions, excess bond premium, BIS credit gap, yield-spread substitutes | No | No | No | No | No | No |

No method in this table is operational. None is approved for publication.

Hamilton monthly variant, Bai–Perron mean shifts, the autoregressive benchmark, and lead–lag have no backlog ids. That gap matches the batch 1 record for diffusion and Harding–Pagan characteristics. They are in the quantitative register only.

## B. Bry–Boschan and Stock–Watson

Batch 1 is already committed. Integration commit `3c5c138c692d19bea37220b15fd52be912c768c7`. The handover that recorded it is `48531b9e051887bd6589e69528b5c3e538fca6cc`.

`date_specific_cycles()` still refuses to date. The 1971 programme listing is not in the volume.

The labelled Spencer-15 variant remains the dating kernel. Runs `8fb20325-414f-401b-8c46-bda82ed94e16` and `3955f7f4-08f8-4e7b-9ded-b3f6eea6633f` each store 18 peaks and 19 troughs. The chronology class is `retrospective_full_sample`. The Spencer smoother is centred, so these dates are not a contemporaneous recession call. Revision sensitivity stays blocked because the file is `latest_revised`. The older payload still replays. MCD is 3. NBER overlap of 30 of 37 dates within six months is a diagnostic, not a gate. Length-bound sensitivity without the five-month phase rule stores 19 peaks and 20 troughs.

The Stock–Watson 1988 CITIBASE payroll panel stays blocked. Employee-hours and the 1982-dollar series are not stored. The modern refit is a latest-revised coincident factor on the stored four-series panel. It is not a GDP nowcast and not a real-time vintage. Preserved parameter version `3f8c7611-c2a1-44a0-8c7e-01bebbfe9a8a` was not overwritten. Re-estimate `940955f1-50d5-4c06-9d90-5ceebd05d352` met the gradient condition, with norms about 0.000629 and 0.000623, and was not adopted. The likelihood gain was about 0.000305. The refit is registered and is not operationally accepted.

## C. Implemented methods and the operational bar

Registration puts a stored full-sample estimate on `default_method_registry` so a replay can resolve the same method id. Registration does not set `publication_allowed` true and does not make a method operational.

`refresh.py` is unchanged. These batch 2 estimates use the full sample. They are not idempotent single-series refresh hooks.

The Hamilton class is `HamiltonMonthlyMethod`, method id `HAMILTON_MONTHLY_REGIME_SWITCHING`. It is a monthly industrial-production log-growth variant with two regimes. It is not a reproduction of Hamilton 1989 quarterly US GNP.

The Bai–Perron class is `BaiPerronMeanShiftsMethod`, method id `BAI_PERRON_MEAN_SHIFTS`. It is intercept-only mean shifts in G.17 monthly log-growth. It is not the general regressor model. Selecting no break under the primary rule is a valid result. Dates are `point_estimates_only`. The 1998 and 2003 papers were not line-checked.

The autoregressive class is `AutoregressiveBenchmarkMethod`, method id `AUTOREGRESSIVE_BENCHMARK`. A fit is a validation baseline. It is not empirically qualified as a forecast.

The lead–lag class is `LeadLagCrossCorrelationMethod`, method id `LEAD_LAG_CROSS_CORRELATION`. A correlation is not a structural lead. No series is assigned leading-indicator status.

Harding–Pagan characteristics, method id `HARDING_PAGAN_CHARACTERISTICS`, remain a characteristics calculation from Spencer-15 dates. Quarterly BBQ was not implemented and was not promoted in the catalogue.

## D. Numerical examples

These figures are stored results. They are not a market view.

Spencer-15, runs `8fb20325-414f-401b-8c46-bda82ed94e16` and `3955f7f4-08f8-4e7b-9ded-b3f6eea6633f`: 18 peaks, 19 troughs, MCD 3. Without the five-month phase rule: 19 peaks and 20 troughs.

Harding–Pagan characteristics, run `0d667a12-5a9c-45e0-b04a-8aea4196bc19`: concordance about 0.664 to 0.879. Payroll, income, and sales turns are not NBER recessions.

Sahm, run `f3db281d-9f6d-4c4c-974f-ba4b9bd68131`: September 2025 gap 0.23, not triggered. July to September 2024 triggered. October 2025 is missing and was not interpolated.

Stock–Watson re-estimate `940955f1-50d5-4c06-9d90-5ceebd05d352`: gradient norms about 0.000629 and 0.000623. Likelihood gain about 0.000305. `adopted_parameter_version` is false. Preserved parameter version `3f8c7611-c2a1-44a0-8c7e-01bebbfe9a8a`.

Restricted coincident diffusion, run `1f747c9f-4851-4588-a4dc-d8fb1ff30558`: correlation with the preserved filtered factor about 0.336 on 352 months.

Hamilton monthly variant, run `4629b31d-b0de-4a2f-a987-9e5d3f94747e`: BIC lag 2. Seeded recovery maximum absolute error about 0.016. Lower-mean expected duration about 2 months. Filtered and smoothed probabilities are stored separately. Neither path is real-time.

Bai–Perron mean shifts, run `2f4c14eb-44f2-40dc-913f-bf7945e972cd`: primary trimming `h = max(24, floor(0.15 * T))` selects no break on G.17 log-growth. Looser trims change the count. That sensitivity is stored and is not a second selected model.

Autoregressive benchmark, run `7c33c9b1-3759-4fa6-86ea-c0bcbc86257e`: AIC lag 12. Horizon 1 beat the historical mean. Horizon 12 did not.

Lead–lag, run `94152391-c3a8-48d7-8f2e-8c4d1dfdb811`: the strongest correlations are contemporaneous. None of those peaks is stable across 1997–2007 and 2010–2019.

## E. Methodological disagreements

These comparisons are disagreements between stored objects. They are not a ranking and not a composite.

The restricted diffusion share correlates about 0.336 with the preserved filtered factor on 352 months. That is not independent confirmation of the factor.

Hamilton's lower-mean regime has an expected duration of about 2 months. That short regime is not the same object as a Spencer-15 peak or trough.

Bai–Perron selects no mean break in G.17 log-growth under the primary trimming rule. The Spencer-15 dating algorithm still finds peaks and troughs in the level index. A mean-shift count and a turning-point chronology answer different questions.

Lead–lag peaks on the four coincident growth rates are contemporaneous, and those peaks are not stable across the predeclared subsamples. That is not a structural lead.

## F. Blocked methods

No VAR code was written. The lead–lag result shows the four coincident growth relationships are not stable across 1997–2007 and 2010–2019, so a small VAR is not justified. The block is recorded on `ADVANCED_FORECASTING` in the quantitative register and in this certification.

Estrella–Mishkin is blocked. `fed.h15.RIFLGFCM03_N.M` is stored. The probit was not estimated: NBER dates are not an approved stored input, and the 1998 equation was not copied from the article.

The US GDP nowcast is blocked. Quarterly real GDP `bea.nipa.T10106.A191RX` is stored as latest-revised history. There is no vintage panel. ALFRED and Philadelphia Fed real-time data were not ingested. Real-time claims remain blocked. Euro-area GDP was not copied onto the US series.

Financial conditions, the excess bond premium, the BIS credit gap, and yield-spread substitutes are blocked. The required series are not stored. They were not proxied.

Also still blocked, with no new code and no new series collection: the 1971 Bry–Boschan listing, the 1988 CITIBASE payroll panel, revision sensitivity for any latest-revised chronology, and a long `SAHMREALTIME` comparison. AQ-103 stays out of scope. Quarterly BBQ was not run on monthly G.17.

## G. Vintage limits

Every historical run in this certification is `latest_revised`. Filtered probabilities, smoothed probabilities, centred dating filters, full-sample factors, diffusion shares, mean-shift searches, autoregressive errors, and cross-correlations on that file are retrospective. None of them is a real-time call. A later observer could not have known the revised values at the historical date.

## H. Test evidence

Batch 1, already recorded: `npm run test:research` passed 561 tests, then Ruff. Catalogue tests passed 7. GitHub Actions was not run.

Batch 2 targeted modules `test_hamilton_monthly.py`, `test_bai_perron_mean_shifts.py`, `test_autoregressive_benchmark.py`, and `test_lead_lag.py`: 36 passed.

After that, `npm run test:research` from this worktree passed 597 tests, then Ruff check and Ruff format (405 files already formatted). The documented preparation rebuilt only `aqil_research_test`. The preserved database `postgres` on `127.0.0.1` port 55432 was not reset.

Web methodology catalogue unit tests passed 8, including the check that batch 2 payloads stay withheld. GitHub Actions was not run for this certification.

## I. Git

Branch: `research/quantitative-methods`.

Registration commit: `2a52262e08f1860e0eac7ecf9fe8722a5fd89526`.

Certification commit: `b2f6096d9f9b47d8c3a35be67679b4d2816f0691`. Its parent is the registration commit. That commit was not amended.

Local `main` was merged into this branch. Merge commit: `790b5fd91fe7f8c361fa68f75768a24767b9bc33`. Parents: `b2f6096d9f9b47d8c3a35be67679b4d2816f0691` and `c03842692c0a18b41ed63fb527cbb9534f44c0ab`. The merge was clean. It brought in `8fd00ac` (hosted research reader role) and `c038426` (reader migration stored as UTF-8). `main` itself was not updated. Nothing was pushed. This branch was not merged into `main`.

The main checkout at `C:\Users\gamer\aqil` was not edited. It still has the uncommitted `apps/web/public/icons/icon.svg` change. That file was not included in the merge.

## J. Next priorities

Only where the dependency is real, in this order:

1. A rights-cleared three-month Treasury yield for an Estrella–Mishkin specification. The federal funds rate is not a proxy.
2. A lawful unemployment history before any long Sahm comparison. AQ-103 stays out of scope until that history exists.
3. Vintages before any real-time claim, including revision sensitivity for Spencer-15.
4. US GDP plus a vintage panel before a nowcast. Euro-area GDP does not remove that requirement.

This certification does not recommend an architectural reset and does not recommend a composite score.

## K. Signed-in visibility, 31 October 2026

Publication approval stays separate from private visibility. `publication_allowed` remains false on every run named in this certification. A signed-in methodologies page may read the stored calculation and show the preserved figures. A signed-out session does not receive that JSON.

The hosted `research_reader` role already has select on `research.research_runs.calculation`. No new grant was added. The named quantitative runs are on local postgres and are not on the hosted project. They were not copied. Hosted Supabase was not migrated and was not deployed.

The preserved Stock–Watson parameter version remains `3f8c7611-c2a1-44a0-8c7e-01bebbfe9a8a`. Re-estimate `940955f1-50d5-4c06-9d90-5ceebd05d352` stays unadopted. The page plots the preserved filtered factor, not the re-estimate and not the smoother. The 1988 CITIBASE panel stays blocked.

Spencer-15 runs `8fb20325-414f-401b-8c46-bda82ed94e16` and `3955f7f4-08f8-4e7b-9ded-b3f6eea6633f` stay the dating record: 18 peaks and 19 troughs, retrospective full sample. The 1971 listing still refuses to date. The page does not call the variant a FORTRAN reproduction.

Harding–Pagan characteristics remain run `0d667a12-5a9c-45e0-b04a-8aea4196bc19`. Quarterly BBQ was not run on monthly industrial production.

Sahm remains run `f3db281d-9f6d-4c4c-974f-ba4b9bd68131`. The stored result is the September 2025 gap of 0.23 percentage points, not triggered. October 2025 is not interpolated. There is no stored monthly gap path, so the page does not plot one.

Diffusion remains run `1f747c9f-4851-4588-a4dc-d8fb1ff30558`. The correlation of about 0.336 is not independent confirmation and the share is not the Chicago Fed index.

Hamilton remains run `4629b31d-b0de-4a2f-a987-9e5d3f94747e`. The page plots the filtered lower-mean probability, not the smoothed path. The lower-mean expected duration is about 2 months. That is not a recession label and the fit is not empirically qualified. A later code note records a six-month duration alternative that is not estimated and not adopted. The stored run was not replaced.

Bai–Perron remains run `2f4c14eb-44f2-40dc-913f-bf7945e972cd`. The primary result is no break. Sensitivity is not a second selected model.

The autoregression remains run `7c33c9b1-3759-4fa6-86ea-c0bcbc86257e`. The twelve-month horizon loses to the historical mean. It is not a qualified forecast.

Lead–lag remains run `94152391-c3a8-48d7-8f2e-8c4d1dfdb811`. The strongest correlations are contemporaneous and not stable. That is not a leading-indicator assignment.

No VAR, nowcast, or Estrella–Mishkin estimate was added. The three-month Treasury yield is still absent. The stored likelihoods on the preserved run and the re-estimate are about -1590.537499 and -1590.537194. The gain is about 0.000305, below the 0.001 adoption margin. Hamilton's stored lower-mean expected duration is about 1.993 months.

`npm run test:research` passed 598 tests, then Ruff check and Ruff format, 405 files already formatted. Only `aqil_research_test` was rebuilt. Database `postgres` was not reset. Web methodology unit tests passed 14. Web typecheck passed. Token styling passed. GitHub Actions was not run.

## L. Quantitative V1 inventory, 31 October 2026

This section records the integration branch after the official yield, GDP, and unemployment history were merged. It does not replace sections A to K. Section K said the three-month yield was still absent. That yield is now stored. No earlier run named above was replaced. `publication_allowed` stays false. Nothing in this section is a publication approval, a forecast, or a real-time claim.

The daily refresher is not built. `aqil-research execute-method --method-id` is the execution contract: it resolves one method on `default_method_registry()`, reads that method's required series, and appends a run. `--refit` is rejected for every method that does not declare a separate refit command. That is every method below except Stock–Watson. Stock–Watson's separate refit still does not replace preserved run `3f8c7611-c2a1-44a0-8c7e-01bebbfe9a8a`. A later refresher must not assume that a new observation rewrites a stored run, that `publication_allowed` becomes true, or that `latest_revised` is a vintage.

The execute-method contract is stable enough for a daily refresher to be designed later. It is not stable enough to run one. The remaining prerequisites are a verified hosted logical dump and point-in-time recovery, a hosted ingest of the BEA series that are on local postgres and were not copied, and a ban on copying local research runs onto the host.

### Stored V1 calculations

Figures below were read from local `postgres` (`127.0.0.1:55432`). They were not copied to the host.

| Record | CPI-U autoregression | Ex-post real federal funds rate | Engle–Granger | CUSUM of recursive residuals |
| --- | --- | --- | --- | --- |
| Name | CPI-U inflation autoregression | Ex-post real federal funds rate | Engle–Granger cointegration | CUSUM of recursive residuals |
| Variant | OLS sum of autoregressive coefficients. Not Andrews–Chen median-unbiased | Funds rate minus trailing 12-month CPI percent change. Not a Taylor rule. Not ex-ante | Residual test on log levels. Not causal | Predeclared lag 12. Not a selected break date |
| Code | `workers/research/src/aqil_research/methods/cpi_u_inflation_autoregression.py` | `workers/research/src/aqil_research/methods/ex_post_real_federal_funds.py` | `workers/research/src/aqil_research/methods/engle_granger_cointegration.py` | `workers/research/src/aqil_research/methods/cusum_recursive_residuals.py` |
| Series | `bls.cu.CUSR0000SA0` | `fed.h15.RIFSPFF_N.M` and `bls.cu.CUSR0000SA0` | `fed.g17.IP.B50001.S` and `bls.ce.CES0000000001` | `fed.g17.IP.B50001.S` |
| Frequency | Monthly | Monthly | Monthly | Monthly |
| Transformations | Monthly log change. Gaps not filled | Twelve-month percent change, not a log change | Natural log levels | Monthly log-growth |
| Parameter version | 1.0.0. Policy `none` | 1.0.0. Policy `none` | 1.0.0. Policy `none` | 1.0.0. Policy `none` |
| execute-method id | `CPI_U_INFLATION_AUTREGRESSION` | `EX_POST_REAL_FEDERAL_FUNDS_RATE` | `ENGLE_GRANGER_COINTEGRATION` | `CUSUM_RECURSIVE_RESIDUALS` |
| Refit rule | `--refit` rejected | `--refit` rejected | `--refit` rejected | `--refit` rejected |
| Run | `bcbf15bc-590e-4738-9bc1-bbe951b12079` | `cf73c312-dc83-49d6-ba46-2ea02054d336` | `570e2f51-1871-4c0e-88c9-c40652093613` | `4943ca23-38bb-447f-8b8a-95c75b5fcd70` |
| Validation label | Implemented. Historically evaluated on latest-revised data. Not a forecast. Not operational. Not approved for publication | Same, and not a policy rule | Historically evaluated. Does not reject no-cointegration. Not causal. Not operational. Not approved for publication | Historically evaluated. Does not cross the boundary. Not a break date. Not operational. Not approved for publication |
| Vintage class | `latest_revised` | `latest_revised` | `latest_revised` | `latest_revised` |
| Publication flag | false | false | false | false |
| A refresher must not assume | October 2025 CPI exists, the OLS sum is median-unbiased, or this run is rewritten in place | An output gap, a Taylor rule, an ex-ante rate, or a policy prescription | Causality, a leading indicator, or ordinary ADF critical values | That February 1973 is a selected break, or that the lag was chosen by AIC |

Stored readings, not a market view:

CPI-U run `bcbf15bc-590e-4738-9bc1-bbe951b12079`: AIC lag 12. Ordinary least squares persistence about 0.803. Monthly log changes from February 1947 to September 2025. October 2025 CPI is missing and was not interpolated. Not a forecast. Not the Andrews–Chen median-unbiased estimator.

Ex-post real rate run `cf73c312-dc83-49d6-ba46-2ea02054d336`: September 2026 federal funds rate 3.75 percent. Trailing 12-month CPI inflation about 3.7173. Real rate about 0.0327 percentage points. Not a Taylor rule. Not ex-ante.

Engle–Granger run `570e2f51-1871-4c0e-88c9-c40652093613`: does not reject no-cointegration. Statistic about -2.865. MacKinnon five percent critical value about -3.342. Not causal.

CUSUM run `4943ca23-38bb-447f-8b8a-95c75b5fcd70`: does not cross the five percent boundary. Largest absolute CUSUM about 47.93 in February 1973, where the boundary is about 66.98. Not a selected break date.

Signed-in methodology pages read these stored fields. If the run is absent, the page says the result is unavailable. Signed-out sessions still receive no calculation JSON. `publication_allowed` false still allows the signed-in private result.

### Blocks that remain

Estrella–Mishkin: yield `fed.h15.RIFLGFCM03_N.M` is stored (541 months, September 1981–September 2026). The probit is not implemented because NBER dates are not an approved stored input. The 1998 equation was not copied from the article. The discount-basis bill was not stored. Federal funds was not used as the spread.

US real GDP `bea.nipa.T10106.A191RX` is stored, 319 quarters, 1947 Q1–2026 Q3. A nowcast is not implemented. There are no vintages. ALFRED was not ingested. Philadelphia Fed real-time data was not ingested. Euro-area GDP was not copied onto this series.

Unemployment `bls.ln.LNS14000000` is revised history from January 1948, 944 distinct months through September 2026. October 2025 is still missing and was not interpolated. This is not a real-time Sahm evaluation. Existing Sahm run `f3db281d-9f6d-4c4c-974f-ba4b9bd68131` remains the short-sample result. It was not replaced.

Still blocked, for the reasons already in the quantitative V1 plan:

- Quarterly BBQ: the journal defaults are not line-checked, and the method must not be run on monthly industrial production.
- The 1971 Bry–Boschan listing: the programme listing is not in the volume, so `date_specific_cycles()` still refuses to date.
- The 1988 CITIBASE Stock–Watson panel: employee-hours and the 1982-dollar series are not stored. Preserved run `3f8c7611-c2a1-44a0-8c7e-01bebbfe9a8a` is not replaced.
- A small VAR: lead–lag run `94152391-c3a8-48d7-8f2e-8c4d1dfdb811` shows the four coincident growth relationships are contemporaneous and not stable across 1997–2007 and 2010–2019.
- NFCI, the excess bond premium, and the BIS credit-to-GDP gap: the required series are not stored and were not proxied. The stored BIS dollar-credit series is not the gap.
- Phillips curve: no equation and no slack measure have been named.
- Taylor rule: no output gap is estimated. The ex-post real funds identity is not that rule.
- Trimmed-mean CPI: component indexes are not stored.
- ALFRED vintages stay prohibited. There is no vintage panel.

### Track B

Production delivery is not successful. `C:\Users\gamer\aqil-release-backups\2026-10-25` holds the five migration files that were already applied, not a `pg_dump`. `C:\Users\gamer\aqil-release-backups\2026-10-30` holds pre-import counts, not a logical dump. The hosted project is on the free plan. The backup list was empty and point-in-time recovery was off. The database password was not readable from Vercel, so `supabase db dump` was not run in this session and must not be improvised. No hosted migration was applied. No local run was copied.

### Test evidence for this inventory

`npm run test:research` passed 636 tests. Ruff check then passed on the restored tree, and Ruff format reported 423 files already formatted. A transient uncommitted registry edit was not part of that pass and was not committed. Only `aqil_research_test` was rebuilt. Database `postgres` was not reset. Methodology unit tests passed 23. Web typecheck passed. Lint passed with the existing unused `_searchParams` warning. Token styling passed. `npm run build` passed, 50 routes. GitHub Actions has not run. The SHA is the views commit on `research/quantitative-v1`.

## M. Feasible V1 methods, 31 October 2026

This section adds the methods that were ready to register. It does not replace sections A to L. Section L's four stored calculations remain. Their runs were not replaced. `publication_allowed` stays false on every run named here. Nothing in this section is a publication approval, a forecast, a recession probability, or a real-time claim.

`default_method_registry()` now also includes `INFLATION_AUTOREGRESSION`, `EX_POST_REAL_FUNDS_RATE`, `IP_GROWTH_CUSUM`, and `ESTRELLA_MISHKIN_TERM_SPREAD`. Registration does not make a method operational. `--refit` is rejected for all four because the parameter policy is `none`. `workers/research/src/aqil_research/workflow/refresh.py` was not changed. No scheduler, cron, or jobs table was added.

The V1 inventory names one Engle–Granger test: `ENGLE_GRANGER_COINTEGRATION`, run `570e2f51-1871-4c0e-88c9-c40652093613`, recorded in section L. `ACTIVITY_LEVEL_COINTEGRATION` used the same pair (`fed.g17.IP.B50001.S` and `bls.ce.CES0000000001`), natural logs, the same regression direction, residual ADF with no constant, and the MacKinnon five percent critical value. The stored conclusion was the same: the test does not reject, and the statistic is about -2.865. That duplicate registration was removed. Local run `314ef1b5-c691-4c0c-a3c4-1fb4577254a4` was left in postgres and is not a second method.

`INFLATION_AUTOREGRESSION` is a 24-month holdout scored against the historical mean. It is not a replacement for `CPI_U_INFLATION_AUTREGRESSION`. `EX_POST_REAL_FUNDS_RATE` uses subsequent twelve-month inflation. It is not a replacement for `EX_POST_REAL_FEDERAL_FUNDS_RATE`, which uses trailing inflation. `IP_GROWTH_CUSUM` is an AR(1). `CUSUM_RECURSIVE_RESIDUALS` uses a predeclared lag of 12. They are two stated CUSUM specifications, not two discoveries of different break dates. `ESTRELLA_MISHKIN_TERM_SPREAD` remains a latest-revised 10-year minus 3-month spread with `probit_estimated` false.

Replay still requires the stored configuration hash to equal the method's own configuration hash. That match rule was not weakened. The four remaining published config ids stay in `reproduction_config`. The activity-level config id was removed.

### Local execution

Commands were `aqil-research execute-method --method-id ID` against local `postgres` on `127.0.0.1:55432`. `--refit` was not passed. No hosted database was read or written.

| Method | Run | Status | What was stored |
| --- | --- | --- | --- |
| `INFLATION_AUTOREGRESSION` | `f0adeed5-991a-4115-be21-f4cbe4c122c7` | `completed_insufficient` | The latest contiguous monthly logarithmic-change sample is shorter than 144 months. October 2025 CPI is missing and was not interpolated. Not empirically qualified as a forecast. Not a Taylor rule. |
| `EX_POST_REAL_FUNDS_RATE` | `e340659b-b693-480a-8e6d-a64b24b90f99` | `completed` | Funds month September 2025. Federal funds rate 4.22 percent. Subsequent twelve-month CPI inflation 3.7173 percent. Ex-post real rate 0.5027 percentage points. Not a Taylor rule. Not empirically qualified as a forecast. |
| `IP_GROWTH_CUSUM` | `8dd294fc-aa4c-47c5-af43-777dc75d9e3a` | `completed` | Stays inside the five percent boundary. Largest absolute CUSUM about 41.71 in April 2020, where the boundary is about 97.99. Not a selected break date. Not Bai–Perron. This AR(1) specification and the lag-12 CUSUM in section L are two stated specifications, not two discoveries of different break dates. |
| `ESTRELLA_MISHKIN_TERM_SPREAD` | `cbfdaf86-8446-435e-8ceb-7f43557613f1` | `completed` | September 2026 spread 0.90 percentage points. 10-year yield 4.99. 3-month yield 4.09. Not a recession probability. No probit was estimated. |

The 3-month yield `fed.h15.RIFLGFCM03_N.M` was already stored: 541 distinct months, 1 September 1981 to 1 September 2026. No second ingest was run. Discount-basis `fed.h15.RIFSGFSM03_N.M` has 0 rows. Federal funds is not the short rate.

### Method record

| Field | Inflation autoregression | Ex-post real funds rate | Industrial-production CUSUM | 10-year minus 3-month spread |
| --- | --- | --- | --- | --- |
| Name | CPI-U inflation autoregression | Ex-post real federal funds rate | Industrial-production CUSUM | 10-year minus 3-month spread |
| Origin | Autoregressive benchmark rule on CPI-U log changes | Funds rate minus subsequent twelve-month CPI inflation | `recursive_olsresiduals` CUSUM on an AR(1) | Estrella and Mishkin, Current Issues, June 1996. The article does not print probit coefficients |
| Variant | Held-out comparison with the historical mean. Not a product forecast. Not a Taylor rule | Subsequent inflation, endpoints only. Not a Taylor rule | Predeclared lag 1. Not Bai–Perron. Not a selected break date. A second stated CUSUM specification, not a second break date | Latest-revised investment-basis spread only. Not a recession probability |
| Code path | `workers/research/src/aqil_research/methods/inflation_autoregression.py` | `workers/research/src/aqil_research/methods/ex_post_real_funds_rate.py` | `workers/research/src/aqil_research/methods/ip_growth_cusum.py` | `workers/research/src/aqil_research/methods/estrella_mishkin.py` |
| Series | `bls.cu.CUSR0000SA0` | `fed.h15.RIFSPFF_N.M` and `bls.cu.CUSR0000SA0` | `fed.g17.IP.B50001.S` | `fed.h15.RIFLGFCY10_N.M` and `fed.h15.RIFLGFCM03_N.M` |
| Frequency | Monthly | Monthly | Monthly | Monthly |
| Transformations | Monthly logarithmic change. Gaps not filled | Twelve-month percent change from t to t+12 | Monthly log-growth | Difference of the two yields. No probit |
| Parameter policy | `none`. Version 0.1.0 | `none`. Version 0.1.0 | `none`. Version 0.1.0 | `none`. Version 1.0.0 |
| execute-method id | `INFLATION_AUTOREGRESSION` | `EX_POST_REAL_FUNDS_RATE` | `IP_GROWTH_CUSUM` | `ESTRELLA_MISHKIN_TERM_SPREAD` |
| Refit rule | `--refit` rejected | `--refit` rejected | `--refit` rejected | `--refit` rejected |
| Run | `f0adeed5-991a-4115-be21-f4cbe4c122c7` | `e340659b-b693-480a-8e6d-a64b24b90f99` | `8dd294fc-aa4c-47c5-af43-777dc75d9e3a` | `cbfdaf86-8446-435e-8ceb-7f43557613f1` |
| Validation label | Implemented. Executed. Insufficient on the latest contiguous sample. Not empirically qualified. Not operational. Not approved for publication | Implemented. Historically evaluated on latest-revised data. Not empirically qualified as a forecast. Not a Taylor rule. Not operational. Not approved for publication | Implemented. Historically evaluated. Stays inside the boundary. Not a break date. Not operational. Not approved for publication | Implemented. Historically evaluated as a spread. Not a recession probability. Probit coefficients were not estimated. Not operational. Not approved for publication |
| Vintage class | `latest_revised` | `latest_revised` | `latest_revised` | `latest_revised` |
| Publication flag | false | false | false | false |
| A refresher must not assume | That October 2025 was interpolated, that an insufficient run is a forecast, or that the run is rewritten in place | An output gap, a Taylor rule, trailing inflation, or a policy prescription | That April 2020 is a selected break, that the lag was chosen by an information criterion, or that this is Bai–Perron | That the spread is a recession probability, that probit coefficients exist in the June 1996 article, or that federal funds is the short rate |

These four methods are implemented. None is empirically qualified. The inflation autoregression did not produce a sufficient calculation on the stored file. The only Engle–Granger test in this inventory is section L's `ENGLE_GRANGER_COINTEGRATION`.

### Preserved runs

These rows were read again after the appends. Each still has `publication_allowed` false and `analysis_mode` `latest_revised`. None was replaced. Local run `314ef1b5-c691-4c0c-a3c4-1fb4577254a4` was not deleted. It is the duplicate registration's stored row, not a second Engle–Granger method.

`8fb20325-414f-401b-8c46-bda82ed94e16`, `3955f7f4-08f8-4e7b-9ded-b3f6eea6633f`, `0d667a12-5a9c-45e0-b04a-8aea4196bc19`, `1f747c9f-4851-4588-a4dc-d8fb1ff30558`, `3f8c7611-c2a1-44a0-8c7e-01bebbfe9a8a` (preserved Stock–Watson; the refit was not adopted), `940955f1-50d5-4c06-9d90-5ceebd05d352` (stays unadopted), `f3db281d-9f6d-4c4c-974f-ba4b9bd68131`, `4629b31d-b0de-4a2f-a987-9e5d3f94747e`, `2f4c14eb-44f2-40dc-913f-bf7945e972cd`, `7c33c9b1-3759-4fa6-86ea-c0bcbc86257e`, `94152391-c3a8-48d7-8f2e-8c4d1dfdb811`.

Section L's runs also remain: `bcbf15bc-590e-4738-9bc1-bbe951b12079`, `cf73c312-dc83-49d6-ba46-2ea02054d336`, `570e2f51-1871-4c0e-88c9-c40652093613`, `4943ca23-38bb-447f-8b8a-95c75b5fcd70`.

### Inventory checked against local postgres

Unemployment `bls.ln.LNS14000000`: 1,054 stored rows and 944 distinct months, 1 January 1948 to 1 September 2026. October 2025 is absent. 1,039 rows are `latest_revised` and 15 are `provider_vintage`. Some months are stored more than once, so the row count is not the month count. `docs/sources/MACRO_COVERAGE.csv` claims 944 distinct periods over that span. That matches the distinct months. The coverage row was not rewritten and no backfill was invented. The live collector still uses a short Public Data API window. AQ-103 is not done.

US real GDP `bea.nipa.T10106.A191RX`: 319 quarters, 1 January 1947 to 1 July 2026, Table 1.1.6, sheet T10106-Q, line 1, account A191RX, millions of chained 2017 dollars, seasonally adjusted at annual rates. No GDP series was ingested in this session. No GDP method was written. This identity is not a nowcast.

### Still blocked

No code was added for these, and none of them was estimated:

- The 1971 Bry–Boschan listing.
- The 1988 CITIBASE panel.
- Quarterly BBQ on monthly G.17. `harding-pagan-bbq` stays a planned card with an empty query list.
- A VAR.
- A Taylor rule. The ex-post real funds rate is not that rule.
- Probit coefficients. The spread is not a recession probability.
- A nowcast.
- A Phillips curve.
- Trimmed-mean CPI.
- NFCI.
- The excess bond premium.
- The BIS credit gap.
- Vintages. ALFRED and Philadelphia Fed real-time data were not ingested.
- A hosted copy of these local runs.

### Track B

No hosted Supabase read or write. No `pg_dump` was created. `C:\Users\gamer\aqil-release-backups` was not contacted as a host and was not given a dump. Track B stops here.

### Whether a later refresher can be designed

The execution contract and this inventory exist, so a later orchestra can design one refresher. It is not ready to run unattended. The three prerequisites still missing are a hosted backup, a hosted BEA ingest, and the scheduler. This session did not build them.

### Test evidence for this section

`npm run test:research` passed 663 tests, then Ruff check and Ruff format (423 files already formatted). Only `aqil_research_test` was rebuilt. Database `postgres` was not reset. Methodology unit tests passed 25. Web typecheck passed. GitHub Actions has not run. This is not a publication approval.

After the duplicate registration was removed, `npm run test:research` passed 658 tests. The five tests in `test_activity_cointegration.py` were deleted with that method. The remaining tests were not weakened. Ruff check passed, and Ruff format reported 431 files already formatted. Only `aqil_research_test` was rebuilt. Database `postgres` was not reset. Catalogue tests in `present-methodology.test.ts` and `private-methodology-result.test.ts` passed 25. GitHub Actions has not run. Web typecheck was not re-run. This is not a publication approval.

## N. Classification and certification, 1 November 2026

This section classifies the quantitative library after the probit execution. It does not replace sections A to M and it does not delete a method that has a stored run. `publication_allowed` stays false. Nothing here is a publication approval, a forecast, a recession call, or a real-time claim. Hosted Supabase was not read or written. No `pg_dump` was created. No scheduler was added. `workers/research/src/aqil_research/workflow/refresh.py` was not changed. Database `postgres` on `127.0.0.1:55432` was not reset. Preserved runs were not replaced.

Section A still says the Estrella–Mishkin probit was not estimated. That was the state on 30 October 2026. The estimate below is a separate method. It is not a silent upgrade of the spread.

### Counts

These four counts stay separate. They are not added into one methodology total. The two CPI autoregressions are one family. The two real-rate definitions are one family. The spread is an indicator. Cointegration non-rejection is a diagnostic. The probit is a separate model from the spread.

- **8 methodology families:** business-cycle dating, dynamic factor, regime switching, mean-shift model, industrial-production autoregressive benchmark, inflation autoregression, ex-post real funds rate, recession probit.
- **10 variants:** the Spencer-15 labelled variant; the modern Stock–Watson specification; the Hamilton monthly variant; intercept-only Bai–Perron; both CPI autoregressions; both real-rate definitions; both CUSUM specifications. Those ten are not ten extra families. The two CUSUM specifications belong to one diagnostic.
- **3 indicators:** restricted coincident diffusion, the Sahm rule, and the 10-year minus 3-month spread.
- **4 diagnostics:** Harding–Pagan characteristics, lead–lag cross-correlation, Engle–Granger non-rejection, and CUSUM.

Static principal components, the Chicago Fed national activity index, and the Kalman filter remain supporting techniques. They are not families. Quarterly BBQ, the 1971 listing as a working dater, a nowcast, the GDP bridge, the funds-rate vector autoregression, a Phillips curve, a Taylor rule, trimmed-mean CPI, NFCI, the excess bond premium, the BIS credit gap, growth-at-risk, and vintages were not added, so they are not in these counts.

### Probit result

`aqil-research execute-method --method-id CONSTANT_MATURITY_SPREAD_RECESSION_PROBIT` was run once against local `postgres`. `--refit` was not passed. Run `137d92b7-6ce1-49eb-82ad-8f5727b00f90` is `completed`, `latest_revised`, and `publication_allowed` false. Config id `constant_maturity_spread_recession_probit_v1`. Parameter policy `none`.

The fit is estimated and stable. Intercept `-0.424740354915` (standard error `0.357843878008`). Spread coefficient `-1.07426638515` (standard error `0.388914248468`). Estimation uses 97 spread quarters through 2005 Q4, of which 6 outcome quarters are contractions. Evaluation uses 83 spread quarters from 2006 Q1, of which 8 outcome quarters are contractions. Evaluation AUROC `0.68`. Brier score `0.14006186313`. Calibration intercept `0.0803910340177`. Calibration slope `0.0956921901357`. One incomplete quarter was omitted and was not interpolated. The windows were not moved.

This is not the New York Fed parameterisation. The short rate is `fed.h15.RIFLGFCM03_N.M`, not the three-month Treasury bill in the June 1996 article. The NBER chronology is the local attributed copy dated 14 March 2023. Automated collection of that page is prohibited. The chronology is a reference classification, not a vintage of the yields. The spread run `cbfdaf86-8446-435e-8ceb-7f43557613f1` stays the spread, not a probability.

Replay from the frozen observation ids is executable but historically unmatched. `incomplete_quarters_omitted` is 1 on the stored row and 0 when recomputed from those ids, because the incomplete quarter was not linked. The intercept, spread coefficient, quarter counts, and AUROC match. The analytical payload hash differs and was not rewritten. The mismatch was not weakened into a pass. The row is not historically replayable and the method is not operational.

### Registered methods with a stored run

None of these is operational. None is approved for publication. Vintage class is `latest_revised` on every row. A later refresher must not treat that class as a real-time vintage, must not set `publication_allowed` true, and must not rewrite a stored run in place.

| execute-method id | Series | Parameter policy | Refit rule | Run | Replay | A refresher must not assume |
| --- | --- | --- | --- | --- | --- | --- |
| `BRY_BOSCHAN_SPENCER15_VARIANT` | `fed.g17.IP.B50001.S` | `none` | `--refit` rejected | `8fb20325-414f-401b-8c46-bda82ed94e16` and `3955f7f4-08f8-4e7b-9ded-b3f6eea6633f` | Not in the 1 November five-row classification. Section B recorded that the older payload still replays. Not a contemporaneous recession call | That the centred Spencer smoother is a real-time date, or that the 1971 listing was executed |
| `STOCK_WATSON_COINCIDENT_1988_MODERN_REFIT` | `fed.g17.IP.B50001.S`, `bea.nipa.T20600.W875RX`, `bea.nipa.U002BU.KPMT`, `bls.ce.CES0000000001` | `refit_separate` | Default command calculates. `--refit` appends an unadopted run and does not replace `3f8c7611-c2a1-44a0-8c7e-01bebbfe9a8a` | Calculate `a7a2620a-7bd9-4cca-917b-992062ab025c`. Preserved `3f8c7611-c2a1-44a0-8c7e-01bebbfe9a8a`. Unadopted `940955f1-50d5-4c06-9d90-5ceebd05d352` | The two historical rows are blocked and are not historically replayable. Preserved: no `observation_ids` for the two BEA series, and `adopted_parameter_version` is still absent. Unadopted: no `observation_ids`, `adopted_parameter_version` false, likelihood gain about 0.000305 | That the unadopted refit was adopted, that the historical rows replay, or that calculate run `a7a2620a-7bd9-4cca-917b-992062ab025c` is a refit. Its likelihood is `-1590.5374990458229` |
| `RESTRICTED_COINCIDENT_DIFFUSION` | The same four coincident series | `none` | `--refit` rejected | `1f747c9f-4851-4588-a4dc-d8fb1ff30558` | Blocked. No `observation_ids`. Not historically replayable | That the share is the Chicago Fed index, or that this historical row replays |
| `HARDING_PAGAN_CHARACTERISTICS` | The same four coincident level series | `none` | `--refit` rejected | `0d667a12-5a9c-45e0-b04a-8aea4196bc19` | Not in the 1 November five-row classification | That these turns are NBER recessions, or that quarterly BBQ was run |
| `HAMILTON_MONTHLY_REGIME_SWITCHING` | `fed.g17.IP.B50001.S` | `none` | `--refit` rejected | `4629b31d-b0de-4a2f-a987-9e5d3f94747e` | Replayable within `1e-8`. Lower-mean duration about 1.993 months. Extra field `minimum_duration_alternative`. Payload hash left as stored | That the lower-mean regime is a recession label, or that the extra field was written back onto the stored hash |
| `BAI_PERRON_MEAN_SHIFTS` | `fed.g17.IP.B50001.S` | `none` | `--refit` rejected | `2f4c14eb-44f2-40dc-913f-bf7945e972cd` | Replayable within `1e-8`. Primary trim selects no break. Implementation hash differs and was not rewritten | That no break is a selected break date, or that a looser trim is the selected model |
| `AUTOREGRESSIVE_BENCHMARK` | `fed.g17.IP.B50001.S` | `none` | `--refit` rejected | `7c33c9b1-3759-4fa6-86ea-c0bcbc86257e` | Not in the 1 November five-row classification | That horizon 1 is a qualified forecast |
| `LEAD_LAG_CROSS_CORRELATION` | The four coincident growth rates | `none` | `--refit` rejected | `94152391-c3a8-48d7-8f2e-8c4d1dfdb811` | Not in the 1 November five-row classification | That a contemporaneous peak is a structural lead |
| `SAHM_UNEMPLOYMENT_GAP` | `bls.ln.LNS14000000` | `none` | `--refit` rejected | `f3db281d-9f6d-4c4c-974f-ba4b9bd68131` | Not in the 1 November five-row classification | That October 2025 was interpolated, or that the short sample is a real-time evaluation |
| `CPI_U_INFLATION_AUTREGRESSION` | `bls.cu.CUSR0000SA0` | `none` | `--refit` rejected | `bcbf15bc-590e-4738-9bc1-bbe951b12079` | Not in the 1 November five-row classification | That the OLS sum is the Andrews–Chen median-unbiased estimator, or that this is a second family beside the holdout |
| `INFLATION_AUTOREGRESSION` | `bls.cu.CUSR0000SA0` | `none` | `--refit` rejected | `f0adeed5-991a-4115-be21-f4cbe4c122c7` | Not a replay classification. The run remains `completed_insufficient` because October 2025 was not interpolated | That the holdout is sufficient, or that the missing month was filled |
| `EX_POST_REAL_FEDERAL_FUNDS_RATE` | `fed.h15.RIFSPFF_N.M` and `bls.cu.CUSR0000SA0` | `none` | `--refit` rejected | `cf73c312-dc83-49d6-ba46-2ea02054d336` | Not in the 1 November five-row classification | That trailing inflation is a Taylor rule, or that this is a second family beside the subsequent definition |
| `EX_POST_REAL_FUNDS_RATE` | `fed.h15.RIFSPFF_N.M` and `bls.cu.CUSR0000SA0` | `none` | `--refit` rejected | `e340659b-b693-480a-8e6d-a64b24b90f99` | Not in the 1 November five-row classification | That subsequent inflation is ex-ante, or a policy prescription |
| `ENGLE_GRANGER_COINTEGRATION` | `fed.g17.IP.B50001.S` and `bls.ce.CES0000000001` | `none` | `--refit` rejected | `570e2f51-1871-4c0e-88c9-c40652093613` | Not in the 1 November five-row classification. The stored result does not reject no-cointegration | That non-rejection is causal, or that ordinary ADF critical values apply |
| `CUSUM_RECURSIVE_RESIDUALS` | `fed.g17.IP.B50001.S` | `none` | `--refit` rejected | `4943ca23-38bb-447f-8b8a-95c75b5fcd70` | Not in the 1 November five-row classification | That February 1973 is a selected break, or that this lag-12 specification and the AR(1) CUSUM are two break dates |
| `IP_GROWTH_CUSUM` | `fed.g17.IP.B50001.S` | `none` | `--refit` rejected | `8dd294fc-aa4c-47c5-af43-777dc75d9e3a` | Not in the 1 November five-row classification | That April 2020 is a selected break, or that this is Bai–Perron |
| `ESTRELLA_MISHKIN_TERM_SPREAD` | `fed.h15.RIFLGFCY10_N.M` and `fed.h15.RIFLGFCM03_N.M` | `none` | `--refit` rejected | `cbfdaf86-8446-435e-8ceb-7f43557613f1` | Not in the 1 November five-row classification. The stored object remains the spread | That the spread is a probability, or that it is the probit |
| `CONSTANT_MATURITY_SPREAD_RECESSION_PROBIT` | `fed.h15.RIFLGFCY10_N.M` and `fed.h15.RIFLGFCM03_N.M`, with the 14 March 2023 NBER chronology as a reference classification | `none` | `--refit` rejected | `137d92b7-6ce1-49eb-82ad-8f5727b00f90` | Executable, historically unmatched on `incomplete_quarters_omitted` (stored 1, recomputed 0). Coefficients match. Not replayable | That the fit is the New York Fed model, that the omission count replays, or that the windows may be moved to manufacture a fit |

### Negative results that were not implemented

US real GDP `bea.nipa.T10106.A191RX` has 319 quarters, 1947 Q1 to 2026 Q3, with no gaps. A regression of GDP log-growth on industrial-production log-growth is unstable: the 1997–2007 slope is 0.330 and the 2010–2019 slope is 0.057, with a 95 percent interval that includes zero. No bridge was added.

A vector autoregression of the federal funds rate and the 10-year yield was not registered. AIC selects lag 12 at the ceiling and BIC selects lag 2. The portmanteau p-value is about 2.83e-9. No VAR code was added.

### Refresher

`execute-method` can be the interface for methods that replay or execute cleanly. The suite cannot run unattended until a hosted backup, a hosted BEA ingest, and a scheduler exist. Those three were not built.

### Track B

No hosted write. No logical dump. No copy of local runs. Publication stays closed.

### Test evidence for this section

`npm run test:research` passed 673 tests, then Ruff check and Ruff format (434 files already formatted). Only `aqil_research_test` was rebuilt. Database `postgres` was not reset. Methodology presentation tests in `present-methodology.test.ts` and `private-methodology-result.test.ts` passed 27. Web typecheck passed. GitHub Actions has not run. This is not a publication approval.

## O. Foundation hardening, 1 November 2026

Section N remains the scientific starting point. This section records what the hardening branch changed. `publication_allowed` stays false. No method became operational. The constant-maturity probit is not the New York Fed model. The 2005 Q4 and 2006 Q1 windows were not moved.

### Why the stored probit omission does not replay

`_quarter_rows` groups monthly spreads into calendar quarters. A quarter is counted in `incomplete_quarters_omitted` when one of its three months is missing or falls after the evaluation period. The ids stored on run `137d92b7-6ce1-49eb-82ad-8f5727b00f90` were only the months inside complete quarters. The omitted month was never linked. Replay therefore does not see that quarter, and the recomputed count is 0 while the stored count stays 1. The row was not rewritten. On the disposable database the outcome was `executable-but-historically-unmatched`, difference `incomplete_quarters_omitted`.

The local 3-month series has 541 months and that run linked 540. New run `adff8815-8582-4c2e-befa-5faef3f9b925` links 541 months of each yield, including two omitted observation ids, and stores `incomplete_quarters_omitted` 1. The intercept and spread coefficient match the stored row (`-0.424740354915` and `-1.07426638515`). That new run replayed. It is not a claim that `137d92b7` now replays, and it is not historically identical to that row.

### Other stored rows, replayed on `aqil_research_test` and rolled back

| Run | Outcome |
| --- | --- |
| Bry–Boschan `3955f7f4-08f8-4e7b-9ded-b3f6eea6633f` | Replayable |
| Stock–Watson calculate `a7a2620a-7bd9-4cca-917b-992062ab025c` | Replayable. Config and payload hashes differ and were not rewritten. Likelihood remains `-1590.5374990458229` |
| Stock–Watson preserved `3f8c7611-c2a1-44a0-8c7e-01bebbfe9a8a` | Blocked. Frozen links omit both BEA series |
| Stock–Watson unadopted `940955f1-50d5-4c06-9d90-5ceebd05d352` | Blocked. No observation ids. Not adopted |
| Hamilton `4629b31d-b0de-4a2f-a987-9e5d3f94747e` | Replayable within `1e-8`. Extra field `minimum_duration_alternative`. Payload hash not rewritten |
| Bai–Perron `2f4c14eb-44f2-40dc-913f-bf7945e972cd` | Replayable within `1e-8`. Implementation hash differs and was not rewritten |
| Autoregressive benchmark `7c33c9b1-3759-4fa6-86ea-c0bcbc86257e` | Replayable |
| CPI-U autoregression `bcbf15bc-590e-4738-9bc1-bbe951b12079` | Executable, historically unmatched on `excluded_growth_months` |
| Ex-post real funds rate `e340659b-b693-480a-8e6d-a64b24b90f99` | Executable, historically unmatched on `computable_month_count` |
| Sahm `f3db281d-9f6d-4c4c-974f-ba4b9bd68131` | Replayable |
| Spread `cbfdaf86-8446-435e-8ceb-7f43557613f1` | Replayable. It stays the spread |
| Diffusion historical `1f747c9f-4851-4588-a4dc-d8fb1ff30558` | Blocked. No observation ids. Stored month shares are null |
| Diffusion new `625e94dc-5bc5-4f4b-a01a-9c3816b9d0c6` | Executable, historically unmatched. Ids are frozen from the sample start, and the three-month change also uses earlier months that are not linked |

No `--refit` was run. `3f8c7611` was not replaced.

### Counts

The eight families, ten variants, three indicators, and four diagnostics in section N are unchanged. No econometric method was added.

On this tree, `npm run test:research` passed 688, then Ruff check and Ruff format (441 files already formatted). Only `aqil_research_test` was rebuilt. Database `postgres` was not reset. This is not a publication approval.

### Certification re-run

The same uncommitted tree was executed again on 1 November 2026. `HEAD` was still `3aaa2aa`. `npm run test:research` passed 688, then Ruff check passed and 441 files were already formatted. `npm run test:db` passed 13 files and 211 tests. `scripts/replay_frozen_family.py` reproduced the table above and rolled each transaction back. Web typecheck passed. Lint passed with the existing unused `_searchParams` warning. The production build generated 55 pages, including `/intelligence/health`. No method was marked operational. `publication_allowed` stays false.

### Registered source freshness, read on 1 November 2026

`classify_source_freshness` was applied to local `postgres` with the calendar date 1 November 2026. The development database was not written. A quarterly series is not stale because one day was empty. The grace is 21 days for a daily series, 28 for weekly, 75 for monthly, and 200 for quarterly, measured from the latest stored period.

Unchanged: SLOOS (2026-07-01), payrolls (2026-09-01), H.8 bank credit (2026-10-07), the federal funds rate (2026-09-01), the ECB deposit facility (2026-10-24), and Bank Rate (2026-10-22).

Inside the cadence window: industrial production (2026-09-01), the 10-year yield (2026-09-01), Eurostat HICP (2026-09-01), the Singapore CPI reference (2026-09-01), and ONS CPI (2026-09-01). CPI-U is also inside that window at 2026-09-01, but its last refresh on 22 October 2026 was `failed_fetch` because the flat file returned HTTP 406. The classifier does not treat `failed_fetch` as technically blocked.

Stale: JOLTS (2026-08-01), both ECB HICP series (2025-12-01), euro-area GDP (2026-04-01), euro-area unemployment, industrial production, and retail (2026-08-01), the Cabinet Office monthly series (2026-08-01), BIS credit (2026-01-01), Malaysia industrial production (2026-08-01), real personal income excluding transfers (2026-08-01), and real manufacturing and trade sales (2026-07-01).

The five document feeds last recorded on 21 October 2026 have no economic-observation period. Their last outcomes were unchanged or completed, so they are not stale and they are not technically blocked. None of the production connectors was discontinued, not due, or rights-blocked on this read.

`bls_cps_unemployment_rate` and `oecd_cli_g20` have older refresh rows and are not in the production connector list. OECD stays rights pending. `fed.h15.RIFLGFCM03_N.M` is stored as 541 months through September 2026 and is not a production refresh step. METI stays technically blocked and disabled. Census advance orders stay unwired without a key. FRED retention stays prohibited.

## P. Close-out, 1 November 2026

`publication_allowed` stays false. No method is operational. No family is operational. V1 is not complete. The local executions below are replayable. They are not a production deployment and they are not an unattended schedule.

### Live source refresh

`aqil-research refresh` ran twice against local `postgres` on `127.0.0.1:55432`. Hosted Supabase was not written. The second run inserted 0 rows for every source that the first run had inserted, so the fetch is idempotent.

CPI-U `https://download.bls.gov/pub/time.series/cu/cu.data.1.AllItems` returned HTTP 200 with `User-Agent: AqilResearch/1.0 (local research retrieval)` and the flat-file header `series_id`. The same URL returned HTTP 403 from Akamai when the client used the default httpx user agent. The 22 October HTTP 406 was not reproduced. The authorised client does not send `Accept: text/plain`. The stored series is 956 months, January 1947 to September 2026. `2025-10-01` is absent from CPI-U and from unemployment. It was not interpolated. That is a gap in the publisher file, not a failed request. The refresh outcome was `unchanged`.

The first refresh inserted rows for the Federal Reserve press, the ECB press, H.8 bank credit, the ECB deposit facility, euro-area GDP, euro-area unemployment, BIS credit, and Bank Rate. The second refresh left those values unchanged.

Both BEA factor inputs failed with `VintageConflictError` for July 2026. The workbook was fetched. Persistence rejected a different value for the same vintage identity. The stored rows were not rewritten. Those two refresh steps are not operational.

`bls_cps_unemployment_rate` was `skipped_fresh`. It is not a broken fetch.

The cycle recorded after the second refresh is `partial`: 29 unchanged sources, 2 failed sources, 8 stale sources, and 26 skipped methods. No registered method's required series changed, so none was recalculated. Stale sources in that cycle: JOLTS, both ECB HICP series, euro-area industrial production, euro-area retail, the Cabinet Office series, BIS credit, and Malaysia industrial production.

### New lineage-frozen runs

Historical rows were not rewritten.

| Run | Result |
| --- | --- |
| Diffusion `18f5d7bb-8227-4441-8b45-6755153d7b8f` | Replayable. 1,434 observation ids, including the three-month lookback. Historical `1f747c9f-4851-4588-a4dc-d8fb1ff30558` stays blocked. `625e94dc-5bc5-4f4b-a01a-9c3816b9d0c6` stays historically unmatched |
| CPI-U autoregression `06ff435b-2279-4a46-99cb-6a99dd4f0a35` | Replayable. 956 observation ids. Historical `bcbf15bc-590e-4738-9bc1-bbe951b12079` stays unmatched on `excluded_growth_months` |
| Ex-post real funds rate `e399de3f-18a6-4a72-b41f-6d14611b4338` | Replayable. 1,720 observation ids. Historical `e340659b-b693-480a-8e6d-a64b24b90f99` stays unmatched on `computable_month_count` |
| Inflation autoregression `221f1c3a-ba9b-4b29-bb7d-4ffbd8821091` | `completed_insufficient`. October 2025 was not filled. Not replayed as a sufficient result |
| Probit `adff8815-8582-4c2e-befa-5faef3f9b925` | Replayable. Historical `137d92b7-6ce1-49eb-82ad-8f5727b00f90` stays unmatched on `incomplete_quarters_omitted`. Not the New York Fed model |
| Stock–Watson calculate `a7a2620a-7bd9-4cca-917b-992062ab025c` | Replayable. Preserved `3f8c7611-c2a1-44a0-8c7e-01bebbfe9a8a` and unadopted `940955f1-50d5-4c06-9d90-5ceebd05d352` stay blocked |
| Stock–Watson refit `b4f95b41-cc0c-4b38-9792-d866abd6e54d` | Replayable. 1,420 observation ids. `adopted_parameter_version` is false. It does not replace `3f8c7611-c2a1-44a0-8c7e-01bebbfe9a8a` |

The read contract returned the new diffusion run as version 1, `completed`, `sufficient`, `publication_allowed` false.

## Q. Hosted runs, 2 November 2026

Sections A to P name local runs unless a sentence says otherwise. Those local run ids were not copied to the host. This section is the hosted inventory. `publication_allowed` stays false. No row here is scientifically operational, a forecast, or a publication approval.

The owner dump restored the five 23 October 2026 macro-reading runs and 34,859 observations. Migration `20261101120000` is applied. Hosted inputs added after the dump: BEA income 813 months, BEA sales 356 months, and the 3-month yield 541 months. Hosted unemployment remains 44 months from January 2023. A fetch failure on 2 November did not extend it. Census stays unwired. AQ-103 was not built.

| Hosted run | Result |
| --- | --- |
| Estrella–Mishkin `b550f7f4-1e20-45f3-90e7-dbf2552d8b6c` | Completed. Spread 0.90 percentage points on 2026-09-01. 10-year yield 4.99. 3-month yield 4.09. Not a recession probability. Shown to a signed-in reader. |
| Ex-post real funds `0da7d406-a3ad-44de-822a-a04036a1b4fd` | Completed. September 2025 funds rate 4.22 percent. Real rate 0.5027. Not a Taylor rule. |
| Bai–Perron `2f094f84-34d6-430b-9323-80fe1780ea61` | Completed. Selected 0 breaks. |
| Engle–Granger `542abfbc-4d74-4e00-ae43-a54104abaa00` | Completed. Statistic -2.8648234. Not a causal claim. |
| Inflation autoregression `713e8ce2-2a5c-44a5-ad3c-8a62a0f932ae` | `completed_insufficient`. No frozen observations to replay. |
| Sahm `c53dd21e-52d2-49f8-bc80-f556952f31e5` | `completed_insufficient` on the 44-month sample. No frozen observations to replay. |
| Stock–Watson modern refit | Not executed. The accepted parameter version is not on the host. No factor was invented. |

The other hosted quantitative runs from the same execution are completed, unpublished, and replay-matched. They are listed in `docs/CURSOR_SESSION_HANDOVER.md`. One hosted refresh at 2026-11-02 04:11:25 UTC is `partial`. The 06:15 UTC schedule is on `main`. A hosted execution is not operational acceptance.

### Checks on this close-out

`npm run test:research` passed 688, then Ruff check passed and 441 files were already formatted. `npm run test:db` passed 13 files and 211 tests. Web typecheck passed. Lint passed with the existing unused `_searchParams` warning. The presentation and health tests passed 32. The production build generated 55 pages, including `/intelligence/health`. GitHub Actions has not run. This is not a publication approval.

