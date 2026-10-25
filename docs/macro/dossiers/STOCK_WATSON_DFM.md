# Stock–Watson dynamic factor model

**Status:** local modern refit recorded. Not a 1959–1987 reproduction and not publication eligible.  
**Role:** first substantive economic-intelligence milestone.  
**Priority:** P0, implementation rank 2, intelligence rank 1.  
**Backlog:** AQ-101 records the 1989 contract. AQ-102 records the 1988 modern refit.  
**Last source check:** 25 October 2026, NBER chapter PDF `c10968` and working paper `w2772`.

## 1. Identity and provenance

James H. Stock and Mark W. Watson, "New Indexes of Coincident and Leading Economic Indicators", in Blanchard and Fischer (eds), *NBER Macroeconomics Annual 1989*, Volume 4, MIT Press, pp. 351–409. ISBN 0-262-02296-6. DOI recorded by NBER: `10.1086/654119`. Chapter URL: `http://www.nber.org/chapters/c10968`. PDF read: `https://www.nber.org/system/files/chapters/c10968/c10968.pdf`.

The chapter says the technical detail of the coincident model is in Stock and Watson (1988a), and the employment variant is in Stock and Watson (1988b). Working paper 2772, the 1988a paper, was read on 25 October 2026 from `https://www.nber.org/system/files/working_papers/w2772/w2772.pdf`. The separate 1988b employment-variant paper was not downloaded. The adopted series list uses employee-hours, so 1988b is not the specification.

Later Stock–Watson work, including the 2016 handbook chapter on factor models (`https://www.princeton.edu/~mwatson/papers/Stock_Watson_DFM_HOM_030916.pdf`), generalises the model. It is not the specification Aqil has adopted. AQ-101 chooses one published specification. It does not blend them.

Static PCA and the Chicago Fed National Activity Index are related factor summaries. Kalman filtering is the estimator used in the 1989 chapter. None of those is a separate milestone.

## 2. Original economic purpose

The chapter asks whether a probability model can define a coincident index as the unobserved state of the economy that generates co-movement in several activity series. The experimental coincident index is an estimate of that state. The leading index in the same paper is a forecast of the growth of that state over six months. The recession index is a probability that the path of the state will meet a stated pattern six months ahead. Those are three outputs. The milestone for Aqil is the coincident dynamic factor, not the recession index and not the leading index, unless AQ-101 explicitly widens the contract.

The chapter treats recessions as patterns in a linear model ("extrinsic"), and contrasts that with Markov-switching ("intrinsic"). Aqil must not describe the factor as a recession classifier.

## 3. Mathematical specification

The PDF glyphs for Greek letters are damaged by text extraction. The assignment of symbols is taken from the sentence on book page 354, which says the lag polynomials are respectively scalar, vector, and matrix, in the order \(\phi(L)\), \(\gamma(L)\), and \(D(L)\). That sentence was read on 25 October 2026. The equations below are that reading. They are confirmed against the chapter PDF and against working paper 2772. They are not a second specification.

Let \(X_t\) be an \(n \times 1\) vector of logarithms of coincident macroeconomic variables. The chapter says those series look integrated but not cointegrated, so the model is in differences. The text's formulation is of the form:

\[
\Delta X_t = \mu + \gamma(L)\Delta C_t + u_t
\]

\[
D(L)u_t = \varepsilon_t
\]

\[
\phi(L)\Delta C_t = \delta + \eta_t
\]

with \(L\) the lag operator. The identifying assumption stated in the chapter is that the idiosyncratic components and \(\Delta C_t\) are mutually uncorrelated at all leads and lags. That is implemented by a diagonal \(D(L)\) and by mutually and serially uncorrelated disturbances. \(\Delta C_t\) is assumed to enter at least one equation contemporaneously. The chapter first says \(\gamma(L) = \gamma_0\) is imposed for all but one coincident variable. The estimated hours model then rejects a purely contemporaneous factor in all four equations: lags of \(\Delta C_t\) enter the employee-hours equation, and the other three measurement equations in Table 2 are contemporaneous. The text calls that hours series slightly lagging.

