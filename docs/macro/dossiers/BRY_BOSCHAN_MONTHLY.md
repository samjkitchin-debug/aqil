# Monthly Bry–Boschan turning-point procedure

**Status:** 1971 listing still refused. A labelled Spencer-15 variant is implemented and is not that listing.  
**Role:** engineering-validation pilot. Not the first strategic intelligence capability.  
**Priority:** P0, implementation rank 1.  
**Backlog:** AQ-094 through AQ-100.  
**Last source check:** 25 October 2026, the full NBER volume: front matter `c2145`, foreword `c2146`, chapter 1 `c2147`, chapter 2 `c2148` (58 pages), chapter 3 `c2149` (88 pages), and chapter 4 `c2150` (67 pages).  
**Campaign A classification:** validated labelled variant, local hook only. The 1971 constant still refuses to date. `BRY_BOSCHAN_SPENCER15_VARIANT` dates with constants printed outside the 1971 volume. It is not a FORTRAN replica. On 25 October 2026 `npm run test:research` passed 528 tests and Ruff reported all checks passed. The disposable database was `aqil_research_test`. Database `postgres` was not reset. GitHub Actions has not run.

## 1. Identity and provenance

Gerhard Bry and Charlotte Boschan, *Cyclical Analysis of Time Series: Selected Procedures and Computer Programs*, NBER, 1971. ISBN 0-87014-223-2. Chapter 2, "Programmed Selection of Cyclical Turning Points", chapter URL recorded by NBER as `http://www.nber.org/chapters/c2148`. PDF read: `https://www.nber.org/system/files/chapters/c2148/c2148.pdf`.

The chapter is the programming of the NBER practice in Burns and Mitchell, *Measuring Business Cycles* (1946), which the chapter cites. It is a book chapter, not a later journal replication.

Harding and Pagan, "Dissecting the cycle", *Journal of Monetary Economics*, 2002, DOI `10.1016/S0304-3932(01)00108-8`, is a **quarterly** analogue. Their 1999 Melbourne Institute working paper No. 13/99 describes the quarterly rule and was read. The journal text was not line-checked. Quarterly BBQ is documented in section 3 as a different method. It is not this pilot.

## 2. Original economic purpose

The chapter dates specific-cycle peaks and troughs in a single seasonally adjusted series so that expansions and contractions can be measured with less discretion than a freehand reading. It is classificatory and descriptive. It does not estimate a probability, a forecast, or a causal effect. It does not define the NBER reference cycle. The reference cycle is an external chronology produced by the NBER's committee procedures.

## 3. Mathematical specification

The procedure below is taken from chapter 2, `https://www.nber.org/system/files/chapters/c2148/c2148.pdf` (58 pages). The same search on 25 October 2026 covered the rest of the volume at `https://www.nber.org/books-and-chapters/cyclical-analysis-time-series-selected-procedures-and-computer-programs`: front matter `https://www.nber.org/system/files/chapters/c2145/c2145.pdf`, foreword `https://www.nber.org/system/files/chapters/c2146/c2146.pdf`, chapter 1 `https://www.nber.org/system/files/chapters/c2147/c2147.pdf`, chapter 3 `https://www.nber.org/system/files/chapters/c2149/c2149.pdf` (88 pages), and chapter 4 `https://www.nber.org/system/files/chapters/c2150/c2150.pdf` (67 pages). The contents list four chapters. Each appendix is a sample run. There is no program-listing chapter. Sequential files `c2151` to `c2162` are Ilse Mintz, *Dating Postwar Business Cycles* (1969), not this volume. The foreword, book page xiii, says the computer programs are mimeographed supplements available on request, and chapter 1, book page 4, tells users to ask for those descriptions. No FORTRAN listing was found. Chapter 3, book page 79, names a Spencer or Henderson curve as an example of a weighted long-term moving average and prints no coefficients. Where chapter 2 prose and Table 1 disagree, Table 1 is the programmed procedure. A constant that the volume does not print is not supplied from later software.

The procedure looks for swings of business-cycle length: longer than fifteen months and shorter than twelve years from trough to trough or peak to peak. The worked example is seasonally adjusted bituminous-coal production.

