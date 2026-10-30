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