Working paper 2772 states the same difference equations and normalises the scale by setting the variance of the factor innovation to 1. Table 2 of the 1989 chapter prints the same normalisation. The plotted index is \(C_{t|t}\), exponentiated and scaled to 100 in July 1967. That reporting scale is separate from the innovation variance. The base-model lag orders are not copied from extracted lines that are not reliable. The comparison model in Table 2 panel D prints orders 5, 6, and 8 for a more heavily parameterised alternative. Those orders are not the base model. The estimation sample printed in the table notes is 1959:1 to 1987:12. Each series was standardised to a growth rate with mean zero and unit variance before estimation.

Estimation is maximum likelihood. The Kalman filter evaluates the likelihood. The coincident index is the minimum mean-square-error linear estimate of the factor from the Kalman filter, a linear combination of current and past values of the coincident variables.

The leading-index equations (4) and (5) in the chapter are a separate system estimated conditional on the coincident parameters. They are out of scope until the coincident model is specified and validated.

**Still not frozen for code:** the Kalman state matrices, and the idiosyncratic coefficients in Table 2. The innovation-variance normalisation is read as 1. The base-model lag orders are not copied from the garbled lines.

## 4. Input data

From the chapter, section 3.1 and Table 1, the proposed coincident index uses four series, log differences, from the 31 January 1989 CITIBASE release, with results from 1959:1:

| CITIBASE code | Chapter description | Aqil holding |
| --- | --- | --- |
| IP | Industrial production, total (BCD 47) | Candidate only. `fed.g17.IP.B50001.S` is the Board total index. It is not confirmed as the 1989 CITIBASE series. |
| GMYXP8 | Personal income less transfer payments, 1982 dollars (BCD 51) | Missing. No `SOURCE_RIGHTS.csv` row. The BEA row in that file is a news-release calendar, not this series. |
| MT82 | Manufacturing and trade sales, total, 1982 dollars (BCD 57) | Missing. `census.m3.adv.MDM.NO` is advance durable-goods new orders, not this composite, and that adapter is not storing observations. |
| LPMHU | Employee-hours in non-agricultural establishments | Missing. `bls.ce.CES0000000001` is payroll headcount. The chapter, following Moore (1988), uses hours because overtime and part-time work make hours a measure of labour input. Headcount is not a substitute. |

No FRED or ALFRED series is used. No rights row clears GMYXP8, MT82, or LPMHU for storage. AQ-102 does not start. A three-series model is not this specification.

Seasonal adjustment is whatever the official series already applies. The model uses log differences, not a second seasonal filter. Missing data and the ragged edge are not solved in the 1989 coincident specification as read. Mixed-frequency nowcasting is a later family.

Vintages are required before any real-time claim. The 1989 empirical results are on a revised CITIBASE extract.

## 5. Outputs

A coincident factor level or its difference, depending on the normalisation AQ-101 freezes, with the Kalman-filter estimate and a stated uncertainty if the filter provides a variance. The 1989 paper also produces a six-month growth forecast and a recession probability. Those are not part of the first milestone unless the contract says so.

The factor is not a probability of recession, not a GDP nowcast, and not an investment signal.

## 6. Estimation

Statistically estimated by maximum likelihood. The sample in the chapter starts in 1959:1. Lag orders were chosen empirically by the authors. Aqil does not reselect them on a later sample, and it does not treat the authors' in-sample choice as confirmation. The base-model orders are not frozen while the extracted coefficient lines remain unreliable.

Re-estimation is a new parameter version. A monthly update of the filtered state with fixed parameters is a different event and must be labelled as such.

## 7. Institutional implementations

The chapter compares the experimental index with the Department of Commerce coincident index of that time. It is not the current Conference Board index and not the Chicago Fed National Activity Index. Those institutional series can be external benchmarks only after their own methodology notes are read. They were not read in this pass.

