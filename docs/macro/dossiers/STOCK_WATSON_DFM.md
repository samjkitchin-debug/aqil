# Stock–Watson dynamic factor model

**Status:** research record. Not an implementation.  
**Role:** first substantive economic-intelligence milestone. Not the first code to be written.  
**Priority:** P0, implementation rank 2, intelligence rank 1.  
**Backlog:** AQ-101 records the 1989 coincident contract. AQ-102 stays blocked on rights and on the unfrozen Kalman matrices.  
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