Steps stated in the chapter:

1. Extreme values are identified against a preliminary unadjusted Spencer curve. The exclusion criterion stated for that example is 3.5 standard deviations of the ratios to that curve. Extremes are replaced by the Spencer-curve value for later smoothed curves. The chapter says an extreme can still be chosen as a final turning point.
2. On the twelve-month moving average of the extreme-adjusted series, a tentative peak is a month higher than the five months on either side. A tentative trough is lower than the five months on either side. Contiguous like turns are reduced by keeping the highest peak, or the latest if equal, and the analogous rule for troughs.
3. Spencer-curve turns are the highest or lowest point within five months of those twelve-month-average turns. Like turns must be at least fifteen months apart. Alternation is enforced. Turns within six months of the ends of the series are rejected. If a twelve-month-average contraction is shorter than ten months, overlapping searches that would invert the order of the Spencer peak and trough cause both turns to be dropped.
4. A short moving average, the MCD curve, is searched within five months of the Spencer turns. MCD is months for cyclical dominance, confined to a three-to-six-month smoother: three months when MCD is one or two, six months when MCD is seven or more. The same duration, endpoint, and crossover tests apply.
5. Final turns are the highest or lowest unsmoothed observations within a span of plus or minus MCD months, or four months, whichever is longer, around the MCD turns. Turns closer than six months to the ends are rejected. The first and last peak or trough must be at least as extreme as any value between it and the end of the series.
6. Full cycles, peak to peak and trough to trough, must last at least fifteen months. Phases must last at least five months. The chapter says the five-month phase rule was not part of standard NBER practice and was added because strikes could be smoothed into false cycles. It also says the rule could be changed if experience showed it was inadequate. The program listing is not in the chapter PDF, so the five-month prose rule stands and was not replaced.

Harding–Pagan quarterly BBQ, from the 1999 working paper: a local peak relative to two quarters on either side, then censoring of phase and cycle length. That paper discusses a four- or five-quarter minimum cycle in its empirical section. Software defaults of a five-quarter cycle and a two-quarter phase appear in later code documentation and were **not** treated as the journal's specification. Do not run that quarterly rule on monthly G.17. Do not "adapt" it by setting the window to five months and calling the result Bry–Boschan. The monthly procedure's smoothing sequence is part of the method. Quarterly BBQ is not a parameter of `BRY_BOSCHAN_MONTHLY_1971`.

### Frozen card, `BRY_BOSCHAN_MONTHLY_1971`

Read from the chapter PDF on 25 October 2026. The same constants are in `workers/research/src/aqil_research/methods/bry_boschan_monthly.py`. `publication_allowed` is false. The method is not registered, because dating is refused.