## 8. Empirical validation

The chapter reports a spectral test of the single-index restrictions: a statistic of 19.8 on 30 degrees of freedom, p-value 92 percent, which the text reads as little evidence against the restrictions. It reports a Stock–Watson cointegration statistic of -25.25 with a p-value of 60 percent, and Dickey–Fuller tests that did not reject integration of each series. Figures plot the index against NBER turning points. Those plots are illustrative. They are not an exact-match test.

Independent replication of the 1989 numerical index is the right first check, if the 1989 data or a published table can be obtained. That has not been done.

## 9. Failure modes

The single-factor assumption fails when nominal and real series need more than one factor. The chapter cites Singleton (1980) on that point. Cointegration findings can change with the sample. Pandemic-scale outliers and sector-specific shocks move one series without being "the" state. Revised data change both the estimate and any backtest that pretends the revised sample was known at the time. Sign and scale of the factor are normalisation choices. Over-fitting lag orders on one US sample does not validate another country. A two-series principal component is not this model.

## 10. Aqil applicability

This is the first method aimed at a current measure of US activity from co-movement. It cannot be claimed until the four-series specification, or another named published specification, is matched to stored data. It does not replace the Bry–Boschan pilot. The pilot's industrial-production dates are not an input to the factor.

Euro-area series already stored could support a different factor model later. They are not the 1989 US specification.

## 11. Data readiness

Not ready. GMYXP8, MT82, and LPMHU are absent from the store and from `SOURCE_RIGHTS.csv`. G.17 is not confirmed as CITIBASE IP. Payroll headcount is not employee-hours. Unemployment backfill is not implied by this specification. US GDP is not required for the coincident index. AQ-102 stays blocked on that data and rights gap, and on the unfrozen Kalman matrices.

## 12. Engineering requirements

A Kalman filter and maximum-likelihood estimation. The research worker does not depend on NumPy, pandas, or a state-space library. Adding one library is an implementation decision for AQ-102, not a platform. Runs are monthly, after the input months exist. Re-estimation is less frequent and versioned. Storage is `research.research_runs` plus a parameter payload or a hash of a stored parameter set. A new results schema is justified only if the run payload cannot hold the factor, the variance, and the parameter hash.

Computational cost of a four-variable monthly model is small. That is not a reason to build a generic state-space service.

## 13. Validation plan

1. Confirm symbols and lag orders against the PDF and, if adopted, against Stock and Watson 1988a.
2. Reproduce a published table or a short fixture with a known factor and known parameters.
3. Only then estimate on Aqil data.
4. Compare the path with a simple average of the standardised log differences. The factor must be reported against that benchmark, not instead of it.
5. NBER dates, if plotted, are a diagnostic with no exact-match gate.
6. No real-time skill claim on revised data.

## 14. Operational acceptance

- **Specification accepted:** AQ-101 names the paper, the equations, the series, the transformations, and the normalisation.
- **Implemented:** fixture likelihood or filtered state matches the reference within a written tolerance.
- **Historically checked:** revised-data estimation completed and labelled retrospective.
- **Operational:** recurring filter update, monitoring of convergence, missing inputs, sign flips, and replay. Still not a real-time forecast claim.
- **Suspend** on non-convergence, a singular information set, or a series revision that the contract says invalidates the parameter version.

## 15. Status and priority

The 1989 coincident equations and the four-series contract are recorded. Working paper 2772 was read again from the PDF on 25 October 2026. The 1988b employment paper was not read. Estimation code was not written.

## Implementation card, 25 October 2026

PyMuPDF text from the PDF is the source. Damaged glyphs were not filled in.

Working paper 2772, pages 6 to 8 and 16 to 17, prints this coincident structure:

