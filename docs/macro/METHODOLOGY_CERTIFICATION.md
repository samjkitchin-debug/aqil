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

Estrella–Mishkin is blocked. The stored 10-year yield and the federal funds rate are not the 10-year minus 3-month Treasury spread. AQ-104 stays the dependency. No new series was ingested.

The US GDP nowcast is blocked. US GDP is not stored. There is no vintage panel. Euro-area GDP does not remove that block.

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

No VAR, nowcast, or Estrella–Mishkin estimate was added. The three-month Treasury yield is still absent.