| Constant | What the chapter prints | Decision |
| --- | --- | --- |
| Spencer fifteen-point weights | Chapter 2 footnote 7, book page 19, calls it a weighted moving average with the highest weights in the centre and negative weights at the ends. Book page 56 calls it a graduated 15-point weight pattern. No coefficient and no divisor are printed in any chapter. A search for the 15-term sequence found none. | Blocker. Not copied from any other program. |
| Program listing | Absent from the volume. The chapter 2 appendix is Output Tables for bituminous coal, including the printed control limit 3.500. The foreword places the listings in mimeographed supplements. | Prose and Table 1 govern. They cannot supply the missing weights. |
| Outlier rule | Ratios to the preliminary unadjusted Spencer curve A. Control limit 3.5 standard deviations of those ratios, printed as 3.500. The coal output records a mean ratio of 99.99 and a standard deviation of 7.853. Extremes are replaced by the Spencer A value on later smoothed curves. An extreme may still be a final turn. | Frozen as 3.5. The replacement value still depends on the missing weights. |
| Twelve-month moving-average alignment | No chapter says centred, trailing, or a two-by-twelve average, and none says which month receives an even-length average. Output Table 2-3, book page 61, is headed 12 months moving average and does not name the receiving month. | Blocker. The sample table was not used to infer an alignment. |
| Spencer alignment | Highest weights in the centre, so the filter is centred once the weights exist. | Not usable without the coefficients. |
| Windows of five months | A twelve-month-average peak is higher than the five months on either side, and a trough is lower. Spencer and MCD turns are the highest or lowest value within plus or minus five months of the previous curve's like turn. | Frozen. |
| MCD span | The smoother is three to six months: three when measured MCD is one or two, six when measured MCD is seven or more. The coal example is four. Footnote 11 defines MCD as the span at which the average irregular change becomes smaller than the average trend-cycle change, and cites Shiskin (1960). The chapter does not specify that decomposition. | The three-to-six cap is frozen. The measurement formula is not operational from this chapter. |
| Final neighbourhood | Plus or minus the MCD term, or four months, whichever is longer, on the unsmoothed series. | Frozen as a rule. It cannot be applied until MCD is measured. |
| Cycle length | Table 1 censors full cycles shorter than fifteen months. The principles section also says swings shorter than twelve years. Table 1 does not contain that ceiling. | Chosen reference: Table 1. The twelve-year sentence is not added as a silent extra censor. |
| Phase length | Five months. Added by the program; not standard NBER practice. | Frozen at five months. |
| Endpoint ban | Table 1 drops turns within six months of either end of the unsmoothed series. The Spencer section also refuses a turn within six months of the end, and the coal run reports a first turn too near the beginning. | Frozen at six months. |
| Tie break | Contiguous twelve-month-average peaks: keep the highest, and the latest if the values are equal. The analogous rule applies to troughs. | Frozen. |
| Alternation | Enforced. A like turn dropped for the fifteen-month rule requires an opposite turn to be dropped as well. | Frozen as an order: reduce contiguous like turns on the twelve-month average first; on the Spencer curve, drop the lower peak or the higher trough, then restore alternation. |
| Crossover | A twelve-month-average contraction shorter than ten months can make the Spencer searches overlap. If that would put the trough before the peak, both turns are dropped. The MCD step repeats the duration, endpoint, and crossover tests. | Frozen. |
| Quarterly Harding–Pagan BBQ | Not in chapter 2. | Not a parameter. |

`date_specific_cycles` still raises `BryBoschanSpecificationBlocked` for `BRY_BOSCHAN_MONTHLY_1971` and returns no dates. The 1971 volume was not treated as the source of the weights.

### Labelled variant, `BRY_BOSCHAN_SPENCER15_VARIANT`

The 1971 footnote 7 does not cite a work. There is no bibliography entry for the Spencer curve in chapters c2145 to c2150. The coefficients used by the variant are printed by Frederick R. Macaulay, *The Smoothing of Time Series* (NBER, 1931), book page 55 (`https://www.nber.org/system/files/chapters/c9363/c9363.pdf`): -3, -6, -5, +3, +21, +46, +67, +74, +67, +46, +21, +3, -5, -6, -3, all over 320. The centre weight is dated at month t.

The twelve-month placement is printed by Takeshi Otsu, "Robust Statistics and Business Cycle Dating", Seijo University Economic Papers, no. 228, March 2020, in the section on the Bry-Boschan procedure (`https://www.seijo.ac.jp/education/faeco/academic-journals/jtmo420000001iji-att/228-3otsu.pdf`). The filter dated at month t uses six lags and five leads, so the window is t-6 through t+5. Otsu says this follows the FORTRAN rather than the 1971 prose. Harding-Pagan quarterly BBQ is not used.

Months for cyclical dominance compare mean absolute differences, which is the difference option Otsu names, and are then confined to three through six months as chapter 2 prints. Even spans use the same one-extra-lag split. `publication_allowed` stays false. One local run on stored G.17 is `8fb20325-414f-401b-8c46-bda82ed94e16`: 18 peaks and 19 troughs, MCD 3. A six-month NBER window contained 30 of those 37 dates. That overlap did not change any window. Runs stored from 30 October 2026 are labelled retrospective_full_sample. The Spencer smoother is centred, so the dates are not a contemporaneous recession call. Revision sensitivity is blocked because the stored file is latest_revised. Section 17 records the comparison with run 8fb20325-414f-401b-8c46-bda82ed94e16.

## 4. Input data