- The series are differenced logarithms, after the authors did not reject integration and did not reject no cointegration.
- Each growth rate is standardised to mean zero and unit variance on the estimation sample.
- The factor innovation variance is 1.
- Idiosyncratic dynamics are diagonal and uncorrelated with the factor at all leads and lags.
- The adopted orders are a factor autoregression of order 2 and idiosyncratic autoregressions of order 2. Page 16 gives log likelihood 341.38 for that model and 327.77 for idiosyncratic order 1.
- In that 1988 model the factor enters all four equations contemporaneously. The fourth series is employees on nonagricultural payrolls (LPNAG), not employee-hours.
- Estimation is Gaussian maximum likelihood through the Kalman filter. The filtered estimate is the real-time index. The smoother is retrospective. The initial mean is zero when the unconditional covariance is used.
- Table 1's factor autoregressive digits are not reliable in extraction, so those coefficients are not frozen. The orders and the unit innovation variance are frozen.

The 1989 chapter puts lags of the factor in the employee-hours equation. Those coefficients were not readable as a clean table. They are not frozen. The leading index, the recession index, and the 2016 handbook form are not this card.

## Data classification, 25 October 2026

Industrial production is held as `fed.g17.IP.B50001.S`, a seasonally adjusted total index, 2017=100, January 1919 to September 2026. That is not the 1989 CITIBASE vintage. The base year differs.

Real personal income less transfers was not stored. `https://apps.bea.gov/api/data/` returned an empty body with no key. `BEA_API_KEY` is unset. No key was invented. Disposable income was not used.

Real manufacturing and trade sales were not stored. `CENSUS_API_KEY` is unset. Advance durable-goods orders are a different series. No nominal sales were deflated.

Employee-hours are not an exact BLS match. Datatype 56 is aggregate weekly hours of all employees. `ce.series` has `CES0500000056`, total private, from March 2006, and `CES0500000081`, production and nonsupervisory employees, total private, from January 1964. `CES0000000056` is absent. Neither private series was stored. Payroll headcount is the 1988 LPNAG concept and is not the 1989 hours concept.

No new rights row was added, because nothing is cleared for ingest and the rights test locks the dataset list. AQ-102 stays blocked. No factor code and no NumPy dependency were added.

## 1988 specification selected, 25 October 2026

The first implementation target is Stock and Watson, NBER Working Paper 2772, November 1988, not the 1989 employee-hours model. The two are not mixed.

Frozen from PDF pages 6–8 and 16–17:

- Inputs are the logarithms of industrial production, real personal income less transfer payments (GMYXP8, 1982 dollars), real manufacturing and trade sales (MT82, 1982 dollars), and employees on nonagricultural payrolls (LPNAG).
- Estimation uses first differences of those logarithms, standardised to mean zero and unit variance on the estimation sample.
- The factor is an autoregression of order 2. Its innovation variance is 1.
- Each idiosyncratic component is its own autoregression of order 2. The idiosyncratic matrix is diagonal. Idiosyncratic shocks are uncorrelated with the factor and with each other.
- The factor enters every equation contemporaneously. There is no lag of the factor in the payroll equation in this paper.
- Estimation is Gaussian maximum likelihood. The Kalman filter is the real-time estimate. The smoother is retrospective.
- Page 16 reports likelihood 341.38 for idiosyncratic order 2 and 327.77 for order 1, sample 1959:2–1987:12. Table 1 coefficient digits are not used as frozen numbers.

The 1989 hours model remains a later variant. Its hours-equation lags are still not frozen.

Code: `workers/research/src/aqil_research/methods/stock_watson_1988.py`. It is not registered and it refuses a real-data estimate. `tests/test_stock_watson_1988.py` passed 4 tests: the constants, the panel block, and a higher likelihood at the parameters that simulated the path than at a factor autoregression of zeros. That simulation is separate from the filter. No economic run was stored. `publication_allowed` is false.

## Download check, same day

BEA `https://apps.bea.gov/national/Release/XLS/Survey/Section2All_xls.xlsx` returned HTTP 200, 4,860,244 bytes, without an API key. The shared strings include “Personal income excluding current transfer receipts, Millions of chained (2017) dollars”. FAQ 147 says BEA website information is in the public domain unless stated otherwise. This is the modern official real series, not 1982 dollars, and it was not parsed into observations.

Census `https://www.census.gov/econ_getzippedfile/?programCode=MTIS` returned the official zip. `MTIS-mf.csv` has 416 seasonally adjusted total-business sales rows, unit millions of dollars, periods labelled January 1992 through December 2026. There is no real or 1982-dollar sales series in the file. Those nominal values were not stored and were not deflated.

`CES0500000081` is production and nonsupervisory aggregate weekly hours, total private, from January 1964. It is not the 1989 all-employee nonagricultural hours series and it is not an input to the 1988 model. It was not stored.

## Acceptance, 25 October 2026

The implemented model is `STOCK_WATSON_COINCIDENT_1988_MODERN_REFIT`, version `0.1.0`. The stored estimation run is `3f8c7611-c2a1-44a0-8c7e-01bebbfe9a8a`, executed at 2026-10-25 00:31:12 UTC, `execution_status` completed, `publication_allowed` false. That row was not overwritten.

The panel is the four official series `fed.g17.IP.B50001.S`, `bea.nipa.T20600.W875RX`, `bea.nipa.U002BU.KPMT`, and `bls.ce.CES0000000001`. Levels run from January 1997 to July 2026. The likelihood uses 354 standardised log differences. Income is BEA Table 2.6 account W875RX, millions of chained 2017 dollars. Sales are BEA underlying account KPMT, millions of chained 2017 dollars. Payrolls are total nonfarm employment. This is not CITIBASE GMYXP8, MT82, or LPMHU, and it is not the 1989 employee-hours model.

### Likelihood convention

At the stored parameter vector, with statsmodels `DynamicFactor` (`k_factors=1`, `factor_order=2`, `error_order=2`, `error_var=False`, `error_cov_type="diagonal"`) and `initialize_known` at a zero mean and an identity covariance:

| Quantity | Value |
| --- | --- |
| Aqil log likelihood | −1590.5374990458229 |
| statsmodels log likelihood | −1591.0984133064417 |
| Difference, statsmodels minus Aqil | −0.5609142606187643 |
| Difference at observation 0 | −0.5667543434979523 |
| Sum of differences after observation 0 | +0.005840082879188 |
| Sum of differences after observation 20 | +2.260698295231123e-10 |
| Filtered-factor correlation | 0.9999472439069732 |
| Maximum factor difference | 0.18750309762787143 at the first growth month |
| Maximum factor difference after month 20 | 1.646203173777394e-10 |

Observation 0 accounts for the gap. Aqil applies the transition and the state-shock covariance before the first likelihood contribution, so the first innovation covariance is `H (T P T' + Q) H'` with `P = I`. statsmodels applies the observation equation directly to the supplied initial state, so the first innovation covariance is `H P H'`. Those two 4×4 matrices were compared on the stored panel. The direct matrix matches statsmodels exactly, including the first log-likelihood contribution −5.190610279858821. Aqil's predictive contribution at the same observation is −4.623855936360869. The design, transition, and shock matrices are the same model. The state ordering in statsmodels is not Aqil's 10×10 companion, which is why a naive matrix subtraction is not zero, but the first innovation covariance under the direct convention matches exactly.

Neither implementation is corrected. Changing Aqil to the direct convention would change the stored likelihood and break exact replay. The authoritative likelihood for this run is Aqil's, because that is the objective that was maximised and the database replay matches it. A regression test may require the filtered factor after index 20 to agree within 1e-8. It must not require the full-sample likelihoods to agree more tightly than about 1 without the same initial-state timing.

### Fitted parameters

L-BFGS-B, two admissible starts, `maxiter` 40, `ftol` 1e-6. Stored message: `CONVERGENCE: RELATIVE REDUCTION OF F <= FACTR*EPSMCH`. `converged` is true. Factor innovation variance is fixed at 1. The industrial-production loading is positive. All five AR(2) pairs satisfy `|b| < 1`, `a + b < 1`, and `b - a < 1`. Innovation scales are positive.