One seasonally adjusted monthly series. The pilot series is `fed.g17.IP.B50001.S`, Federal Reserve G.17 total industrial production index. A read-only recount on local `postgres` on 25 October 2026, after the specification stop and before any dating code, found 1,293 rows. All 1,293 are `latest_revised`, `live`, monthly, seasonally adjusted, unit `index_2017_100`, and numerically finite. There were 0 fixture rows, 0 replay rows, 0 duplicate months, and 0 missing months from 1919-01-01 to 2026-09-01. The hosted project was not queried. This is not a GitHub Actions result.

The chapter assumes seasonal adjustment has already been done. Aqil must not seasonally adjust this index again. Missing months fail the run. The series is revised data, not a vintage panel. No transformation to growth rates is part of the classical procedure described in the chapter. Growth-cycle dating, which the book also discusses, is out of scope.

## 5. Outputs

Dated peaks and troughs on the original monthly index, plus the phase and cycle lengths implied by those dates. No probability, no index level, and no statement that the US economy is in recession. A specific cycle in industrial production is not the NBER reference cycle.

## 6. Estimation

Rule-based. No estimated parameters. The MCD span is a property of the series under the chapter's definition, not a fitted regression coefficient. Re-estimation does not apply. A code or constant change is a new implementation version.

## 7. Institutional implementations

The NBER used programmed selection as a check on its own dating of specific cycles. The chapter compares program dates with Burns–Mitchell dates for a *Business Cycle Developments* sample and reports discrepancies, including a 1934 coal-production episode. Later quarterly practice is Harding–Pagan, not a monthly redefinition. Public code exists that claims to implement Bry–Boschan. It is not an authority until AQ-094 shows it matches the chapter. It may be used as an independent numerical reference only after that check.

## 8. Empirical validation

The chapter's own check is agreement with previously selected NBER specific-cycle dates on 51 indicators, with stated discrepancies. That is a diagnostic of the procedure against an earlier judgement, not a proof of investment value. The sample is biased toward series that already had recognisable cycles. The chapter says so.

Aqil's historical check is the same kind of diagnostic against the NBER **reference** chronology, which is a different object from specific-cycle dates. Disagreement is expected and is not a failure.

## 9. Failure modes

Smoothing can move or invent short contractions, as the chapter's 1934 coal example shows. Extreme values and strikes can become turning points. Endpoint rules leave the latest months undated. A revised industrial-production history can move past dates. The procedure has no sampling error of the regression kind, but the censoring constants are judgement. Applying quarterly BBQ windows to monthly data would date a different object. Latest-revised data are not what an analyst would have seen in real time.

## 10. Aqil applicability

The pilot proves the engineering lifecycle on a long series Aqil already holds. It does not answer whether the US economy is currently in a reference-cycle recession. Later factor and nowcast models can use these specific-cycle dates only as a labelled retrospective diagnostic, not as a training label known in real time.

## 11. Data readiness

Ready for a retrospective pilot. See `docs/macro/DATA_DEPENDENCIES.md`. No acquisition. Rights for G.17 are already operational. Vintages are absent.

## 12. Engineering requirements

Pure Python is the default. No numerical library was added. Dating is not in the registry. Storage would be one `research.research_runs` row per evaluation once a chapter-complete procedure exists. The worker has no cron and no job queue. No recurring entry point was added, because there is no dating result to refresh.

## 13. Validation plan

Numerical acceptance is a fixture series with known dates produced by the frozen procedure, plus a second implementation or a worked chapter example if the coal-production output tables can be transcribed. It is not an exact match to NBER reference dates.

The NBER chronology is loaded as an external dated list, with the date of the chronology file recorded. The report counts agreements and misses. It does not set a minimum overlap.

Robustness that is in scope after the base procedure passes: the effect of the five-month phase rule, and the effect of dropping the latest six months. Changing those constants is a new version, not a silent tweak.

## 14. Operational acceptance