Loadings, industrial production, income, sales, payrolls: 0.9074156691709212, 0.592332010645985, 0.7468422714668663, 0.8337971126257162.

Factor autoregression: 0.21593139825856147, −0.20902512910372195.

Idiosyncratic autoregression, same series order: (−0.135055359330801, −0.1853845911590007), (−0.05395491262894935, −0.05349521674490646), (−0.17587617069890396, −0.10032913242621615), (−0.08764350781001158, 0.18173780298752065).

Idiosyncratic innovation scales: 0.3683167232210555, 0.7875917515174838, 0.5955094247543465, 0.5045708876089342.

A finite-difference gradient at this point has norm 0.4146. A further L-BFGS-B run from the same point, 12 iterations, improved the negative log likelihood by 6.1e-5, moved no parameter by more than 2.9e-4, and kept the filtered-path correlation at 0.99999999. Two other admissible starts, stopped at 12 iterations, reached negative log likelihoods 1590.632 and 1590.660, with path correlations 0.999980 and 0.999947. They had not formally converged. No new parameter version was stored. The gradient is not machine zero, so a unique global maximum is not claimed. The stored run remains the fitted model.

A statsmodels cold start did not converge in 25 iterations. A warm start from these parameters reached about −1590.468 on the statsmodels likelihood and still emitted a convergence warning. That number is not an Aqil likelihood and was not adopted.

### Filter updates

`record_filter_update` keeps the stored parameters and the training-sample moments. A changed balanced panel inserts a new completed run and leaves the previous run in place. A failed panel inserts `execution_status` `failed_method` with `update_kind` `filter_failure` and does not replace the last completed factor. The next read selects the latest completed calculation that still contains the loadings. Advisory lock `410221002` returns `locked` when it cannot be acquired. One series arriving ahead of the other three does not move the balanced sample and does not create a new factor.

Disposable database `aqil_research_test` exercised six cases in `tests/test_stock_watson_lifecycle.py`: an unchanged panel twice, one new complete month, one historical revision, one series alone, a held lock, and a negative level. The negative level is rejected because log differences require positive levels. The completed factor count stayed unchanged and a failure row was stored.

### Empirical review on revised data

The filtered factor is the model's own scale, not a GDP growth rate. Its correlation with the equal-weight average of the four standardised log differences is 0.973. Setting one loading to zero and keeping the other parameters fixed changes the path by a maximum absolute amount of 1.692 for production, 0.719 for income, 0.968 for sales, and 1.984 for payrolls. The corresponding correlations with the stored path are 0.956, 0.998, 0.993, and 0.986.

On the stored path, March–November 2001 has 9 months, minimum −0.764, maximum 0.013, mean −0.417. September 2008–June 2009 has 10 months, minimum −2.885, maximum 0.032, mean −1.285. March–May 2020 has 3 months, minimum −14.711, maximum 2.385, mean −5.229. March–June 2021 has 4 months, minimum 0.053, maximum 2.063, mean 0.694. The filtered factor variance has median 0.0850 and maximum 0.1040. The July 2026 filtered value is 0.119 with a filtered standard deviation of 0.292. The 2020 decline is large relative to that variance. It is recorded as an economic movement in the revised sample, not as a failed calculation. These windows use latest revised observations. They are not a real-time historical path and they are not a forecast evaluation.

### Classification

| Gate | Status |
| --- | --- |
| Numerically verified | Yes, with the initial-state timing difference documented above |
| Empirically evaluated | Yes, as a retrospective modern-data refit |
| Reproducible | Yes. Replay matches the stored likelihood and path. A second unchanged update does not insert a run |
| Locally operational | Yes. Manual refresh calls the filter update on local postgres |
| Unattended locally | No. `scripts/register-local-macro-refresh.ps1` prints the monthly command and exits without registering a task |
| Hosted operational | No |
| Publication eligible | No |

`npm run test:research` passed 534 tests. Ruff passed after the likelihood formatter change.