- **Implemented:** the frozen card's steps pass the fixtures.
- **Historically validated:** the NBER diagnostic has been written and does not pretend to be a real-time test. There is no overlap threshold.
- **Recurring:** a new or revised G.17 month produces a new run or an explicit unchanged result, idempotently.
- **Operational:** monitoring for this run is on, replay matches, and `publication_allowed` is still false. Operational here means the pilot machinery is safe to keep running. It does not mean the dates are a business-cycle call.
- **Suspend** if replay fails, censoring rules are breached, or the input series is incomplete.

## 15. Campaign A classification

Blocked, on the evidence of this session. Commands actually run:

- Read-only SQL on local `postgres` as `research_worker`, `default_transaction_read_only = on`. Result: 1,293 live `latest_revised` G.17 months, 1919-01-01 to 2026-09-01, no gaps, no fixture rows.
- `uv run pytest tests/test_bry_boschan_monthly.py -q` in `workers/research`: 9 passed. The tests cover a contiguous level sample, a gap, a fixture retrieval, a growth-rate representation, a non-level unit, a series that is not seasonally adjusted, a non-finite value, and the refusal to date.
- `uv run ruff check` and `uv run ruff format` on the new module and test: clean after format.

The 1971 refusal stored no dates. The labelled variant later stored local run `8fb20325-414f-401b-8c46-bda82ed94e16`. Replay matched. The NBER comparison is a diagnostic. No cron was added. `publication_allowed` remains false.

## 16. Status and priority

AQ-094 keeps the 1971 refusal and records the labelled variant. The 1971 volume still does not print the Spencer coefficients or the twelve-month alignment. Those two constants are taken from the Macaulay and Otsu pages named above, not from the 1971 book. AQ-095 recount stands. AQ-096 through AQ-100 are implemented on the variant only: the method is registered, run `8fb20325-414f-401b-8c46-bda82ed94e16` is stored on local postgres, replay matched, and the G.17 refresh hook was idempotent on disposable database `aqil_research_test`. Health failures were injected in unit tests. The NBER comparison is not a gate. The strategic milestone remains `STOCK_WATSON_DFM`. AQ-102 now records the 1988 modern refit in the Stock-Watson dossier. This dating note does not change that factor.

### Full research suite, 25 October 2026

`npm run test:research` passed 528 tests in 12.33 seconds, including Ruff. The development database was not reset. This does not change the six-month NBER window and does not make the variant a 1971 replica. Unattended hosted scheduling is still off. The hook runs only when refresh is invoked.

## 17. Spencer-15 validation on 30 October 2026

The production bounds are unchanged: a full cycle of at least fifteen months, a phase of at least five months, and a six-month ban at each end. `date_specific_cycles` still refuses to date. The Spencer-15 weights were not replaced.

The stored chronology class is `retrospective_full_sample`. The Spencer smoother is centred, so these dates are not a contemporaneous recession call. Revision sensitivity is blocked because `fed.g17.IP.B50001.S` is `latest_revised`. No vintage panel was invented.

Local run `8fb20325-414f-401b-8c46-bda82ed94e16` was left in place. It still has 18 peaks, 19 troughs, and MCD 3, with `publication_allowed` false. A new run was appended: `3955f7f4-08f8-4e7b-9ded-b3f6eea6633f`. It has the same 18 peaks, the same 19 troughs, and the same MCD. `publication_allowed` is false. Recomputing the new run matched its stored calculation. Recomputing the earlier run does not match its stored calculation, because the new calculation adds the chronology label, the length-bound diagnostic, the revision block, and the NBER diagnostic. The peak list and the trough list are the same.

The length-bound diagnostic is a separate result. It does not replace the production dates. Not applying the five-month phase rule adds a peak on 1 May 1934 and a trough on 1 September 1934, so that case has 19 peaks and 20 troughs. Not applying the six-month endpoint ban leaves the production dates unchanged on this sample. A six-month NBER window contains 30 of the 37 production dates. That overlap does not gate the method and is not an acceptance test.

This section does not claim operational acceptance or publication. Targeted pytest on 30 October 2026, from `workers/research`, was 29 passed and 1 failed. The failure is `test_refresh_hook_is_idempotent_until_a_month_changes`: the first collect on disposable database `aqil_research_test` returned unchanged because that G.17 package was already stored. The assertion was not changed. `npm run test:research` was not run. Database `postgres` was not reset.
